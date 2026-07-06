package com.smartdialer.agent.ui.leads

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.smartdialer.agent.data.Lead
import com.smartdialer.agent.databinding.ItemLeadBinding

class LeadsAdapter(
    private val onDial: (Lead) -> Unit,
    private val onView: (Lead) -> Unit,
) : ListAdapter<Lead, LeadsAdapter.LeadViewHolder>(DIFF) {

    inner class LeadViewHolder(val binding: ItemLeadBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(lead: Lead) {
            binding.tvName.text  = lead.name
            binding.tvPhone.text = lead.phone
            binding.tvStatus.text = lead.status.uppercase()

            val statusColor = when (lead.status) {
                "new"      -> 0xFF0984E3.toInt()
                "callback" -> 0xFFFDCB6E.toInt()
                "done"     -> 0xFF00B894.toInt()
                "dnc"      -> 0xFFD63031.toInt()
                else       -> 0xFF636E72.toInt()
            }
            binding.tvStatus.setTextColor(statusColor)

            binding.btnCall.setOnClickListener { onDial(lead) }
            binding.root.setOnClickListener { onView(lead) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        LeadViewHolder(ItemLeadBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: LeadViewHolder, position: Int) =
        holder.bind(getItem(position))

    companion object {
        val DIFF = object : DiffUtil.ItemCallback<Lead>() {
            override fun areItemsTheSame(a: Lead, b: Lead) = a.id == b.id
            override fun areContentsTheSame(a: Lead, b: Lead) = a == b
        }
    }
}
