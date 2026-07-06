package com.smartdialer.agent.ui.leads

import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.smartdialer.agent.MainActivity
import com.smartdialer.agent.R
import com.smartdialer.agent.data.Lead
import com.smartdialer.agent.databinding.FragmentLeadDetailBinding
import com.smartdialer.agent.ui.call.CallState

class LeadDetailFragment : Fragment() {

    private var _binding: FragmentLeadDetailBinding? = null
    private val binding get() = _binding!!
    private val viewModel: LeadsViewModel by viewModels()

    private val leadId     by lazy { arguments?.getString("leadId",     "") ?: "" }
    private val leadName   by lazy { arguments?.getString("leadName",   "") ?: "" }
    private val leadPhone  by lazy { arguments?.getString("leadPhone",  "") ?: "" }
    private val leadEmail  by lazy { arguments?.getString("leadEmail",  "") ?: "" }
    private val leadNotes  by lazy { arguments?.getString("leadNotes",  "") ?: "" }
    private val leadStatus by lazy { arguments?.getString("leadStatus", "new") ?: "new" }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentLeadDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.tvName.text   = leadName
        binding.tvPhone.text  = leadPhone
        binding.tvEmail.text  = leadEmail.ifEmpty { "—" }
        binding.tvNotes.text  = leadNotes.ifEmpty { "No notes" }
        binding.tvStatus.text = leadStatus.uppercase()

        val statuses = arrayOf("new", "callback", "done", "dnc")
        var selectedStatus = leadStatus

        binding.btnChangeStatus.setOnClickListener {
            android.app.AlertDialog.Builder(requireContext())
                .setTitle("Change Status")
                .setSingleChoiceItems(statuses, statuses.indexOf(selectedStatus)) { dialog, idx ->
                    selectedStatus = statuses[idx]
                    dialog.dismiss()
                    val notes = binding.etNotes.text.toString()
                    viewModel.updateLeadStatus(leadId, selectedStatus, notes)
                    binding.tvStatus.text = selectedStatus.uppercase()
                    Toast.makeText(requireContext(), "Status updated", Toast.LENGTH_SHORT).show()
                }
                .show()
        }

        binding.btnCall.setOnClickListener {
            viewModel.dial(
                Lead(
                    id     = leadId,
                    name   = leadName,
                    phone  = leadPhone,
                    email  = leadEmail,
                    notes  = leadNotes,
                    status = leadStatus,
                )
            )
        }

        binding.btnBack.setOnClickListener {
            findNavController().popBackStack()
        }

        viewModel.dialResult.observe(viewLifecycleOwner) { result ->
            result.onSuccess {
                Toast.makeText(requireContext(), "Dialing $leadName...", Toast.LENGTH_SHORT).show()
            }.onFailure { err ->
                Toast.makeText(requireContext(), "Dial failed: ${err.message}", Toast.LENGTH_LONG).show()
            }
        }

        (activity as? MainActivity)?.callViewModel?.callState?.observe(viewLifecycleOwner) { state ->
            if (state == CallState.RINGING || state == CallState.CONNECTED) {
                findNavController().navigate(R.id.action_detail_to_call)
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
