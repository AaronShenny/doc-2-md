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
from core.config import USER_AGENT, TIMEOUT_SECONDS
def fetch_url(url: str) -> str:
    """Fetch raw HTML from *url*.

    Raises:
        requests.HTTPError      – non-2xx HTTP status
        requests.Timeout        – request timed out
        requests.RequestException – other network error
    """
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text

def fetch_xml(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text
