def handle_error(e):
    msg = str(e)

    if "RESOURCE_EXHAUSTED" in msg:
        print("⚠️ Quota exceeded")
        return

    if "API key" in msg:
        print("❌ API key issue")
        return

    print("❌ Unexpected:", msg)
