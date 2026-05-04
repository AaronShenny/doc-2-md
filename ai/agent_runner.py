import asyncio
import os

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv
from .agent import beautifier_agent, metadata_agent

APP_NAME = "docs_pipeline_agent"
USER_ID = "default_user"

#load_dotenv()
#os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError("Please set GOOGLE_API_KEY in your environment before running this script.")


async def run_agent(agent, content: str, session_id: str) -> str:
    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=content)],
    )

    events = runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=user_message,
    )

    final_text = []
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_text.append(event.content.parts[0].text)

    return "\n".join(final_text).strip()


async def main():

    with open("content.md", "r", encoding="utf-8") as f:
        content = f.read()

    print("Running beautifier agent...")
    clean_md = await run_agent(beautifier_agent, content, session_id="beautify_1")

    with open("cleaned.md", "w", encoding="utf-8") as f:
        f.write(clean_md)

    print("Running metadata agent...")
    llms_txt = await run_agent(metadata_agent, clean_md, session_id="metadata_1")

    with open("llms.txt", "w", encoding="utf-8") as f:
        f.write(llms_txt)

    print("\nSaved: cleaned.md")
    print("Saved: llms.txt")
    print("\nPreview:\n")
    print(llms_txt)


if __name__ == "__main__":
    asyncio.run(main())
