package com.smartdialer.agent.ui.accent

import android.app.Application
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioTrack
import android.media.AudioAttributes
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.net.HttpURLConnection
import java.net.URL
import java.nio.ByteBuffer
import java.nio.ByteOrder

enum class AccentState { IDLE, RECORDING, CONVERTING, PLAYING, ERROR }

class AccentViewModel(app: Application) : AndroidViewModel(app) {

    val state       = MutableLiveData(AccentState.IDLE)
    val transcript  = MutableLiveData<String>()
    val error       = MutableLiveData<String?>()
    val latencyMs   = MutableLiveData<Int>()

    // Cartesia credentials hardcoded — no server needed
    private val CARTESIA_KEY   = "sk_car_tVthKN3ZyTmFYxCuATc5XY"
    private val CARTESIA_VOICE = "710feaa3-b550-42f3-b3eb-6f37f2a7cc0a" // Tyler American male
    private val CARTESIA_MODEL = "sonic-3.5"

    private var speechRecognizer: SpeechRecognizer? = null
    private var tStart: Long = 0L

    fun startRecording() {
        if (state.value == AccentState.RECORDING) return

        if (!SpeechRecognizer.isRecognitionAvailable(getApplication())) {
            error.value = "Speech recognition not available on this device"
            return
        }

        state.value = AccentState.RECORDING
        error.value = null
        transcript.value = ""

        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(getApplication())
        speechRecognizer!!.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {
                state.postValue(AccentState.CONVERTING)
            }
            override fun onError(error: Int) {
                val msg = when (error) {
                    SpeechRecognizer.ERROR_AUDIO            -> "Audio recording error"
                    SpeechRecognizer.ERROR_CLIENT           -> "Client error"
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Need microphone permission"
                    SpeechRecognizer.ERROR_NETWORK          -> "Network error"
                    SpeechRecognizer.ERROR_NETWORK_TIMEOUT  -> "Network timeout"
                    SpeechRecognizer.ERROR_NO_MATCH         -> "No speech detected — try again"
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY  -> "Recognizer busy"
                    SpeechRecognizer.ERROR_SERVER           -> "Server error"
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT   -> "No speech input — tap and speak"
                    else -> "Speech error ($error)"
                }
                state.postValue(AccentState.IDLE)
                // Use postValue for error too
                viewModelScope.launch(Dispatchers.Main) {
                    AccentViewModel@ this@AccentViewModel.error.value = msg
                }
            }
            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull() ?: return
                transcript.postValue(text)
                tStart = System.currentTimeMillis()
                synthesize(text)
            }
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 1000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
        }
        speechRecognizer!!.startListening(intent)
    }

    fun stopRecording() {
        speechRecognizer?.stopListening()
        if (state.value == AccentState.RECORDING) state.value = AccentState.IDLE
    }

    private fun synthesize(text: String) {
        state.value = AccentState.CONVERTING
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val body = """
                    {
                      "transcript": ${escapeJson(text)},
                      "model_id": "$CARTESIA_MODEL",
                      "voice": {"mode": "id", "id": "$CARTESIA_VOICE"},
                      "output_format": {
                        "container": "wav",
                        "encoding": "pcm_f32le",
                        "sample_rate": 24000
                      }
                    }
                """.trimIndent()

                val url = URL("https://api.cartesia.ai/tts/bytes")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("X-API-Key", CARTESIA_KEY)
                conn.setRequestProperty("Cartesia-Version", "2024-06-10")
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true
                conn.connectTimeout = 10000
                conn.readTimeout = 15000
                conn.outputStream.use { it.write(body.toByteArray()) }

                val code = conn.responseCode
                if (code != 200) {
                    val errBody = conn.errorStream?.bufferedReader()?.readText() ?: "HTTP $code"
                    viewModelScope.launch(Dispatchers.Main) {
                        error.value = "Cartesia error: $errBody"
                        state.value = AccentState.IDLE
                    }
                    return@launch
                }

                val wavBytes = conn.inputStream.readBytes()
                conn.disconnect()

                val elapsed = (System.currentTimeMillis() - tStart).toInt()
                viewModelScope.launch(Dispatchers.Main) {
                    latencyMs.value = elapsed
                    state.value = AccentState.PLAYING
                }

                playWav(wavBytes)

                viewModelScope.launch(Dispatchers.Main) {
                    state.value = AccentState.IDLE
                }

            } catch (e: Exception) {
                viewModelScope.launch(Dispatchers.Main) {
                    error.value = "Failed: ${e.message}"
                    state.value = AccentState.IDLE
                }
            }
        }
    }

    private fun playWav(wavBytes: ByteArray) {
        try {
            // WAV header = 44 bytes, rest is PCM float32 LE at 24000Hz
            val pcm = if (wavBytes.size > 44) wavBytes.copyOfRange(44, wavBytes.size) else wavBytes
            val floats = FloatArray(pcm.size / 4)
            ByteBuffer.wrap(pcm).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(floats)

            val sampleRate = 24000
            val minBuf = AudioTrack.getMinBufferSize(
                sampleRate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_FLOAT
            )
            val track = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                        .setSampleRate(sampleRate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(maxOf(minBuf, pcm.size))
                .setTransferMode(AudioTrack.MODE_STATIC)
                .build()

            track.write(floats, 0, floats.size, AudioTrack.WRITE_BLOCKING)
            track.play()
            // Wait for playback to finish
            Thread.sleep((floats.size.toLong() * 1000L / sampleRate) + 300)
            track.stop()
            track.release()
        } catch (e: Exception) {
            viewModelScope.launch(Dispatchers.Main) {
                error.value = "Playback error: ${e.message}"
            }
        }
    }

    private fun escapeJson(s: String): String {
        val sb = StringBuilder("\"")
        for (c in s) {
            when (c) {
                '"'  -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                else -> sb.append(c)
            }
        }
        sb.append("\"")
        return sb.toString()
    }

    override fun onCleared() {
        super.onCleared()
        speechRecognizer?.destroy()
        speechRecognizer = null
    }
}
