"""
generate_linphone_guide.py — Linphone softphone configuration guide generator.

Produces a Markdown file (linphone_setup.md) with step-by-step instructions
for configuring Linphone, making calls, troubleshooting, and administrator
commands for the VoIP system.

Requirements: 3.3, 3.4, 3.7, 12.5, 15.1, 15.2, 15.3, 15.4, 15.5
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Guide content
# ---------------------------------------------------------------------------

LINPHONE_GUIDE_CONTENT: str = r"""# Linphone Softphone Configuration Guide

This guide covers how to configure Linphone for use with the Asterisk PBX,
make internal and outbound calls, troubleshoot common issues, and run
administrator commands.

---

## 1. Account Setup in Linphone

Follow these steps to add your SIP account in Linphone (desktop or mobile).

### 1.1 Open Account Settings

1. Launch Linphone.
2. Go to **Preferences** (desktop) or **Settings → Account** (mobile).
3. Click **Add account** (or the **+** button on mobile).

### 1.2 Enter Account Details

| Field | Value |
|---|---|
| **SIP address / Username** | Your 3-digit extension (e.g. `101`) |
| **SIP domain / Server address** | `pbx.vouchersdept.com` |
| **Password** | Your extension password (≥ 12 mixed alphanumeric characters) |
| **Display name** | Your name (e.g. `Alice Smith`) |
| **Transport** | `TLS` |
| **Port** | `5061` |

> **Important:** Transport must be set to **TLS** and port must be **5061**.
> Plain SIP on port 5060 is blocked by the firewall.

### 1.3 Set Transport to TLS on Port 5061

1. In the account settings, locate the **Transport** or **Protocol** field.
2. Select **TLS** from the dropdown.
3. Set the **SIP port** to **5061**.
4. Save the account settings.

### 1.4 Enable SRTP (Media Encryption)

SRTP encrypts your audio media stream. To enable it:

1. Go to **Preferences → Audio/Video** (desktop) or **Settings → Audio/Video** (mobile).
2. Find **Media encryption** (or **SRTP**).
3. Select **SRTP** from the dropdown.
4. Save the settings.

> Linphone will now negotiate SRTP for all calls, matching the Asterisk
> `media_encryption=sdes` setting on the server.

### 1.5 Set Codec Preferences (G.711 ulaw and alaw)

To ensure compatibility with the PSTN trunk and minimise transcoding:

1. Go to **Preferences → Audio** (desktop) or **Settings → Audio codecs** (mobile).
2. In the codec list, locate **PCMU/8000** (G.711 ulaw) and **PCMA/8000** (G.711 alaw).
3. Move both codecs to the **top** of the list using the up arrow or drag-and-drop.
4. Disable any codecs that are not needed (optional).
5. Save the settings.

### 1.6 Set Re-registration Interval

To keep your registration active and match the server's re-registration window:

1. Go to **Preferences → Account** (or the account detail screen).
2. Find **Expire** or **Registration duration** (in seconds).
3. Set the value to **1800** seconds (30 minutes).
4. Save the settings.

> The Asterisk server accepts registrations up to 3600 seconds. Setting
> 1800 seconds ensures Linphone re-registers before the server-side expiry.

### 1.7 Verify Registration

