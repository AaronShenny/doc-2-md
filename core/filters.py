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
# ===========================================================================
# 7. Domain-specific filters  (url_to_markdown_common_filters.js)
# ===========================================================================

# Each entry in this list is applied when the URL hostname matches *domain*.
# The global entry (domain=.*) is always applied first.
_DOMAIN_FILTERS = [
    {
        # ── Global filters applied to every page ───────────────────────────
        "domain": re.compile(r'.*'),
        "remove": [
            # Section-anchor paragraph marks like [¶](#heading "Permalink")
            re.compile(r'\[¶\]\(#[^\s]+ "[^"]+"\)'),
        ],
        "replace": [
            {
                # Unwanted whitespace inside link text: [ text ](url) → [text](url)
                "find": re.compile(r'\[[\n\s]*([^\]\n]*)[\n\s]*\]\(([^\)]*)\)'),
                "replacement": r'[\1](\2)',
            },
            {
                # Links stuck together: )[  →  )\n[
                "find": re.compile(r'\)\['),
                "replacement": ')\n[',
            },
            {
                # Missing URI scheme: [text](//host/path) → [text](https://host/path)
                "find": re.compile(r'\[([^\]]*)\]\(\/\/([^\)]*)\)'),
                "replacement": r'[\1](https://\2)',
            },
        ],
    },
    {
        # ── Wikipedia ──────────────────────────────────────────────────────
        "domain": re.compile(r'.*\.wikipedia\.org'),
        "remove": [
            re.compile(r'\*\*\[\^\]\(#cite_ref[^\)]+\)\*\*'),
            re.compile(r'(?:\\\[)?\[edit\]\([^\s]+ "[^"]+"\)(?:\\\])?', re.IGNORECASE),
            re.compile(r'\^\s\[Jump up to[^\)]*\)', re.IGNORECASE),
            re.compile(r'\[[^\]]*\]\(#cite_ref[^\)]+\)'),
            re.compile(r'\[\!\[Edit this at Wikidata\].*'),
            re.compile(
                r'\[\!\[Listen to this article\]\([^\)]*\)\]\([^\)]*\.(mp3|ogg|oga|flac)[^\)]*\)',
                re.IGNORECASE,
            ),
            re.compile(r'\[This audio file\]\([^\)]*\).*'),
            re.compile(r'\!\[Spoken Wikipedia icon\]\([^\)]*\)'),
            re.compile(r'\[.*\]\(.*Play audio.*\).*'),
        ],
        "replace": [
            {
                # Use the full-size image instead of the thumbnail
                "find": re.compile(
                    r'\(https://upload\.wikimedia\.org/wikipedia/([^/]+)/thumb/([^\)]+\..{3,4})/[^\)]+\)',
                    re.IGNORECASE,
                ),
                "replacement": r'(https://upload.wikimedia.org/wikipedia/\1/\2)',
            },
            {
                # Fix over-long setext underlines generated from Wikipedia tables
                "find": re.compile(r'\n(.+)\n-{32,}\n', re.IGNORECASE),
                "replacement": lambda m: (
                    '\n' + m.group(1) + '\n' + '-' * len(m.group(1)) + '\n'
                ),
            },
        ],
    },
    {
        # ── Medium ─────────────────────────────────────────────────────────
        "domain": re.compile(r'(?:.*\.)?medium\.com'),
        "replace": [
            {
                # Fix truncated Medium CDN image URLs
                "find": "(https://miro.medium.com/max/60/",
                "replacement": "(https://miro.medium.com/max/600/",
            },
            {
                # Unwrap nested image+link into a clean image + caption link
                "find": re.compile(
                    r'\s*\[\s*!\[([^\]]+)\]\(([^\)]+)\)\s*\]\(([^\?\)]*)\?[^\)]*\)\s*'
                ),
                "replacement": r'\n![\1](\2)\n[\1](\3)\n\n',
            },
        ],
    },
    {
        # ── Stack Overflow ─────────────────────────────────────────────────
        "domain": re.compile(r'(?:.*\.)?stackoverflow\.com'),
        "remove": [
            re.compile(r'\* +Links(.|\r|\n)*Three +\|'),
        ],
    },
]


def apply_domain_filters(url: str, markdown: str, ignore_links: bool = False) -> str:
    """Apply global and domain-specific regex filters to *markdown*.

    Also:
    - Converts relative URLs to absolute ones using the page's base address.
    - Strips inline links if *ignore_links* is True.
    """
    parsed = urlparse(url) if url else None
    domain = (parsed.hostname or "") if parsed else ""
    # Only build base_address when we have a full scheme + hostname
    base_address = (
        f"{parsed.scheme}://{parsed.hostname}"
        if parsed and parsed.scheme and parsed.hostname
        else ""
    )

    for entry in _DOMAIN_FILTERS:
        if entry["domain"].search(domain):
            # Remove patterns
            for pattern in entry.get("remove", []):
                markdown = re.sub(pattern, "", markdown)

            # Replace patterns
            for rep in entry.get("replace", []):
                find = rep["find"]
                replacement = rep["replacement"]
                if isinstance(find, str):
                    # Plain string replacement
                    markdown = markdown.replace(find, replacement)
                elif callable(replacement):
                    # Regex with a callable replacement function
                    markdown = re.sub(find, replacement, markdown)
                else:
                    # Regex with a string replacement (may contain back-references)
                    markdown = re.sub(find, replacement, markdown)

    # Make relative URLs absolute: [text](/path) → [text](https://host/path)
    if base_address:
        def _make_absolute(m: re.Match) -> str:
            # urljoin handles trailing-slash edge cases correctly
            return f"[{m.group(1)}]({urljoin(base_address, '/' + m.group(2))})"

        markdown = re.sub(
            r'\[([^\]]*)\]\(\/([^\/][^\)]*)\)',
            _make_absolute,
            markdown,
        )

    # Strip link markup when the caller wants plain text output
    if ignore_links:
        markdown = re.sub(r'\[\[?([^\]]+\]?)\]\([^\)]+\)', r'\1', markdown)
        markdown = re.sub(r'[\\\[]+([0-9]+)[\\\]]+', r'[\1]', markdown)

    return markdown
