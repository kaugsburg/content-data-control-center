"""
Loads configuration from Streamlit secrets (when deployed to Streamlit Cloud)
or from a local .env file (for local development).
"""

import json
import os

try:
    import streamlit as st
    _st_available = True
except ImportError:
    _st_available = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get(key: str, default: str = "") -> str:
    """Read a config value from Streamlit secrets first, then env vars."""
    if _st_available:
        try:
            return st.secrets[key]
        except (KeyError, Exception):
            pass
    return os.getenv(key, default)


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
GOOGLE_SHEET_ID = _get("GOOGLE_SHEET_ID")
GOOGLE_DRIVE_FOLDER_ID = _get("GOOGLE_DRIVE_FOLDER_ID")

# For local dev: path to a credentials JSON file
GOOGLE_CREDENTIALS_PATH = _get("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# For Streamlit Cloud: the entire service account JSON stored as a string secret
# Set this in the Streamlit Cloud dashboard as GOOGLE_CREDENTIALS_JSON
GOOGLE_CREDENTIALS_JSON = _get("GOOGLE_CREDENTIALS_JSON", "")

# Sheet tab names
TAB_MASTER_COMPANY = "Master Data by Company"
TAB_GENERAL_COST = "General Cost Data"
TAB_AUDIT_REPORT = "Audit Report"
TAB_URLS = "URLs"

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"


def get_google_credentials(scopes: list[str]):
    """
    Return a Google Credentials object.
    Uses the JSON string secret (Streamlit Cloud) if available,
    otherwise falls back to the credentials file (local dev).
    """
    from google.oauth2.service_account import Credentials

    if GOOGLE_CREDENTIALS_JSON:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(info, scopes=scopes)

    return Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scopes)
