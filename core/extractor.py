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

# HTML elements that are rarely part of the article body
_NOISE_TAGS = ["nav", "footer", "aside", "button", "header", "script", "style"]
_NOISE_HINTS = ("nav", "menu", "sidebar", "footer", "header", "ads", "banner", "cookie")



def strip_scripts_and_styles(html: str) -> str:
    """Remove all <script>…</script> and <style>…</style> blocks.

    This is done with a regex pass before any DOM parsing so that JS/CSS
    content cannot accidentally end up in the final Markdown.
    """
    html = re.sub(r'<style[\s\S]*?</style[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[\s\S]*?</script[^>]*>', '', html, flags=re.IGNORECASE)
    return html

def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove common non-content blocks from *soup* in-place.

    Keeps structural content tags such as headings, sections, and code blocks
    intact, while removing obvious UI chrome and ad/cookie wrappers.
    """
    for tag in soup.find_all(True):

      try:
          class_attr = tag.get("class")
      except Exception:
          class_attr = None

      if isinstance(class_attr, list):
          classes = " ".join(class_attr).lower()
      elif isinstance(class_attr, str):
          classes = class_attr.lower()
      else:
          classes = ""

      try:
          elem_id = tag.get("id")
          elem_id = elem_id.lower() if isinstance(elem_id, str) else ""
      except Exception:
          elem_id = ""

      marker = f"{classes} {elem_id}".strip()

      if not marker:
          continue

      if not any(hint in marker for hint in _NOISE_HINTS):
          continue

      try:
          role = tag.get("role")
      except Exception:
          role = None

      # Preserve important content
      if tag.name in {"main", "article"} or role == "main":
          continue

      try:
          has_content = tag.find(["h1", "h2", "h3", "pre", "code", "article", "section"])
      except Exception:
          has_content = False

      if has_content:
          continue

      try:
          tag.decompose()
      except Exception:
          continue
    return soup

def extract_main_content(html: str, url: str = "", use_readability: bool = True) -> tuple:
    """Extract the main article body from *html*.

    Returns:
        (content_html: str, title: str)

    Documentation-first strategy:
    1. Extract title from <title>.
    2. Extract semantic main containers (<main>, <article>, <div role="main">).
    3. If none found, choose largest meaningful <section>/<div> block.
    4. Final fallback: cleaned full HTML.
    """
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Step 2 & 3: docs-oriented semantic containers, cleaned and returned
    # directly to preserve structure (headings, sections, and code blocks).
    for node in soup.select("main, article, div[role='main']"):
        candidate = BeautifulSoup(str(node), "lxml")
        clean_html(candidate)
        return str(candidate), title

    # Step 4: fallback to largest meaningful <section>/<div> by text size.
    best_html = ""
    best_len = 0
    for node in soup.find_all(["section", "div"]):
        candidate = BeautifulSoup(str(node), "lxml")
        clean_html(candidate)
        text_len = len(candidate.get_text(" ", strip=True))
        if text_len > best_len:
            best_len = text_len
            best_html = str(candidate)
    if best_html:
        return best_html, title

    # Step 5: final fallback to cleaned full HTML.
    clean_html(soup)
    body = soup.find("body")
    fallback_html = str(body) if body else str(soup)
    return fallback_html, title


def is_content_valid(content: str) -> bool:
    """Heuristic quality gate for extracted content HTML."""
    if not content:
        return False
    soup = BeautifulSoup(content, "lxml")
    text = soup.get_text(" ", strip=True)
    if len(text) <= 300:
        return False
    heading_count = len(soup.find_all(["h1", "h2", "h3"]))
    paragraph_count = len(soup.find_all("p"))
    code_count = len(soup.find_all(["pre", "code"]))
    return code_count > 0 or heading_count >= 2 or paragraph_count >= 3


# ===========================================================================
# 4. Table conversion  (html_table_to_markdown.js)
# ===========================================================================

def _clean_cell(cell_html: str) -> str:
    """Strip HTML tags from a table cell, collapse newlines, decode entities."""
    text = re.sub(r'</?[^>]+(>|$)', '', cell_html)
    text = re.sub(r'[\r\n]+', ' ', text)
    text = html_module.unescape(text)
    return text.strip()


def convert_table(table_html: str) -> str:
    """Convert an HTML table string to a Markdown table.

    If the total column width exceeds MAX_TABLE_WIDTH the table is rendered as
    an indented bullet list instead (mirrors html_table_to_markdown.js).

    Returns an empty string for degenerate tables (< 2 rows).
    """
    result = "\n"

    # Optional table caption
    caption_match = re.search(
        r'<caption[^>]*>([\s\S]*?)</caption>', table_html, re.IGNORECASE
    )
    if caption_match:
        result += _clean_cell(caption_match.group(1)) + "\n\n"

    # Collect rows
    rows_raw = re.findall(r'<tr[^>]*>[\s\S]*?</tr>', table_html, re.IGNORECASE)
    n_rows = len(rows_raw)
    if n_rows < 2:
        # Not a proper data table; skip it
        return ""

    items = []
    for row_html in rows_raw:
        cells = re.findall(r'<t[hd][^>]*>([\s\S]*?)</t[hd]>', row_html, re.IGNORECASE)
        items.append([_clean_cell(c) for c in cells])

    # Find the maximum column count across all rows
    n_cols = max((len(row) for row in items), default=0)
    if n_cols == 0:
        return ""

    # Normalise: pad short rows with empty strings
    for row in items:
        while len(row) < n_cols:
            row.append("")

    # Compute per-column widths (minimum 3 to fit the separator "---")
    col_widths = [3] * n_cols
    for row in items:
        for c, cell in enumerate(row):
            if len(cell) > col_widths[c]:
                col_widths[c] = len(cell)

    total_width = sum(col_widths)

    if total_width <= MAX_TABLE_WIDTH:
        # ── Markdown pipe table ──────────────────────────────────────────────
        # Pad each cell to its column width
        padded = [
            [cell.ljust(col_widths[c]) for c, cell in enumerate(row)]
            for row in items
        ]
        # Header row
        result += "|" + "|".join(padded[0]) + "|\n"
        # Separator row
        result += "|" + "|".join("-" * w for w in col_widths) + "|\n"
        # Data rows
        for row in padded[1:]:
            result += "|" + "|".join(row) + "|\n"
    else:
        # ── Indented bullet list (fallback for wide tables) ─────────────────
        header = items[0]
        result += "\n"
        for row in items[1:]:
            if header[0] or row[0]:
                result += "* "
            if header[0]:
                result += header[0] + ": "
            if row[0]:
                result += row[0]
            if header[0] or row[0]:
                result += "\n"
            for c in range(1, n_cols):
                if header[c] or row[c]:
                    result += "  * "
                if header[c]:
                    result += header[c] + ": "
                if row[c]:
                    result += row[c]
                if header[c] or row[c]:
                    result += "\n"

    return result

