import os, json, secrets, requests, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SCOPES = "read:recovery read:sleep read:cycles read:profile offline"

state = secrets.token_urlsafe(16)
auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success! You can close this tab.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Failed.")
    def log_message(self, *args):
        pass

auth_url = (
    f"https://api.prod.whoop.com/oauth/oauth2/auth"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&response_type=code"
    f"&scope={SCOPES.replace(' ', '%20')}"
    f"&state={state}"
)

print("Opening browser for authorization...")
webbrowser.open(auth_url)
print("Waiting for callback...")

server = HTTPServer(("localhost", 8080), Handler)
server.handle_request()

if not auth_code:
    print("Failed to get auth code.")
    exit(1)

print("Got code, exchanging for tokens...")
tokens = requests.post(TOKEN_URL, data={
    "grant_type": "authorization_code",
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
}).json()

if "access_token" in tokens:
    with open("data/whoop_tokens.json", "w") as f:
        json.dump(tokens, f, indent=2)
    print("Done! Granted scopes:", tokens.get("scope"))
else:
    print("Error:", tokens)
