#!/usr/bin/env python3
"""
Debug Gmail Authentication
Quick script to test Gmail token loading and refresh
"""

import os
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.gmail_client import GmailClient
from utils_oauth import get_token_store

def test_gmail_auth():
    print("Testing Gmail Authentication...")
    
    # Check token store configuration
    from utils_oauth import get_oauth_config
    config = get_oauth_config()
    print(f"Token backend: {config.get('token_backend', 'disk')}")
    print(f"Airtable base ID: {config.get('token_airtable_base_id', 'Not set')}")
    print(f"Encryption key configured: {'Yes' if config.get('enc_key') else 'No'}")
    
    # Test token store direct access
    store = get_token_store()
    print(f"Token store type: {type(store).__name__}")
    
    # Initialize Gmail client
    try:
        gmail = GmailClient()
        print("Gmail client initialized")
    except Exception as e:
        print(f"Failed to initialize Gmail client: {e}")
        return
    
    # Test token loading for both mailboxes
    mailboxes = ["bradford@2lambda.co", "macanthonyemmanuel12@gmail.com"]
    
    for mailbox in mailboxes:
        print(f"\n Testing mailbox: {mailbox}")
        
        token = store.load(mailbox)
        
        if token:
            print(f"[OK] Token found for {mailbox}")
            print(f"   - Has access_token: {'access_token' in token}")
            print(f"   - Has refresh_token: {'refresh_token' in token}")
            print(f"   - Has expires_in: {'expires_in' in token}")
            print(f"   - Has obtained_at: {'obtained_at' in token}")
        else:
            print(f"[ERROR] No token found for {mailbox}")
            continue
        
        # Test access token retrieval
        try:
            access_token = gmail.get_access_token(mailbox)
            if access_token:
                print(f"[OK] Access token retrieved successfully")
                print(f"   - Token length: {len(access_token)} chars")
            else:
                print(f"[ERROR] Failed to get access token")
        except Exception as e:
            print(f"[ERROR] Error getting access token: {e}")
        
        # Test a simple Gmail API call
        try:
            result = gmail.search_emails(mailbox, "is:sent", max_results=1)
            if "error" in result:
                print(f"[ERROR] Gmail API call failed: {result['error']}")
                if "details" in result:
                    print(f"   Details: {result['details']}")
            else:
                print(f"[OK] Gmail API call successful")
                print(f"   Found {len(result.get('messages', []))} messages")
        except Exception as e:
            print(f"[ERROR] Exception during Gmail API call: {e}")

if __name__ == "__main__":
    test_gmail_auth()