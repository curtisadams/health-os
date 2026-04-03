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

def get_recovery():
    headers = get_headers()
    response = requests.get(f"{API_BASE}/recovery", headers=headers)
    print(f"Recovery status code: {response.status_code}")
    print(f"Recovery raw response: {response.text}")
    if response.status_code == 401:
        print("Token expired, refreshing...")
        tokens = load_tokens()
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if new_tokens:
            headers = get_headers()
            response = requests.get(f"{API_BASE}/recovery", headers=headers)
    return response.json()

def get_sleep():
    headers = get_headers()
    response = requests.get(f"{API_BASE}/activity/sleep", headers=headers)
    if response.status_code == 401:
        tokens = load_tokens()
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if new_tokens:
            headers = get_headers()
            response = requests.get(f"{API_BASE}/activity/sleep", headers=headers)
    return response.json()

def get_strain():
    headers = get_headers()
    response = requests.get(f"{API_BASE}/cycle", headers=headers)
    if response.status_code == 401:
        tokens = load_tokens()
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if new_tokens:
            headers = get_headers()
            response = requests.get(f"{API_BASE}/cycle", headers=headers)
    return response.json()

if __name__ == "__main__":
    print("Fetching WHOOP data...\n")

    print("--- RECOVERY ---")
    recovery = get_recovery()
    print(json.dumps(recovery, indent=2))

    print("\n--- SLEEP ---")
    sleep = get_sleep()
    print(json.dumps(sleep, indent=2))

    print("\n--- STRAIN ---")
    strain = get_strain()
    print(json.dumps(strain, indent=2))