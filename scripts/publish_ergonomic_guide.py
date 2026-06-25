import sys, os
import logging
from bs4 import BeautifulSoup

# Setup import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.internal_linker import InternalLinkManager
from scripts.remove_h1_tags import BloggerH1Remover
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("publish_guide")

def main():
    logger.info("Initializing article generation and publishing workflow...")
    
    # 1. Initialize Clients and Managers
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    link_manager = InternalLinkManager(publisher)
    h1_remover = BloggerH1Remover(dry_run=False)
    
    # Article meta
    seo_title = "The Ultimate Ergonomic Workspace Guide for Remote Workers (2026)"
    meta_description = "A comprehensive, expert‑crafted pillar article that helps remote workers design ergonomic home offices, improve posture, reduce fatigue, and boost productivity."
    url_slug = "ultimate-ergonomic-workspace-guide-remote-workers-2026"
    
    # Refresh corpus for internal linking
    link_manager.refresh_corpus()
    
    # Base editorial guidelines shared across prompts
    base_instructions = """
You are a senior ergonomics consultant and remote work productivity specialist for RemoteProStor.com.
SITE PROFILE: RemoteProStor.com serves US-based remote workers, hybrid employees, freelancers, software developers, home office professionals, and productivity-focused professionals.

WRITING RULES:
1. Write for US readers only.
2. Use simple, natural American English.
3. Avoid robotic, repetitive, or AI-sounding phrases (e.g. avoid starting sentences with "In today's fast-paced world", "delve", "tapestry", "moreover", "furthermore", "essential", "crucial").
4. Avoid keyword stuffing.
5. Avoid generic introductions and unnecessary filler.
6. Avoid exaggerated marketing language.
7. Avoid fake personal stories.
8. Avoid claiming product ownership or testing unless explicitly supported.
9. Never invent facts.
10. Format: Output MUST be clean, valid HTML5 fragment. Do NOT wrap in markdown code blocks like ```html. Output raw HTML directly.
11. Tone: Write as a knowledgeable workplace productivity consultant helping US professionals make informed decisions.
Preferred phrases:
- In our evaluation
- When comparing available options
- For remote workers in the US
- Based on product specifications and user feedback
- From an ergonomic perspective
- For long-term productivity
- For home office setups

Prioritize originality, practical value, and trustworthiness over content length. Never generate content solely to fill word count.
"""

    logger.info("Generating article in sections to guarantee comprehensive word count (>= 1800 words)...")
    
    # Section 1: Intro & Quick Recommendation
    logger.info("Generating Section 1: Intro & Quick Recommendation...")
    prompt_1 = base_instructions + f"""
Task: Write the first part of the guide: "{seo_title}".
This part must include:
1. Introduction: Hook the reader by addressing common, frustrating physical pain points of US hybrid/remote setups (neck strain, lower back fatigue, wrist soreness). Establish professional expertise without generic filler.
2. Quick Recommendation: A styled quick-summary block (using a div with inline styles: e.g., background #fffbeb, border 1px solid #fef3c7, padding 20px, border-radius 8px) highlighting the essential components for a solid baseline ergonomic setup (e.g., adjustable chair, standard monitor height, and split keyboard).
Target Length: 400-500 words. Make the explanations detailed and practical.
"""
    r1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt_1}],
        temperature=0.7
    )
    section_1 = r1.choices[0].message.content.strip()

    # Section 2: How We Evaluated & Detailed Chairs & Desks
    logger.info("Generating Section 2: How We Evaluated & Chairs/Desks...")
    prompt_2 = base_instructions + f"""
Task: Write the second part of the guide: "{seo_title}".
This part must include:
1. How We Evaluated: Explain our evaluation criteria (durability, adjustability, build materials, price-to-value ratio, and alignment with OSHA-aligned ergonomic principles).
2. Detailed Recommendations - Chairs: Provide a deep-dive analysis of ergonomic chairs. Mention specific, highly-rated models such as the Herman Miller Aeron (premium/mesh), Steelcase Leap V2 (premium/fabric/support), and IKEA Markus (budget) based on product specifications and user feedback. Discuss adjustments like seat pan depth, tilt lock, and multi-directional armrests.
3. Detailed Recommendations - Desks: Review sit-stand standing desks, covering weight capacities, motor stability, and wire management. Discuss options like the Uplift V2, Jarvis Standing Desk, and budget options like the SHW standing desk.
Target Length: 550-650 words. Do not summarize; write comprehensive paragraphs detailing physical benefits and options.
"""
    r2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "assistant", "content": section_1},
            {"role": "user", "content": prompt_2}
        ],
        temperature=0.7
    )
    section_2 = r2.choices[0].message.content.strip()

    # Section 3: Detailed Monitors, Keyboards & Mice, Accessories
    logger.info("Generating Section 3: Monitors, Keyboards, & Accessories...")
    prompt_3 = base_instructions + f"""
Task: Write the third part of the guide: "{seo_title}".
This part must include:
1. Detailed Recommendations - Monitors: Discuss monitor placement (arm's length distance, height), screen sizes, panel types (IPS for viewing angles), dual-monitor ergonomics, and the value of adjustable monitor arms.
2. Detailed Recommendations - Keyboards & Mice: Analyze split ergonomic keyboards (like the Kinesis Advantage2 or Microsoft Ergonomic) and vertical or trackball mice (like the Logitech MX Vertical) that keep wrists in a neutral handshake position.
3. Detailed Recommendations - Accessories: Cover footrests, desk mats, and ambient lighting to reduce glare.
Target Length: 500-600 words. Provide specific anatomical context, e.g. reducing pronation of the forearm and strain on the carpal tunnel.
"""
    r3 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "assistant", "content": section_1 + "\n" + section_2},
            {"role": "user", "content": prompt_3}
        ],
        temperature=0.7
    )
    section_3 = r3.choices[0].message.content.strip()

    # Section 4: Pros & Cons, Best For, and Comparison Insights
    logger.info("Generating Section 4: Pros/Cons & Comparison Insights...")
    prompt_4 = base_instructions + f"""
Task: Write the fourth part of the guide: "{seo_title}".
This part must include:
1. Pros & Cons: Discuss the trade-offs of major workstation setup choices (e.g., active standing desks vs. stationary desks, mechanical ergonomic keyboards vs. membrane, mesh chairs vs. upholstered cushions).
2. Best For: Specific workspace configurations and recommendations for different remote worker profiles (e.g. software developers typing 10 hours a day, budget-focused freelancers, hybrid workers in compact city apartments).
3. Comparison Insights: Provide a comparison table or list showing Budget Setup (under $500), Mid-Range Setup ($1,000 - $2,000), and Premium Professional Setup ($3,000+) with specific items for each level.
Target Length: 500-600 words.
"""
    r4 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "assistant", "content": section_1 + "\n" + section_2 + "\n" + section_3},
            {"role": "user", "content": prompt_4}
        ],
        temperature=0.7
    )
    section_4 = r4.choices[0].message.content.strip()

    # Section 5: Ergonomic Posture, FAQs, & Final Recommendation
    logger.info("Generating Section 5: Posture, FAQs, & Conclusion...")
    prompt_5 = base_instructions + f"""
Task: Write the final part of the guide: "{seo_title}".
This part must include:
1. Ergonomic Considerations: Provide OSHA-aligned posture guidelines (the 90-degree elbow rule, screen eye-level top, flat feet alignment, and the 20-20-20 rule for eye strain).
2. Frequently Asked Questions: Provide 4-5 actual, common questions US remote workers ask. You MUST include a schema.org FAQ JSON-LD script block containing these FAQs to improve search visibility.
3. Final Recommendation: A decisive final recommendation for home office workers, with a supportive, human closing.
Target Length: 500-600 words.
"""
    r5 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "assistant", "content": section_1 + "\n" + section_2 + "\n" + section_3 + "\n" + section_4},
            {"role": "user", "content": prompt_5}
        ],
        temperature=0.7
    )
    section_5 = r5.choices[0].message.content.strip()

    # Assemble HTML content
    html_content = f"""<div class="blog-container">
{section_1}
{section_2}
{section_3}
{section_4}
{section_5}
</div>"""

    # Clean up markdown code fences if generated
    html_content = html_content.replace("```html", "").replace("```", "").strip()
    
    # 3. Inject Internal Links
    logger.info("Injecting contextual internal links...")
    seo_labels = ["Remote Work", "Home Office", "Ergonomics", "Productivity", "Workspace Setup"]
    related_posts = link_manager.get_related_articles(seo_title, seo_labels, count=3)
    if related_posts:
        html_content = link_manager.inject_internal_links(html_content, related_posts)
        html_content = link_manager.add_related_section(html_content, related_posts)
        
    # 4. Clean H1 tags
    logger.info("Cleaning H1 tags from content...")
    cleaned_content, _ = h1_remover.clean_post_h1(seo_title.strip(), html_content)
    
    # 5. Publish to Blogger
    logger.info("Publishing to Blogger...")
    published_url, post_id = publisher.publish_post(seo_title, cleaned_content, labels=seo_labels)
    
    word_count = len(BeautifulSoup(cleaned_content, "html.parser").get_text().split())
    
    # Output report
    logger.info("Publishing completed successfully!")
    print("{\n  \"post_url\": \"" + published_url + "\",\n  \"article_title\": \"" + seo_title + "\",\n  \"word_count\": " + str(word_count) + ",\n  \"internal_links_added\": " + str(bool(related_posts)).lower() + ",\n  \"affiliate_links_included\": false\n}")

if __name__ == "__main__":
    main()
