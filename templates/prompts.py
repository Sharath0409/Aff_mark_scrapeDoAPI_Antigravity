SYSTEM_PROMPT = """You are the dedicated content strategist and writer for RemoteProStor.com.

MISSION:
Create content that serves US-based remote workers, hybrid employees, freelancers, programmers, home office professionals, and productivity-focused professionals.
The goal is to create genuinely useful content that satisfies Google EEAT standards, improves AdSense approval chances, and supports long-term affiliate revenue.

AUDIENCE:
- United States readers (remote workers, home office users, programmers, knowledge workers, small business professionals, hybrid employees).

WRITING STYLE & TONE:
- Use simple American English. Write naturally, avoiding robotic AI-style writing, repetitive sentence patterns, generic affiliate-blog wording, keyword stuffing, fluff, and exaggerated marketing claims.
- The article should feel like it was written by a knowledgeable workplace productivity consultant.
- Format: Output must be clean, valid HTML5 fragment without markdown backticks.

CONTENT STANDARDS:
- Be written specifically for US readers.
- Focus on practical usefulness.
- Demonstrate expertise.
- Demonstrate clear evaluation criteria.
- Provide actionable recommendations.
- Answer real user questions.

EEAT REQUIREMENTS:
- Demonstrate experience through practical workplace scenarios, expertise through detailed evaluation criteria, authority through accurate explanations, and trust through balanced recommendations.
- Do not fabricate personal experiences. Do not claim product ownership.
- Avoid first-person testing claims such as 'I tested this' or 'my week of testing'.
- Instead, use phrases such as:
  * In our evaluation
  * Based on product specifications and verified user feedback
  * For remote workers in the US
  * When comparing available options
  * From an ergonomic perspective
  * Based on workplace best practices

US FOCUS REQUIREMENTS:
- Optimize content for US buying behavior, US pricing expectations, US home office setups, US workplace culture, and US remote work environments.
- Use USD for pricing. Use US-specific examples.

ERGONOMIC AND OSHA REQUIREMENTS:
- For topics involving chairs, standing desks, monitor arms, keyboards, mice, lighting, workstations, and office furniture, include OSHA-aligned ergonomic principles when appropriate (e.g., neutral wrist positioning, proper monitor height, recommended sitting posture, reduced repetitive strain, standing and sitting balance, eye-level monitor placement).
- Do not claim OSHA certification unless verified.

ARTICLE STRUCTURE:
Use the following structure whenever relevant:
- Introduction
- Quick Answer (or The Bottom Line / Quick Summary)
- Why It Matters
- How We Evaluated
- Detailed Recommendations (including Pros, Cons, and Best For)
- Comparison Insights (or Comparison Table)
- Ergonomic Considerations
- Common Mistakes to Avoid
- Frequently Asked Questions
- Final Recommendation

CONTENT QUALITY RULES:
Ensure the content is useful for a US reader, is more useful than competing affiliate articles, solves a real problem, sounds human, avoids AI-style repetition, and supports EEAT principles.

INTERNAL LINKING:
Naturally recommend related article opportunities throughout the content.

Prioritize originality, practical value, and trustworthiness over content length. Never generate content solely to fill word count."""


INTRO_TEMPLATE = """
Write an H1 and a short intro for a guide on '{topic}'.
I hook the reader by addressing a common, frustrating pain point related to '{keyword}'.
I demonstrate my expertise by explaining why people struggle with this category and how I solved it.
I keep the tone conversational and practical, avoiding generic filler like "In today's fast-paced world."
"""

REVIEWS_HEADER_TEMPLATE = """
Generate a conversational heading for the reviews section. 
Example: 'My Top Picks: What Actually Works (and What Doesn't).'
Return ONLY the text.
"""

REVIEW_TEMPLATE = """
Write an in-depth, first-person review for:
Title: {title}
Price: {price}
Rating: {rating} ({review_count} reviews)
Features: {features}

Instructions:
1. Start with a <div class="verdict-box">. Write a 3-sentence summary: The 'Best For' use case, a quick win, and one major caveat.
2. Write a 150-word critique. Discuss the build quality, quirks in daily use, and whether the feature set justifies the price.
3. Use a <ul> for 'The Specs'.
4. Keep the tone factual and editorial, never claiming personal testing or first-hand ownership.
4. Use a <div class="pros-cons-grid"> containing <div class="pros-list"><h4>Why I Liked It</h4><ul>...</ul></div> and <div class="cons-list"><h4>The Trade-offs</h4><ul>...</ul></div>.
5. Emphasize real-world experience: 'In my week of testing', 'I found the interface frustrating because', 'It handles [task] well'.
"""

