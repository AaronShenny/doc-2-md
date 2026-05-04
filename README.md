# doc-2-md

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI%20Powered-4285F4?style=flat&logo=google&logoColor=white)](https://aistudio.google.com/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-1.32.0-34A853?style=flat&logo=google&logoColor=white)](https://pypi.org/project/google-adk/)
[![Markdownify](https://img.shields.io/badge/markdownify-1.2.2-000000?style=flat&logo=markdown&logoColor=white)](https://pypi.org/project/markdownify/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-4.10.0-59666C?style=flat)](https://pypi.org/project/beautifulsoup4/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat)](https://github.com/AaronShenny/doc-2-md/pulls)

> **Bulk-convert any documentation website into clean, AI-polished Markdown files — ready for LLM ingestion or offline reading.**

`doc-2-md` takes a `sitemap.xml` URL, fetches every documentation page listed in it, converts the raw HTML to Markdown, and then passes each page through a Google Gemini AI agent that strips UI chrome, fixes formatting, and generates structured metadata. The final outputs are a collection of clean `.md` files and a `llms.json` index that describes every page with title, summary, and keywords.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)
- [Example](#example)
- [Limitations](#limitations)

---

## Overview

Documentation websites are designed for humans browsing in a browser. They are full of navigation bars, breadcrumbs, cookie banners, sidebars, and other HTML chrome that adds noise when you try to feed the content into an LLM or store it for offline use.

`doc-2-md` solves this by combining a deterministic HTML-to-Markdown conversion pipeline with a pair of Gemini AI agents:

1. **Beautifier Agent** — removes residual navigation junk, fixes spacing, and ensures proper heading hierarchy and fenced code blocks.
2. **Metadata Agent** — reads the clean Markdown and produces a structured JSON entry (title, summary, keywords) that is collected into a single `llms.json` index file.

---

## How It Works

```
sitemap.xml URL
      │
      ▼
[Sitemap Parser]  ── parses sitemapindex or urlset XML
      │
      ▼
[Interactive Filter]  ── optional keyword-based URL filter
      │
      ▼
  for each URL:
      │
      ├─ [Fetcher]  ── requests.get with a 15-second timeout
      │
      ├─ [HTML Processor]
      │       ├─ strip <script> and <style> blocks
      │       ├─ extract <main> / <article> / largest <div> (BeautifulSoup)
      │       ├─ pre-process <pre> blocks → fenced code placeholders
      │       ├─ pre-process <table> blocks → Markdown table placeholders
      │       ├─ convert remaining HTML → Markdown (markdownify, ATX headings)
      │       ├─ restore placeholders
      │       └─ apply domain-specific regex filters
      │             (Wikipedia, Medium, Stack Overflow, global)
      │
      ├─ [Beautifier Agent (Gemini)]  ── AI-powered Markdown cleanup
      │
      ├─ [save .md file]  → output/<run-id>/docs/<page-title>.md
      │
      └─ [Metadata Agent (Gemini)]  ── extracts title / summary / keywords
              │
              └─ accumulates into llms.json
      │
      ▼
[Save llms.json]  → output/<run-id>/llms.json
```

### Special-cased domains

| Domain | Strategy |
|---|---|
| `developer.apple.com` | Fetches the underlying JSON documentation API directly (no HTML parsing) |
| `stackoverflow.com/questions` | Splits the question and answers into separate DOM sections before conversion |
| `*.wikipedia.org` | Removes citation anchors, audio file links, edit links, and normalises CDN image URLs |
| `*.medium.com` | Fixes truncated CDN image URLs and unwraps nested image+link patterns |

---

## Features

- **Sitemap-driven** — point it at any `sitemap.xml` or nested `sitemapindex` and it handles the rest.
- **Interactive URL selection** — choose individual sub-sitemaps and optionally filter pages by keyword before processing.
- **Readability extraction** — uses `readability-lxml` to identify the article body, falling back to the largest meaningful `<section>`/`<div>` block.
- **Faithful code block preservation** — `<pre>`/`<code>` blocks are extracted before HTML→Markdown conversion and reinserted afterwards, preserving language identifiers (e.g. ` ```python `).
- **Markdown table rendering** — HTML tables are converted to pipe-style Markdown tables; wide tables fall back to an indented bullet list.
- **AI beautification** — Gemini strips breadcrumbs, navigation links, and duplicate lines without removing any real documentation content.
- **Structured metadata index** — every page's title, summary, and keywords are written to a single `llms.json` file alongside the source URL and output file path.
- **Quota-aware retry** — handles `RESOURCE_EXHAUSTED` (HTTP 429) responses from the Gemini API with a graceful wait-and-continue rather than a hard crash.
- **Timestamped run directories** — each run is isolated under `output/YYYY-MM-DD-HH-MM-<sitemap-host>/`.

---

## Project Structure

```
doc-2-md/
├── main.py                  # Entry point — async orchestration loop
├── requirements.txt
├── .env                     # API key and model name (not committed)
│
├── ai/
│   ├── agent.py             # Gemini agent definitions (beautifier + metadata)
│   └── agent_runner.py      # Google ADK runner wrapper
│
├── core/
│   ├── config.py            # Global constants (timeout, user-agent, etc.)
│   ├── fetcher.py           # HTTP helpers (fetch_url, fetch_xml)
│   ├── extractor.py         # HTML content extraction + table conversion
│   ├── formatter.py         # Code block and table placeholder logic
│   ├── converter.py         # markdownify wrapper
│   ├── filters.py           # Domain-specific regex filters
│   └── special.py           # Apple Developer + Stack Overflow readers
│
├── pipeline/
│   └── processor.py         # process_html() and url_to_markdown() pipeline
│
├── sitemap/
│   ├── parser.py            # XML sitemap / sitemapindex parser
│   └── interactive.py       # CLI prompts for sitemap + URL selection
│
├── utils/
│   ├── env.py               # .env loader and API key validation
│   ├── errors.py            # Error handler
│   ├── file_ops.py          # save_text / save_json helpers
│   └── helpers.py           # Filename sanitiser
│
└── output/                  # Generated files (git-ignored)
    └── <run-id>/
        ├── docs/
        │   ├── <page-title>.md
        │   └── ...
        └── llms.json
```

---

## Requirements

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com/) API key with access to the Gemini model specified in `.env`

Python dependencies (installed via `pip`):

| Package | Purpose |
|---|---|
| `google-adk` | Google Agent Development Kit — runs Gemini agents |
| `google-genai` | Google GenAI Python SDK |
| `python-dotenv` | Loads `.env` into `os.environ` |
| `requests` | HTTP fetching |
| `beautifulsoup4` | HTML parsing and DOM traversal |
| `readability-lxml` | Mozilla Readability port — extracts article body |
| `markdownify` | HTML → Markdown conversion |
| `aiohttp` | Async HTTP (available for future use) |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/AaronShenny/doc-2-md.git
cd doc-2-md

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
MODEL_NAME=gemini-2.0-flash
```

- **`GOOGLE_API_KEY`** — required. Obtain from [Google AI Studio](https://aistudio.google.com/app/apikey).
- **`MODEL_NAME`** — the Gemini model used by both the beautifier and metadata agents. `gemini-2.0-flash` or `gemini-1.5-flash` are good choices for the free tier.

---

## Usage

```bash
python main.py
```

The script runs interactively:

1. **Enter sitemap URL** — e.g. `https://docs.example.com/sitemap.xml`
2. **Choose sub-sitemaps** — if the sitemap is a `sitemapindex`, you are shown a numbered list and can type `A` for all or comma-separated numbers (e.g. `1,3`).
3. **Filter URLs (optional)** — type `y` and enter a keyword (e.g. `javascript`) to process only matching pages.
4. Processing begins — each URL is fetched, converted, beautified, and saved automatically.

### Non-interactive tip

To skip the interactive prompts during testing, pipe answers via stdin:

```bash
echo -e "https://docs.example.com/sitemap.xml\nA\nn" | python main.py
```

---

## Output

Each run produces a timestamped directory under `output/`:

```
output/
└── 2026-05-02-19-31-https_docs_example_com_sitemap_xml/
    ├── docs/
    │   ├── getting_started.md
    │   ├── api_reference.md
    │   └── ...
    └── llms.json
```

### `llms.json` format

```json
[
  {
    "title": "Getting Started",
    "summary": "A step-by-step introduction to installing and configuring the SDK.",
    "keywords": ["installation", "quickstart", "SDK", "configuration"],
    "file_location": "<run-id>/docs/getting_started.md",
    "source_url": "https://docs.example.com/getting-started/"
  }
]
```

This file is designed to serve as an `llms.txt`-style index for LLM retrieval-augmented generation (RAG) pipelines.

---

## Example

```
$ python main.py
Enter sitemap.xml URL: https://adk.dev/sitemap.xml

Available sitemaps:

1. https://adk.dev/sitemap-0.xml

Options:
A - Extract ALL
Enter numbers (e.g., 1,3,5)

Select sitemaps: A

Total URLs found: 87

Do you want to filter URLs? (y/n)
n

Final URLs: 87

Converting: https://adk.dev/
============================================================
✅ Saved: agent_development_kit_adk.md

Converting: https://adk.dev/release-notes/
============================================================
✅ Saved: release_notes__agent_development_kit_adk.md
...

LLMS.json is saved and updated in output/2026-05-02-19-31-https_adk_dev_sitemap_xml/llms.json
Work is completed. Please check the output folder
```

---

## Limitations

- **Interactive only** — the tool requires a terminal session; there is no batch or server mode yet.
- **Free-tier quota** — the Gemini free tier has per-minute and per-day request limits. Processing large sitemaps (100+ pages) will likely hit `RESOURCE_EXHAUSTED` (HTTP 429). The tool handles this gracefully by skipping the affected page and continuing, but those pages will be missing from the output.
- **JavaScript-rendered pages** — pages that require a headless browser (React SPAs, Angular apps) will not render correctly because the fetcher uses plain `requests.get`. The tool works best on server-rendered or static documentation sites.
- **Single-run session state** — each `run_agent` call creates a fresh `InMemorySessionService`; there is no cross-page memory or context reuse between agent calls.
- **No deduplication** — if the same URL appears in multiple sub-sitemaps it will be processed twice.
