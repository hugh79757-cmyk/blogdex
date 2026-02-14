from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

CREDENTIALS_FILE = "/Users/twinssn/Projects/blogdex/cli/client_secret_hugh7973.json"
TOKEN_FILE = "/Users/twinssn/Projects/blogdex/cli/google_token.pickle"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/blogger.readonly"
]

def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return creds

if __name__ == "__main__":
    creds = get_credentials()
    print("인증 성공! 토큰 저장됨:", TOKEN_FILE)
