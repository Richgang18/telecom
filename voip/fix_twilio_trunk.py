#!/usr/bin/env python3
"""
fix_twilio_trunk.py — Add credentials and IP to existing Twilio trunk

Usage:
    export TWILIO_ACCOUNT_SID=ACxxxxxxxx
    export TWILIO_AUTH_TOKEN=xxxxxxxx
    python3 fix_twilio_trunk.py
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
TRUNK_SID = "TK207bd184b6c772ac0d4085538323a357"

def get_public_ip():
    try:
        resp = requests.get("https://api.ipify.org", timeout=5)
        return resp.text.strip()
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None

def main():
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        sys.exit(1)
    
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    print("=== Fixing Twilio Trunk ===\n")
    
    # Get public IP
    public_ip = get_public_ip()
    print(f"Public IP: {public_ip}\n")
    
    # Create credential list
    print("Creating credential list...")
    url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/CredentialLists.json"
    resp = requests.post(url, auth=auth, data={"FriendlyName": "Asterisk Creds"})
    
    if resp.status_code == 201:
        cred_list = resp.json()
        cred_list_sid = cred_list['sid']
        print(f"✓ Credential list: {cred_list_sid}")
        
        # Add credential
        cred_url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/CredentialLists/{cred_list_sid}/Credentials.json"
        username = "asterisk"
        password = "Str0ngTwili0Pass!"
        cred_resp = requests.post(cred_url, auth=auth, data={"Username": username, "Password": password})
        
        if cred_resp.status_code == 201:
            print(f"✓ Credential added: {username} / {password}")
        else:
            print(f"✗ Credential failed: {cred_resp.text}")
        
        # Link to trunk
        trunk_url = f"https://trunking.twilio.com/v1/Trunks/{TRUNK_SID}/CredentialLists"
        trunk_resp = requests.post(trunk_url, auth=auth, data={"CredentialListSid": cred_list_sid})
        if trunk_resp.status_code == 201:
            print(f"✓ Linked to trunk")
    else:
        print(f"✗ Failed: {resp.text}")
    
    print()
    
    # Create IP ACL
    print("Creating IP ACL...")
    acl_url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/IpAccessControlLists.json"
    acl_resp = requests.post(acl_url, auth=auth, data={"FriendlyName": "Asterisk IP"})
    
    if acl_resp.status_code == 201:
        acl = acl_resp.json()
        acl_sid = acl['sid']
        print(f"✓ IP ACL: {acl_sid}")
        
        # Add IP
        ip_url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/IpAccessControlLists/{acl_sid}/IpAddresses.json"
        ip_resp = requests.post(ip_url, auth=auth, data={"FriendlyName": "Server", "IpAddress": public_ip})
        
        if ip_resp.status_code == 201:
            print(f"✓ IP added: {public_ip}")
        else:
            print(f"✗ IP failed: {ip_resp.text}")
        
        # Link to trunk
        trunk_ip_url = f"https://trunking.twilio.com/v1/Trunks/{TRUNK_SID}/IpAccessControlLists"
        trunk_ip_resp = requests.post(trunk_ip_url, auth=auth, data={"IpAccessControlListSid": acl_sid})
        if trunk_ip_resp.status_code == 201:
            print(f"✓ Linked to trunk")
    else:
        print(f"✗ Failed: {acl_resp.text}")
    
    print("\n=== Complete ===")
    print(f"Trunk SID:    {TRUNK_SID}")
    print(f"SIP Domain:   dataism-voip.pstn.twilio.com")
    print(f"Username:     asterisk")
    print(f"Password:     Str0ngTwili0Pass!")
    print(f"IP:           {public_ip}")

if __name__ == "__main__":
    main()
