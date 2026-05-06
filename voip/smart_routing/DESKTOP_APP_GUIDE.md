# Smart Outbound Dialer - Desktop Application Guide

## 🎯 Overview

Professional desktop application for managing outbound calling campaigns with live agent connection and voicemail drop capabilities.

## ✨ Features

- **📊 Dashboard** - Real-time campaign monitoring with start/stop controls
- **📋 CSV Upload** - Drag & drop contact lists with automatic phone formatting
- **📞 Call Results** - Live tracking of answered, voicemail, and no-answer calls
- **⚙ Settings** - Easy configuration of Twilio credentials and webhook URLs
- **👥 Agent Management** - Monitor agent status and Linphone configuration
- **📈 Reports** - Export call results to CSV for analysis
- **🚀 Service Control** - One-click start/stop for webhook server and ngrok

## 🚀 Quick Start

### Windows

1. Double-click `launch_app.bat`
2. The application will start automatically

### WSL2/Linux

```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
./launch_app.sh
```

Or directly:
```bash
python3 desktop_app.py
```

## 📋 Setup Guide

### Step 1: First Launch

When you first launch the app, you'll see the Dashboard with system status indicators.

### Step 2: Configure Settings

1. Click the **⚙ Settings** tab
2. Fill in your Twilio credentials:
   - Account SID: `ACcf15065d54bfedd91baec3cc1283561c`
   - Auth Token: `34677dad892d854fcf70b7b2a4003faf`
   - From Number: `+17868339866`
3. Click **💾 Save Settings**

### Step 3: Start Services

1. Go back to the **📊 Dashboard** tab
2. Click **🚀 Start Services**
   - This starts the webhook server on port 5000
   - This starts ngrok tunnel (if installed)
3. Wait 3 seconds for ngrok to initialize
4. Go to **⚙ Settings** tab
5. Click **🔄 Auto-detect Ngrok URL**
6. Click **💾 Save Settings**

### Step 4: Upload Contacts

1. Click the **📋 Contacts** tab
2. Click **📁 Browse CSV File**
3. Select your CSV file with columns:
   - `Firstname`
   - `Lastname`
   - `Dob`
   - `Phone`
   - `Address1`
   - `Address2`
   - `City`
   - `Zip`
4. The app will automatically:
   - Extract name and phone
   - Format phone numbers to E.164 (+1XXXXXXXXXX)
   - Save to internal format

### Step 5: Configure Agents

1. Click the **👥 Agents** tab
2. Install Linphone on 2 agent devices: https://www.linphone.org/
3. Configure each agent with:

**Agent 1:**
- Extension: `101`
- Password: `ChangeMe101!`
- Domain: `pbx.vouchersdept.com`
- Port: `5061`
- Transport: `TLS`

**Agent 2:**
- Extension: `102`
- Password: `ChangeMe102!`
- Domain: `pbx.vouchersdept.com`
- Port: `5061`
- Transport: `TLS`

4. Click **🔄 Refresh Status** to verify agents are registered

### Step 6: Start Calling

1. Go to **📊 Dashboard** tab
2. Verify all status indicators are green:
   - ● Asterisk: Running
   - ● Webhook Server: Running on port 5000
   - ● Ngrok Tunnel: Active
3. Click **▶ Start Calling**
4. Confirm the campaign start
5. Monitor progress in the Activity Log

### Step 7: Monitor Results

1. Click the **📞 Call Results** tab
2. View real-time call outcomes:
   - 🟢 **Answered** - Connected to agent
   - 🟡 **Voicemail** - Voicemail dropped
   - 🔴 **No Answer** - No response
3. Filter by status using the dropdown
4. Click **📊 Export to CSV** to save results

## 🎮 Using the Application

### Dashboard Tab

**System Status:**
- Green ● = Service running
- Red ● = Service not running
- Gray ● = Service not detected

**Campaign Control:**
- **▶ Start Calling** - Begin dialing contacts
- **⏹ Stop Calling** - Stop current campaign
- **🚀 Start Services** - Start webhook server and ngrok
- **⏸ Stop Services** - Stop all background services

**Statistics:**
- **Total Contacts** - Number of loaded contacts
- **Answered** - Calls connected to agents
- **Voicemail** - Voicemails dropped
- **No Answer** - Unanswered calls

**Activity Log:**
- Real-time event logging
- Scroll to see history
- Auto-scrolls to latest events

### Contacts Tab

**Upload Contacts:**
- Click **📁 Browse CSV File** to select file
- Click **🔄 Reload Contacts** to refresh from file
- Click **🗑 Clear All** to remove all contacts

**Contact Table:**
- Shows: Name, Phone, City, Zip
- Automatically formatted phone numbers
- Scrollable for large lists

### Call Results Tab

**Filter Results:**
- Dropdown to filter by status
- **All** - Show all calls
- **Answered** - Only successful connections
- **Voicemail** - Only voicemail drops
- **No Answer** - Only unanswered calls

**Export:**
- Click **📊 Export to CSV**
- Choose save location
- File includes: Timestamp, Name, Phone, Status, Agent

**Summary:**
- Shows total counts for each status
- Updates in real-time during campaign

### Settings Tab

**Twilio Configuration:**
- Account SID from Twilio console
- Auth Token (hidden for security)
- From Number (your Twilio number)
- Webhook URL (auto-detected from ngrok)

**Voicemail Configuration:**
- Path to voicemail.mp3 file
- Click **Browse** to select different file

**Dialer Configuration:**
- Ring Timeout: How long to wait for answer (10-60 seconds)
- Batch Delay: Delay between dialing batches (1-10 seconds)

