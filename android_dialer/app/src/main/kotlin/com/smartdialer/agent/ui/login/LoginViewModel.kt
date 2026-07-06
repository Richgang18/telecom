package com.smartdialer.agent.ui.login

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.smartdialer.agent.data.ApiClient
import com.smartdialer.agent.data.LoginRequest
import com.smartdialer.agent.data.SessionManager
import kotlinx.coroutines.launch

sealed class LoginState {
    object Idle : LoginState()
    object Loading : LoginState()
    data class Success(val agentId: String, val agentName: String) : LoginState()
    data class Error(val message: String) : LoginState()
}

class LoginViewModel(app: Application) : AndroidViewModel(app) {

    val state = MutableLiveData<LoginState>(LoginState.Idle)
    private val session = SessionManager(app)

    fun login(serverUrl: String, agentId: String, password: String) {
        state.value = LoginState.Loading
        viewModelScope.launch {
            try {
                // Configure client with server URL (no token yet)
                ApiClient.configure(serverUrl, "")
                val response = ApiClient.service.login(LoginRequest(agentId, password))
                if (response.isSuccessful) {
                    val body = response.body()!!
                    session.saveSession(
                        token      = body.token,
                        agentId    = body.agent.id,
                        agentName  = body.agent.name,
                        serverUrl  = serverUrl,
                    )
                    state.value = LoginState.Success(body.agent.id, body.agent.name)
                } else {
                    state.value = LoginState.Error("Invalid credentials (${response.code()})")
                }
            } catch (e: Exception) {
                state.value = LoginState.Error("Cannot reach server: ${e.message}")
            }
        }
    }
}
