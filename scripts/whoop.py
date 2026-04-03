import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer/v2"
TOKENS_FILE = "data/whoop_tokens.json"

def load_tokens():
    with open(TOKENS_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token(refresh_token):
    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    tokens = response.json()
    if "access_token" in tokens:
        save_tokens(tokens)
        print("Tokens refreshed successfully.")
        return tokens
    else:
        print(f"Error refreshing tokens: {tokens}")
        return None

def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def fetch(url):
    """GET a WHOOP API URL, auto-refreshing on 401. Returns parsed JSON or raises on error."""
    headers = get_headers()
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        print("Token expired, refreshing...")
        tokens = load_tokens()
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if new_tokens:
            headers = get_headers()
            response = requests.get(url, headers=headers)
        else:
            raise RuntimeError("Token refresh failed.")
    if not response.ok:
        raise RuntimeError(f"Request to {url} failed [{response.status_code}]: {response.text}")
    if not response.text.strip():
        raise RuntimeError(f"Empty response from {url} [{response.status_code}]")
    return response.json()

def get_recovery():
    return fetch(f"{API_BASE}/recovery")

def get_sleep():
    return fetch(f"{API_BASE}/activity/sleep")

def get_strain():
    return fetch(f"{API_BASE}/cycle")

DATA_FILE = "data/whoop_daily.json"

if __name__ == "__main__":
    print("Fetching WHOOP data...\n")

    recovery = get_recovery()
    sleep = get_sleep()
    strain = get_strain()

    whoop_data = {
        "recovery": recovery,
        "sleep": sleep,
        "strain": strain,
    }

    with open(DATA_FILE, "w") as f:
        json.dump(whoop_data, f, indent=2)
    print(f"Saved full WHOOP data to {DATA_FILE}\n")

    print("=" * 60)
    print("WHOOP DAILY DATA")
    print("=" * 60)
    for section, data in whoop_data.items():
        print(f"\n--- {section.upper()} ---")
        print(json.dumps(data, indent=2))
    print("\n" + "=" * 60)