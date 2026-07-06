package com.smartdialer.agent.ui.leads

import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.appcompat.widget.SearchView
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.smartdialer.agent.MainActivity
import com.smartdialer.agent.R
import com.smartdialer.agent.data.Lead
import com.smartdialer.agent.databinding.FragmentLeadsBinding
import com.smartdialer.agent.ui.call.CallState

class LeadsFragment : Fragment() {

    private var _binding: FragmentLeadsBinding? = null
    private val binding get() = _binding!!
    private val viewModel: LeadsViewModel by viewModels()
    private lateinit var adapter: LeadsAdapter

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentLeadsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = LeadsAdapter(
            onDial = { lead -> viewModel.dial(lead) },
            onView = { lead -> navigateToDetail(lead) },
        )

        binding.recyclerLeads.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerLeads.adapter = adapter

        binding.swipeRefresh.setOnRefreshListener {
            viewModel.loadLeads()
        }

        // Search
        binding.searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                viewModel.loadLeads(search = query ?: "")
                return true
            }
            override fun onQueryTextChange(newText: String?): Boolean {
                if (newText.isNullOrEmpty()) viewModel.loadLeads()
                return false
            }
        })

        // Filter chips
        binding.chipAll.setOnClickListener { viewModel.loadLeads(statusFilter = "") }
        binding.chipNew.setOnClickListener { viewModel.loadLeads(statusFilter = "new") }
        binding.chipCallback.setOnClickListener { viewModel.loadLeads(statusFilter = "callback") }
        binding.chipDone.setOnClickListener { viewModel.loadLeads(statusFilter = "done") }

        // Observe
        viewModel.leads.observe(viewLifecycleOwner) { leads ->
            adapter.submitList(leads)
            binding.tvCount.text = "${viewModel.total.value ?: 0} leads"
        }

        viewModel.loading.observe(viewLifecycleOwner) { loading ->
            binding.swipeRefresh.isRefreshing = loading
        }

        viewModel.error.observe(viewLifecycleOwner) { err ->
            if (err != null) Toast.makeText(requireContext(), err, Toast.LENGTH_LONG).show()
        }

        viewModel.dialResult.observe(viewLifecycleOwner) { result ->
            result.onSuccess { resp ->
                Toast.makeText(requireContext(), "Dialing...", Toast.LENGTH_SHORT).show()
            }.onFailure { err ->
                Toast.makeText(requireContext(), "Dial failed: ${err.message}", Toast.LENGTH_LONG).show()
            }
        }

        // If a call is active, show the call screen
        (activity as? MainActivity)?.callViewModel?.callState?.observe(viewLifecycleOwner) { state ->
            if (state == CallState.RINGING || state == CallState.CONNECTED) {
                findNavController().navigate(R.id.activeCallFragment)
            }
        }

        viewModel.loadLeads()
    }

    private fun navigateToDetail(lead: Lead) {
        val bundle = android.os.Bundle().apply {
            putString("leadId",     lead.id)
            putString("leadName",   lead.name)
            putString("leadPhone",  lead.phone)
            putString("leadEmail",  lead.email)
            putString("leadNotes",  lead.notes)
            putString("leadStatus", lead.status)
        }
        findNavController().navigate(R.id.action_leads_to_detail, bundle)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
