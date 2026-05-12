SYSTEM_PROMPT = """You are a seasoned gadget reviewer and tech enthusiast. 
Write in a relatable, human, and slightly opinionated tone. 
Use personal pronouns like 'I' and 'you'. 
Break up long paragraphs into punchy, 2-3 sentence chunks. 
Avoid robotic transitions and 'corporate' AI language.
Always output pure HTML5 without Markdown backticks."""

INTRO_TEMPLATE = """
Start with a centered <h1> title for '{topic}'.
Then write a conversational, SEO-optimized intro. 
Hook the reader immediately—don't just define the topic, tell them WHY they need to care. 
Include the keyword '{keyword}' naturally.
Make it sound like a friend giving advice, not an encyclopedia entry.
"""

REVIEWS_HEADER_TEMPLATE = """
Generate a conversational heading for the detailed product reviews section (e.g., 'A Closer Look: Our In-Depth Reviews').
Return ONLY the heading text.
"""

REVIEW_TEMPLATE = """
Create a 'Product Card' for this Amazon item:
Title: {title}
Price: {price}
Rating: {rating} ({review_count} reviews)
Features: {features}

Instructions:
1. Write a 3-sentence 'Verdict'—wrap it in a <div class="verdict-box">.
2. Write a detailed 100-word product description.
3. Create a <ul> list for 'Key Specifications'.
4. Create a <div class="pros-cons-grid">.
5. Inside, use a <div class="pros-list"><h4>Pros</h4><ul>...</ul></div> and a <div class="cons-list"><h4>Cons</h4><ul>...</ul></div>.
6. Use professional, authoritative language.
"""

COMPARISON_TEMPLATE = """
Start with a conversational heading (e.g., 'Side-by-Side: How They Compare').
Generate a detailed TRANSPOSED HTML comparison table. 
- Identify 6-8 of the most important technical specifications/features specifically relevant to this product category.
- The first column must be 'Feature'.
- Each subsequent column must be one of the products.
- Always include 'Price' and 'Verdict' rows.
- The last row must be 'Action' with a 'Check Price' button for each product.
- Use <table class="comparison-table">.
"""

FAQ_TEMPLATE = """
Start with a conversational heading (e.g., 'Questions? We've Got Answers').
Generate 3 'Real-World' FAQs for '{topic}'. 
Answer them briefly and helpfully. Include JSON-LD schema.
"""

QUICK_SUMMARY_TEMPLATE = """
Start with a conversational heading (e.g., 'The Quick Version: Our Top Picks').
Write a 'Quick Summary' for this guide on '{topic}'. 
Include:
1. A 'Top Pick' with a brief reason why.
2. A 'Best Budget' option.
3. A 'Premium Choice'.
Keep it extremely concise and scan-friendly using a simple HTML list.
"""

CONCLUSION_TEMPLATE = """
Start with a conversational heading (e.g., 'The Final Word' or 'Wrapping Up').
Write a final 'Conclusion' for this buying guide on '{topic}'. 
Summarize what the reader should look for and give a final expert recommendation based on different user needs.
Use a helpful, encouraging tone.
"""


SEO_TAGS_TEMPLATE = """
Generate a comma-separated list of 5-8 SEO tags for '{topic}'.
CRITICAL: Do NOT include any years (e.g., no '2023', '2024', etc.).
Keep them evergreen and keyword-focused.
Return ONLY the tags, no quotes.
"""

# --- Internal Linking Prompts ---

INTERNAL_LINK_RELEVANCE_PROMPT = """
You are an SEO Strategist. 
Given a new blog topic and a list of existing blog post titles/labels, identify the top {count} most relevant existing posts.

New Topic: {topic}
New Labels: {labels}

Existing Posts:
{corpus}

Instructions:
1. Prioritize posts with matching labels.
2. Use semantic similarity for titles (e.g., a post about 'Work from Home' is relevant to 'Remote Productivity').
3. Avoid linking to identical topics if they exist (don't link a laptop review to another review of the same laptop).
4. Return a JSON array of indices (0-based) of the selected posts, in order of relevance.
Example Output: [2, 5, 12]
"""

CONTEXTUAL_LINK_INJECTION_PROMPT = """
You are an expert HTML editor. 
Your task is to insert 3-5 internal links into the provided blog HTML.

Related Articles to Link:
{related_articles}

HTML Content:
{html_content}

Rules:
1. Find natural anchor text for each related article within the existing <p> tags.
2. Do NOT change the original meaning of the text.
3. If no natural anchor text exists for a specific link, do NOT force it (skip that link).
4. Do NOT link the same phrase twice.
5. Do NOT link to the same URL twice.
6. Use clean <a> tags: <a href="URL">Anchor Text</a>.
7. Return ONLY the modified HTML. No explanations.
"""
