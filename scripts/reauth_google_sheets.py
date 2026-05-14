#!/usr/bin/env python3
"""
One-time OAuth flow to add Google Sheets write permission.
Saves GOOGLE_SHEETS_REFRESH_TOKEN to .env.

Usage: python3 scripts/reauth_google_sheets.py
"""

import os
import json
import webbrowser
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
REDIRECT_URI = "http://localhost:8080"

_auth_code = None


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def save_token(refresh_token):
    lines = ENV_PATH.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("GOOGLE_SHEETS_REFRESH_TOKEN"):
            lines[i] = f"GOOGLE_SHEETS_REFRESH_TOKEN = '{refresh_token}'"
            found = True
            break
    if not found:
        lines.append(f"GOOGLE_SHEETS_REFRESH_TOKEN = '{refresh_token}'")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    print(f"  Saved GOOGLE_SHEETS_REFRESH_TOKEN to {ENV_PATH}")


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Auth complete. You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code parameter.")

    def log_message(self, *args):
        pass  # suppress request logs


def main():
    env = load_env(ENV_PATH)
    client_id = env["GOOGLE_ADS_CLIENT_ID"]
    client_secret = env["GOOGLE_ADS_CLIENT_SECRET"]

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        })
    )

    print("Opening browser for Google authorization...")
    print(f"  URL: {auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for redirect on http://localhost:8080 ...")
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not _auth_code:
        print("ERROR: No auth code received.")
        return

    print(f"  Got auth code. Exchanging for refresh token...")

    data = urllib.parse.urlencode({
        "code": _auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print(f"ERROR: No refresh token in response: {token_data}")
        return

    save_token(refresh_token)
    print("Done. GOOGLE_SHEETS_REFRESH_TOKEN is set.")


if __name__ == "__main__":
    main()
