import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from google.genai.errors import ClientError

from ai.agent_runner import run_agent
from ai.agent import beautifier_agent, metadata_agent
from core.fetcher import fetch_xml
from pipeline.processor import url_main
from sitemap.interactive import choose_sitemaps, filter_urls
from sitemap.parser import extract_sitemaps, extract_urls
from utils.env import setup_env
from utils.errors import handle_error
from utils.file_ops import save_json, save_text
from utils.helpers import get_filename_from_markdown

OUTPUT_ROOT = Path("output")
USER_AGENT_RUN_ID_FORMAT = "%Y-%m-%d-%H-%M"


def make_run_id(sitemap_url: str) -> str:
    timestamp = datetime.now().strftime(USER_AGENT_RUN_ID_FORMAT)
    clean_url = re.sub(r"[^a-zA-Z0-9]+", "_", sitemap_url).strip("_")
    return f"{timestamp}-{clean_url}"


def parse_metadata_json(meta_str: str):
    if not meta_str:
        return None

    meta_str = re.sub(r"```json|```", "", meta_str, flags=re.IGNORECASE).strip()

    match = re.search(r"\{.*\}", meta_str, re.DOTALL)
    if match:
        meta_str = match.group(0)

    try:
        return json.loads(meta_str)
    except json.JSONDecodeError:
        return None


async def process_url(url: str, run_id: str, docs_dir: Path, all_meta: list) -> None:
    raw_md = url_main(url)
    if not raw_md or not raw_md.strip():
        print(f"⚠️ Empty markdown from: {url}")
        return
    #TESTING
    #raw_filename = get_filename_from_markdown(raw_md)
    #raw_path = docs_dir / f"before_agent_{raw_filename}"
    #save_text(raw_path, raw_md)

    clean_md = await run_agent(beautifier_agent, raw_md, f"{run_id}_beautify")
    if not clean_md or not clean_md.strip():
        print(f"⚠️ Beautifier returned empty output for: {url}")
        return

    clean_filename = get_filename_from_markdown(clean_md)
    clean_path = docs_dir / clean_filename
    save_text(clean_path, clean_md)

    meta_str = await run_agent(metadata_agent, clean_md, f"{run_id}_meta")
    meta = parse_metadata_json(meta_str)

    if not meta:
        print(f"⚠️ Invalid or empty metadata for: {url}")
        return

   
    meta["file_location"] = f"{run_id}/docs/{clean_path.name}"
    meta["source_url"] = url
    all_meta.append(meta)

    print(f"✅ Saved: {clean_path.name}")


async def run():
    setup_env()

    all_meta = []
    sitemap_url = input("Enter sitemap.xml URL: ").strip()

    xml_content = fetch_xml(sitemap_url)
    sitemaps = extract_sitemaps(xml_content)

    if sitemaps:
        selected = choose_sitemaps(sitemaps)
        all_urls = []
        for sm in selected:
            print(f"\nFetching: {sm}")
            sm_xml = fetch_xml(sm)
            all_urls.extend(extract_urls(sm_xml))
    else:
        all_urls = extract_urls(xml_content)

    print(f"\nTotal URLs found: {len(all_urls)}")

    final_urls = filter_urls(all_urls)
    print(f"\nFinal URLs: {len(final_urls)}\n")

    run_id = make_run_id(sitemap_url)
    docs_dir = OUTPUT_ROOT / run_id / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    for url in final_urls:
        try:
            await process_url(url, run_id, docs_dir, all_meta)

        except ValueError as e:
            if "API key" in str(e):
                print("\n❌ ERROR: No API key found")
                print("👉 Set GOOGLE_API_KEY in your .env file")
                return
            raise

        except ClientError as e:
            msg = str(e)

            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                print("\n⚠️ API QUOTA EXCEEDED")
                print("👉 You hit the free-tier limit")
                print("👉 Options:")
                print("   - Wait for reset")
                print("   - Reduce URLs")
                print("   - Change the model in ai_agent/.env")
                print("   - Upgrade plan")
                print(msg)
                await asyncio.sleep(5)
                continue

            if "API key" in msg or "permission" in msg:
                print("\n❌ Invalid API key or permission issue")
                continue

            print("\n❌ Unknown API error:")
            print(msg)
            continue

        except Exception as e:
            handle_error(e)
            continue

    llms_path = OUTPUT_ROOT / run_id / "llms.json"
    save_json(llms_path, all_meta)

    print(f"LLMS.json is saved and updated in {llms_path}")
    print("Work is completed. Please check the output folder")


if __name__ == "__main__":
    asyncio.run(run())
