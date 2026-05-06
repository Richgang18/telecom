#!/usr/bin/env python3
"""
Smart Outbound Dialer - Desktop Application
Professional GUI for managing outbound calling campaigns
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import configparser
import requests
from typing import Optional, Dict, List

# Get the directory where this script is located
APP_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = APP_DIR / "config.ini"
CALL_LOG_FILE = APP_DIR / "call_results.json"
CONTACTS_FILE = APP_DIR / "contacts.csv"


class CallResult:
    """Store call result data"""
    def __init__(self, name: str, phone: str, status: str, timestamp: str, agent: str = ""):
        self.name = name
        self.phone = phone
        self.status = status  # answered, voicemail, no-answer, busy, failed
        self.timestamp = timestamp
        self.agent = agent


class DialerApp:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Outbound Dialer - VoIP System")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Application state
        self.dialer_process: Optional[subprocess.Popen] = None
        self.webhook_process: Optional[subprocess.Popen] = None
        self.ngrok_process: Optional[subprocess.Popen] = None
        self.is_calling = False
        self.call_results: List[CallResult] = []
        self.contacts_data: List[Dict] = []
        self.config = configparser.ConfigParser()
        
        # Load configuration
        self.load_config()
        
        # Load previous call results
        self.load_call_results()
        
        # Setup UI
        self.setup_ui()
        
        # Start status monitoring
        self.update_status()
        
    def load_config(self):
        """Load configuration from config.ini"""
        if CONFIG_FILE.exists():
            self.config.read(CONFIG_FILE)
        else:
            # Create default config
            self.config['twilio'] = {
                'account_sid': '',
                'auth_token': '',
                'from_number': '',
                'webhook_base_url': ''
            }
            self.config['agents'] = {
                'max_concurrent_calls': '2',
                'agent_extensions': '101,102',
                'agent_names': 'Agent 1,Agent 2'
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to config.ini"""
        with open(CONFIG_FILE, 'w') as f:
            self.config.write(f)
    
    def load_call_results(self):
        """Load previous call results from JSON file"""
        if CALL_LOG_FILE.exists():
            try:
                with open(CALL_LOG_FILE, 'r') as f:
                    data = json.load(f)
                    self.call_results = [
                        CallResult(r['name'], r['phone'], r['status'], r['timestamp'], r.get('agent', ''))
                        for r in data
                    ]
            except Exception as e:
                print(f"Error loading call results: {e}")
    
    def save_call_results(self):
        """Save call results to JSON file"""
        try:
            data = [
                {
                    'name': r.name,
                    'phone': r.phone,
                    'status': r.status,
                    'timestamp': r.timestamp,
                    'agent': r.agent
                }
                for r in self.call_results
            ]
            with open(CALL_LOG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving call results: {e}")
    
    def setup_ui(self):
        """Setup the main UI"""
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_contacts_tab()
        self.create_results_tab()
        self.create_settings_tab()
        self.create_agents_tab()
        
    def create_dashboard_tab(self):
        """Create the main dashboard tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Dashboard")
        
        # Top section - System Status
        status_frame = ttk.LabelFrame(tab, text="System Status", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill='x')
        
        # Status indicators
        ttk.Label(status_grid, text="Asterisk:").grid(row=0, column=0, sticky='w', padx=5)
        self.asterisk_status = ttk.Label(status_grid, text="●", foreground="gray", font=("Arial", 16))
        self.asterisk_status.grid(row=0, column=1, sticky='w')
        self.asterisk_label = ttk.Label(status_grid, text="Checking...")
        self.asterisk_label.grid(row=0, column=2, sticky='w', padx=5)
        
        ttk.Label(status_grid, text="Webhook Server:").grid(row=1, column=0, sticky='w', padx=5)
        self.webhook_status = ttk.Label(status_grid, text="●", foreground="gray", font=("Arial", 16))
        self.webhook_status.grid(row=1, column=1, sticky='w')
        self.webhook_label = ttk.Label(status_grid, text="Not running")
        self.webhook_label.grid(row=1, column=2, sticky='w', padx=5)
        
        ttk.Label(status_grid, text="Ngrok Tunnel:").grid(row=2, column=0, sticky='w', padx=5)
        self.ngrok_status = ttk.Label(status_grid, text="●", foreground="gray", font=("Arial", 16))
        self.ngrok_status.grid(row=2, column=1, sticky='w')
        self.ngrok_label = ttk.Label(status_grid, text="Not running")
        self.ngrok_label.grid(row=2, column=2, sticky='w', padx=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(tab, text="Campaign Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack()
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Calling", command=self.start_calling, 
                                     style="Success.TButton", width=20)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop Calling", command=self.stop_calling,
                                    style="Danger.TButton", width=20, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        self.start_services_btn = ttk.Button(btn_frame, text="🚀 Start Services", 
                                              command=self.start_services, width=20)
        self.start_services_btn.pack(side='left', padx=5)
        
        self.stop_services_btn = ttk.Button(btn_frame, text="⏸ Stop Services",
                                             command=self.stop_services, width=20)
        self.stop_services_btn.pack(side='left', padx=5)
        
        self.refresh_status_btn = ttk.Button(btn_frame, text="🔄 Refresh Status",
                                              command=self.force_status_update, width=20)
        self.refresh_status_btn.pack(side='left', padx=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(tab, text="Campaign Statistics", padding=10)
        stats_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill='x', pady=10)
        
        # Create stat cards
        self.create_stat_card(stats_grid, "Total Contacts", "0", 0, 0)
        self.create_stat_card(stats_grid, "Answered", "0", 0, 1, "green")
        self.create_stat_card(stats_grid, "Voicemail", "0", 0, 2, "orange")
        self.create_stat_card(stats_grid, "No Answer", "0", 0, 3, "red")
        
        # Activity log
        log_label = ttk.Label(stats_frame, text="Activity Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor='w', pady=(10, 5))
        
        self.activity_log = scrolledtext.ScrolledText(stats_frame, height=15, wrap=tk.WORD)
        self.activity_log.pack(fill='both', expand=True)
        self.activity_log.config(state='disabled')
        
        self.log_message("Application started")
        
    def create_stat_card(self, parent, label, value, row, col, color="blue"):
        """Create a statistics card"""
        frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky='ew')
        parent.columnconfigure(col, weight=1)
        
        value_label = ttk.Label(frame, text=value, font=("Arial", 24, "bold"), foreground=color)
        value_label.pack(pady=(10, 0))
        
        text_label = ttk.Label(frame, text=label, font=("Arial", 10))
        text_label.pack(pady=(0, 10))
        
        # Store reference for updating
        setattr(self, f"stat_{label.lower().replace(' ', '_')}", value_label)
        
    def create_contacts_tab(self):
        """Create the contacts management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 Contacts")
        
        # Upload section
        upload_frame = ttk.LabelFrame(tab, text="Upload Contacts", padding=10)
        upload_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(upload_frame, text="Upload a CSV file with columns: Firstname, Lastname, Dob, Phone, Address1, Address2, City, Zip").pack(anchor='w')
        
        btn_frame = ttk.Frame(upload_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="📁 Browse CSV File", command=self.browse_csv).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 Reload Contacts", command=self.reload_contacts).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🗑 Clear All", command=self.clear_contacts).pack(side='left', padx=5)
        
        self.contacts_file_label = ttk.Label(upload_frame, text="No file loaded", foreground="gray")
        self.contacts_file_label.pack(anchor='w')
        
        # Contacts table
        table_frame = ttk.LabelFrame(tab, text="Loaded Contacts", padding=10)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side='right', fill='y')
        
        self.contacts_tree = ttk.Treeview(table_frame, yscrollcommand=tree_scroll.set,
                                          columns=("Name", "Phone", "City", "Zip"), show='headings')
        tree_scroll.config(command=self.contacts_tree.yview)
        
        self.contacts_tree.heading("Name", text="Name")
        self.contacts_tree.heading("Phone", text="Phone")
        self.contacts_tree.heading("City", text="City")
        self.contacts_tree.heading("Zip", text="Zip")
        
        self.contacts_tree.column("Name", width=200)
        self.contacts_tree.column("Phone", width=150)
        self.contacts_tree.column("City", width=150)
        self.contacts_tree.column("Zip", width=100)
        
        self.contacts_tree.pack(fill='both', expand=True)
        
        # Load existing contacts if any
        self.reload_contacts()

    def create_results_tab(self):
        """Create the call results tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📞 Call Results")
        
        # Filter section
        filter_frame = ttk.LabelFrame(tab, text="Filter Results", padding=10)
        filter_frame.pack(fill='x', padx=10, pady=5)
        
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill='x')
        
        ttk.Label(filter_grid, text="Status:").grid(row=0, column=0, padx=5, sticky='w')
        self.filter_status = ttk.Combobox(filter_grid, values=["All", "Answered", "Voicemail", "No Answer", "Busy", "Failed"],
                                          state='readonly', width=15)
        self.filter_status.set("All")
        self.filter_status.grid(row=0, column=1, padx=5)
        self.filter_status.bind("<<ComboboxSelected>>", lambda e: self.update_results_table())
        
        ttk.Button(filter_grid, text="📊 Export to CSV", command=self.export_results).grid(row=0, column=2, padx=20)
        ttk.Button(filter_grid, text="🔄 Refresh", command=self.update_results_table).grid(row=0, column=3, padx=5)
        
        # Results table
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side='right', fill='y')
        
        self.results_tree = ttk.Treeview(table_frame, yscrollcommand=tree_scroll.set,
                                         columns=("Timestamp", "Name", "Phone", "Status", "Agent"), show='headings')
        tree_scroll.config(command=self.results_tree.yview)
        
        self.results_tree.heading("Timestamp", text="Time")
        self.results_tree.heading("Name", text="Name")
        self.results_tree.heading("Phone", text="Phone")
        self.results_tree.heading("Status", text="Status")
        self.results_tree.heading("Agent", text="Agent")
        
        self.results_tree.column("Timestamp", width=150)
        self.results_tree.column("Name", width=200)
        self.results_tree.column("Phone", width=150)
        self.results_tree.column("Status", width=120)
        self.results_tree.column("Agent", width=120)
        
        self.results_tree.pack(fill='both', expand=True)
        
        # Add tags for coloring
        self.results_tree.tag_configure('answered', background='#d4edda')
        self.results_tree.tag_configure('voicemail', background='#fff3cd')
        self.results_tree.tag_configure('no-answer', background='#f8d7da')
        
        # Summary section
        summary_frame = ttk.LabelFrame(tab, text="Summary", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="No calls yet", font=("Arial", 10))
        self.summary_label.pack()
        
        # Load existing results
        self.update_results_table()
        
    def create_settings_tab(self):
        """Create the settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙ Settings")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Twilio Settings
        twilio_frame = ttk.LabelFrame(scrollable_frame, text="Twilio Configuration", padding=10)
        twilio_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(twilio_frame, text="Account SID:").grid(row=0, column=0, sticky='w', pady=5)
        self.twilio_sid = ttk.Entry(twilio_frame, width=50)
        self.twilio_sid.grid(row=0, column=1, pady=5, padx=5)
        self.twilio_sid.insert(0, self.config.get('twilio', 'account_sid', fallback=''))
        
        ttk.Label(twilio_frame, text="Auth Token:").grid(row=1, column=0, sticky='w', pady=5)
        self.twilio_token = ttk.Entry(twilio_frame, width=50, show="*")
        self.twilio_token.grid(row=1, column=1, pady=5, padx=5)
        self.twilio_token.insert(0, self.config.get('twilio', 'auth_token', fallback=''))
        
        ttk.Label(twilio_frame, text="From Number:").grid(row=2, column=0, sticky='w', pady=5)
        self.twilio_number = ttk.Entry(twilio_frame, width=50)
        self.twilio_number.grid(row=2, column=1, pady=5, padx=5)
        self.twilio_number.insert(0, self.config.get('twilio', 'from_number', fallback=''))
        
        ttk.Label(twilio_frame, text="Webhook URL:").grid(row=3, column=0, sticky='w', pady=5)
        self.webhook_url = ttk.Entry(twilio_frame, width=50)
        self.webhook_url.grid(row=3, column=1, pady=5, padx=5)
        self.webhook_url.insert(0, self.config.get('twilio', 'webhook_base_url', fallback=''))
        
        ttk.Button(twilio_frame, text="🔄 Auto-detect Ngrok URL", 
                   command=self.detect_ngrok_url).grid(row=3, column=2, padx=5)
        
        # Voicemail Settings
        voicemail_frame = ttk.LabelFrame(scrollable_frame, text="Voicemail Configuration", padding=10)
        voicemail_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(voicemail_frame, text="Voicemail File:").grid(row=0, column=0, sticky='w', pady=5)
        self.voicemail_path = ttk.Entry(voicemail_frame, width=50)
        self.voicemail_path.grid(row=0, column=1, pady=5, padx=5)
        self.voicemail_path.insert(0, str(APP_DIR / "voicemail.mp3"))
        
        ttk.Button(voicemail_frame, text="Browse", 
                   command=self.browse_voicemail).grid(row=0, column=2, padx=5)
        
        # Dialer Settings
        dialer_frame = ttk.LabelFrame(scrollable_frame, text="Dialer Configuration", padding=10)
        dialer_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(dialer_frame, text="Ring Timeout (seconds):").grid(row=0, column=0, sticky='w', pady=5)
        self.ring_timeout = ttk.Spinbox(dialer_frame, from_=10, to=60, width=10)
        self.ring_timeout.grid(row=0, column=1, sticky='w', pady=5, padx=5)
        self.ring_timeout.set(20)
        
        ttk.Label(dialer_frame, text="Batch Delay (seconds):").grid(row=1, column=0, sticky='w', pady=5)
        self.batch_delay = ttk.Spinbox(dialer_frame, from_=1, to=10, width=10)
        self.batch_delay.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        self.batch_delay.set(2)
        
        # Save button
        save_frame = ttk.Frame(scrollable_frame)
        save_frame.pack(fill='x', padx=10, pady=20)
        
        ttk.Button(save_frame, text="💾 Save Settings", command=self.save_settings,
                   style="Success.TButton").pack()
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_agents_tab(self):
        """Create the agents configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="👥 Agents")
        
        # Agent configuration
        config_frame = ttk.LabelFrame(tab, text="Agent Configuration", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(config_frame, text="Configure Linphone extensions for your agents:").pack(anchor='w', pady=5)
        
        # Agent 1
        agent1_frame = ttk.LabelFrame(config_frame, text="Agent 1", padding=10)
        agent1_frame.pack(fill='x', pady=5)
        
        ttk.Label(agent1_frame, text="Extension: 101").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(agent1_frame, text="Password: ChangeMe101!").grid(row=1, column=0, sticky='w', padx=5)
        ttk.Label(agent1_frame, text="Domain: pbx.vouchersdept.com").grid(row=2, column=0, sticky='w', padx=5)
        ttk.Label(agent1_frame, text="Port: 5061 (TLS)").grid(row=3, column=0, sticky='w', padx=5)
        
        # Agent 2
        agent2_frame = ttk.LabelFrame(config_frame, text="Agent 2", padding=10)
        agent2_frame.pack(fill='x', pady=5)
        
        ttk.Label(agent2_frame, text="Extension: 102").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(agent2_frame, text="Password: ChangeMe102!").grid(row=1, column=0, sticky='w', padx=5)
        ttk.Label(agent2_frame, text="Domain: pbx.vouchersdept.com").grid(row=2, column=0, sticky='w', padx=5)
        ttk.Label(agent2_frame, text="Port: 5061 (TLS)").grid(row=3, column=0, sticky='w', padx=5)
        
        # Agent status
        status_frame = ttk.LabelFrame(tab, text="Agent Status", padding=10)
        status_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create agent status table
        self.agents_tree = ttk.Treeview(status_frame, columns=("Extension", "Name", "Status", "Current Call"), 
                                        show='headings', height=5)
        
        self.agents_tree.heading("Extension", text="Extension")
        self.agents_tree.heading("Name", text="Name")
        self.agents_tree.heading("Status", text="Status")
        self.agents_tree.heading("Current Call", text="Current Call")
        
        self.agents_tree.column("Extension", width=100)
        self.agents_tree.column("Name", width=150)
        self.agents_tree.column("Status", width=120)
        self.agents_tree.column("Current Call", width=200)
        
        self.agents_tree.pack(fill='both', expand=True, pady=5)
        
        # Add sample data
        self.agents_tree.insert("", "end", values=("101", "Agent 1", "Unknown", "—"))
        self.agents_tree.insert("", "end", values=("102", "Agent 2", "Unknown", "—"))
        
        ttk.Button(status_frame, text="🔄 Refresh Status", command=self.refresh_agent_status).pack(pady=5)
        
        # Linphone download
        download_frame = ttk.LabelFrame(tab, text="Linphone Setup", padding=10)
        download_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(download_frame, text="Download Linphone softphone for your agents:").pack(anchor='w')
        ttk.Label(download_frame, text="https://www.linphone.org/", foreground="blue", cursor="hand2").pack(anchor='w')

    # ========== Event Handlers ==========
    
    def browse_csv(self):
        """Browse for CSV file"""
        filename = filedialog.askopenfilename(
            title="Select Contacts CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.load_csv_file(filename)
    
    def load_csv_file(self, filename):
        """Load contacts from CSV file"""
        try:
            self.contacts_data = []
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check if required columns exist
                if 'Phone' not in reader.fieldnames:
                    messagebox.showerror("Error", "CSV must contain 'Phone' column")
                    return
                
                for row in reader:
                    # Extract and format data
                    firstname = row.get('Firstname', '').strip()
                    lastname = row.get('Lastname', '').strip()
                    name = f"{firstname} {lastname}".strip()
                    phone = row.get('Phone', '').strip()
                    city = row.get('City', '').strip()
                    zipcode = row.get('Zip', '').strip()
                    
                    # Format phone to E.164 if needed
                    if phone and not phone.startswith('+'):
                        # Assume US number
                        phone = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
                        if len(phone) == 10:
                            phone = f"+1{phone}"
                    
                    if phone:  # Only add if phone exists
                        self.contacts_data.append({
                            'name': name or 'Unknown',
                            'phone': phone,
                            'city': city,
                            'zip': zipcode
                        })
            
            # Save to contacts.csv in standard format
            self.save_contacts_to_file()
            
            # Update UI
            self.contacts_file_label.config(text=f"Loaded: {filename} ({len(self.contacts_data)} contacts)", 
                                           foreground="green")
            self.update_contacts_table()
            self.update_statistics()
            self.log_message(f"Loaded {len(self.contacts_data)} contacts from {Path(filename).name}")
            
            messagebox.showinfo("Success", f"Loaded {len(self.contacts_data)} contacts successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
            self.log_message(f"Error loading CSV: {str(e)}")
    
    def save_contacts_to_file(self):
        """Save contacts to standard contacts.csv format"""
        try:
            with open(CONTACTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['name', 'phone_number'])
                for contact in self.contacts_data:
                    writer.writerow([contact['name'], contact['phone']])
        except Exception as e:
            self.log_message(f"Error saving contacts: {str(e)}")
    
    def reload_contacts(self):
        """Reload contacts from file"""
        if CONTACTS_FILE.exists():
            try:
                self.contacts_data = []
                with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.contacts_data.append({
                            'name': row.get('name', 'Unknown'),
                            'phone': row.get('phone_number', ''),
                            'city': '',
                            'zip': ''
                        })
                self.update_contacts_table()
                self.update_statistics()
                self.log_message(f"Reloaded {len(self.contacts_data)} contacts")
            except Exception as e:
                self.log_message(f"Error reloading contacts: {str(e)}")
    
    def clear_contacts(self):
        """Clear all contacts"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all contacts?"):
            self.contacts_data = []
            self.update_contacts_table()
            self.update_statistics()
            if CONTACTS_FILE.exists():
                CONTACTS_FILE.unlink()
            self.log_message("Cleared all contacts")
    
    def update_contacts_table(self):
        """Update the contacts table"""
        # Clear existing items
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)
        
        # Add contacts
        for contact in self.contacts_data:
            self.contacts_tree.insert("", "end", values=(
                contact['name'],
                contact['phone'],
                contact.get('city', ''),
                contact.get('zip', '')
            ))
    
    def update_results_table(self):
        """Update the results table"""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Filter results
        filter_val = self.filter_status.get().lower()
        filtered_results = self.call_results
        if filter_val != "all":
            filtered_results = [r for r in self.call_results if r.status.lower() == filter_val]
        
        # Add results
        for result in filtered_results:
            tag = result.status.lower().replace(' ', '-')
            self.results_tree.insert("", "end", values=(
                result.timestamp,
                result.name,
                result.phone,
                result.status.title(),
                result.agent
            ), tags=(tag,))
        
        # Update summary
        total = len(self.call_results)
        answered = len([r for r in self.call_results if r.status == 'answered'])
        voicemail = len([r for r in self.call_results if r.status == 'voicemail'])
        no_answer = len([r for r in self.call_results if r.status == 'no-answer'])
        
        self.summary_label.config(
            text=f"Total: {total} | Answered: {answered} | Voicemail: {voicemail} | No Answer: {no_answer}"
        )
    
    def export_results(self):
        """Export results to CSV"""
        if not self.call_results:
            messagebox.showinfo("Info", "No results to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"call_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Name', 'Phone', 'Status', 'Agent'])
                    for result in self.call_results:
                        writer.writerow([result.timestamp, result.name, result.phone, 
                                       result.status, result.agent])
                messagebox.showinfo("Success", f"Exported {len(self.call_results)} results to {filename}")
                self.log_message(f"Exported results to {Path(filename).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def browse_voicemail(self):
        """Browse for voicemail file"""
        filename = filedialog.askopenfilename(
            title="Select Voicemail Audio",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")]
        )
        if filename:
            self.voicemail_path.delete(0, tk.END)
            self.voicemail_path.insert(0, filename)
    
    def detect_ngrok_url(self):
        """Auto-detect ngrok URL"""
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            data = response.json()
            if data.get('tunnels'):
                url = data['tunnels'][0]['public_url']
                self.webhook_url.delete(0, tk.END)
                self.webhook_url.insert(0, url)
                messagebox.showinfo("Success", f"Detected ngrok URL: {url}")
                self.log_message(f"Auto-detected ngrok URL: {url}")
            else:
                messagebox.showwarning("Warning", "No ngrok tunnels found. Make sure ngrok is running.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not detect ngrok URL: {str(e)}\n\nMake sure ngrok is running.")
    
    def save_settings(self):
        """Save settings to config.ini"""
        try:
            # Update config
            self.config['twilio']['account_sid'] = self.twilio_sid.get()
            self.config['twilio']['auth_token'] = self.twilio_token.get()
            self.config['twilio']['from_number'] = self.twilio_number.get()
            self.config['twilio']['webhook_base_url'] = self.webhook_url.get()
            
            # Save to file
            self.save_config()
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.log_message("Settings saved")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def refresh_agent_status(self):
        """Refresh agent status from webhook server"""
        try:
            response = requests.get("http://localhost:5000/status", timeout=2)
            data = response.json()
            
            # Clear existing items
            for item in self.agents_tree.get_children():
                self.agents_tree.delete(item)
            
            # Update with live data
            for agent in data.get('agents', []):
                status = "Available" if agent['available'] else "Busy"
                self.agents_tree.insert("", "end", values=(
                    agent['extension'],
                    agent['name'],
                    status,
                    agent.get('current_call', '—')
                ))
            
            self.log_message("Agent status refreshed")
        except Exception as e:
            self.log_message(f"Could not refresh agent status: {str(e)}")
            # Show default data
            for item in self.agents_tree.get_children():
                self.agents_tree.delete(item)
            self.agents_tree.insert("", "end", values=("101", "Agent 1", "Unknown", "—"))
            self.agents_tree.insert("", "end", values=("102", "Agent 2", "Unknown", "—"))

    # ========== Service Control ==========
    
    def find_ngrok(self):
        """Find ngrok executable in common locations"""
        import shutil
        from pathlib import Path
        
        # Check if ngrok is in PATH
        ngrok_path = shutil.which("ngrok")
        if ngrok_path:
            return ngrok_path
        
        # Check in the same folder as the app (highest priority)
        local_ngrok = APP_DIR / "ngrok.exe"
        if local_ngrok.exists():
            return str(local_ngrok)
        
        # Check common Windows locations
        common_paths = [
            Path.home() / "Downloads" / "ngrok.exe",
            Path("C:/ngrok/ngrok.exe"),
            Path("C:/Program Files/ngrok/ngrok.exe"),
            Path("C:/Program Files (x86)/ngrok/ngrok.exe"),
            Path.home() / "AppData" / "Local" / "ngrok" / "ngrok.exe",
            Path("C:/Users/Admin/Downloads/ngrok.exe"),
        ]
        
        for path in common_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def start_asterisk(self):
        """Start Asterisk service"""
        try:
            # Check if running in WSL2
            result = subprocess.run(
                ["uname", "-r"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if "microsoft" in result.stdout.lower() or "wsl" in result.stdout.lower():
                # Running in WSL2
                self.log_message("Starting Asterisk service...")
                
                # Try to start Asterisk
                # First check if already running
                check = subprocess.run(
                    ["systemctl", "is-active", "asterisk"],
                    capture_output=True,
                    text=True
                )
                
                if "active" in check.stdout:
                    self.log_message("Asterisk is already running")
                    return True
                
                # Try to start without sudo first (if user has permissions)
                start = subprocess.run(
                    ["systemctl", "start", "asterisk"],
                    capture_output=True,
                    text=True
                )
                
                if start.returncode == 0:
                    self.log_message("Asterisk started successfully")
                    return True
                else:
                    # Need sudo - try with sudo
                    self.log_message("Starting Asterisk with sudo...")
                    start_sudo = subprocess.run(
                        ["sudo", "-n", "systemctl", "start", "asterisk"],
                        capture_output=True,
                        text=True
                    )
                    
                    if start_sudo.returncode == 0:
                        self.log_message("Asterisk started successfully")
                        return True
                    else:
                        # Sudo requires password - show message
                        self.log_message("Asterisk requires sudo password")
                        messagebox.showwarning("Asterisk Startup",
                            "Asterisk needs to be started with sudo.\n\n"
                            "Please run this command in WSL2:\n"
                            "sudo systemctl start asterisk\n\n"
                            "Or configure passwordless sudo for Asterisk.")
                        return False
            else:
                self.log_message("Not running in WSL2 - cannot start Asterisk")
                return False
                
        except Exception as e:
            self.log_message(f"Error starting Asterisk: {e}")
            return False
    
    def start_services(self):
        """Start webhook server and ngrok"""
        try:
            # Start webhook server
            if not self.webhook_process or self.webhook_process.poll() is not None:
                webhook_script = APP_DIR / "webhook_server.py"
                self.webhook_process = subprocess.Popen(
                    [sys.executable, str(webhook_script)],
                    cwd=str(APP_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                self.log_message("Webhook server started")
            
            # Start ngrok - use Downloads folder directly
            if not self.ngrok_process or self.ngrok_process.poll() is not None:
                ngrok_path = Path("C:/Users/Admin/Downloads/ngrok.exe")
                
                if ngrok_path.exists():
                    self.ngrok_process = subprocess.Popen(
                        [str(ngrok_path), "http", "5000"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                    self.log_message(f"Ngrok started from Downloads folder")
                    # Wait for ngrok to start and auto-detect URL
                    self.root.after(3000, self.detect_ngrok_url)
                else:
                    self.log_message("ERROR: ngrok.exe not found in C:/Users/Admin/Downloads/")
                    messagebox.showerror("Ngrok Not Found",
                        "ngrok.exe not found in Downloads folder.\n\n"
                        "Expected location:\n"
                        "C:/Users/Admin/Downloads/ngrok.exe\n\n"
                        "Please place ngrok.exe there.")
            
            messagebox.showinfo("Services Started", 
                "Webhook server and ngrok started!\n\n"
                "Wait 5 seconds for status to update.")
            
            # Auto-refresh status after 5 seconds
            self.root.after(5000, self.force_status_update)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start services: {str(e)}")
            self.log_message(f"Error starting services: {str(e)}")
    
    def stop_services(self):
        """Stop webhook server and ngrok"""
        try:
            if self.webhook_process and self.webhook_process.poll() is None:
                self.webhook_process.terminate()
                self.webhook_process.wait(timeout=5)
                self.log_message("Webhook server stopped")
            
            if self.ngrok_process and self.ngrok_process.poll() is None:
                self.ngrok_process.terminate()
                self.ngrok_process.wait(timeout=5)
                self.log_message("Ngrok tunnel stopped")
            
            messagebox.showinfo("Success", "Services stopped successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop services: {str(e)}")
            self.log_message(f"Error stopping services: {str(e)}")
    
    def start_calling(self):
        """Start the dialing campaign"""
        # Validation
        if not self.contacts_data:
            messagebox.showerror("Error", "No contacts loaded. Please upload a CSV file first.")
            return
        
        if not self.config.get('twilio', 'account_sid') or not self.config.get('twilio', 'auth_token'):
            messagebox.showerror("Error", "Twilio credentials not configured. Please check Settings tab.")
            return
        
        if not self.config.get('twilio', 'webhook_base_url'):
            messagebox.showerror("Error", "Webhook URL not configured. Please check Settings tab.")
            return
        
        # Check if services are running
        try:
            requests.get("http://localhost:5000/status", timeout=2)
        except:
            if messagebox.askyesno("Services Not Running", 
                                   "Webhook server is not running. Start services now?"):
                self.start_services()
                self.root.after(3000, self.start_calling)  # Retry after services start
                return
            else:
                return
        
        # Confirm start
        if not messagebox.askyesno("Confirm", 
                                   f"Start calling {len(self.contacts_data)} contacts?"):
            return
        
        try:
            # Start dialer in background thread
            self.is_calling = True
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            dialer_thread = threading.Thread(target=self.run_dialer, daemon=True)
            dialer_thread.start()
            
            self.log_message(f"Started calling campaign with {len(self.contacts_data)} contacts")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start calling: {str(e)}")
            self.log_message(f"Error starting campaign: {str(e)}")
            self.is_calling = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def run_dialer(self):
        """Run the dialer script"""
        try:
            dialer_script = APP_DIR / "dialer.py"
            self.dialer_process = subprocess.Popen(
                [sys.executable, str(dialer_script)],
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Read output in real-time
            for line in self.dialer_process.stdout:
                if not self.is_calling:
                    break
                self.log_message(line.strip())
                
                # Parse call results from output
                if "answered" in line.lower() or "voicemail" in line.lower() or "no answer" in line.lower():
                    self.parse_call_result(line)
            
            self.dialer_process.wait()
            
            # Update UI when done
            self.root.after(0, self.calling_finished)
            
        except Exception as e:
            self.log_message(f"Dialer error: {str(e)}")
            self.root.after(0, self.calling_finished)
    
    def parse_call_result(self, line):
        """Parse call result from dialer output"""
        # This is a simple parser - adjust based on actual dialer output format
        try:
            # Example: "Called John Smith (+14145551001): answered by Agent 1"
            # You'll need to adjust this based on your actual dialer output
            pass
        except:
            pass
    
    def stop_calling(self):
        """Stop the dialing campaign"""
        if messagebox.askyesno("Confirm", "Stop the calling campaign?"):
            self.is_calling = False
            if self.dialer_process and self.dialer_process.poll() is None:
                self.dialer_process.terminate()
                try:
                    self.dialer_process.wait(timeout=5)
                except:
                    self.dialer_process.kill()
            
            self.calling_finished()
            self.log_message("Calling campaign stopped by user")
    
    def calling_finished(self):
        """Called when calling campaign finishes"""
        self.is_calling = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log_message("Calling campaign finished")
        self.update_statistics()
        self.update_results_table()
    
    # ========== Status Updates ==========
    
    def force_status_update(self):
        """Force an immediate status update"""
        self.log_message("Refreshing status...")
        self.update_status()
    
    def update_status(self):
        """Update system status indicators"""
        # Check Asterisk
        try:
            result = subprocess.run(
                ["asterisk", "-rx", "core show version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                self.asterisk_status.config(foreground="green")
                self.asterisk_label.config(text="Running")
            else:
                self.asterisk_status.config(foreground="red")
                self.asterisk_label.config(text="Not running")
        except:
            self.asterisk_status.config(foreground="red")
            self.asterisk_label.config(text="Not running")
        
        # Check webhook server
        try:
            # First check if process is running
            if self.webhook_process and self.webhook_process.poll() is None:
                # Process is running, now check if it's responding
                try:
                    response = requests.get("http://localhost:5000/status", timeout=2)
                    if response.status_code == 200:
                        self.webhook_status.config(foreground="green")
                        self.webhook_label.config(text="Running on port 5000")
                    else:
                        self.webhook_status.config(foreground="orange")
                        self.webhook_label.config(text="Starting...")
                except requests.exceptions.RequestException:
                    # Process running but not responding yet
                    self.webhook_status.config(foreground="orange")
                    self.webhook_label.config(text="Starting...")
            else:
                self.webhook_status.config(foreground="red")
                self.webhook_label.config(text="Not running")
        except Exception as e:
            self.webhook_status.config(foreground="red")
            self.webhook_label.config(text="Not running")
        
        # Check ngrok
        try:
            # First check if process is running
            if self.ngrok_process and self.ngrok_process.poll() is None:
                # Process is running, now check API
                try:
                    response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
                    data = response.json()
                    if data.get('tunnels'):
                        url = data['tunnels'][0]['public_url']
                        self.ngrok_status.config(foreground="green")
                        self.ngrok_label.config(text=f"Active: {url}")
                    else:
                        self.ngrok_status.config(foreground="orange")
                        self.ngrok_label.config(text="Starting...")
                except requests.exceptions.RequestException:
                    # Process running but API not ready yet
                    self.ngrok_status.config(foreground="orange")
                    self.ngrok_label.config(text="Starting...")
            else:
                self.ngrok_status.config(foreground="gray")
                self.ngrok_label.config(text="Not running")
        except Exception as e:
            self.ngrok_status.config(foreground="gray")
            self.ngrok_label.config(text="Not running")
        
        # Schedule next update
        self.root.after(5000, self.update_status)
    
    def update_statistics(self):
        """Update statistics display"""
        total = len(self.contacts_data)
        answered = len([r for r in self.call_results if r.status == 'answered'])
        voicemail = len([r for r in self.call_results if r.status == 'voicemail'])
        no_answer = len([r for r in self.call_results if r.status == 'no-answer'])
        
        self.stat_total_contacts.config(text=str(total))
        self.stat_answered.config(text=str(answered))
        self.stat_voicemail.config(text=str(voicemail))
        self.stat_no_answer.config(text=str(no_answer))
    
    def log_message(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.config(state='normal')
        self.activity_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_log.see(tk.END)
        self.activity_log.config(state='disabled')


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')
    
    # Custom button styles
    style.configure("Success.TButton", foreground="white", background="#28a745", font=("Arial", 10, "bold"))
    style.configure("Danger.TButton", foreground="white", background="#dc3545", font=("Arial", 10, "bold"))
    
    # Create app
    app = DialerApp(root)
    
    # Run
    root.mainloop()


if __name__ == "__main__":
    main()
