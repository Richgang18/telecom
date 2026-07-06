package com.smartdialer.agent.ui.call

import android.app.AlertDialog
import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.smartdialer.agent.MainActivity
import com.smartdialer.agent.data.ApiClient
import com.smartdialer.agent.data.LeadUpdateRequest
import com.smartdialer.agent.databinding.FragmentActiveCallBinding
import com.smartdialer.agent.service.CallService
import kotlinx.coroutines.launch

class ActiveCallFragment : Fragment() {

    private var _binding: FragmentActiveCallBinding? = null
    private val binding get() = _binding!!
    private lateinit var callViewModel: ActiveCallViewModel

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentActiveCallBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        callViewModel = (activity as MainActivity).callViewModel

        callViewModel.loadAgents()

        // Observe state
        callViewModel.activeCall.observe(viewLifecycleOwner) { info ->
            if (info != null) {
                binding.tvLeadName.text  = info.leadName
                binding.tvLeadPhone.text = info.leadPhone
            }
        }

        callViewModel.callState.observe(viewLifecycleOwner) { state ->
            when (state) {
                CallState.RINGING -> {
                    binding.tvCallStatus.text = "Ringing..."
                    binding.tvCallStatus.setTextColor(0xFFFDCB6E.toInt())
                }
                CallState.CONNECTED -> {
                    binding.tvCallStatus.text = "Connected"
                    binding.tvCallStatus.setTextColor(0xFF00B894.toInt())
                    // Start foreground service to keep call alive when backgrounded
                    val info = callViewModel.activeCall.value
                    if (info != null) CallService.start(requireContext(), info.leadName, info.leadPhone)
                }
                CallState.ENDED -> {
                    binding.tvCallStatus.text = "Call ended"
                    binding.tvCallStatus.setTextColor(0xFF636E72.toInt())
                    CallService.stop(requireContext())
                    view.postDelayed({ if (isAdded) findNavController().popBackStack() }, 2000)
                }
                CallState.FAILED -> {
                    binding.tvCallStatus.text = "Failed"
                    binding.tvCallStatus.setTextColor(0xFFD63031.toInt())
                    CallService.stop(requireContext())
                    view.postDelayed({ if (isAdded) findNavController().popBackStack() }, 2000)
                }
                else -> {}
            }
        }

        callViewModel.callDuration.observe(viewLifecycleOwner) { seconds ->
            val m = seconds / 60
            val s = seconds % 60
            binding.tvDuration.text = String.format("%02d:%02d", m, s)
        }

        callViewModel.recordingUrl.observe(viewLifecycleOwner) { url ->
            if (url != null) {
                binding.tvRecording.visibility = View.VISIBLE
                binding.tvRecording.text = "● Recording"
            }
        }

        callViewModel.error.observe(viewLifecycleOwner) { err ->
            if (err != null) Toast.makeText(requireContext(), err, Toast.LENGTH_LONG).show()
        }

        callViewModel.transferDone.observe(viewLifecycleOwner) { done ->
            if (done) {
                Toast.makeText(requireContext(), "Call transferred", Toast.LENGTH_SHORT).show()
                findNavController().popBackStack()
            }
        }

        // Buttons
        binding.btnHangup.setOnClickListener {
            callViewModel.hangup()
        }

        binding.btnTransfer.setOnClickListener {
            showTransferDialog()
        }

        binding.btnNotes.setOnClickListener {
            showNotesDialog()
        }
    }

    private fun showTransferDialog() {
        val agentList = callViewModel.agents.value ?: emptyList()
        if (agentList.isEmpty()) {
            Toast.makeText(requireContext(), "No other agents available", Toast.LENGTH_SHORT).show()
            return
        }
        val names = agentList.map { it["name"] as? String ?: "Agent" }.toTypedArray()
        AlertDialog.Builder(requireContext())
            .setTitle("Transfer to")
            .setItems(names) { _, idx ->
                val targetId = agentList[idx]["id"] as? String ?: return@setItems
                callViewModel.transfer(targetId)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showNotesDialog() {
        val input = android.widget.EditText(requireContext()).apply {
            hint = "Add call note..."
            setPadding(32, 16, 32, 16)
        }
        AlertDialog.Builder(requireContext())
            .setTitle("Call Notes")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val notes  = input.text.toString()
                val leadId = callViewModel.activeCall.value?.leadId ?: return@setPositiveButton
                lifecycleScope.launch {
                    try {
                        ApiClient.service.updateLead(leadId, LeadUpdateRequest("callback", notes))
                        Toast.makeText(requireContext(), "Note saved", Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Toast.makeText(requireContext(), "Failed to save note", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