**Save:**
- Click **💾 Save Settings** to apply changes
- Settings saved to `config.ini`

### Agents Tab

**Agent Configuration:**
- Shows Linphone setup details for each agent
- Extension, password, domain, port

**Agent Status:**
- Real-time status of each agent
- Shows: Extension, Name, Status, Current Call
- Click **🔄 Refresh Status** to update

**Linphone Setup:**
- Link to download Linphone
- Instructions for agent configuration

## 📊 CSV Format

Your CSV file should have these columns:

```csv
Firstname,Lastname,Dob,Phone,Address1,Address2,City,Zip
John,Smith,1980-01-15,4145551001,123 Main St,Apt 4,Miami,33101
Jane,Doe,1975-05-20,4145551002,456 Oak Ave,,Tampa,33602
```

**Notes:**
- Phone numbers can be with or without country code
- App automatically adds +1 for US numbers
- Only `Firstname`, `Lastname`, and `Phone` are required
- Other columns are optional but recommended

## 🔧 Troubleshooting

### Services Won't Start

**Problem:** Webhook server or ngrok fails to start

**Solution:**
1. Check if ports are already in use:
   ```bash
   netstat -ano | findstr :5000
   netstat -ano | findstr :4040
   ```
2. Close any processes using these ports
3. Try starting services again

### Ngrok Not Found

**Problem:** "Ngrok not found" warning

**Solution:**
1. Install ngrok:
   ```bash
   # In WSL2
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
   echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
   sudo apt update && sudo apt install ngrok
   ```
2. OR configure port forwarding manually on your router
3. Update webhook URL in Settings tab

### Asterisk Not Running

**Problem:** Red ● next to Asterisk status

**Solution:**
1. In WSL2, run:
   ```bash
   sudo systemctl start asterisk
   sudo systemctl status asterisk
   ```
2. If still not working, redeploy:
   ```bash
   cd /mnt/c/Users/Admin/SPdevTech/telecom/voip
   sudo -E python3 deploy.py
   ```

### Agents Not Registering

**Problem:** Agents show "Unknown" status

**Solution:**
1. Verify Linphone configuration matches exactly
2. Check domain resolves: `ping pbx.vouchersdept.com`
3. Verify port 5061 is open
4. Check Asterisk logs:
   ```bash
   asterisk -rx "pjsip show registrations"
   ```

### Calls Not Connecting

**Problem:** Calls initiated but not reaching agents

**Solution:**
1. Verify webhook URL is publicly accessible
2. Test webhook: `curl https://your-ngrok-url.ngrok.io/status`
3. Check Twilio console for webhook errors
4. Verify agents are registered in Linphone
5. Check Activity Log for error messages

### CSV Upload Fails

**Problem:** "Failed to load CSV" error

**Solution:**
1. Verify CSV has `Phone` column (case-sensitive)
2. Check file encoding is UTF-8
3. Ensure no special characters in phone numbers
4. Try opening CSV in Excel and re-saving

## 📁 File Structure

```
smart_routing/
├── desktop_app.py          ← Main desktop application
├── launch_app.bat          ← Windows launcher
├── launch_app.sh           ← Linux launcher
├── config.ini              ← Configuration (auto-created)
├── contacts.csv            ← Contact list (auto-created)
├── call_results.json       ← Call results database
├── smart_routing.log       ← Activity log
├── voicemail.mp3           ← Your voicemail recording
├── dialer.py               ← Background dialer script
├── webhook_server.py       ← Webhook server
├── agent_router.py         ← Agent routing logic
├── voicemail_drop.py       ← Voicemail drop logic
└── requirements.txt        ← Python dependencies
```

## 🔐 Security Notes

- Auth tokens are hidden in the UI (shown as ***)
- Config.ini contains sensitive credentials - keep secure
- Never commit config.ini to version control
- Use strong passwords for Linphone extensions
- Ngrok URLs are temporary - update after each restart

## 📞 Support

For issues or questions:
1. Check the Activity Log in Dashboard tab
2. Review `smart_routing.log` file
3. Check Asterisk logs: `asterisk -rx "core show channels"`
4. Verify Twilio console for webhook errors

## 🎯 Best Practices

1. **Test First**: Use a small contact list (5-10) for initial testing
2. **Monitor Agents**: Ensure agents are ready before starting campaign
3. **Check Voicemail**: Test voicemail.mp3 plays correctly
4. **Export Results**: Regularly export call results for backup
5. **Update Webhook**: If ngrok restarts, update webhook URL in Settings
6. **Agent Availability**: Ensure agents are logged into Linphone before calling
7. **Batch Size**: System automatically limits to 2 concurrent calls (1 per agent)

## 🚀 Production Deployment

For production use:

1. **Replace Ngrok** with proper port forwarding:
   - Forward port 5000 from public IP to your machine
   - Update webhook URL to: `https://pbx.vouchersdept.com:5000`

2. **SSL Certificate**: Install proper TLS certificate (not self-signed)

3. **Firewall**: Ensure ports 5060, 5061, 5000 are open

4. **Monitoring**: Set up log monitoring and alerts

5. **Backup**: Regularly backup call_results.json and config.ini

6. **Scaling**: For more than 2 agents, update config.ini:
   ```ini
   [agents]
   max_concurrent_calls = 4
   agent_extensions = 101,102,103,104
   agent_names = Agent 1,Agent 2,Agent 3,Agent 4
   ```

---

**Version:** 1.0.0  
**Last Updated:** May 6, 2026  
**Platform:** Windows 10/11, WSL2 Ubuntu 24.04
