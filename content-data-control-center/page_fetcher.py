import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Tags to remove entirely (content + tag)
_REMOVE_TAGS = ["nav", "footer", "header", "script", "style", "noscript", "aside",
                "iframe", "svg", "button", "form"]


def fetch_page(url: str) -> tuple[str, str]:
    """
    Fetch a URL and return (clean_html, page_title).
    clean_html is the page body with scripts/nav/footer removed but with
    structural tags (tables, divs) preserved so the AI can read relationships
    between companies and their data points.
    Raises requests.HTTPError on non-2xx responses.
    """
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else url

    # Remove boilerplate tags entirely
    for tag in soup(_REMOVE_TAGS):
        tag.decompose()

    # Prefer main content area
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        main = soup

    # Return cleaned HTML string — preserves tables, divs, and data structure
    clean_html = str(main)

    return clean_html, page_title
