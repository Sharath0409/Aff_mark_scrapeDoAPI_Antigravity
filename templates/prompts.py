SYSTEM_PROMPT = """You are an expert product reviewer and SEO specialist.
Write in a conversational, authoritative, and engaging tone. 
Avoid overused AI buzzwords (e.g., 'In conclusion', 'Delve into', 'Tapestry', 'Testament').
Always output pure HTML5 format without Markdown wrappers unless specified."""

INTRO_TEMPLATE = """
Write an engaging SEO-optimized introduction for an affiliate blog post about '{topic}'.
Include the target keyword: '{keyword}'.
Structure it with an engaging hook, the problem it solves, and what the reader will find in the article.
"""

REVIEW_TEMPLATE = """
Write a compelling product review for the following Amazon product:
Title: {title}
Price: {price}
Rating: {rating} ({review_count} reviews)
Features: {features}

Include:
- A brief description.
- A bulleted list of 3 Pros and 2 Cons.
- Do NOT include any placeholder URLs. I will inject them later.
"""

COMPARISON_TEMPLATE = """
Based on the products reviewed above, generate a comparative HTML table summarizing their key features and prices.
Ensure the final row of the table for each product contains a "Check Price" button linking to the product URL provided.
Use `<table class="comparison-table">`.
"""

FAQ_TEMPLATE = """
Generate a FAQ section for the topic '{topic}' with 3 common questions and answers.
Also, output the corresponding JSON-LD FAQ schema.
"""

SEO_TAGS_TEMPLATE = """
Generate a comma-separated list of 5 to 8 highly relevant, SEO-optimized keywords and tags for a blog post about '{topic}' (main keyword: '{keyword}').
Return ONLY the comma-separated string, with no quotes, bullet points, or extra text.
"""
