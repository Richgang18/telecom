package com.smartdialer.agent.ui.accent

import android.app.Application
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import okhttp3.*
import okio.ByteString
import java.nio.ByteBuffer
import java.nio.ByteOrder

enum class AccentState { IDLE, RECORDING, CONVERTING, PLAYING }

class AccentViewModel(app: Application) : AndroidViewModel(app) {

    val state       = MutableLiveData(AccentState.IDLE)
    val transcript  = MutableLiveData<String>()
    val error       = MutableLiveData<String?>()
    val latencyMs   = MutableLiveData<Int>()

    private var serverUrl: String = ""
    private val CARTESIA_KEY  = "sk_car_tVthKN3ZyTmFYxCuATc5XY"
    private val CARTESIA_VOICE = "710feaa3-b550-42f3-b3eb-6f37f2a7cc0a" // Tyler - American male
    private val CARTESIA_MODEL = "sonic-3.5"
    private var wsSession: WebSocket? = null
    private var audioRecord: AudioRecord? = null
    private var recordJob: Job? = null
    private var tStart: Long = 0L

    fun configure(url: String) {
        serverUrl = url.trimEnd('/')
    }

    fun startRecording() {
        if (state.value == AccentState.RECORDING) return
        state.value = AccentState.RECORDING
        error.value = null

        // Connect to accent demo WebSocket on port 8080
        val wsUrl = serverUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .let {
                // Replace port 5001 with 8080 for demo server
                if (it.contains(":5001")) it.replace(":5001", ":8080")
                else it.trimEnd('/').plus(":8080").replace("8080:8080", "8080")
            } + "/stream"

        val request = Request.Builder().url(wsUrl).build()
        val client  = OkHttpClient()

        wsSession = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                startAudioCapture(ws)
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val json = org.json.JSONObject(text)
                    if (json.getString("type") == "transcript") {
                        val t = json.getString("text")
                        viewModelScope.launch(Dispatchers.Main) {
                            transcript.value = t
                            tStart = System.currentTimeMillis()
                            state.value = AccentState.CONVERTING
                        }
                    }
                } catch (e: Exception) { /* ignore */ }
            }

            override fun onMessage(ws: WebSocket, bytes: ByteString) {
                val elapsed = (System.currentTimeMillis() - tStart).toInt()
                viewModelScope.launch(Dispatchers.Main) {
                    latencyMs.value = elapsed
                    state.value = AccentState.PLAYING
                }
                playAudio(bytes.toByteArray())
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                viewModelScope.launch(Dispatchers.Main) {
                    error.value = "Connection failed: ${t.message}"
                    state.value = AccentState.IDLE
                }
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                viewModelScope.launch(Dispatchers.Main) {
                    if (state.value != AccentState.PLAYING) state.value = AccentState.IDLE
                }
            }
        })
    }

    fun stopRecording() {
        recordJob?.cancel()
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
        wsSession?.send("""{"type":"stop"}""")
        wsSession?.close(1000, "Done")
        wsSession = null
        state.value = AccentState.IDLE
    }

    private fun startAudioCapture(ws: WebSocket) {
        val sampleRate  = 16000
        val bufferSize  = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ) * 2

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )
        audioRecord!!.startRecording()

        recordJob = viewModelScope.launch(Dispatchers.IO) {
            val buf = ByteArray(4096)
            while (state.value == AccentState.RECORDING) {
                val read = audioRecord?.read(buf, 0, buf.size) ?: break
                if (read > 0) {
                    ws.send(ByteString.of(*buf.copyOf(read)))
                }
            }
        }
    }

    private fun playAudio(wavBytes: ByteArray) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // WAV header is 44 bytes — skip to PCM data
                val pcmData = if (wavBytes.size > 44) wavBytes.copyOfRange(44, wavBytes.size) else wavBytes
                val sampleRate = 24000
                val bufSize = android.media.AudioTrack.getMinBufferSize(
                    sampleRate,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_FLOAT
                )
                val track = android.media.AudioTrack.Builder()
                    .setAudioAttributes(
                        android.media.AudioAttributes.Builder()
                            .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                            .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                            .setSampleRate(sampleRate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setBufferSizeInBytes(maxOf(bufSize, pcmData.size))
                    .setTransferMode(android.media.AudioTrack.MODE_STATIC)
                    .build()

                // Convert bytes to float array
                val floatBuf = FloatArray(pcmData.size / 4)
                ByteBuffer.wrap(pcmData).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(floatBuf)

                track.write(floatBuf, 0, floatBuf.size, android.media.AudioTrack.WRITE_BLOCKING)
                track.play()
                Thread.sleep((floatBuf.size.toLong() * 1000L) / sampleRate + 200)
                track.stop()
                track.release()

                viewModelScope.launch(Dispatchers.Main) {
                    state.value = AccentState.IDLE
                }
            } catch (e: Exception) {
                viewModelScope.launch(Dispatchers.Main) {
                    error.value = "Playback error: ${e.message}"
                    state.value = AccentState.IDLE
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        stopRecording()
    }
}