After saving, Linphone should display a **green dot** or **"Registered"**
status next to your account. If registration fails, see
[Section 4 — Troubleshooting](#4-troubleshooting).

---

## 2. Making Internal Calls

Internal calls connect directly between extensions (101–105) without going
through the PSTN trunk.

### Steps

1. Ensure your Linphone account shows **Registered** status.
2. In the Linphone dial pad, enter the **3-digit extension** of the person
   you want to call (e.g. `102`, `103`, `104`, or `105`).
3. Press the **Call** button (green phone icon).
4. The call will ring for up to **30 seconds**. If unanswered, Linphone
   returns to idle.

### Notes

- Internal calls use **SRTP** for encrypted audio.
- The caller ID displayed to the recipient is your display name and extension.
- Internal calls do **not** consume PSTN trunk capacity.
- If you dial an extension outside the range 101–105, you will hear an
  invalid-number announcement and the call will end.

---

## 3. Making Outbound International Calls

Outbound calls are routed through the SIP trunk to the PSTN.

### 3.1 Dial Using E.164 Format

All outbound calls must be dialled in **E.164 format**: a `+` sign followed
by the country code and subscriber number, with no spaces or dashes.

**Examples:**

| Destination | Dial |
|---|---|
| US/Canada (country code 1) | `+12025551234` |
| UK (country code 44) | `+441234567890` |
| Australia (country code 61) | `+61298765432` |
| Germany (country code 49) | `+4930123456` |

### 3.2 Steps

1. In the Linphone dial pad, enter the number in E.164 format
   (e.g. `+12025551234`).
2. Press the **Call** button.
3. Linphone sends the call to Asterisk, which routes it through the SIP trunk.
4. Your outbound caller ID will be the verified DID (Direct Inward Dialing
   number) configured on the server — not your extension number.

### 3.3 US/Canada 11-Digit Format (Alternative)

You may also dial US and Canada numbers in 11-digit format starting with `1`
(e.g. `12025551234`). The dialplan accepts both formats.

### 3.4 Notes

- If the trunk is not registered, you will hear a fast busy tone and the
  call will fail with a **TRUNK_UNAVAILABLE** result. See
  [Section 4 — Troubleshooting](#4-troubleshooting).
- Emergency calls: dial `911` directly (no `+` prefix required).

---

## 4. Troubleshooting

### 4.1 Registration Failure

**Symptom:** Linphone shows a red dot, "Registration failed", or
"401 Unauthorized".

**Checklist:**

1. **Verify credentials** — confirm the username (extension), password, and
   SIP domain are entered correctly.
2. **Check transport and port** — transport must be **TLS**, port must be
   **5061**. Plain SIP (port 5060) is blocked.
3. **Check server reachability** — ping the PBX domain from a terminal:
   ```
   ping pbx.vouchersdept.com
   ```
4. **Check Windows portproxy** — on the Windows host, run:
   ```powershell
   netsh interface portproxy show all
   ```
   Confirm a rule forwards TCP 5061 to the WSL2 IP.
5. **Check Windows Firewall** — on the Windows host, run:
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "VoIP*"}
   ```
   Confirm the "VoIP SIP TLS" rule is enabled and set to Allow.
6. **Check if your IP is banned** — see
   [Section 4.4 — Banned IP Recovery](#44-banned-ip-recovery).
7. **Check Asterisk logs** inside WSL2:
   ```bash
   sudo tail -f /var/log/asterisk/messages
   ```

---

### 4.2 One-Way Audio

**Symptom:** You can hear the other party but they cannot hear you, or
vice versa.

**Cause:** Usually a NAT traversal issue.

**Checklist:**

1. **Verify SRTP is enabled** in Linphone (see Section 1.4). Mismatched
   encryption settings cause audio failure.
2. **Check RTP firewall rules** — on the Windows host, confirm UDP ports
   10000–20000 are allowed:
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "VoIP*"}
   ```
3. **Verify Asterisk NAT settings** — inside WSL2, confirm `pjsip.conf`
   contains `rtp_symmetric=yes`, `force_rport=yes`, and `direct_media=no`
   for your endpoint.
4. **Reload Asterisk** inside WSL2 after any config change:
   ```bash
   asterisk -rx "core reload"
   ```

---

### 4.3 Trunk Unavailable

**Symptom:** Outbound calls fail immediately with a fast busy tone. Asterisk
logs show `TRUNK_UNAVAILABLE`.

**Checklist:**

1. **Check trunk registration status** inside WSL2:
   ```bash
   asterisk -rx "pjsip show registrations"
   ```
   The trunk should show **Registered**. If it shows **Rejected** or
   **Unregistered**, the credentials or provider settings are incorrect.
2. **Verify trunk credentials** in `pjsip.conf` — check the `[auth]` section
   for the trunk.
3. **Check provider status** — log in to your SIP trunk provider's portal
   and verify the account is active and the DID is provisioned.
4. **Check Asterisk logs** for SIP error codes (404, 503, 486):
   ```bash
   sudo tail -f /var/log/asterisk/messages
   ```

---

### 4.4 Banned IP Recovery

**Symptom:** Registration suddenly fails from a specific device or network.
Asterisk logs show repeated 401 responses followed by silence (packets
dropped at the firewall).

**Cause:** Fail2Ban has banned the IP address after 5 or more failed
authentication attempts within 60 seconds.

**Steps to unban:**

1. Find the banned IP address. Inside WSL2, run:
   ```bash
   fail2ban-client status asterisk
   ```
   Look for the IP in the **Banned IP list**.

2. Unban the IP (replace `<IP>` with the actual address):
   ```bash
   fail2ban-client set asterisk unbanip <IP>
   ```

3. Verify the IP is no longer banned:
   ```bash
   fail2ban-client status asterisk
   ```

4. Retry registration in Linphone.

---

### 4.5 WSL2 Not Starting on Boot

**Symptom:** After a Windows reboot, Linphone cannot register. The PBX is
unreachable.

**Cause:** The WSL2 auto-start Task Scheduler task did not run, or WSL2
failed to start.

**Steps:**

1. **Check Task Scheduler** on the Windows host:
   - Open **Task Scheduler** (search in Start menu).
   - Navigate to **Task Scheduler Library**.
   - Find the task named **"WSL2 VoIP Startup"**.
   - Check the **Last Run Result** column. A result of `0x0` means success.
   - If the task is missing, re-run `setup_windows_host.ps1` as Administrator.

2. **Run the startup script manually** (PowerShell as Administrator):
   ```powershell
   C:\VoIP\wsl_startup.ps1
   ```
   This will start WSL2, update the portproxy rule with the current WSL2 IP,
   and start the Asterisk service.

3. **Verify WSL2 is running** (PowerShell):
   ```powershell
   wsl hostname -I
   ```
   This should return the WSL2 internal IP address.

4. **Verify Asterisk is running** inside WSL2:
   ```bash
   systemctl status asterisk
   ```

---

## 5. Administrator Commands

### 5.1 Commands Inside WSL2

Run these commands inside the WSL2 Ubuntu terminal.

**Check SIP registration status (extensions and trunk):**
```bash
asterisk -rx "pjsip show registrations"
```

**List all active call channels:**
```bash
asterisk -rx "core show channels"
```

**Check Fail2Ban status for the Asterisk jail:**
```bash
fail2ban-client status asterisk
```

**Unban a specific IP address (replace `<IP>` with the actual address):**
```bash
fail2ban-client set asterisk unbanip <IP>
```

**Reload Asterisk configuration without restarting:**
```bash
asterisk -rx "core reload"
```

**Reload only the PJSIP module:**
```bash
asterisk -rx "module reload res_pjsip.so"
```

**View live Asterisk log:**
```bash
sudo tail -f /var/log/asterisk/messages
```

**Check iptables firewall rules inside WSL2:**
```bash
sudo iptables -L -n -v
```

---

### 5.2 Commands on the Windows Host

Run these commands in a PowerShell window on the Windows 11 host.

**Show all netsh portproxy rules (verify TCP 5061 forwarding):**
```powershell
netsh interface portproxy show all
```

**List all VoIP-related Windows Firewall rules:**
```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "VoIP*"}
```

**Get the current WSL2 internal IP address:**
```powershell
wsl hostname -I
```

**Manually update the portproxy rule with the current WSL2 IP:**
```powershell
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]
netsh interface portproxy delete v4tov4 listenport=5061 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=5061 listenaddress=0.0.0.0 connectport=5061 connectaddress=$wslIP
```

**Run the WSL2 startup script manually (as Administrator):**
```powershell
C:\\VoIP\\wsl_startup.ps1
```

---

*Guide generated by `generate_linphone_guide.py`.*
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_guide(path: str = "linphone_setup.md") -> Path:
    """
    Write the Linphone configuration guide to *path*.

    Parameters
    ----------
    path:
        Destination file path. Defaults to ``linphone_setup.md`` in the
        current working directory.

    Returns
    -------
    Path
        The resolved Path of the written file.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(LINPHONE_GUIDE_CONTENT, encoding="utf-8")
    return dest.resolve()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    written = generate_guide()
    print(f"Guide written to: {written}")
