import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_REMOVE_TAGS = ["nav", "footer", "header", "script", "style", "noscript", "aside",
                "iframe", "svg", "button", "form", "meta", "link"]


def fetch_page(url: str) -> tuple[str, str]:
    """
    Fetch a URL and return (clean_content, page_title).
    Returns structured text that preserves table rows and list items
    while stripping HTML noise so the AI can reliably extract data.
    """
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else url

    # Remove boilerplate
    for tag in soup(_REMOVE_TAGS):
        tag.decompose()

    # Prefer main content area
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        main = soup

    # Strip all HTML attributes to remove noise
    for tag in main.find_all(True):
        tag.attrs = {}

    # Convert to structured text:
    # Table rows get pipe separators so columns stay associated
    # List items get bullet prefixes
    lines = []
    seen = set()

    for tag in main.find_all(["tr", "li", "h1", "h2", "h3", "h4", "p", "td", "th"]):
        if tag.name == "tr":
            cells = [cell.get_text(strip=True) for cell in tag.find_all(["td", "th"])]
            row = " | ".join(c for c in cells if c)
            if row and row not in seen:
                seen.add(row)
                lines.append(row)
        elif tag.name == "li":
            text = tag.get_text(strip=True)
            if text and text not in seen:
                seen.add(text)
                lines.append(f"• {text}")
        else:
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 3 and text not in seen:
                seen.add(text)
                lines.append(text)

    clean_content = "\n".join(lines)
    return clean_content, page_title
