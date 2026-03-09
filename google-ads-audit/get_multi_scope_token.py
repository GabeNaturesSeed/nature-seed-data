"""
Google Multi-API OAuth2 Refresh Token Generator
Scopes: Google Ads + Analytics + Merchant Center

Usage: python3 get_multi_scope_token.py
Then paste the auth code when prompted.
"""
import os
import sys
import urllib.request
import urllib.parse
import json
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")

CLIENT_ID = env_vars["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = env_vars["GOOGLE_ADS_CLIENT_SECRET"]

SCOPES = " ".join([
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/content",              # Merchant Center
])

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

auth_url = (
    "https://accounts.google.com/o/oauth2/auth"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={urllib.parse.quote(SCOPES)}"
    "&response_type=code"
    "&access_type=offline"
    "&prompt=consent"
)

print("=" * 60)
print("  Open this URL and authorize:")
print("=" * 60)
print(f"\n{auth_url}\n")

try:
    import webbrowser
    webbrowser.open(auth_url)
    print("(Browser opened)")
except Exception:
    pass

print("=" * 60)
print("  Paste the authorization code below:")
print("=" * 60)
auth_code = input("\nAuth code: ").strip()

if not auth_code:
    print("No code provided.")
    sys.exit(1)

data = urllib.parse.urlencode({
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"ERROR: {e.code}")
    print(e.read().decode())
    sys.exit(1)

refresh_token = result.get("refresh_token", "")
if refresh_token:
    print(f"\nRefresh token:\n{refresh_token}")
    print("\nThis token covers: Google Ads + Analytics + Merchant Center")
else:
    print("No refresh token returned:")
    print(json.dumps(result, indent=2))