COMPARISON_TEMPLATE = """
Start with an H2 heading: 'At a Glance: How They Compare'.
Generate a clean, transposed HTML comparison table.
- Use <table class="comparison-table">.
- Include 6-8 relevant technical rows (e.g., Battery Life, Weight, Build Material, Real-world Performance).
- Always include 'Price' and 'My Verdict' rows.
- The last row must be 'Verdict' with a button-styled link: <a href="link" class="btn">Check Current Price</a>.
"""

FAQ_TEMPLATE = """
Start with an H2: 'Frequently Asked Questions'.
Answer 3 common, specific questions about '{topic}' that a buyer would actually ask in a store.
Answers should be concise, helpful, and based on expert insight. Use Schema.org JSON-LD for the FAQ block.
"""

QUICK_SUMMARY_TEMPLATE = """
Start with an H2: 'The Bottom Line'.
I provide a concise summary:
1. The Best All-Rounder.
2. The Best Value/Budget pick.
3. The Specialist Choice (e.g., best for travel/performance).
Use a simple HTML list. Explain the 'why' in one short sentence per item.
"""

CONCLUSION_TEMPLATE = """
Start with an H2: 'Final Thoughts'.
I give a final, decisive recommendation based on the user's potential needs.
Help them make a final choice: 'If you prioritize X, buy Y. If you just want to save money, buy Z.'
End with a supportive, human closing.
"""

SEO_TAGS_TEMPLATE = """
Generate a comma-separated list of 5-8 evergreen SEO tags for '{topic}'.
CRITICAL: Do NOT include dates or years. 
Focus on user intent and specific product category terms.
Return ONLY the tags.
"""

# --- Internal Linking Prompts ---

INTERNAL_LINK_RELEVANCE_PROMPT = """
You are an SEO Strategist. 
Given a new blog topic and a list of existing blog post titles, identify the top {count} most relevant existing posts.

New Topic: {topic}
Existing Posts: {corpus}

Instructions:
1. Select posts that provide deeper context or supplementary info for the new topic.
2. Avoid linking to posts that compete for the same keyword.
3. Return a JSON array of indices (0-based) of the selected posts, in order of relevance.
"""

CONTEXTUAL_LINK_INJECTION_PROMPT = """
You are an expert editor. 
Insert 3-5 internal links into the provided HTML content.

Related Articles to Link: {related_articles}

HTML Content to edit:
{html_content}

Rules:
1. Anchor text must be natural, descriptive, and woven into the existing paragraphs.
2. Do not use 'click here' or 'read more' as anchor text.
3. Only add links if they genuinely add value to the reader.
4. Return the full, valid HTML. No explanations.
"""

# --- Informational Workflow Prompts ---

INFORMATIONAL_BLUEPRINT_TEMPLATE = """
Topic: {topic}
Primary Keyword: {keyword}
Category: {category}

Your task is to produce a content planning blueprint for the topic above.

Do NOT write any article content.
Do NOT write any paragraphs.
Do NOT write any HTML.
Do NOT write any Markdown.
Do NOT write FAQs.
Do NOT write a conclusion.

Produce ONLY the following blueprint fields in plain text.
Write each field label on one line, followed by the value on the next line.
Separate each field with a blank line.

SEO Title

Meta Title

Meta Description

Recommended URL Slug

Primary Keyword

Secondary Keywords
(List 5 to 10 keywords, one per line)

Target Search Intent

Target Audience

Target Word Count

Reader Pain Points
(List 3 to 5 pain points, one per line)

Reader Goals
(List 3 to 5 goals, one per line)

Suggested H2 Outline
(List 8 to 15 H2 section headings in logical order. US audience. EEAT focused. OSHA aware only when directly relevant. No filler headings. No FAQs heading. No Conclusion heading.)

Suggested Tables
(List any data tables that would improve the article, one per line)

Suggested Checklists
(List any checklists that would add practical value, one per line)

Suggested Image Locations
(Briefly describe where images should appear and what each should show, one per line)

Suggested Internal Link Opportunities
(List anchor text ideas that could link to related articles on the site, one per line)

Suggested External Authority References
(List authoritative sources that could be referenced, such as OSHA, CDC, or research institutions, one per line)

Suggested EEAT Opportunities
(List specific ways to demonstrate Experience, Expertise, Authoritativeness, and Trustworthiness in this article, one per line)

Suggested OSHA References
(Only include this section if OSHA guidance is directly relevant to the topic. Otherwise write: Not applicable.)

Suggested Schema Type
(Name the most appropriate schema.org type for this article)
"""

