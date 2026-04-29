"""
Creates a Google Doc for a page that has mismatches.
The doc contains:
  1. A summary table at the top listing each mismatch
  2. The full article text with outdated sections highlighted in yellow
"""

from datetime import datetime
from googleapiclient.discovery import build
import config

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

_YELLOW = {"red": 1.0, "green": 0.98, "blue": 0.0}


def _get_services():
    creds = config.get_google_credentials(SCOPES)
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return docs, drive


def create_review_doc(
    page_title: str,
    page_url: str,
    page_text: str,
    mismatches: list[dict],
) -> str:
    """
    Create a Google Doc in the configured Drive folder.
    Returns the shareable edit URL of the new doc.
    """
    docs_service, drive_service = _get_services()

    doc_title = f"{page_title} — Data Review {datetime.now().strftime('%Y-%m-%d')}"

    # Create empty doc
    doc = docs_service.documents().create(body={"title": doc_title}).execute()
    doc_id = doc["documentId"]

    # Move to the configured Drive folder
    if config.GOOGLE_DRIVE_FOLDER_ID:
        file = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))
        drive_service.files().update(
            fileId=doc_id,
            addParents=config.GOOGLE_DRIVE_FOLDER_ID,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    # Build the full document text
    separator = "\n" + ("─" * 60) + "\n\n"
    summary_lines = [
        "DATA REVIEW SUMMARY\n",
        f"Page: {page_url}\n",
        f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n",
        "MISMATCHES FOUND:\n",
    ]
    for m in mismatches:
        summary_lines.append(
            f"  • {m['company_or_category']} / {m['data_type']}: "
            f"page shows \"{m['found_on_page']}\" → should be \"{m['master_value']}\"\n"
        )
    summary_lines.append(separator)
    summary_lines.append("FULL ARTICLE TEXT\n\n")

    header_text = "".join(summary_lines)
    full_doc_text = header_text + page_text

    # Insert all text at once
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": full_doc_text,
                    }
                }
            ]
        },
    ).execute()

    # Apply yellow highlighting to each mismatch context snippet
    highlight_requests = _build_highlight_requests(full_doc_text, mismatches)
    if highlight_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": highlight_requests},
        ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"  → Created review doc: {doc_url}")
    return doc_url


def _build_highlight_requests(full_text: str, mismatches: list[dict]) -> list[dict]:
    """
    For each mismatch with a context_snippet, find its position in full_text
    and return an updateTextStyle request that applies yellow highlighting.
    Google Docs API indices are 1-based: python index i → doc index i+1.
    """
    requests = []
    for m in mismatches:
        snippet = m.get("context_snippet")
        if not snippet:
            continue

        idx = full_text.find(snippet)
        if idx == -1:
            # Try a shorter version in case the snippet was slightly rephrased
            short = snippet[:40]
            idx = full_text.find(short)
            if idx == -1:
                continue
            end_idx = idx + len(short)
        else:
            end_idx = idx + len(snippet)

        requests.append(
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": idx + 1,
                        "endIndex": end_idx + 1,
                    },
                    "textStyle": {
                        "backgroundColor": {
                            "color": {"rgbColor": _YELLOW}
                        }
                    },
                    "fields": "backgroundColor",
                }
            }
        )

    return requests
