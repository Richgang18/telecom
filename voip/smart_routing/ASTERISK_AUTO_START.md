# 🚀 Asterisk Auto-Start Setup

## Problem

The desktop app needs to start Asterisk, but Asterisk requires `sudo` which asks for a password.

## Solution

Configure **passwordless sudo** for Asterisk service (one-time setup).

---

## Quick Setup (30 seconds)

### Step 1: Run Setup Script

In WSL2:
```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
chmod +x setup_sudo.sh
./setup_sudo.sh
```

Enter your password when prompted (only this once).

### Step 2: Test It

```bash
sudo -n systemctl start asterisk
```

If it starts without asking for password, you're done!

### Step 3: Use the App

Now when you click "Start Services" in the app:
- ✅ Asterisk starts automatically
- ✅ Webhook server starts
- ✅ Ngrok starts
- ✅ Everything ready!

---

## What It Does

The setup script creates a sudoers rule that allows your user to run these commands without a password:

```bash
sudo systemctl start asterisk
sudo systemctl stop asterisk
sudo systemctl restart asterisk
sudo systemctl status asterisk
```

**Security:** Only these specific commands are allowed, nothing else.

---

## Manual Setup (Alternative)

If you prefer to do it manually:

1. Edit sudoers:
   ```bash
   sudo visudo -f /etc/sudoers.d/asterisk-$(whoami)
   ```

2. Add this line (replace `dataist` with your username):
   ```
   dataist ALL=(ALL) NOPASSWD: /bin/systemctl start asterisk, /bin/systemctl stop asterisk, /bin/systemctl restart asterisk, /bin/systemctl status asterisk, /bin/systemctl is-active asterisk
   ```

3. Save and exit (Ctrl+X, Y, Enter)

4. Test:
   ```bash
   sudo -n systemctl start asterisk
   ```

---

## Verification

After setup, verify it works:

```bash
# Should start without asking for password
sudo -n systemctl start asterisk

# Check status
sudo -n systemctl status asterisk

# Should show "active (running)"
```

---

## Troubleshooting

### "sudo: a password is required"

**Problem:** Setup didn't work

**Solution:**
1. Check the sudoers file exists:
   ```bash
   ls -la /etc/sudoers.d/asterisk-*
   ```

2. Check permissions (should be 0440):
   ```bash
   ls -l /etc/sudoers.d/asterisk-*
   ```

3. Validate syntax:
   ```bash
   sudo visudo -c -f /etc/sudoers.d/asterisk-$(whoami)
   ```

4. Re-run setup script

### "visudo: syntax error"

**Problem:** Sudoers file has syntax error

**Solution:**
1. Remove the file:
   ```bash
   sudo rm /etc/sudoers.d/asterisk-$(whoami)
   ```

2. Run setup script again

---

## Removing Passwordless Sudo

If you want to remove this later:

```bash
sudo rm /etc/sudoers.d/asterisk-$(whoami)
```

---

## After Setup

**Desktop App Behavior:**

**Before Setup:**
- Click "Start Services"
- Asterisk: ⚠ Needs manual start
- Must run `sudo systemctl start asterisk` manually

**After Setup:**
- Click "Start Services"
- Asterisk: ✓ Started automatically
- Webhook: ✓ Started
- Ngrok: ✓ Started
- Everything ready!

---

## Summary

**One-time setup:** Run `./setup_sudo.sh` (30 seconds)  
**Result:** App starts everything automatically  
**Security:** Only Asterisk service commands allowed  
**Reversible:** Can remove anytime  

---

**Run the setup script now and the app will handle everything! 🚀**
