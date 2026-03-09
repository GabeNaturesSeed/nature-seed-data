"""
Generate a new OAuth refresh token that covers ALL Google APIs:
- Google Ads
- Google Analytics (readonly)
- Merchant Center (Content API)
- Search Console (webmasters readonly)

Usage: python3 get_token_with_search_console.py
Then paste the auth code back here (or give it to Claude).
"""
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Load .env
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
    "https://www.googleapis.com/auth/content",
    "https://www.googleapis.com/auth/webmasters.readonly",
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
print("  Open this URL and authorize all 4 scopes:")
print("=" * 60)
print(f"\n{auth_url}\n")

try:
    import webbrowser
    webbrowser.open(auth_url)
    print("(Browser opened)")
except Exception:
    print("(Copy/paste the URL above)")

print("\nPaste the authorization code below:")
auth_code = input("Code: ").strip()

if not auth_code:
    print("No code provided.")
    sys.exit(1)

# Exchange for tokens
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
    print(f"ERROR: {e.code} — {e.read().decode()}")
    sys.exit(1)

refresh_token = result.get("refresh_token", "")
if not refresh_token:
    print("No refresh token returned:")
    print(json.dumps(result, indent=2))
    sys.exit(1)

print("\n" + "=" * 60)
print("  NEW REFRESH TOKEN (all 4 scopes):")
print("=" * 60)
print(f"\n{refresh_token}\n")
print("Update GOOGLE_ADS_REFRESH_TOKEN in .env with this value.")
