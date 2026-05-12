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

def normalize_topic(topic):
    """Normalize topic for duplicate detection (lowercase, trim, no special chars)."""
    if not topic:
        return ""
    # Convert to lowercase
    topic = topic.lower()
    # Remove special characters except spaces
    topic = re.sub(r'[^a-z0-9\s]', '', topic)
    # Collapse multiple spaces and trim
    topic = " ".join(topic.split())
    return topic
