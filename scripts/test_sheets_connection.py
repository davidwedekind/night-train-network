# scripts/test_sheets_connection.py
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials

PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "files" / "sheets_reader_credentials.json"
SPREADSHEET_ID = "174729Ovv5lI5EcdNVnE5ZOlSqT6AUvty6avxVmL22OU"
WORKSHEET_NAME = "stops"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

creds = Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
rows = sheet.get_all_records()

print(f"Connected! Found {len(rows)} rows.")
print("First row:", rows[0] if rows else "empty")