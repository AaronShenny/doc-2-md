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
# 8. Apple Developer Documentation  (url_to_markdown_apple_dev_docs.js)
# ===========================================================================

def apple_dev_doc_url(url: str) -> str:
    """Map an Apple Developer *url* to its JSON API endpoint.

    Example:
      https://developer.apple.com/documentation/swift/array
      → https://developer.apple.com/tutorials/data/documentation/swift/array.json
    """
    queryless = url.split('?')[0].rstrip('/')
    parts = queryless.split('/')
    json_url = "https://developer.apple.com/tutorials/data"
    for part in parts[3:]:
        json_url += "/" + part
    json_url += ".json"
    return json_url


def _process_content_section(section: dict, dev_references: dict, ignore_links: bool) -> str:
    """Recursively convert an Apple Dev Doc content section to Markdown."""
    text = ""
    for content in section.get("content", []):
        content_type = content.get("type")

        if content_type == "paragraph":
            inline_text = ""
            for inline in content.get("inlineContent", []):
                inline_type = inline.get("type")
                if inline_type == "text":
                    inline_text += inline.get("text", "")
                elif inline_type == "link":
                    if ignore_links:
                        inline_text += inline.get("title", "")
                    else:
                        inline_text += (
                            f"[{inline.get('title', '')}]"
                            f"({inline.get('destination', '')})"
                        )
                elif inline_type == "reference":
                    identifier = inline.get("identifier", "")
                    ref = dev_references.get(identifier, {})
                    inline_text += ref.get("title", "")
                elif inline_type == "codeVoice":
                    inline_text += f"`{inline.get('code', '')}`"
            text += inline_text + "\n\n"

        elif content_type == "codeListing":
            code_text = "\n```\n"
            code_text += "\n".join(content.get("code", []))
            code_text += "\n```\n\n"
            text += code_text

        elif content_type == "unorderedList":
            for list_item in content.get("items", []):
                # rstrip to avoid extra blank lines breaking list continuity
                text += "* " + _process_content_section(
                    list_item, dev_references, ignore_links
                ).rstrip() + "\n"

        elif content_type == "orderedList":
            for n, list_item in enumerate(content.get("items", []), start=1):
                text += f"{n}. " + _process_content_section(
                    list_item, dev_references, ignore_links
                ).rstrip() + "\n"

        elif content_type == "heading":
            level = content.get("level", 2)
            heading_text = content.get("text", "")
            text += "#" * level + " " + heading_text + "\n\n"

    return text


def _process_sections(sections: list, dev_references: dict, ignore_links: bool) -> str:
    """Convert a list of Apple Dev Doc sections to Markdown."""
    text = ""
    for section in sections:
        kind = section.get("kind")

        if kind == "declarations":
            for declaration in section.get("declarations", []):
                tokens = declaration.get("tokens", [])
                if tokens:
                    text += "".join(t.get("text", "") for t in tokens)
                languages = declaration.get("languages", [])
                if languages:
                    text += " \nLanguages: " + ", ".join(languages)
                platforms = declaration.get("platforms", [])
                if platforms:
                    text += " \nPlatforms: " + ", ".join(platforms)
            text += "\n\n"

        elif kind == "content":
            text += _process_content_section(section, dev_references, ignore_links)

        section_title = section.get("title")
        if section_title:
            if kind == "hero":
                text += "# " + section_title + "\n"
            else:
                text += "## " + section_title + "\n\n"

        for section_content in section.get("content", []):
            if section_content.get("type") == "text":
                text += section_content.get("text", "") + "\n"

    return text




