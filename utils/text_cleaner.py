import re

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    markdown = None

def extract_json(text):
    # Optional logic to extract JSON if LLM wraps it in markdown blocks
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def convert_markdown_to_html(md_text: str) -> str:
    """Convert markdown text to HTML. Handles headers, paragraphs, lists, etc."""
    if not MARKDOWN_AVAILABLE or not md_text:
        return md_text
    
    # Configure markdown with safe extensions
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
        ],
        output_format='html'
    )
    return md.convert(md_text)

def sanitize_html(html_str):
    """
    Clean and convert content to valid HTML.
    - Converts markdown to HTML if needed
    - Strips whitespace
    - Removes markdown code fences if present
    - Ensures no raw markdown headers (# ) leak into output
    """
    if not html_str:
        return ""
    
    # Remove markdown code fences if present
    html_str = html_str.strip()
    if html_str.startswith("```html"):
        html_str = html_str.replace("```html", "").replace("```", "").strip()
    elif html_str.startswith("```"):
        html_str = html_str.replace("```", "").strip()
    
    # Check if content appears to be markdown (has markdown-style headers, etc.)
    # Heuristic: if it has markdown headers but no HTML tags, convert it
    has_html_tags = bool(re.search(r'<[a-z][^>]*>', html_str))
    has_markdown_headers = bool(re.search(r'^#{1,6}\s+\S', html_str, re.MULTILINE))
    
    if has_markdown_headers and not has_html_tags:
        # Likely pure markdown - convert to HTML
        html_str = convert_markdown_to_html(html_str)
    elif has_markdown_headers and has_html_tags:
        # Mixed content - try to convert markdown portions
        # For safety, convert the whole thing
        html_str = convert_markdown_to_html(html_str)
    
    # Final safety: strip any remaining raw markdown headers that weren't converted
    # This catches cases where markdown conversion missed something
    html_str = re.sub(r'^#{1,6}\s+(.+)$', r'<h2>\1</h2>', html_str, flags=re.MULTILINE)
    
    return html_str.strip()

def extract_json(text):
    # Optional logic to extract JSON if LLM wraps it in markdown blocks
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

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
