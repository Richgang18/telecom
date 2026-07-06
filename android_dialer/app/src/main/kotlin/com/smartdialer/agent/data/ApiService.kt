package com.smartdialer.agent.data

import retrofit2.Response
import retrofit2.http.*

// ── Auth ─────────────────────────────────────────────────────────────────────
data class LoginRequest(val agent_id: String, val password: String)
data class AgentInfo(val id: String, val name: String)
data class LoginResponse(val token: String, val agent: AgentInfo)

// ── Leads ─────────────────────────────────────────────────────────────────────
data class Lead(
    val id: String,
    val name: String,
    val phone: String,
    val email: String = "",
    val notes: String = "",
    val status: String = "new"
)
data class LeadsResponse(val leads: List<Lead>, val total: Int, val page: Int)
data class LeadUpdateRequest(val status: String, val notes: String = "")

// ── Calls ─────────────────────────────────────────────────────────────────────
data class DialRequest(val lead_id: String, val lead_phone: String, val lead_name: String)
data class DialResponse(val ok: Boolean, val call_sid: String)
data class TransferRequest(val target_agent_id: String)
data class CallRecord(
    val call_sid: String,
    val agent_id: String,
    val lead_id: String,
    val lead_phone: String,
    val lead_name: String,
    val started_at: String,
    val ended_at: String?,
    val status: String,
    val duration: Int,
    val recording_url: String?
)
data class CallHistoryResponse(val calls: List<CallRecord>, val total: Int)

interface ApiService {
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("api/auth/me")
    suspend fun me(): Response<AgentInfo>

    @GET("api/leads")
    suspend fun getLeads(
        @Query("search") search: String = "",
        @Query("status_filter") statusFilter: String = "",
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50
    ): Response<LeadsResponse>

    @GET("api/leads/{id}")
    suspend fun getLead(@Path("id") id: String): Response<Lead>

    @PATCH("api/leads/{id}")
    suspend fun updateLead(@Path("id") id: String, @Body body: LeadUpdateRequest): Response<Map<String, Any>>

    @POST("api/calls/dial")
    suspend fun dial(@Body request: DialRequest): Response<DialResponse>

    @POST("api/calls/{callSid}/hangup")
    suspend fun hangup(@Path("callSid") callSid: String): Response<Map<String, Any>>

    @POST("api/calls/{callSid}/transfer")
    suspend fun transfer(
        @Path("callSid") callSid: String,
        @Body request: TransferRequest
    ): Response<Map<String, Any>>

    @GET("api/calls/history")
    suspend fun callHistory(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50
    ): Response<CallHistoryResponse>

    @GET("api/agents")
    suspend fun getAgents(): Response<Map<String, Any>>

    @GET("api/ping")
    suspend fun ping(): Response<Map<String, Any>>
}
