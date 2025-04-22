#!/usr/bin/env python3
"""
Blackboard API Key Test Script
This script tests if your Blackboard API key and secret are working correctly
by attempting to obtain an authentication token.
"""

import requests
import json
import sys
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress insecure HTTPS warnings (for testing environments)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# API Key and Secret from Blackboard
APPLICATION_KEY = ""
APPLICATION_SECRET = ""
APPLICATION_ID = ""

# Target Blackboard instance (try different variations)
POSSIBLE_TARGETS = [
    "uic.blackboard.com",
    "blackboard.uic.edu",
    "www.uic.blackboard.com"
]

def test_authentication_with_url(target_url):
    """
    Test authentication with Blackboard Learn REST API for a specific URL
    """
    auth_url = f"https://{target_url}/learn/api/public/v1/oauth2/token"
    
    # Define payload and headers for token request
    payload = {
        'grant_type': 'client_credentials'
    }
    
    # Try to get an access token
    try:
        print(f"\nTesting connection to {auth_url}...")
        
        # Print detailed request information for debugging
        print(f"Using key: {APPLICATION_KEY}")
        print(f"Using secret: {APPLICATION_SECRET[:3]}...{APPLICATION_SECRET[-3:]}")
        
        response = requests.post(
            auth_url,
            auth=(APPLICATION_KEY, APPLICATION_SECRET),
            data=payload,
            verify=False  # For testing only - set to True in production
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print("\n✅ SUCCESS! API credentials are working correctly")
            print(f"Access token received: {token_data['access_token'][:10]}...")
            print(f"Token expires in: {token_data['expires_in']} seconds")
            return True, response
        else:
            print(f"\n❌ ERROR: Could not authenticate with the Blackboard API")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"Response headers: {response.headers}")
            return False, response
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        return False, None

def test_authentication():
    """
    Test authentication with multiple possible Blackboard URLs
    """
    for target in POSSIBLE_TARGETS:
        print(f"\n--- Testing with {target} ---")
        success, response = test_authentication_with_url(target)
        if success:
            return True
    
    # If we reached here, all authentication attempts failed
    print("\n❌ All authentication attempts failed.")
    
    # Provide guidance on troubleshooting
    print("\nTROUBLESHOOTING TIPS:")
    print("1. Verify your API key and secret are exactly as provided in the Blackboard Developer Portal")
    print("2. Confirm that your application is registered in the UIC Blackboard environment")
    print("3. Check with UIC's Blackboard administrator to ensure the API is enabled")
    print("4. Verify the application has appropriate entitlements in Blackboard")
    
    return False

def test_get_system_version():
    """
    Test getting the Blackboard Learn system version
    using the obtained access token.
    """
    # Try with each possible URL
    for target_url in POSSIBLE_TARGETS:
        print(f"\n--- Testing system version with {target_url} ---")
        
        # First get an access token
        auth_url = f"https://{target_url}/learn/api/public/v1/oauth2/token"
        payload = {'grant_type': 'client_credentials'}
        
        try:
            auth_response = requests.post(
                auth_url,
                auth=(APPLICATION_KEY, APPLICATION_SECRET),
                data=payload,
                verify=False
            )
            
            if auth_response.status_code != 200:
                print(f"Failed to get access token for {target_url}. Trying next URL.")
                continue
                
            token_data = auth_response.json()
            access_token = token_data['access_token']
            
            # Use the token to get system version
            version_url = f"https://{target_url}/learn/api/public/v1/system/version"
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
            
            print(f"Testing access to system version information at {version_url}...")
            version_response = requests.get(
                version_url,
                headers=headers,
                verify=False
            )
            
            if version_response.status_code == 200:
                version_data = version_response.json()
                print("\n✅ SUCCESS! Successfully retrieved system information")
                print(f"Learn Version: {version_data.get('learn', {}).get('version', 'Unknown')}")
                print(f"Major Release: {version_data.get('learn', {}).get('major_release', 'Unknown')}")
                return True
            else:
                print(f"\n❌ ERROR: Could not retrieve system version from {target_url}")
                print(f"Status code: {version_response.status_code}")
                print(f"Response: {version_response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"\n❌ CONNECTION ERROR with {target_url}: {e}")
    
    # If we've tried all URLs and still failed
    print("\n❌ Could not retrieve system version from any URL")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("BLACKBOARD API CREDENTIALS TEST")
    print("=" * 60)
    print(f"Using Application Key: {APPLICATION_KEY[:5]}...{APPLICATION_KEY[-5:]}")
    print(f"Using Application ID: {APPLICATION_ID[:5]}...{APPLICATION_ID[-5:]}")
    
    # Test basic authentication
    auth_result = test_authentication()
    
    # If authentication succeeded, try to access some data
    if auth_result:
        system_version_result = test_get_system_version()
        
        if system_version_result:
            print("\n✅ ALL TESTS PASSED! Your Blackboard API credentials are working correctly.")
        else:
            print("\n⚠️ PARTIAL SUCCESS: Authentication succeeded, but couldn't access system data.")
            print("This might be due to permission issues or API entitlement configuration.")
    else:
        print("\n❌ TEST FAILED: Please check your credentials and Blackboard domain.")
        
    print("\n" + "=" * 60) 