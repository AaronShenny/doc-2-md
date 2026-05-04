
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
def get_namespace(root):
    if root.tag.startswith("{"):
        return root.tag.split("}")[0] + "}"
    return ""


def extract_sitemaps(xml_content):
    """Extract child sitemap URLs"""
    root = ET.fromstring(xml_content)
    ns = get_namespace(root)

    sitemaps = []

    if root.tag.endswith("sitemapindex"):
        for sm in root.findall(f"{ns}sitemap"):
            loc = sm.find(f"{ns}loc")
            if loc is not None and loc.text:
                sitemaps.append(loc.text.strip())

    return sitemaps


def extract_urls(xml_content):
    """Extract URLs from a sitemap"""
    root = ET.fromstring(xml_content)
    ns = get_namespace(root)

    urls = []

    for url in root.findall(f"{ns}url"):
        loc = url.find(f"{ns}loc")
        if loc is not None and loc.text:
            urls.append(loc.text.strip())

    return urls

