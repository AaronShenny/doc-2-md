import re

def get_filename_from_markdown(content: str):
    for line in content.split("\n"):
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            break
    else:
        title = "untitled"

    filename = re.sub(r'[^a-zA-Z0-9_ ]', '', title)
    return filename.replace(" ", "_").lower()
