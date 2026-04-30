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


OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
GOOGLE_SHEET_ID = _get("GOOGLE_SHEET_ID")
GOOGLE_DRIVE_FOLDER_ID = _get("GOOGLE_DRIVE_FOLDER_ID")

# For local dev: path to a credentials JSON file
GOOGLE_CREDENTIALS_PATH = _get("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# For Streamlit Cloud: the entire service account JSON stored as a string secret
GOOGLE_CREDENTIALS_JSON = _get("GOOGLE_CREDENTIALS_JSON", "")

# Sheet tab names
TAB_MASTER_COMPANY = "Master Data by Company"
TAB_GENERAL_COST = "General Cost Data"
TAB_AUDIT_REPORT = "Audit Report"
TAB_URLS = "URLs"

# Model to use via OpenRouter — Claude Sonnet is a good balance of speed and accuracy
OPENROUTER_MODEL = "anthropic/claude-sonnet-4-5"
AI_MODEL = "gpt-4o"


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
