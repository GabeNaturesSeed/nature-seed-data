"""
Google Ads OAuth2 Refresh Token Generator
Opens a browser for authorization, then prints the refresh token.

Usage: python3 get_refresh_token.py
"""
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            env_vars[key.strip()] = val

CLIENT_ID = env_vars.get("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = env_vars.get("GOOGLE_ADS_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET must be set in .env")
    sys.exit(1)

print(f"Client ID: {CLIENT_ID[:20]}...")
print(f"Client Secret: {CLIENT_SECRET[:10]}...")

# Google Ads API requires these scopes
SCOPE = "https://www.googleapis.com/auth/adwords"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

# Step 1: Generate authorization URL
auth_url = (
    "https://accounts.google.com/o/oauth2/auth"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={SCOPE}"
    "&response_type=code"
    "&access_type=offline"
    "&prompt=consent"
)

print("\n" + "=" * 60)
print("  STEP 1: Open this URL in your browser and authorize:")
print("=" * 60)
print(f"\n{auth_url}\n")

# Try to open browser automatically
try:
    import webbrowser
    webbrowser.open(auth_url)
    print("(Browser should have opened automatically)")
except Exception:
    print("(Copy and paste the URL above into your browser)")

print("\n" + "=" * 60)
print("  STEP 2: Paste the authorization code below:")
print("=" * 60)
auth_code = input("\nAuthorization code: ").strip()

if not auth_code:
    print("ERROR: No authorization code provided.")
    sys.exit(1)

# Step 3: Exchange auth code for refresh token
import urllib.request
import urllib.parse
import json

token_url = "https://oauth2.googleapis.com/token"
data = urllib.parse.urlencode({
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request(token_url, data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"\nERROR: {e.code} {e.reason}")
    print(error_body)
    sys.exit(1)

refresh_token = result.get("refresh_token", "")
access_token = result.get("access_token", "")

if not refresh_token:
    print("\nERROR: No refresh token in response. Full response:")
    print(json.dumps(result, indent=2))
    sys.exit(1)

print("\n" + "=" * 60)
print("  SUCCESS! Your refresh token:")
print("=" * 60)
print(f"\n{refresh_token}\n")
print("Add this to your .env as GOOGLE_ADS_REFRESH_TOKEN")