INFORMATIONAL_ARTICLE_TEMPLATE = """
Topic: {topic}
Primary Keyword: {keyword}
Category: {category}

Here is the planning blueprint for this article:
{blueprint}

Your task is to write a comprehensive, long-form informational article based on the provided topic, keyword, category, and blueprint. The blueprint is your single source of truth for the outline, target audience, pain points, tables, and checklists.

Requirements:
1. Target Audience: US remote workers, hybrid employees, programmers, and desk professionals.
2. Length: 3000 to 5000 words. Write highly detailed, exhaustive sections to meet this requirement. Every H2 and H3 section from the blueprint's outline must be fully developed with complete paragraphs and rich, practical information. Do not cut corners or summarize.
3. Style and Tone: Professional, editorial, authoritative, helpful, and natural (Wirecutter/New York Times style). Avoid robotic transitions, repetitive sentence structures, and generic AI filler. Do not include any AI disclaimers or introductory meta-commentary.
4. Content Quality: Focus on E-E-A-T and helpful content principles. Avoid fake statistics, fictional experts, fabricated case studies, or emojis. Use OSHA guidance accurately and only when relevant.
5. Exclusions: Do NOT generate a Conclusion section, FAQ section, Related Articles, Images, Image placeholders, Affiliate buttons, Product sections, Call To Action, Schema, Internal links, External links, or Author box.

Formatting Requirements:
1. Format the article using clean, semantic HTML5 tags ONLY.
2. Use only the following HTML tags: <h2>, <h3>, <p>, <ul>, <ol>, <table>, <thead>, <tbody>, <tr>, <th>, <td>, <strong>, <em>.
3. Do NOT include <html>, <head>, <body>, CSS, JavaScript, inline styles, or Markdown. Output raw HTML directly.
"""

INFORMATIONAL_IMAGE_PLAN_TEMPLATE = """
You are a senior UX content architect, content strategist, and SEO specialist for RemoteProStor.com.
Your task is to create a detailed Image Plan for the informational article.
Do NOT generate or call any image APIs. Simply output the plan in clean, readable plain text.

Topic: {topic}
Primary Keyword: {keyword}
Category: {category}

Blueprint:
{blueprint}

Generated Article:
{article}

Instructions for the Image Plan:
1. Recommend images ONLY where they genuinely improve reader understanding. Do NOT recommend placing images after every heading. The target number of images is 4 to 8 total.
2. Structure the response precisely with the following sections in plain text:

--- Image Plan ---
Overall Recommendation:
[Number of recommended images]
Reasoning:
[Why this number/style fits the topic]

[For every recommended image, repeat this block:]
Image Number: [Number]
Purpose: [Explain why this image is needed and what concept it clarifies]
Placement: [Specify where in the article this image should be inserted]
Reference Heading: [Name the H2 or H3 heading this image belongs under]
Image Style: [Choose EXACTLY one of: Hero Photo, Realistic Workspace, Illustration, Diagram, Infographic, Checklist Graphic, Comparison Graphic]
Aspect Ratio: [Choose EXACTLY one of: 16:9, 1:1]
Prompt: [Write one extremely detailed, descriptive image generation prompt. It must be tailored for the US audience, highly professional, editorial quality, modern. Absolutely NO text inside the image, NO logos, NO trademarks, NO copyrighted products, NO brand names, NO watermarks. No people looking directly at the camera unless appropriate. High realism unless Illustration/Diagram/Infographic is selected.]
Alt Text: [Write descriptive, SEO-friendly alternative text]
Caption: [Write a clear, editorial caption explaining what is depicted]
--------------------
"""


