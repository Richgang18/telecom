package com.smartdialer.agent.ui.leads

import androidx.navigation.NavDirections
import com.smartdialer.agent.R

/**
 * Navigation directions for LeadsFragment.
 * Safe Args normally generates this — this stub keeps the code compilable
 * before the first Gradle sync.
 */
object LeadsFragmentDirections {
    fun actionLeadsToDetail(
        leadId: String,
        leadName: String,
        leadPhone: String,
        leadEmail: String = "",
        leadNotes: String = "",
        leadStatus: String = "new",
    ): NavDirections = object : NavDirections {
        override val actionId = R.id.action_leads_to_detail
        override val arguments = android.os.Bundle().apply {
            putString("leadId",     leadId)
            putString("leadName",   leadName)
            putString("leadPhone",  leadPhone)
            putString("leadEmail",  leadEmail)
            putString("leadNotes",  leadNotes)
            putString("leadStatus", leadStatus)
        }
    }
}
