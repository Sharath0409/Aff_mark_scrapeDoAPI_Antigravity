import re

def extract_json(text):
    # Optional logic to extract JSON if LLM wraps it in markdown blocks
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def sanitize_html(html_str):
    # Basic cleanup if necessary
    return html_str.strip()
