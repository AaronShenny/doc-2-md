import json
def save_text(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
