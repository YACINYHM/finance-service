"""Append parsed transactions to the "Log" sheet via the Google Sheets API."""

import json
import logging
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LOG_SHEET = "Log"


def _get_service():
    """Build a Sheets v4 service from the service-account JSON in env."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        info = json.loads(raw)
    else:
        path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        if not path:
            raise RuntimeError("No Google service account configured")
        info = path

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def append_log_row(values, spreadsheet_id=None):
    """Append one row [date, main_category, value, payment_type, observation] to Log.

    values: list/tuple of 5 strings.
    spreadsheet_id: override GOOGLE_SHEET_ID env var.
    Returns the API response.
    """
    spreadsheet_id = spreadsheet_id or os.environ.get("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is not set")

    service = _get_service()
    body = {"values": [list(values)]}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=LOG_SHEET,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    logger.info("Appended row to Log: %s", values)
    return result