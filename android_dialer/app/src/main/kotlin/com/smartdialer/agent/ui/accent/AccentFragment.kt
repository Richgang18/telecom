package com.smartdialer.agent.ui.accent

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.smartdialer.agent.data.SessionManager
import com.smartdialer.agent.databinding.FragmentAccentBinding
import kotlinx.coroutines.launch

class AccentFragment : Fragment() {

    private var _binding: FragmentAccentBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AccentViewModel by viewModels()

    private val requestMic = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startRecording() else
            Toast.makeText(requireContext(), "Microphone permission required", Toast.LENGTH_LONG).show()
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAccentBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Configure server URL
        lifecycleScope.launch {
            val url = com.smartdialer.agent.data.SessionManager(requireContext()).getServerUrl()
                ?: "http://10.0.2.2:8080"
            viewModel.configure(url)
        }

        binding.btnBack.setOnClickListener { findNavController().popBackStack() }

        binding.btnRecord.setOnClickListener {
            when (viewModel.state.value) {
                AccentState.RECORDING -> viewModel.stopRecording()
                AccentState.IDLE      -> checkMicAndRecord()
                else                  -> { /* ignore taps during converting/playing */ }
            }
        }

        // Observe state
        viewModel.state.observe(viewLifecycleOwner) { state ->
            when (state) {
                AccentState.IDLE -> {
                    binding.btnRecord.text = "🎤 TAP TO SPEAK"
                    binding.btnRecord.setBackgroundColor(0xFFE94560.toInt())
                    binding.tvStatus.text  = "Ready"
                    binding.waveView.visibility = View.INVISIBLE
                    animateStep(0)
                }
                AccentState.RECORDING -> {
                    binding.btnRecord.text = "⏹ TAP TO STOP"
                    binding.btnRecord.setBackgroundColor(0xFFD63031.toInt())
                    binding.tvStatus.text  = "Listening..."
                    binding.waveView.visibility = View.VISIBLE
                    animateStep(1)
                }
                AccentState.CONVERTING -> {
                    binding.btnRecord.text = "⏳ CONVERTING..."
                    binding.btnRecord.setBackgroundColor(0xFF0984E3.toInt())
                    binding.tvStatus.text  = "Converting accent..."
                    animateStep(2)
                }
                AccentState.PLAYING -> {
                    binding.btnRecord.text = "🔊 PLAYING..."
                    binding.btnRecord.setBackgroundColor(0xFF00B894.toInt())
                    binding.tvStatus.text  = "American voice playing"
                    animateStep(3)
                }
                else -> {}
            }
        }

        viewModel.transcript.observe(viewLifecycleOwner) { text ->
            binding.tvTranscript.text = text
            binding.tvConverted.text  = text
        }

        viewModel.latencyMs.observe(viewLifecycleOwner) { ms ->
            binding.tvLatency.text = "${ms}ms"
        }

        viewModel.error.observe(viewLifecycleOwner) { err ->
            if (err != null) Toast.makeText(requireContext(), err, Toast.LENGTH_LONG).show()
        }
    }

    private fun checkMicAndRecord() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED) {
            startRecording()
        } else {
            requestMic.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun startRecording() {
        viewModel.startRecording()
    }

    private fun animateStep(active: Int) {
        val steps = listOf(
            binding.step1, binding.step2, binding.step3, binding.step4
        )
        steps.forEachIndexed { i, v ->
            v.alpha     = if (i <= active) 1f else 0.3f
            v.scaleX    = if (i == active) 1.1f else 1f
            v.scaleY    = if (i == active) 1.1f else 1f
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
