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
def format_codeblocks(html: str, replacements: list) -> str:
    """Replace every <pre>…</pre> block with a unique placeholder string.

    The real Markdown fenced code block is stored in *replacements* and is
    substituted back after the HTML→Markdown conversion so that markdownify
    cannot mangle the code content.

    Language detection: if the <pre> or inner <code> tag has a class like
    ``language-python`` or ``lang-js`` we carry that language identifier
    into the fence (e.g. ```python … ```).
    """
    def _convert(match: re.Match) -> str:
        block = match.group(0)

        # Try to detect a programming language from the CSS class
        lang = ""
        lang_match = re.search(
            r'<(?:pre|code)[^>]+class="[^"]*(?:language|lang)-([a-zA-Z0-9+#.-]+)',
            block,
            re.IGNORECASE,
        )
        if lang_match:
            lang = lang_match.group(1)

        # Normalise in-block line breaks before stripping tags
        block = re.sub(r'<br[^>]*>', '\n', block, flags=re.IGNORECASE)
        block = re.sub(r'<p>', '\n', block, flags=re.IGNORECASE)

        # Strip all remaining HTML tags
        text = re.sub(r'</?[^>]+(>|$)', '', block)

        # Decode HTML entities (e.g. &amp; → &)
        text = html_module.unescape(text)

        markdown = f"```{lang}\n{text}\n```\n"
        placeholder = f"urltomarkdowncodeblockplaceholder{len(replacements)}{uuid.uuid4().hex}"
        replacements.append({"placeholder": placeholder, "replacement": markdown})
        return f"<p>{placeholder}</p>"

    return re.sub(r'<pre[^>]*>[\s\S]*?</pre>', _convert, html, flags=re.IGNORECASE)


def format_tables(html: str, replacements: list) -> str:
    """Replace every <table>…</table> block with a unique placeholder string.

    The converted Markdown table (or indented list) is stored in *replacements*
    and substituted back after the HTML→Markdown conversion.
    """
    def _convert(match: re.Match) -> str:
        table_html = match.group(0)
        markdown = convert_table(table_html)
        placeholder = f"urltomarkdowntableplaceholder{len(replacements)}{uuid.uuid4().hex}"
        replacements.append({"placeholder": placeholder, "replacement": markdown})
        return f"<p>{placeholder}</p>"

    return re.sub(r'<table[^>]*>[\s\S]*?</table>', _convert, html, flags=re.IGNORECASE)

