package com.smartdialer.agent.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "session")

class SessionManager(private val context: Context) {

    companion object {
        private val KEY_TOKEN      = stringPreferencesKey("auth_token")
        private val KEY_AGENT_ID   = stringPreferencesKey("agent_id")
        private val KEY_AGENT_NAME = stringPreferencesKey("agent_name")
        private val KEY_SERVER_URL = stringPreferencesKey("server_url")
    }

    val token:      Flow<String?> = context.dataStore.data.map { it[KEY_TOKEN] }
    val agentId:    Flow<String?> = context.dataStore.data.map { it[KEY_AGENT_ID] }
    val agentName:  Flow<String?> = context.dataStore.data.map { it[KEY_AGENT_NAME] }
    val serverUrl:  Flow<String?> = context.dataStore.data.map { it[KEY_SERVER_URL] }

    suspend fun saveSession(
        token: String, agentId: String, agentName: String, serverUrl: String
    ) {
        context.dataStore.edit { prefs ->
            prefs[KEY_TOKEN]      = token
            prefs[KEY_AGENT_ID]   = agentId
            prefs[KEY_AGENT_NAME] = agentName
            prefs[KEY_SERVER_URL] = serverUrl
        }
        ApiClient.configure(serverUrl, token)
    }

    suspend fun clearSession() {
        context.dataStore.edit { it.clear() }
        ApiClient.setToken("")
    }

    /** Suspend until the token value is available (first emission). */
    suspend fun getToken(): String?     = token.firstOrNull()
    suspend fun getAgentId(): String?   = agentId.firstOrNull()
    suspend fun getServerUrl(): String? = serverUrl.firstOrNull()
}
