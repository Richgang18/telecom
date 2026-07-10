package com.smartdialer.agent.ui.login

import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.smartdialer.agent.MainActivity
import com.smartdialer.agent.R
import com.smartdialer.agent.data.ApiClient
import com.smartdialer.agent.data.SessionManager
import com.smartdialer.agent.databinding.FragmentLoginBinding
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class LoginFragment : Fragment() {

    private var _binding: FragmentLoginBinding? = null
    private val binding get() = _binding!!
    private val viewModel: LoginViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentLoginBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Pre-fill for convenience
        binding.etAgentId.setText("agent1")
        binding.etPassword.setText("callcenter@1")

        binding.btnLogin.setOnClickListener {
            val server   = binding.etServer.text.toString().trim()
            val agentId  = binding.etAgentId.text.toString().trim()
            val password = binding.etPassword.text.toString()

            if (agentId.isEmpty() || password.isEmpty()) {
                Toast.makeText(requireContext(), "Fill in Agent ID and Password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // DEMO MODE: if server is empty or "demo", skip login and load mock data
            if (server.isEmpty() || server.lowercase() == "demo") {
                enterDemoMode(agentId)
                return@setOnClickListener
            }

            viewModel.login(server, agentId, password)
        }

        // Demo mode button
        binding.btnDemo.setOnClickListener {
            enterDemoMode("agent1")
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            when (state) {
                is LoginState.Loading -> {
                    binding.btnLogin.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                is LoginState.Success -> {
                    binding.btnLogin.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                    val server = binding.etServer.text.toString().trim()
                    lifecycleScope.launch {
                        val token = SessionManager(requireContext()).token.first() ?: return@launch
                        (activity as? MainActivity)?.connectWebSocket(server, state.agentId, token)
                    }
                    findNavController().navigate(R.id.action_login_to_leads)
                }
                is LoginState.Error -> {
                    binding.btnLogin.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                    // Offer demo mode on connection failure
                    Toast.makeText(
                        requireContext(),
                        "${state.message}\n\nTap 'Demo Mode' to preview the UI",
                        Toast.LENGTH_LONG
                    ).show()
                }
                else -> {
                    binding.btnLogin.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                }
            }
        }
    }

    private fun enterDemoMode(agentId: String) {
        // Save a demo session — no real server needed
        lifecycleScope.launch {
            SessionManager(requireContext()).saveSession(
                token     = "demo-token",
                agentId   = agentId,
                agentName = if (agentId == "agent1") "Daniels" else "Qandarius",
                serverUrl = "demo"
            )
            ApiClient.configure("http://localhost:5001", "demo-token")
            findNavController().navigate(R.id.action_login_to_leads)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
