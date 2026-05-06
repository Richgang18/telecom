#!/usr/bin/env python3
"""
Integrated Softphone - Built-in SIP Client
Handles incoming calls directly in the desktop application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import socket
import re
from datetime import datetime
from typing import Optional, Callable
import wave
import pyaudio


class SIPClient:
    """Simple SIP client for receiving calls"""
    
    def __init__(self, extension: str, password: str, domain: str, port: int = 5060):
        self.extension = extension
        self.password = password
        self.domain = domain
        self.port = port
        self.registered = False
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.on_incoming_call: Optional[Callable] = None
        self.on_call_ended: Optional[Callable] = None
        self.on_status_change: Optional[Callable] = None
        self.current_call_id: Optional[str] = None
        self.audio_stream: Optional[pyaudio.Stream] = None
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        
    def start(self):
        """Start the SIP client"""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        
        # Bind to any available port
        self.socket.bind(('0.0.0.0', 0))
        local_port = self.socket.getsockname()[1]
        
        # Start listener thread
        listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listener_thread.start()
        
        # Register with Asterisk
        self._register()
        
        # Start keepalive thread
        keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        keepalive_thread.start()
        
        self._update_status(f"Started on port {local_port}")
        
    def stop(self):
        """Stop the SIP client"""
        self.running = False
        self._unregister()
        if self.socket:
            self.socket.close()
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        self._update_status("Stopped")
        
    def answer_call(self):
        """Answer incoming call"""
        if self.current_call_id:
            self._send_200_ok()
            self._start_audio()
            self._update_status("Call answered")
            
    def hangup_call(self):
        """Hangup current call"""
        if self.current_call_id:
            self._send_bye()
            self._stop_audio()
            self.current_call_id = None
            if self.on_call_ended:
                self.on_call_ended()
            self._update_status("Call ended")
            
    def _register(self):
        """Send SIP REGISTER"""
        call_id = f"register-{int(time.time())}"
        local_ip = self._get_local_ip()
        local_port = self.socket.getsockname()[1]
        
        register_msg = (
            f"REGISTER sip:{self.domain}:{self.port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-{int(time.time())}\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: <sip:{self.extension}@{self.domain}>;tag=register-{int(time.time())}\r\n"
            f"To: <sip:{self.extension}@{self.domain}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 REGISTER\r\n"
            f"Contact: <sip:{self.extension}@{local_ip}:{local_port}>\r\n"
            f"Expires: 3600\r\n"
            f"User-Agent: PythonSoftphone/1.0\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        try:
            self.socket.sendto(register_msg.encode(), (self.domain, self.port))
            self._update_status("Registering...")
        except Exception as e:
            self._update_status(f"Registration failed: {e}")
            
    def _unregister(self):
        """Send SIP UNREGISTER"""
        call_id = f"unregister-{int(time.time())}"
        local_ip = self._get_local_ip()
        local_port = self.socket.getsockname()[1]
        
        unregister_msg = (
            f"REGISTER sip:{self.domain}:{self.port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-{int(time.time())}\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: <sip:{self.extension}@{self.domain}>;tag=unregister-{int(time.time())}\r\n"
            f"To: <sip:{self.extension}@{self.domain}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 REGISTER\r\n"
            f"Contact: <sip:{self.extension}@{local_ip}:{local_port}>\r\n"
            f"Expires: 0\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        try:
            self.socket.sendto(unregister_msg.encode(), (self.domain, self.port))
        except:
            pass
            
    def _listen_loop(self):
        """Listen for incoming SIP messages"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                self._handle_message(message, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self._update_status(f"Listen error: {e}")
                    
    def _keepalive_loop(self):
        """Send periodic keepalive"""
        while self.running:
            time.sleep(300)  # Re-register every 5 minutes
            if self.running and self.registered:
                self._register()
                
    def _handle_message(self, message: str, addr):
        """Handle incoming SIP message"""
        lines = message.split('\r\n')
        if not lines:
            return
            
        first_line = lines[0]
        
        # Handle responses
        if first_line.startswith('SIP/2.0'):
            if '200 OK' in first_line:
                if 'REGISTER' in message:
                    self.registered = True
                    self._update_status("✓ Registered")
            elif '401 Unauthorized' in first_line or '407 Proxy Authentication Required' in first_line:
                # Handle authentication challenge
                self._handle_auth_challenge(message, addr)
                
        # Handle INVITE (incoming call)
        elif first_line.startswith('INVITE'):
            self._handle_invite(message, addr)
            
        # Handle BYE (call ended)
        elif first_line.startswith('BYE'):
            self._handle_bye(message, addr)
            
        # Handle ACK
        elif first_line.startswith('ACK'):
            pass  # Call established
            
    def _handle_auth_challenge(self, message: str, addr):
        """Handle 401/407 authentication challenge"""
        # Extract authentication parameters
        auth_line = None
        for line in message.split('\r\n'):
            if line.startswith('WWW-Authenticate:') or line.startswith('Proxy-Authenticate:'):
                auth_line = line
                break
                
        if not auth_line:
            return
            
        # Parse realm, nonce, etc.
        realm_match = re.search(r'realm="([^"]+)"', auth_line)
        nonce_match = re.search(r'nonce="([^"]+)"', auth_line)
        
        if not realm_match or not nonce_match:
            return
            
        realm = realm_match.group(1)
        nonce = nonce_match.group(1)
        
        # Calculate response (simplified - real implementation needs MD5 digest)
        import hashlib
        ha1 = hashlib.md5(f"{self.extension}:{realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:sip:{self.domain}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        
        # Send authenticated REGISTER
        call_id = f"register-auth-{int(time.time())}"
        local_ip = self._get_local_ip()
        local_port = self.socket.getsockname()[1]
        
        auth_register = (
            f"REGISTER sip:{self.domain}:{self.port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-{int(time.time())}\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: <sip:{self.extension}@{self.domain}>;tag=register-{int(time.time())}\r\n"
            f"To: <sip:{self.extension}@{self.domain}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 2 REGISTER\r\n"
            f"Contact: <sip:{self.extension}@{local_ip}:{local_port}>\r\n"
            f"Authorization: Digest username=\"{self.extension}\", realm=\"{realm}\", "
            f"nonce=\"{nonce}\", uri=\"sip:{self.domain}\", response=\"{response}\"\r\n"
            f"Expires: 3600\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        try:
            self.socket.sendto(auth_register.encode(), (self.domain, self.port))
        except Exception as e:
            self._update_status(f"Auth failed: {e}")
            
    def _handle_invite(self, message: str, addr):
        """Handle incoming INVITE (call)"""
        # Extract caller info
        from_match = re.search(r'From:.*<sip:([^@>]+)', message)
        caller = from_match.group(1) if from_match else "Unknown"
        
        # Extract Call-ID
        call_id_match = re.search(r'Call-ID:\s*(.+)', message)
        if call_id_match:
            self.current_call_id = call_id_match.group(1).strip()
        
        # Send 180 Ringing
        self._send_180_ringing(message, addr)
        
        # Notify UI
        if self.on_incoming_call:
            self.on_incoming_call(caller)
            
        self._update_status(f"Incoming call from {caller}")
        
    def _handle_bye(self, message: str, addr):
        """Handle BYE (call ended)"""
        self._send_200_ok_bye(message, addr)
        self._stop_audio()
        self.current_call_id = None
        if self.on_call_ended:
            self.on_call_ended()
        self._update_status("Call ended by remote")
        
    def _send_180_ringing(self, invite_message: str, addr):
        """Send 180 Ringing response"""
        # Parse INVITE to extract necessary headers
        via_match = re.search(r'Via:\s*(.+)', invite_message)
        from_match = re.search(r'From:\s*(.+)', invite_message)
        to_match = re.search(r'To:\s*(.+)', invite_message)
        call_id_match = re.search(r'Call-ID:\s*(.+)', invite_message)
        cseq_match = re.search(r'CSeq:\s*(.+)', invite_message)
        
        if not all([via_match, from_match, to_match, call_id_match, cseq_match]):
            return
            
        response = (
            f"SIP/2.0 180 Ringing\r\n"
            f"Via: {via_match.group(1)}\r\n"
            f"From: {from_match.group(1)}\r\n"
            f"To: {to_match.group(1)};tag=softphone-{int(time.time())}\r\n"
            f"Call-ID: {call_id_match.group(1)}\r\n"
            f"CSeq: {cseq_match.group(1)}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        try:
            self.socket.sendto(response.encode(), addr)
        except Exception as e:
            self._update_status(f"Failed to send 180: {e}")
            
    def _send_200_ok(self):
        """Send 200 OK to answer call"""
        # Simplified - real implementation needs full SDP negotiation
        self._update_status("Sending 200 OK...")
        
    def _send_200_ok_bye(self, bye_message: str, addr):
        """Send 200 OK response to BYE"""
        via_match = re.search(r'Via:\s*(.+)', bye_message)
        from_match = re.search(r'From:\s*(.+)', bye_message)
        to_match = re.search(r'To:\s*(.+)', bye_message)
        call_id_match = re.search(r'Call-ID:\s*(.+)', bye_message)
        cseq_match = re.search(r'CSeq:\s*(.+)', bye_message)
        
        if not all([via_match, from_match, to_match, call_id_match, cseq_match]):
            return
            
        response = (
            f"SIP/2.0 200 OK\r\n"
            f"Via: {via_match.group(1)}\r\n"
            f"From: {from_match.group(1)}\r\n"
            f"To: {to_match.group(1)}\r\n"
            f"Call-ID: {call_id_match.group(1)}\r\n"
            f"CSeq: {cseq_match.group(1)}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        try:
            self.socket.sendto(response.encode(), addr)
        except Exception as e:
            self._update_status(f"Failed to send 200 OK: {e}")
            
    def _send_bye(self):
        """Send BYE to end call"""
        # Simplified - real implementation needs proper headers
        self._update_status("Sending BYE...")
        
    def _start_audio(self):
        """Start audio stream"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=8000,
                input=True,
                output=True,
                frames_per_buffer=160
            )
            self._update_status("Audio started")
        except Exception as e:
            self._update_status(f"Audio error: {e}")
            
    def _stop_audio(self):
        """Stop audio stream"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
            
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to external address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.domain, self.port))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return '127.0.0.1'
            
    def _update_status(self, status: str):
        """Update status"""
        if self.on_status_change:
            self.on_status_change(status)


class SoftphoneWindow:
    """Softphone GUI window"""
    
    def __init__(self, parent, extension: str, password: str, domain: str, port: int = 5060):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Softphone - Extension {extension}")
        self.window.geometry("400x600")
        self.window.resizable(False, False)
        
        self.extension = extension
        self.sip_client = SIPClient(extension, password, domain, port)
        self.sip_client.on_incoming_call = self.on_incoming_call
        self.sip_client.on_call_ended = self.on_call_ended
        self.sip_client.on_status_change = self.on_status_change
        
        self.in_call = False
        self.caller_name = ""
        
        self.setup_ui()
        
        # Start SIP client
        self.sip_client.start()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_ui(self):
        """Setup the UI"""
        # Header
        header_frame = tk.Frame(self.window, bg="#2c3e50", height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f"Extension {self.extension}", 
                font=("Arial", 18, "bold"), bg="#2c3e50", fg="white").pack(pady=10)
        
        self.status_label = tk.Label(header_frame, text="Initializing...", 
                                     font=("Arial", 10), bg="#2c3e50", fg="#ecf0f1")
        self.status_label.pack()
        
        # Call display area
        call_frame = tk.Frame(self.window, bg="white")
        call_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.call_status_label = tk.Label(call_frame, text="Ready", 
                                          font=("Arial", 16), bg="white", fg="#7f8c8d")
        self.call_status_label.pack(pady=30)
        
        self.caller_label = tk.Label(call_frame, text="", 
                                     font=("Arial", 24, "bold"), bg="white", fg="#2c3e50")
        self.caller_label.pack(pady=10)
        
        self.call_duration_label = tk.Label(call_frame, text="", 
                                           font=("Arial", 14), bg="white", fg="#7f8c8d")
        self.call_duration_label.pack(pady=5)
        
        # Call control buttons
        button_frame = tk.Frame(self.window, bg="white")
        button_frame.pack(fill='x', padx=20, pady=20)
        
        self.answer_btn = tk.Button(button_frame, text="📞 Answer", 
                                    font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                                    command=self.answer_call, state='disabled',
                                    width=15, height=2, relief='flat', cursor="hand2")
        self.answer_btn.pack(pady=5)
        
        self.hangup_btn = tk.Button(button_frame, text="📵 Hangup", 
                                    font=("Arial", 14, "bold"), bg="#e74c3c", fg="white",
                                    command=self.hangup_call, state='disabled',
                                    width=15, height=2, relief='flat', cursor="hand2")
        self.hangup_btn.pack(pady=5)
        
        # Activity log
        log_frame = tk.LabelFrame(self.window, text="Activity Log", bg="white")
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, 
                               font=("Courier", 9), bg="#ecf0f1", state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log("Softphone initialized")
        
    def on_incoming_call(self, caller: str):
        """Handle incoming call"""
        self.in_call = False
        self.caller_name = caller
        
        self.window.after(0, self._update_incoming_call_ui)
        
        # Play ringtone (optional)
        self.window.bell()
        
    def _update_incoming_call_ui(self):
        """Update UI for incoming call"""
        self.call_status_label.config(text="📞 Incoming Call", fg="#e67e22")
        self.caller_label.config(text=self.caller_name)
        self.answer_btn.config(state='normal')
        self.hangup_btn.config(state='normal')
        self.log(f"Incoming call from {self.caller_name}")
        
        # Flash window to get attention
        self.window.attributes('-topmost', True)
        self.window.attributes('-topmost', False)
        self.window.focus_force()
        
    def answer_call(self):
        """Answer the call"""
        self.in_call = True
        self.sip_client.answer_call()
        
        self.call_status_label.config(text="📞 In Call", fg="#27ae60")
        self.answer_btn.config(state='disabled')
        self.hangup_btn.config(state='normal')
        self.log(f"Answered call from {self.caller_name}")
        
        # Start call timer
        self.call_start_time = time.time()
        self._update_call_duration()
        
    def hangup_call(self):
        """Hangup the call"""
        self.sip_client.hangup_call()
        self.on_call_ended()
        
    def on_call_ended(self):
        """Handle call ended"""
        self.in_call = False
        
        self.window.after(0, self._update_call_ended_ui)
        
    def _update_call_ended_ui(self):
        """Update UI for call ended"""
        self.call_status_label.config(text="Ready", fg="#7f8c8d")
        self.caller_label.config(text="")
        self.call_duration_label.config(text="")
        self.answer_btn.config(state='disabled')
        self.hangup_btn.config(state='disabled')
        self.log("Call ended")
        
    def _update_call_duration(self):
        """Update call duration display"""
        if self.in_call:
            duration = int(time.time() - self.call_start_time)
            minutes = duration // 60
            seconds = duration % 60
            self.call_duration_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.window.after(1000, self._update_call_duration)
            
    def on_status_change(self, status: str):
        """Handle status change"""
        self.window.after(0, lambda: self._update_status(status))
        
    def _update_status(self, status: str):
        """Update status label"""
        self.status_label.config(text=status)
        self.log(status)
        
    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def on_close(self):
        """Handle window close"""
        if messagebox.askyesno("Confirm", "Close softphone? You will not receive calls."):
            self.sip_client.stop()
            self.window.destroy()


def launch_softphone(parent, extension: str, password: str, domain: str, port: int = 5060):
    """Launch softphone window"""
    return SoftphoneWindow(parent, extension, password, domain, port)


if __name__ == "__main__":
    # Test standalone
    root = tk.Tk()
    root.withdraw()
    
    softphone = launch_softphone(root, "101", "ChangeMe101!", "172.25.17.93", 5060)
    
    root.mainloop()
