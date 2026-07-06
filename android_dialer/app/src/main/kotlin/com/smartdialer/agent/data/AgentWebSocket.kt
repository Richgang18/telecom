package com.smartdialer.agent.data

import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import okhttp3.*

data class WsEvent(val event: String, val payload: Map<String, Any?>)

class AgentWebSocket(private val serverUrl: String, private val agentId: String, private val token: String) {

    private var webSocket: WebSocket? = null
    private val gson = Gson()

    private val _events = MutableSharedFlow<WsEvent>(extraBufferCapacity = 32)
    val events: SharedFlow<WsEvent> = _events

    private val _connected = MutableSharedFlow<Boolean>(replay = 1)
    val connected: SharedFlow<Boolean> = _connected

    fun connect() {
        val wsUrl = serverUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .trimEnd('/')
            .plus("/ws/agent/$agentId?token=$token")

        val request = Request.Builder().url(wsUrl).build()

        webSocket = ApiClient.wsClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                _connected.tryEmit(true)
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    @Suppress("UNCHECKED_CAST")
                    val raw = gson.fromJson(text, Map::class.java) as Map<String, Any?>
                    val event = raw["event"] as? String ?: return
                    _events.tryEmit(WsEvent(event, raw))
                } catch (e: Exception) { /* ignore malformed */ }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                _connected.tryEmit(false)
                // Reconnect after 3s
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({ connect() }, 3000)
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                _connected.tryEmit(false)
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
    }

    fun sendPing() {
        webSocket?.send("""{"event":"ping"}""")
    }
}
