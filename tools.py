import os
import requests
import json
import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from .auth import authorize
from pydantic import BaseModel, EmailStr
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)

class EmailPayload(BaseModel):
    draft_id: Optional[str|None]
    to: EmailStr
    subject: str
    body: str

class PlaceAQI(BaseModel):
    place: str
    aqi: bool

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def get_weather(place:str, aqi:bool) -> dict:
    try:  
        PlaceAQI(place=place, aqi=aqi)
        if not aqi:
            is_aqi = "no"
        else:
            is_aqi = "yes"
        result = requests.get(
            url=f"http://api.weatherapi.com/v1/current.json?key={os.getenv('WEATHER_API_KEY')}&q={place}&aqi={is_aqi}",
            timeout=5
        )
        result.raise_for_status() 
        return result.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"Weather API HTTP Error: {e.response.status_code} - {e.response.text}")
        return {"error": "Failed to retrieve weather data due to an HTTP error."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Weather API Request Exception: {e}")
        return {"error": "Failed to connect to the weather service."}

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type(HttpError)
)
def add_draft(to:str, subject:str, body:str) -> dict:
    try:
        EmailPayload(draft_id=None, to=to, subject=subject, body=body)
        
        creds = authorize()
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["Subject"] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"message": {"raw": encoded_message}}
        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        logging.info(f"Draft created with ID: {draft.get('id')}")
        return draft
    except HttpError as error:
        logging.error(f"An HTTP error occurred while adding a draft: {error}")
        return {"error": f"Failed to add draft: {error}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred while adding a draft: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type(HttpError)
)
def send_email(to:str, subject:str, body:str) -> dict:
    try:
        EmailPayload(draft_id=None, to=to, subject=subject, body=body)
        
        creds = authorize()
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["Subject"] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        logging.info(f"Email sent with ID: {sent_message.get('id')}")
        return sent_message
    except HttpError as error:
        logging.error(f"An HTTP error occurred while sending an email: {error}")
        return {"error": f"Failed to send email: {error}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending an email: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type(HttpError)
)
def update_draft(draft_id:str, to:str, subject:str, body:str):
    try:
        EmailPayload(draft_id=draft_id,to=to, subject=subject, body=body)
        
        creds = authorize()
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["Subject"] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"message": {"raw": encoded_message}}
        updated_draft = service.users().drafts().update(userId = "me", id=draft_id, body=create_message).execute()
        logging.info(f"Draft updated with ID: {updated_draft.get('id')}")
        return updated_draft
    except HttpError as error:
        logging.error(f"An HTTP error occurred while updating the draft: {error}")
        return {"error": f"Failed to update the draft: {error}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred while updating the draft: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, max=60, min=1),
    retry=retry_if_exception_type((HttpError))
)
def list_drafts():
    try:
        creds = authorize()
        service = build("gmail", "v1", credentials=creds)
        results = service.users().drafts().list(userId = "me").execute()
        list_drafts = results.get("drafts", [])
        drafts = []
        for draft in list_drafts:
            draft_content = service.users().drafts().get(userId = "me", id = draft["id"]).execute()
            drafts.append(draft_content)
        logging.info(f"Successfully retrieved {len(drafts)} drafts.")
        return drafts
    except HttpError as error:
        logging.error(f"An HTTP error occurred while listing drafts: {error}")
        return [{"error": f"Failed to list drafts: {error}"}]
    except Exception as e:
        logging.error(f"An unexpected error occurred while listing drafts: {e}")
        return [{"error": f"An unexpected error occurred: {e}"}]