#!/usr/bin/env python3
"""
setup_twilio_trunk.py — Automated Twilio SIP trunk setup via API

Creates a SIP trunk, credential list, and configures termination.
Run with Twilio credentials as environment variables.

Usage:
    export TWILIO_ACCOUNT_SID=ACxxxxxxxx
    export TWILIO_AUTH_TOKEN=xxxxxxxx
    python3 setup_twilio_trunk.py
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth

# Twilio API base
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

def get_public_ip():
    """Get the public IP of this machine."""
    try:
        resp = requests.get("https://api.ipify.org", timeout=5)
        return resp.text.strip()
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None

def create_trunk(account_sid, auth_token, trunk_name="Dataism VoIP"):
    """Create a SIP trunk."""
    url = f"https://trunking.twilio.com/v1/Trunks"
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    data = {
        "FriendlyName": trunk_name,
        "DomainName": "dataism-voip.pstn.twilio.com"
    }
    
    resp = requests.post(url, auth=auth, data=data)
    if resp.status_code == 201:
        trunk = resp.json()
        print(f"✓ Trunk created: {trunk['sid']}")
        print(f"  Domain: {trunk['domain_name']}")
        return trunk
    else:
        print(f"✗ Failed to create trunk: {resp.status_code}")
        print(resp.text)
        return None

def create_credential_list(account_sid, auth_token, username="asterisk", password="Str0ngTwili0Pass!"):
    """Create a credential list for SIP authentication."""
    url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/CredentialLists.json"
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    data = {"FriendlyName": "Asterisk Credentials"}
    resp = requests.post(url, auth=auth, data=data)
    
    if resp.status_code == 201:
        cred_list = resp.json()
        cred_list_sid = cred_list['sid']
        print(f"✓ Credential list created: {cred_list_sid}")
        
        # Add credential to the list — URL without .json suffix for nested resource
        cred_url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/CredentialLists/{cred_list_sid}/Credentials.json"
        cred_data = {"Username": username, "Password": password}
        cred_resp = requests.post(cred_url, auth=auth, data=cred_data)
        
        if cred_resp.status_code == 201:
            print(f"✓ Credential added: {username}")
            return cred_list_sid, username, password
        else:
            print(f"✗ Failed to add credential: {cred_resp.status_code}")
            print(cred_resp.text)
            return cred_list_sid, None, None
    else:
        print(f"✗ Failed to create credential list: {resp.status_code}")
        print(resp.text)
        return None, None, None


def create_ip_access_list(account_sid, auth_token, public_ip):
    """Create an IP access control list."""
    url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/IpAccessControlLists.json"
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    data = {"FriendlyName": "Asterisk Server"}
    resp = requests.post(url, auth=auth, data=data)
    
    if resp.status_code == 201:
        acl = resp.json()
        acl_sid = acl['sid']
        print(f"✓ IP ACL created: {acl_sid}")
        
        # Add IP to the list — URL without .json suffix for nested resource
        ip_url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/SIP/IpAccessControlLists/{acl_sid}/IpAddresses.json"
        ip_data = {"FriendlyName": "WSL2 Server", "IpAddress": public_ip}
        ip_resp = requests.post(ip_url, auth=auth, data=ip_data)
        
        if ip_resp.status_code == 201:
            print(f"✓ IP added: {public_ip}")
            return acl_sid
        else:
            print(f"✗ Failed to add IP: {ip_resp.status_code}")
            print(ip_resp.text)
            return acl_sid
    else:
        print(f"✗ Failed to create IP ACL: {resp.status_code}")
        print(resp.text)
        return None

def link_credential_list_to_trunk(account_sid, auth_token, trunk_sid, cred_list_sid):
    """Link credential list to trunk."""
    url = f"https://trunking.twilio.com/v1/Trunks/{trunk_sid}/CredentialLists"
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    data = {"CredentialListSid": cred_list_sid}
    resp = requests.post(url, auth=auth, data=data)
    
    if resp.status_code == 201:
        print(f"✓ Credential list linked to trunk")
        return True
    else:
        print(f"✗ Failed to link credential list: {resp.status_code}")
        print(resp.text)
        return False

def link_ip_acl_to_trunk(account_sid, auth_token, trunk_sid, acl_sid):
    """Link IP ACL to trunk."""
    url = f"https://trunking.twilio.com/v1/Trunks/{trunk_sid}/IpAccessControlLists"
    auth = HTTPBasicAuth(account_sid, auth_token)
    
    data = {"IpAccessControlListSid": acl_sid}
    resp = requests.post(url, auth=auth, data=data)
    
    if resp.status_code == 201:
        print(f"✓ IP ACL linked to trunk")
        return True
    else:
        print(f"✗ Failed to link IP ACL: {resp.status_code}")
        print(resp.text)
        return False

def main():
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables")
        sys.exit(1)
    
    print("=== Twilio SIP Trunk Setup ===\n")
    
    # Get public IP
    print("Getting public IP...")
    public_ip = get_public_ip()
    if not public_ip:
        print("✗ Could not determine public IP")
        sys.exit(1)
    print(f"✓ Public IP: {public_ip}\n")
    
    # Create trunk
    print("Creating SIP trunk...")
    trunk = create_trunk(account_sid, auth_token)
    if not trunk:
        sys.exit(1)
    trunk_sid = trunk['sid']
    domain = trunk['domain_name']
    print()
    
    # Create credential list
    print("Creating credential list...")
    cred_list_sid, username, password = create_credential_list(account_sid, auth_token)
    if not cred_list_sid:
        sys.exit(1)
    print()
    
    # Create IP ACL
    print("Creating IP access control list...")
    acl_sid = create_ip_access_list(account_sid, auth_token, public_ip)
    if not acl_sid:
        sys.exit(1)
    print()
    
    # Link credential list to trunk
    print("Linking credential list to trunk...")
    link_credential_list_to_trunk(account_sid, auth_token, trunk_sid, cred_list_sid)
    print()
    
    # Link IP ACL to trunk
    print("Linking IP ACL to trunk...")
    link_ip_acl_to_trunk(account_sid, auth_token, trunk_sid, acl_sid)
    print()
    
    print("=== Setup Complete ===\n")
    print(f"Trunk SID:       {trunk_sid}")
    print(f"SIP Domain:      {domain}")
    print(f"SIP Username:    {username}")
    print(f"SIP Password:    {password}")
    print(f"Whitelisted IP:  {public_ip}")
    print("\nUse these values in your Asterisk config.")

if __name__ == "__main__":
    main()
