# main.py
import os
import base64
import re
import time
import requests
import logging
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# lazy import of pushover so importing module doesn't perform network calls
try:
    from pushover_complete import PushoverAPI
except Exception:
    PushoverAPI = None

load_dotenv()

# --- Settings (read from environment) ---
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
]

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
LOG_FILE = os.getenv("LOG_FILE", "kindle_watcher.log")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Logging ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def get_pushover():
    """Return a PushoverAPI instance if configured, else None."""
    if not (PUSHOVER_TOKEN and PUSHOVER_USER and PushoverAPI):
        return None
    return PushoverAPI(PUSHOVER_TOKEN)


# --- Google OAuth credentials helper ---
def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.json must be present (downloaded from Google Cloud Console)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


# --- Fetch latest Kindle link from Gmail ---
def fetch_latest_kindle_link(creds, mailbox_query="label:skribe"):
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", q=mailbox_query, maxResults=1).execute()
    messages = results.get("messages", [])
    if not messages:
        return None, None

    msg_id = messages[0]["id"]
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    subject = ""
    for header in msg["payload"]["headers"]:
        if header["name"] == "Subject":
            subject = header["value"]

    match_subject = re.search(r'"(.+?)"', subject)
    file_name = match_subject.group(1) if match_subject else subject.replace(" ", "_")

    body = ""
    payload = msg["payload"]
    # handle nested parts if necessary
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            data = part["body"]["data"]
            body = base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8")

    # Amazon Kindle download link pattern (adjust if needed)
    match_link = re.search(r"https://www\.amazon\.com/gp/f\.html\?[^'\"]+", body)
    download_link = match_link.group(0) if match_link else None

    # Remove a label to avoid reprocessing (Label ID must be adapted for your account)
    # Replace with your label id or remove this block if you prefer manual management
    try:
        service.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["Label_5840616301921684099"]}
        ).execute()
    except Exception as e:
        logging.debug(f"Failed to remove label: {e}")

    return download_link, file_name


def download_file_from_link(url, filename):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        path = os.path.join(DOWNLOAD_FOLDER, filename + ".pdf")
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"Downloaded {path}")
        return path
    except Exception as e:
        logging.error(f"Download failed: {e}")
        return None


def upload_to_drive(creds, filename):
    if not DRIVE_FOLDER_ID:
        logging.error("DRIVE_FOLDER_ID is not set; skipping upload.")
        return
    try:
        service = build("drive", "v3", credentials=creds)
        file_metadata = {"name": os.path.basename(filename), "parents": [DRIVE_FOLDER_ID]}
        with open(filename, "rb") as f:
            media = MediaIoBaseUpload(f, mimetype="application/pdf", resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        os.remove(filename)
        logging.info(f"Uploaded and removed local file {filename}")
    except Exception as e:
        logging.error(f"Upload to Drive failed: {e}")


def notify(subject, filename):
    pushover = get_pushover()
    if not pushover:
        logging.info("Pushover not configured; skipping notification.")
        return
    try:
        message = f"Uploaded {filename} from Kindle note: {subject}"
        pushover.send_message(PUSHOVER_USER, message)
        logging.info("Pushover notification sent.")
    except Exception as e:
        logging.error(f"Pushover notification failed: {e}")


def main_loop_once():
    creds = get_credentials()
    link, file_name = fetch_latest_kindle_link(creds)
    if link:
        logging.info(f"Found Kindle link: {file_name} -> {link}")
        local_file = download_file_from_link(link, file_name)
        if local_file:
            upload_to_drive(creds, local_file)
            notify(file_name, local_file)
    else:
        logging.info("No new Kindle emails found.")


if __name__ == "__main__":
    # run once and loop; running locally first time will open browser for OAuth.
    pushover = get_pushover()
    if pushover:
        try:
            pushover.send_message(PUSHOVER_USER, "Kindle watcher starting (container/local).")
        except Exception:
            logging.debug("Could not send startup pushover message.")
    logging.info("=== Kindle Watcher Starting ===")
    while True:
        try:
            main_loop_once()
        except Exception as e:
            logging.error(f"Main loop error: {e}")
        time.sleep(5)
