"""
Generate a new OAuth refresh token that covers ALL Google APIs:
- Google Ads
- Google Analytics (readonly)
- Merchant Center (Content API)
- Search Console (webmasters readonly)

Usage: python3 get_token_with_search_console.py
Opens browser, you authorize, it captures the code via localhost redirect.
"""
import json
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parents[2] / ".env"
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

REDIRECT_URI = "http://localhost:8085"
auth_code_holder = {"code": None}


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code_holder["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful!</h2><p>You can close this tab and return to the terminal.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error = params.get("error", ["unknown"])[0]
            self.wfile.write(f"<h2>Error: {error}</h2>".encode())

    def log_message(self, format, *args):
        pass  # Suppress request logging


auth_url = (
    "https://accounts.google.com/o/oauth2/auth"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={urllib.parse.quote(SCOPES)}"
    "&response_type=code"
    "&access_type=offline"
    "&prompt=consent"
)

print("=" * 60)
print("  Opening browser for Google OAuth authorization...")
print("  Authorize ALL 4 scopes when prompted.")
print("=" * 60)

# Start local server to capture redirect
server = HTTPServer(("localhost", 8085), OAuthHandler)
server_thread = threading.Thread(target=server.handle_request)
server_thread.start()

# Open browser
try:
    webbrowser.open(auth_url)
    print("\n  Browser opened. Waiting for authorization...\n")
except Exception:
    print(f"\n  Open this URL manually:\n\n{auth_url}\n")

# Wait for the callback
server_thread.join(timeout=120)
server.server_close()

auth_code = auth_code_holder["code"]
if not auth_code:
    print("ERROR: No authorization code received (timeout or denied).")
    sys.exit(1)

print("  Authorization code received! Exchanging for tokens...")

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
print("Also update the GitHub Actions secret if using CI/CD.")
