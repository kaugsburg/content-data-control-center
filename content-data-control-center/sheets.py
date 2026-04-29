import gspread
from datetime import datetime
import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client():
    creds = config.get_google_credentials(SCOPES)
    return gspread.authorize(creds)


def _open_sheet():
    client = _get_client()
    return client.open_by_key(config.GOOGLE_SHEET_ID)


def read_urls() -> list[str]:
    """Return the list of page URLs from the URLs tab."""
    sheet = _open_sheet()
    ws = sheet.worksheet(config.TAB_URLS)
    values = ws.col_values(1)  # All values in column A
    # Skip header row if present
    urls = [v.strip() for v in values if v.strip().startswith("http")]
    return urls


def read_master_company_data() -> list[dict]:
    """
    Return rows from 'Master Data by Company'.
    Expected columns: Company, Data Type, Value, Unit, Notes, Last Updated
    """
    sheet = _open_sheet()
    ws = sheet.worksheet(config.TAB_MASTER_COMPANY)
    return ws.get_all_records()


def read_general_cost_data() -> list[dict]:
    """
    Return rows from 'General Cost Data'.
    Expected columns: Category, Data Type, Value, Unit, Notes, Last Updated
    """
    sheet = _open_sheet()
    ws = sheet.worksheet(config.TAB_GENERAL_COST)
    return ws.get_all_records()


def write_audit_report(rows: list[dict]) -> None:
    """
    Append mismatch rows to the Audit Report tab.
    Each row dict must have: page_url, company_or_category, data_type,
    found_on_page, master_value, notes, doc_link
    """
    if not rows:
        return

    sheet = _open_sheet()
    ws = sheet.worksheet(config.TAB_AUDIT_REPORT)
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_rows = []
    for r in rows:
        new_rows.append([
            run_date,
            r.get("page_url", ""),
            r.get("company_or_category", ""),
            r.get("data_type", ""),
            r.get("found_on_page", ""),
            r.get("master_value", ""),
            r.get("notes", ""),
            r.get("doc_link", ""),
        ])

    ws.append_rows(new_rows, value_input_option="USER_ENTERED")
    print(f"  → Wrote {len(new_rows)} mismatch row(s) to Audit Report.")
