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
    Append one row per page to the Audit Report tab.
    rows is a list of mismatch dicts grouped by page — we collapse them into
    one summary row per unique page_url.
    Each row dict must have: page_url, doc_link, and a list of mismatches.
    """
    if not rows:
        return

    sheet = _open_sheet()
    ws = sheet.worksheet(config.TAB_AUDIT_REPORT)
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Group mismatches by page URL
    pages: dict[str, dict] = {}
    for r in rows:
        url = r.get("page_url", "")
        if url not in pages:
            pages[url] = {
                "doc_link": r.get("doc_link", ""),
                "mismatches": [],
            }
        pages[url]["mismatches"].append(
            f"{r.get('company_or_category', '')} / {r.get('data_type', '')}: "
            f"found '{r.get('found_on_page', '')}' → should be '{r.get('master_value', '')}'"
        )

    new_rows = []
    for url, data in pages.items():
        summary = " | ".join(data["mismatches"])
        mismatch_count = len(data["mismatches"])
        new_rows.append([
            run_date,
            url,
            mismatch_count,
            summary,
            data["doc_link"],
        ])

    ws.append_rows(new_rows, value_input_option="USER_ENTERED")
    print(f"  → Wrote {len(new_rows)} page row(s) to Audit Report.")
