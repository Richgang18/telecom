package com.smartdialer.agent.ui.call

import android.app.Application
import androidx.lifecycle.*
import com.smartdialer.agent.data.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

enum class CallState { IDLE, INITIATING, RINGING, CONNECTED, ENDED, FAILED }

data class ActiveCallInfo(
    val callSid: String,
    val leadName: String,
    val leadPhone: String,
    val leadId: String,
    val startedAt: Long = System.currentTimeMillis(),
)

class ActiveCallViewModel(app: Application) : AndroidViewModel(app) {

    val callState    = MutableLiveData(CallState.IDLE)
    val activeCall   = MutableLiveData<ActiveCallInfo?>(null)
    val callDuration = MutableLiveData(0)
    val recordingUrl = MutableLiveData<String?>(null)
    val error        = MutableLiveData<String?>(null)
    val transferDone = MutableLiveData(false)
    val agents       = MutableLiveData<List<Map<String, Any>>>(emptyList())

    private var durationJob: kotlinx.coroutines.Job? = null

    fun onCallInitiated(callSid: String, leadName: String, leadPhone: String, leadId: String) {
        callState.value  = CallState.RINGING
        activeCall.value = ActiveCallInfo(callSid, leadName, leadPhone, leadId)
        callDuration.value = 0
    }

    fun onCallAnswered() {
        callState.value = CallState.CONNECTED
        startTimer()
    }

    fun onCallEnded(duration: Int = 0) {
        callState.value    = CallState.ENDED
        callDuration.value = duration
        durationJob?.cancel()
    }

    fun onRecordingReady(url: String) {
        recordingUrl.value = url
    }

    fun hangup() {
        val sid = activeCall.value?.callSid ?: return
        viewModelScope.launch {
            try {
                ApiClient.service.hangup(sid)
            } catch (e: Exception) {
                error.value = "Hangup failed: ${e.message}"
            }
        }
    }

    fun transfer(targetAgentId: String) {
        val sid = activeCall.value?.callSid ?: return
        viewModelScope.launch {
            try {
                val r = ApiClient.service.transfer(sid, TransferRequest(targetAgentId))
                if (r.isSuccessful) {
                    transferDone.value = true
                    durationJob?.cancel()
                    callState.value = CallState.ENDED
                } else {
                    error.value = "Transfer failed: ${r.code()}"
                }
            } catch (e: Exception) {
                error.value = "Transfer error: ${e.message}"
            }
        }
    }

    fun loadAgents() {
        viewModelScope.launch {
            try {
                val r = ApiClient.service.getAgents()
                if (r.isSuccessful) {
                    @Suppress("UNCHECKED_CAST")
                    val list = (r.body()?.get("agents") as? List<Map<String, Any>>) ?: emptyList()
                    agents.value = list
                }
            } catch (e: Exception) { /* ignore */ }
        }
    }

    private fun startTimer() {
        durationJob?.cancel()
        durationJob = viewModelScope.launch {
            while (true) {
                delay(1000)
                callDuration.value = (callDuration.value ?: 0) + 1
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        durationJob?.cancel()
    }
}
