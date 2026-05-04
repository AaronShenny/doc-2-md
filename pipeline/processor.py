import asyncio
import os
import html as html_module
import sys,os
import uuid
from urllib.parse import urlparse, urljoin
import requests
import xml.etree.ElementTree as ET
import markdownify
import requests
from bs4 import BeautifulSoup
import re,json

from google.genai.errors import ClientError
from datetime import datetime
from dotenv import load_dotenv
# readability-lxml is optional but strongly preferred
try:
    from readability import Document as ReadabilityDocument
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False
from core import config
from core.extractor import extract_main_content,strip_scripts_and_styles
from core.formatter import format_codeblocks, format_tables
from core.converter import html_to_markdown
from core.filters import apply_domain_filters
from core.fetcher import fetch_url
# ===========================================================================
# 10. Core processing pipeline  (url_to_markdown_processor.js)
# ===========================================================================
STACKOVERFLOW_PREFIX = "https://stackoverflow.com/questions"
def process_html(html: str, url: str = "", options: dict = None) -> str:
    """Convert an HTML string to Markdown.

    This is the shared processing pipeline used by both the URL-fetching path
    and any direct-HTML-input path.

    Steps:
    1. Strip <script> and <style> blocks.
    2. Extract main content with Readability (fallback: cleaned full HTML).
    3. Pre-process <pre> blocks → fenced code block placeholders.
    4. Pre-process <table> blocks → Markdown table placeholders.
    5. Convert remaining HTML to Markdown with markdownify.
    6. Substitute placeholders.
    7. Apply global + domain-specific regex filters.
    8. Optionally prepend the page <title>.
    """
    if options is None:
        options = {}

    inline_title = options.get("inline_title", True)
    ignore_links = options.get("ignore_links", False)
    use_readability = options.get("use_readability", True)

    # Step 1 – strip scripts and styles
    html = strip_scripts_and_styles(html)

    # Step 2 – extract main content (Readability → fallback to full HTML)
    content, title = extract_main_content(html, url=url, use_readability=use_readability)

    # Steps 3 & 4 – pre-process code blocks and tables into placeholders
    replacements: list = []
    content = format_codeblocks(content, replacements)
    content = format_tables(content, replacements)

    # Step 5 & 6 – convert to Markdown and restore placeholders
    markdown = html_to_markdown(content, replacements)

    # Step 7 – domain-specific regex cleanup
    markdown = apply_domain_filters(url, markdown, ignore_links=ignore_links)

    # Step 8 – prepend the page title as an H1 if requested
    if inline_title and title:
        markdown = f"# {title}\n{markdown}"

    return markdown


# ===========================================================================
# 11. Main entry point  (url_to_markdown_readers.js + index.js)
# ===========================================================================

def url_to_markdown(
    url: str,
    inline_title: bool = True,
    ignore_links: bool = False,
    use_readability: bool = True,
) -> str:
    """Convert a URL to Markdown.

    Dispatches to the appropriate reader based on the URL:
    - Apple Developer docs  → JSON API reader (no HTML involved)
    - Stack Overflow pages  → split question / answer reader
    - Everything else       → standard HTML reader

    Args:
        url:             The URL to convert.
        inline_title:    When True, prepend the page <title> as an H1.
        ignore_links:    When True, strip all hyperlink markup from the output.
        use_readability: When True, use Mozilla Readability to extract the
                         main article body.  Disable to get the full page.

    Returns:
        Markdown string.

    Raises:
        requests.HTTPError / requests.RequestException on network failures.
    """
    options = {
        "inline_title": inline_title,
        "ignore_links": ignore_links,
        "use_readability": use_readability,
    }
    APPLE_DEV_PREFIX = "https://developer.apple.com"
    if url.startswith(APPLE_DEV_PREFIX):
        return fetch_apple_dev_doc(url, options)
    elif url.startswith(STACKOVERFLOW_PREFIX):
        return process_stackoverflow(url, options)
    else:
        html = fetch_url(url)
        return process_html(html, url=url, options=options)



def url_main(url):
    # Only accept valid URLs from CLI

    test_url = url

    print(f"Converting: {test_url}")
    print("=" * 60)

    try:
        result = url_to_markdown(test_url)
        return result
        # with open(result.split("\n")[0][1:].replace(" ","_"),"w") as f:
        #   f.write(result)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
