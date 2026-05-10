SYSTEM_PROMPT = """You are a seasoned gadget reviewer and tech enthusiast. 
Write in a relatable, human, and slightly opinionated tone. 
Use personal pronouns like 'I' and 'you'. 
Break up long paragraphs into punchy, 2-3 sentence chunks. 
Avoid robotic transitions and 'corporate' AI language.
Always output pure HTML5 without Markdown backticks."""

INTRO_TEMPLATE = """
Write a conversational, SEO-optimized intro for '{topic}'. 
Hook the reader immediately—don't just define the topic, tell them WHY they need to care. 
Include the keyword '{keyword}' naturally.
Make it sound like a friend giving advice, not an encyclopedia entry.
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
Generate a detailed TRANSPOSED HTML comparison table. 
- Identify 6-8 of the most important technical specifications/features specifically relevant to this product category.
- The first column must be 'Feature'.
- Each subsequent column must be one of the products.
- Always include 'Price' and 'Verdict' rows.
- The last row must be 'Action' with a 'Check Price' button for each product.
- Use <table class="comparison-table">.
"""

FAQ_TEMPLATE = """
Generate 3 'Real-World' FAQs for '{topic}'. 
Answer them briefly and helpfully. Include JSON-LD schema.
"""

SEO_TAGS_TEMPLATE = """
Generate a comma-separated list of 5-8 SEO tags for '{topic}'.
CRITICAL: Do NOT include any years (e.g., no '2023', '2024', etc.).
Keep them evergreen and keyword-focused.
Return ONLY the tags, no quotes.
"""
