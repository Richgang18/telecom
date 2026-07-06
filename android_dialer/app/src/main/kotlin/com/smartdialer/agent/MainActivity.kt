package com.smartdialer.agent

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import com.smartdialer.agent.data.AgentWebSocket
import com.smartdialer.agent.data.ApiClient
import com.smartdialer.agent.data.SessionManager
import com.smartdialer.agent.data.WsEvent
import com.smartdialer.agent.ui.call.ActiveCallViewModel
import com.smartdialer.agent.ui.call.CallState
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var navController: NavController
    lateinit var callViewModel: ActiveCallViewModel
    private var webSocket: AgentWebSocket? = null
    private val session by lazy { SessionManager(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val navHost = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        navController = navHost.navController

        callViewModel = ViewModelProvider(this)[ActiveCallViewModel::class.java]

        // Restore session on launch
        lifecycleScope.launch {
            val token     = session.getToken()
            val agentId   = session.getAgentId()
            val serverUrl = session.getServerUrl()

            if (!token.isNullOrEmpty() && !agentId.isNullOrEmpty() && !serverUrl.isNullOrEmpty()) {
                ApiClient.configure(serverUrl, token)
                connectWebSocket(serverUrl, agentId, token)
                // Only navigate away from login if we're still on it
                if (navController.currentDestination?.id == R.id.loginFragment) {
                    navController.navigate(R.id.action_login_to_leads)
                }
            }
        }
    }

    fun connectWebSocket(serverUrl: String, agentId: String, token: String) {
        webSocket?.disconnect()
        webSocket = AgentWebSocket(serverUrl, agentId, token)
        webSocket!!.connect()
        lifecycleScope.launch {
            webSocket!!.events.collectLatest { event -> handleWsEvent(event) }
        }
    }

    private fun handleWsEvent(event: WsEvent) {
        Log.d("WS", "Event: ${event.event}")
        when (event.event) {
            "call_initiated" -> {
                val sid   = event.payload["call_sid"]   as? String ?: return
                val name  = event.payload["lead_name"]  as? String ?: "Unknown"
                val phone = event.payload["lead_phone"] as? String ?: ""
                val id    = event.payload["lead_id"]    as? String ?: ""
                callViewModel.onCallInitiated(sid, name, phone, id)
                runOnUiThread {
                    if (navController.currentDestination?.id != R.id.activeCallFragment) {
                        navController.navigate(R.id.activeCallFragment)
                    }
                }
            }
            "call_answered", "call_status" -> {
                val status = event.payload["status"] as? String ?: event.event
                when (status) {
                    "answered", "in-progress" -> callViewModel.onCallAnswered()
                    "completed", "failed", "busy", "no-answer", "canceled" -> {
                        val duration = (event.payload["duration"] as? Double)?.toInt() ?: 0
                        callViewModel.onCallEnded(duration)
                    }
                }
            }
            "recording_ready" -> {
                val url = event.payload["recording_url"] as? String ?: return
                callViewModel.onRecordingReady(url)
            }
            "call_ended" -> {
                val duration = (event.payload["duration"] as? Double)?.toInt() ?: 0
                callViewModel.onCallEnded(duration)
            }
            "call_transferred" -> {
                callViewModel.onCallEnded(0)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        webSocket?.disconnect()
    }
}
