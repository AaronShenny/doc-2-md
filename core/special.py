
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
# 9. Stack Overflow special handling  (url_to_markdown_readers.js)
# ===========================================================================
def process_stackoverflow(url: str, options: dict) -> str:
    """Fetch a Stack Overflow question page and return question + best answer.

    The JS reader splits the page by DOM id ("question" and "answers") and
    processes each independently so Readability doesn't merge them.
    """
    html = fetch_url(url)
    html = strip_scripts_and_styles(html)
    soup = BeautifulSoup(html, "lxml")

    # Extract question and answer blocks by their well-known DOM ids
    question_el = soup.find(id="question")
    answers_el = soup.find(id="answers")

    question_html = str(question_el) if question_el else html
    answers_html = str(answers_el) if answers_el else ""

    # Process question (Readability disabled – content is already scoped)
    q_options = {**options, "use_readability": False}
    markdown_q = process_html(question_html, url=url, options=q_options)

    # Process answers
    if answers_html:
        a_options = {**options, "inline_title": False, "use_readability": False}
        markdown_a = process_html(answers_html, url=url, options=a_options)
    else:
        markdown_a = ""

    # If there are no real answers yet, return only the question
    if not markdown_a or markdown_a.startswith("Your Answer"):
        return markdown_q

    return markdown_q + "\n\n## Answer\n" + markdown_a



def fetch_apple_dev_doc(url: str, options: dict) -> str:
    """Fetch and convert an Apple Developer Documentation page to Markdown."""
    json_url = apple_dev_doc_url(url)
    response = requests.get(
        json_url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_apple_dev_doc_json(response.json(), options)

def parse_apple_dev_doc_json(json_data: dict, options: dict) -> str:
    """Convert a parsed Apple Developer Documentation JSON object to Markdown."""
    inline_title = options.get("inline_title", True)
    ignore_links = options.get("ignore_links", False)
    text = ""

    if inline_title:
        title = json_data.get("metadata", {}).get("title", "")
        if title:
            text += "# " + title + "\n\n"

    dev_references = json_data.get("references", {})

    if "primaryContentSections" in json_data:
        text += _process_sections(
            json_data["primaryContentSections"], dev_references, ignore_links
        )
    elif "sections" in json_data:
        text += _process_sections(json_data["sections"], dev_references, ignore_links)

    return text
