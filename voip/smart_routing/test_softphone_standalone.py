#!/usr/bin/env python3
"""
Standalone Softphone Test
Launch this to test the softphone without the full desktop app
"""

import tkinter as tk
from tkinter import messagebox
import sys

try:
    from softphone import launch_softphone
    print("✓ Softphone module loaded successfully")
except ImportError as e:
    print(f"✗ Failed to import softphone: {e}")
    print("\nMake sure you have installed:")
    print("  pip install pyaudio")
    sys.exit(1)

def main():
    """Test the softphone"""
    root = tk.Tk()
    root.title("Softphone Test")
    root.geometry("400x300")
    
    # Header
    header = tk.Label(root, text="Softphone Test", font=("Arial", 18, "bold"))
    header.pack(pady=20)
    
    info = tk.Label(root, text="Click a button to launch a test softphone", 
                   font=("Arial", 11))
    info.pack(pady=10)
    
    # Configuration
    config_frame = tk.LabelFrame(root, text="Configuration", padx=20, pady=10)
    config_frame.pack(pady=20)
    
    tk.Label(config_frame, text="Domain:").grid(row=0, column=0, sticky='w', pady=5)
    domain_entry = tk.Entry(config_frame, width=20)
    domain_entry.insert(0, "172.25.17.93")
    domain_entry.grid(row=0, column=1, pady=5)
    
    tk.Label(config_frame, text="Port:").grid(row=1, column=0, sticky='w', pady=5)
    port_entry = tk.Entry(config_frame, width=20)
    port_entry.insert(0, "5060")
    port_entry.grid(row=1, column=1, pady=5)
    
    # Launch buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)
    
    def launch_agent1():
        try:
            domain = domain_entry.get()
            port = int(port_entry.get())
            softphone = launch_softphone(root, "101", "ChangeMe101!", domain, port)
            messagebox.showinfo("Success", "Agent 1 softphone launched!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch:\n{str(e)}")
    
    def launch_agent2():
        try:
            domain = domain_entry.get()
            port = int(port_entry.get())
            softphone = launch_softphone(root, "102", "ChangeMe102!", domain, port)
            messagebox.showinfo("Success", "Agent 2 softphone launched!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch:\n{str(e)}")
    
    tk.Button(button_frame, text="Launch Agent 1 (Ext 101)", 
             command=launch_agent1, width=25, height=2,
             bg="#3498db", fg="white", font=("Arial", 11, "bold")).pack(pady=5)
    
    tk.Button(button_frame, text="Launch Agent 2 (Ext 102)", 
             command=launch_agent2, width=25, height=2,
             bg="#2ecc71", fg="white", font=("Arial", 11, "bold")).pack(pady=5)
    
    # Instructions
    instructions = tk.Label(root, 
                           text="Make sure Asterisk is running in WSL2",
                           font=("Arial", 9), fg="gray")
    instructions.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    print("=" * 50)
    print("Softphone Standalone Test")
    print("=" * 50)
    print("")
    print("This will launch a test softphone window.")
    print("Make sure:")
    print("  1. Asterisk is running in WSL2")
    print("  2. Endpoints 101 and 102 are configured")
    print("  3. PyAudio is installed (pip install pyaudio)")
    print("")
    print("=" * 50)
    print("")
    
    main()
