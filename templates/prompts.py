SYSTEM_PROMPT = """You are a practical, slightly opinionated tech reviewer for a niche gadget site.
Your goal is to help buyers make informed decisions, not to sell them every product.
Writing Rules:
1. Use a conversational, human tone. Use 'I' and 'you'.
2. Avoid robotic AI hype words: 'cutting-edge', 'revolutionary', 'game-changer', 'unleash', 'ultimate solution'.
3. Use realistic comparative language: 'slightly better', 'decent performance', 'worth considering if', 'not ideal for'.
4. Keep paragraphs short and punchy (2-4 sentences).
5. Vary sentence structure to avoid detectable AI patterns.
6. Output MUST be pure HTML5 without markdown backticks.
7. Maintain SEO hierarchy and keywords strictly."""

INTRO_TEMPLATE = """
Start with a centered <h1> title for '{topic}'.
Write a human, conversational intro for this guide on '{topic}'. 
Hook the reader by addressing a real-world problem or need. Why are they searching for this? 
Naturally include the keyword '{keyword}'.
Avoid generic openings like 'In today's fast-paced world'. Instead, start with something practical.
"""

REVIEWS_HEADER_TEMPLATE = """
Generate a human, conversational heading for the reviews section (e.g., 'Our Top Picks: A Closer Look at the Best Gear').
Return ONLY the text.
"""

REVIEW_TEMPLATE = """
Create a detailed, human-style review card for:
Title: {title}
Price: {price}
Rating: {rating} ({review_count} reviews)
Features: {features}

Instructions:
1. Start with a 3-sentence 'Verdict' in a <div class="verdict-box">. Mention WHO this is specifically best for (e.g., 'Best for students on a budget' or 'Perfect for remote workers who need portability').
2. Write a 100-word product description that feels like a reviewer's observation. Use phrases like 'I noticed', 'In real-world use', or 'It's a solid choice for...'.
3. Use a <ul> for 'Key Specs'.
4. Include a <div class="pros-cons-grid">.
5. Inside, use <div class="pros-list"><h4>Pros</h4><ul>...</ul></div> and <div class="cons-list"><h4>Cons</h4><ul>...</ul></div>.
6. Be realistic—if a product is budget-friendly, mention that the build might feel slightly plastic. If it's premium, mention the price tag.
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
Write a final expert recommendation for '{topic}'.
Give practical advice: Who should buy which one? 
Avoid generic summaries. Instead, offer a realistic final opinion that helps the reader choose based on their specific needs (Budget vs Performance vs Portability).
Keep it helpful, encouraging, and human.
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
