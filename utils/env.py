import os
from dotenv import load_dotenv


def setup_env():
    """
    Load environment variables and validate required keys.
    """

    # Load .env file
    load_dotenv()

    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    modal_name = os.getenv("MODEL_NAME")

    # Validate
    if not api_key:
        raise ValueError(
            "❌ GOOGLE_API_KEY not found.\n"
            "👉 Create a .env file and add:\n"
            "GOOGLE_API_KEY=your_key_here"
        )

    # Ensure it's available globally (for SDKs that read from env)
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["MODAL_NAME"] = modal_name

    return api_key,modal_name
