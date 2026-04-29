import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Tags whose content we strip before extracting text
_STRIP_TAGS = ["nav", "footer", "header", "script", "style", "noscript", "aside"]


def fetch_page(url: str) -> tuple[str, str]:
    """
    Fetch a URL and return (clean_text, page_title).
    clean_text is the article body with nav/footer/scripts removed.
    Raises requests.HTTPError on non-2xx responses.
    """
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title before stripping tags
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else url

    # Remove boilerplate sections
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    # Prefer the main content area if the site uses <main> or <article>
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        main = soup

    text = main.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    return clean_text, page_title
