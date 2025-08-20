import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)

def authorize():
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.compose","https://www.googleapis.com/auth/userinfo.profile"]
    creds = None
    try:
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
    except HttpError as e:
        logging.error(f"HTTP error during authorization: {e.resp.status} - {e.content.decode()}")
        creds = None
    except Exception as e:
        logging.error(f"An unexpected error occurred during authorization: {e}")
        creds = None
    return creds