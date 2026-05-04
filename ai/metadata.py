async def get_metadata(content):
    meta_str = await run_agent(metadata_agent, content, "session_meta")

    meta_str = re.sub(r"```json|```", "", meta_str).strip()

    if not meta_str:
        return None

    try:
        return json.loads(meta_str)
    except:
        return None
