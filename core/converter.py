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
# 6. HTML → Markdown
# ===========================================================================

def html_to_markdown(html: str, replacements: list = None) -> str:
    """Convert *html* to Markdown using markdownify, then substitute any
    placeholder strings that were created by format_codeblocks / format_tables.
    """
    md = markdownify.markdownify(
        html,
        heading_style=markdownify.ATX,  # use # / ## / ### style headings
        bullets="-",                    # bullet character for unordered lists
        strip=["script", "style"],      # drop any remaining script/style nodes
    )

    # Restore pre-computed code blocks and tables
    if replacements:
        for item in replacements:
            md = md.replace(item["placeholder"], item["replacement"])

    return md

