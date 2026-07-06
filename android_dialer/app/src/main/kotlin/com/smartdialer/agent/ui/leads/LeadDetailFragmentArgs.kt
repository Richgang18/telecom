package com.smartdialer.agent.ui.leads

import android.os.Bundle
import androidx.navigation.NavArgs

/**
 * Args class for LeadDetailFragment.
 * Safe Args normally generates this — this stub keeps the code compilable
 * before the first Gradle sync.
 */
data class LeadDetailFragmentArgs(
    val leadId: String,
    val leadName: String,
    val leadPhone: String,
    val leadEmail: String = "",
    val leadNotes: String = "",
    val leadStatus: String = "new",
) : NavArgs {
    companion object {
        @JvmStatic
        fun fromBundle(bundle: Bundle) = LeadDetailFragmentArgs(
            leadId     = bundle.getString("leadId",     ""),
            leadName   = bundle.getString("leadName",   ""),
            leadPhone  = bundle.getString("leadPhone",  ""),
            leadEmail  = bundle.getString("leadEmail",  ""),
            leadNotes  = bundle.getString("leadNotes",  ""),
            leadStatus = bundle.getString("leadStatus", "new"),
        )
    }
}
