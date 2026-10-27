"""Run ONCE on your own computer to get a YouTube refresh token.

1. pip install google-auth-oauthlib
2. Put the OAuth client file you downloaded from Google Cloud next to this
   script as client_secret.json (Desktop app type).
3. python src/get_refresh_token.py
4. A browser opens -> sign in with the Google account that owns your
   YouTube channel -> pick the channel -> Allow.
5. Copy the three values it prints into GitHub repo secrets.

Never commit client_secret.json or the printed token to the repo.
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
here = os.path.dirname(os.path.abspath(__file__))
secret = next(p for p in [os.path.join(here, "client_secret.json"), "client_secret.json"] if os.path.exists(p))

flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
cfg = json.load(open(secret))
cfg = cfg.get("installed") or cfg.get("web")

print("\nAdd these as GitHub secrets (Settings > Secrets and variables > Actions):\n")
print("YT_CLIENT_ID     =", cfg["client_id"])
print("YT_CLIENT_SECRET =", cfg["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
