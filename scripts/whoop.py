import os
import webbrowser
import json
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

def exchange_code_for_tokens(code):
    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    })
    return response.json()

def save_tokens(tokens):
    with open("data/whoop_tokens.json", "w") as f:
        json.dump(tokens, f, indent=2)
    print("Tokens saved to data/whoop_tokens.json")

if __name__ == "__main__":
    print("Paste your callback URL (the full localhost URL from your browser):")
    callback_url = input("> ").strip()
    
    params = parse_qs(urlparse(callback_url).query)
    
    if "code" not in params:
        print("No code found in URL. Please try again.")
        exit(1)
    
    code = params["code"][0]
    print(f"Got authorization code, exchanging for tokens...")
    
    tokens = exchange_code_for_tokens(code)
    
    if "access_token" in tokens:
        save_tokens(tokens)
        print("Authentication successful!")
        print(f"Access token expires in: {tokens.get('expires_in')} seconds")
    else:
        print(f"Error getting tokens: {tokens}")