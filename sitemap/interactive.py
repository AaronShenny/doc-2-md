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
# -------------------------------
# INTERACTIVE FLOW
# -------------------------------

def choose_sitemaps(sitemaps):
    print("\nAvailable sitemaps:\n")

    for i, sm in enumerate(sitemaps):
        print(f"{i+1}. {sm}")

    print("\nOptions:")
    print("A - Extract ALL")
    print("Enter numbers (e.g., 1,3,5)")

    choice = input("\nSelect sitemaps: ").strip().lower()

    if choice == "a":
        return sitemaps

    selected = []
    indices = choice.split(",")

    for idx in indices:
        try:
            selected.append(sitemaps[int(idx)-1])
        except:
            pass

    return selected


def filter_urls(urls):
    print("\nDo you want to filter URLs? (y/n)")
    if input().lower() != "y":
        return urls

    keyword = input("Enter keyword (e.g., javascript): ").lower()

    filtered = [u for u in urls if keyword in u.lower()]

    print(f"\nFiltered {len(filtered)} URLs from {len(urls)} total")
    return filtered
