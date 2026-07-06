package com.smartdialer.agent.ui.leads

import android.app.Application
import androidx.lifecycle.*
import com.smartdialer.agent.data.*
import kotlinx.coroutines.launch

class LeadsViewModel(app: Application) : AndroidViewModel(app) {

    val leads      = MutableLiveData<List<Lead>>(emptyList())
    val total      = MutableLiveData(0)
    val loading    = MutableLiveData(false)
    val error      = MutableLiveData<String?>(null)
    val dialResult = MutableLiveData<Result<DialResponse>>()

    private var currentSearch  = ""
    private var currentFilter  = ""
    private var currentPage    = 1

    fun loadLeads(search: String = "", statusFilter: String = "", page: Int = 1) {
        currentSearch = search
        currentFilter = statusFilter
        currentPage   = page
        loading.value = true
        error.value   = null
        viewModelScope.launch {
            try {
                val r = ApiClient.service.getLeads(search, statusFilter, page)
                if (r.isSuccessful) {
                    val body = r.body()!!
                    leads.value = if (page == 1) body.leads else (leads.value ?: emptyList()) + body.leads
                    total.value = body.total
                } else {
                    error.value = "Failed to load leads (${r.code()})"
                }
            } catch (e: Exception) {
                error.value = "Network error: ${e.message}"
            } finally {
                loading.value = false
            }
        }
    }

    fun loadMore() {
        if ((leads.value?.size ?: 0) < (total.value ?: 0)) {
            loadLeads(currentSearch, currentFilter, currentPage + 1)
        }
    }

    fun dial(lead: Lead) {
        viewModelScope.launch {
            try {
                val r = ApiClient.service.dial(DialRequest(lead.id, lead.phone, lead.name))
                if (r.isSuccessful) {
                    dialResult.value = Result.success(r.body()!!)
                } else {
                    dialResult.value = Result.failure(Exception("Dial failed: ${r.code()} ${r.errorBody()?.string()}"))
                }
            } catch (e: Exception) {
                dialResult.value = Result.failure(e)
            }
        }
    }

    fun updateLeadStatus(leadId: String, status: String, notes: String = "") {
        viewModelScope.launch {
            try {
                ApiClient.service.updateLead(leadId, LeadUpdateRequest(status, notes))
                // Refresh current page
                loadLeads(currentSearch, currentFilter, 1)
            } catch (e: Exception) {
                error.value = "Update failed: ${e.message}"
            }
        }
    }
}
