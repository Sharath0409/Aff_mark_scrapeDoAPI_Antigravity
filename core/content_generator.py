from core.deepseek_client import DeepseekHttpClient
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from templates.prompts import (
    SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE,
    COMPARISON_TEMPLATE, FAQ_TEMPLATE, SEO_TAGS_TEMPLATE,
    QUICK_SUMMARY_TEMPLATE, CONCLUSION_TEMPLATE,
    REVIEWS_HEADER_TEMPLATE, INFORMATIONAL_BLUEPRINT_TEMPLATE,
    INFORMATIONAL_ARTICLE_TEMPLATE, INFORMATIONAL_IMAGE_PLAN_TEMPLATE,
    LONG_TAIL_HEADING_VARIANTS_PROMPT
)
from utils.text_cleaner import sanitize_html
import re
import json
from bs4 import BeautifulSoup
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader
from core.author_signals import generate_author_signals, DEFAULT_AUTHOR, DEFAULT_METHODOLOGY
from core.detemplater import detemplate_article, SectionVariator
from core.schema_generator import SchemaGenerator, generate_product_schemas
from core.cannibalization_checker import CannibalizationChecker

logger = get_logger(__name__)

class ContentGenerator:
    def __init__(self):
        self.client = DeepseekHttpClient(api_key=settings.DEEPSEEK_API_KEY) if settings.DEEPSEEK_API_KEY else None
        self.schema_generator = SchemaGenerator()
        self.section_variator = SectionVariator()
        self.cannibalization_checker = CannibalizationChecker()

    def _apply_quality_corrections(self, html, topic, keyword):
        """Clean generated HTML so it stays topic-focused, US-focused, and EEAT-safe."""
        if not html:
            return html

        soup = BeautifulSoup(html, "html.parser")
        topic_text = f"{topic} {keyword}".strip()
        topic_lower = topic_text.lower()

        placeholder_patterns = [
            r"\bxyz\s+product\b",
            r"\babc\s+chair\b",
            r"\bsample\s+product\b",
            r"\blorem\s+ipsum\b",
            r"\bexample\s+product\b",
            r"\bdummy\s+specifications\b",
            r"\bgeneric\s+premium\s+choice\b",
            r"\btravel\s+chair\b",
        ]
        ai_phrase_replacements = [
            (r"\bi\s+tested\s+this\b", "Based on manufacturer specifications, verified customer feedback, and industry best practices"),
            (r"\bi've\s+used\s+this\b", "Based on manufacturer specifications, verified customer feedback, and industry best practices"),
            (r"\bmy\s+experience\b", "Verified customer feedback"),
            (r"\bmy\s+week\s+of\s+testing\b", "verified customer feedback and industry best practices"),
            (r"\bi\s+personally\s+recommend\b", "This guide recommends"),
            (r"\bin\s+my\s+week\s+of\s+testing\b", "based on verified customer feedback and industry best practices"),
        ]
        unrelated_patterns = [
            r"\bwebcam\s+comparison\b",
            r"\bchair\s+recommendation\b",
            r"\bkeyboard\s+buying\s+guide\b",
            r"\bstanding\s+desk\s+advice\b",
            r"\bmouse\s+recommendation\b",
            r"\bnas\s+recommendation\b",
        ]

        human_phrases = [
            (r"\bin\s+today's\s+fast-paced\s+world\b", "For many US remote workers"),
            (r"\bwhen\s+it\s+comes\s+to\b", "with"),
            (r"\bit\s+is\s+important\s+to\s+note\b", "remember"),
            (r"\bthis\s+guide\s+will\s+show\s+you\b", "this article explains"),
            (r"\bone\s+of\s+the\s+best\s+options\b", "a strong choice"),
            (r"\busers\s+can\b", "you can"),
            (r"\bfor\s+remote\s+workers\b", "for US remote workers"),
            (r"\bin\s+the\s+us\b", "for the US"),
            (r"\bamerican\s+office\b", "US home office"),
        ]

        for text_node in soup.find_all(string=True):
            if text_node.parent and text_node.parent.name in {"script", "style"}:
                continue

            original = str(text_node)
            updated = original
            for pattern in placeholder_patterns:
                updated = re.sub(pattern, "the featured option", updated, flags=re.IGNORECASE)
            for pattern, replacement in ai_phrase_replacements + human_phrases:
                updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
            if re.search(r"\b(xyz|abc|sample|lorem|example|dummy|generic)\b", updated, flags=re.IGNORECASE):
                updated = re.sub(r"\b(xyz|abc|sample|lorem|example|dummy|generic)\b", "the featured option", updated, flags=re.IGNORECASE)
            if any(re.search(pattern, updated, flags=re.IGNORECASE) for pattern in unrelated_patterns):
                updated = ""

            if updated != original:
                text_node.replace_with(updated)

        def is_empty_removable_tag(tag):
            if tag.name in {"img", "br", "hr", "input", "meta", "link", "source", "track", "wbr", "area"}:
                return False
            if tag.get_text(" ", strip=True):
                return False
            if tag.find(["img", "iframe", "video", "audio", "picture", "svg"]):
                return False
            return True

        for tag in soup.find_all(True):
            if is_empty_removable_tag(tag):
                tag.decompose()

        if not soup.find(["h1", "h2", "p"]):
            wrapper = soup.new_tag("p")
            wrapper.string = f"This guide focuses on {topic} and helps US readers make an informed, practical decision."
            soup.append(wrapper)

        intro_target = soup.find(["h1", "h2", "p"])
        if intro_target and topic_lower and topic_lower not in intro_target.get_text(" ", strip=True).lower():
            if not intro_target.find("strong"):
                topic_sentence = soup.new_tag("p")
                topic_sentence.string = f"This article is focused on {topic} and is written for US readers looking for practical, topic-specific guidance."
                intro_target.insert_after(topic_sentence)

        text_content = " ".join([tag.get_text(" ", strip=True) for tag in soup.find_all(["p", "li", "h2", "h3"])])
        if "united states" not in text_content.lower() and "us " not in text_content.lower() and "u.s." not in text_content.lower():
            us_note = soup.new_tag("p")
            us_note.string = "This article is tailored for US buyers and home office setups, with practical advice for American remote work and workplace environments."
            if intro_target is not None:
                intro_target.insert_after(us_note)
            else:
                soup.insert(0, us_note)

        if "verified product specifications" not in text_content.lower() and "customer feedback" not in text_content.lower():
            eeat_note = soup.new_tag("p")
            eeat_note.string = "The review is based on verified product specifications, customer feedback, and workplace best practices to provide trustworthy guidance."
            if intro_target is not None:
                intro_target.insert_after(eeat_note)
            else:
                soup.insert(0, eeat_note)

        if any(term in topic_lower for term in ["ergonomic", "chair", "desk", "standing desk", "keyboard", "mouse", "monitor", "lighting", "workstation", "workspace", "office furniture"]):
            if "osha" not in text_content.lower() and "neutral wrist" not in text_content.lower():
                anchor = soup.find("p") or soup.find("h2") or soup.find("h3")
                if anchor is not None:
                    safety_note = soup.new_tag("p")
                    safety_note.string = "For US work setups, OSHA-aligned ergonomic guidance favors neutral wrist positioning, a monitor at roughly eye level, and a setup that reduces repetitive strain while supporting balanced sitting and standing habits."
                    anchor.insert_after(safety_note)

        return str(soup).strip()
        
    @get_retry_decorator()
    def generate_section(self, prompt, model="deepseek-v4-flash"):
        """Call Deepseek API to generate content."""
        logger.info(f"Generating content with model {model}")
        if not self.client:
            return "<p>Content generation skipped because no Deepseek API key is configured.</p>"
        if model in {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4o-mini"}:
            model = "deepseek-v4-flash"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            
            # Deepseek sometimes wraps HTML in markdown blocks, let's clean it
            if content.startswith("```html"):
                content = content.replace("```html", "").replace("```", "")
            
            return sanitize_html(content)
        except Exception as e:
            logger.error(f"Error calling Deepseek API: {e}")
            raise
            
    def generate_seo_tags(self, topic, keyword):
        """Generate SEO labels for Blogger."""
        logger.info("Generating SEO optimized labels...")
        prompt = SEO_TAGS_TEMPLATE.format(topic=topic, keyword=keyword)
        result = self.generate_section(prompt, model="deepseek-v4-flash")
        # Strip HTML tags just in case
        result = result.replace('<p>', '').replace('</p>', '').replace('\n', '').strip()
        tags = [tag.strip() for tag in result.replace('"', '').split(',') if tag.strip()]
        
        # Sanitize tags and enforce Blogger's strict 200 character limit for ALL labels combined
        safe_tags = []
        total_length = 0
        for tag in tags:
            # Only allow alphanumeric, spaces, and hyphens
            safe_tag = re.sub(r'[^a-zA-Z0-9\s\-]', '', tag).strip()
            # Safety fallback: Strip any 4-digit years (e.g. 2023, 2024)
            safe_tag = re.sub(r'\b\d{4}\b', '', safe_tag).strip()
            
            if safe_tag and safe_tag not in safe_tags:
                if total_length + len(safe_tag) + 1 < 180: # Keep a safe buffer
                    safe_tags.append(safe_tag)
                    total_length += len(safe_tag) + 1
                
        return safe_tags
        
    def generate_full_post(self, topic, keyword, products):
        """Assemble the complete blog post with visual styling and all requested sections."""
        logger.info("Starting full post generation")
        
        # 0. CSS Styles for a modern, fluid editorial layout
        style_block = """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
            .blog-container { max-width: 850px; margin: 0 auto; padding: 10px; color: #333; line-height: 1.8; font-family: 'Inter', -apple-system, sans-serif; text-align: justify; hyphens: auto; }
            .section-divider { margin: 60px 0; border: none; border-top: 1px solid #eee; }
            .product-section { margin-bottom: 60px; padding-bottom: 40px; border-bottom: 1px solid #eee; }
            .product-section:last-of-type { border-bottom: none; }
            .product-title { color: #111; font-size: 2em; font-weight: 800; margin-bottom: 20px; line-height: 1.2; text-align: center; }
            h1, h2 { text-align: center; margin-top: 50px; }
            .product-image-centered { text-align: center; margin-bottom: 30px; }
            .product-image-centered img { max-width: 100%; height: auto; width: auto; border-radius: 8px; max-height: 400px; object-fit: contain; }
            .product-summary-full { margin-bottom: 30px; }
            .price-badge { display: inline-block; background: #fef3c7; color: #451a03; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 15px; }
            .verdict-box { background: #f9fafb; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; font-style: italic; }
            .pros-cons-grid { display: block; margin: 25px 0; }
            .pros-list { margin-bottom: 20px; }
            .pros-list h4 { color: #059669; margin-top: 0; }
            .cons-list h4 { color: #dc2626; margin-top: 0; }
            .buy-button-wrapper { text-align: center; margin-top: 40px; }
            .buy-btn { display: inline-block; background: #fbbf24; color: #000 !important; padding: 16px 40px; border-radius: 4px; text-decoration: none !important; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; border: 1px solid #d97706; transition: all 0.2s; }
            .comparison-table-wrapper { overflow-x: auto; margin: 40px 0; border: 1px solid #eee; border-radius: 8px; }
            .comparison-table { width: 100%; border-collapse: collapse; min-width: 600px; }
            .comparison-table td, .comparison-table th { padding: 15px; border: 1px solid #eee; font-size: 0.95em; }
            .comparison-table th { background: #f8fafc; color: #475569; font-weight: 700; text-align: left; }
            .quick-summary-box { background: #fffbeb; border: 1px solid #fef3c7; padding: 25px; border-radius: 12px; margin: 40px 0; }
            @media (max-width: 640px) { .pros-cons-grid { grid-template-columns: 1fr; } .product-title { font-size: 1.6em; } }
        </style>
        """
        
        # Helper for generating context blocks to maintain consistency
        products_summary = "\n".join([f"- {p['title']} | {p['price']} | {p['rating']} | URL: {p.get('url', '#')}" for p in products])
        
        def build_context(intro="", qs="", comp=""):
            ctx = f"Current Article Context\nArticle Topic: {topic}\nPrimary Keyword: {keyword}\nProducts Reviewed:\n{products_summary}\n\nPreviously Generated Sections:\n"
            if intro: ctx += f"Summary of Introduction:\n{intro}\n\n"
            if qs: ctx += f"Summary of Bottom Line:\n{qs}\n\n"
            if comp: ctx += f"Summary of Comparison:\n{comp}\n\n"
            if not intro and not qs and not comp: ctx += "(None yet)\n\n"
            ctx += "This context is read-only. The LLM must use it only to maintain consistency, avoid duplicating information, and ensure no hallucinated products or contradictory advice are added.\n\n=========================\n"
            return ctx
        
        # 1. Intro
        intro_prompt = build_context() + INTRO_TEMPLATE.format(topic=topic, keyword=keyword)
        intro_html = self.generate_section(intro_prompt, model="gpt-4o-mini")
        
        # 2. Quick Summary (New)
        qs_prompt = build_context(intro=intro_html) + QUICK_SUMMARY_TEMPLATE.format(topic=topic)
        qs_raw = self.generate_section(qs_prompt, model="gpt-4o-mini")
        qs_html = f'<div class="quick-summary-box">{qs_raw}</div>'
        
        # 3. Comparison Table (Moved Up)
        comparison_prompt = build_context(intro=intro_html, qs=qs_raw) + COMPARISON_TEMPLATE + f"\n\nHere are the products:\n{products_summary}"
        comparison_raw = self.generate_section(comparison_prompt, model="gpt-4o")
        comparison_html = f'<div class="comparison-table-wrapper">{comparison_raw}</div>'
        
        # 4. Detailed Reviews
        rh_prompt = build_context(intro=intro_html, qs=qs_raw, comp=comparison_raw) + REVIEWS_HEADER_TEMPLATE
        reviews_header = self.generate_section(rh_prompt, model="gpt-4o-mini")
        reviews_html = f"<h2>{reviews_header}</h2>"
        for p in products:
            r_prompt = build_context(qs=qs_raw) + REVIEW_TEMPLATE.format(
                title=p['title'], price=p['price'], 
                rating=p['rating'], review_count=p['review_count'], 
                features=p['features']
            )
            
            review_content = self.generate_section(r_prompt, model="deepseek-v4-flash")
            
            # Build optimized image tag with explicit dimensions
            image_html = ""
            if p.get('image_url'):
                width_attr = f' width="{p.get("image_width")}"' if p.get("image_width") else ''
                height_attr = f' height="{p.get("image_height")}"' if p.get("image_height") else ''
                image_html = f'<div class="product-image-centered"><img src="{p["image_url"]}" alt="{p["title"]}"{width_attr}{height_attr} loading="lazy"></div>'
            
            reviews_html += f"""
            <section class="product-section">
                <h3 class="product-title">{p['title']}</h3>
                {image_html}
                <div class="product-summary-full">
                    <div class="price-badge">Price: {p['price']}</div>
                    {review_content}
                </div>
                <div class="buy-button-wrapper">
                    <a href="{p['url']}" target="_blank" rel="nofollow sponsored" class="buy-btn">View Latest Price on Amazon</a>
                </div>
            </section>
            """
            
        # 5. FAQ Section
        faq_prompt = build_context(qs=qs_raw, comp=comparison_raw) + FAQ_TEMPLATE.format(topic=topic)
        faq_html = self.generate_section(faq_prompt, model='gpt-4o-mini')
        
        # 6. Conclusion
        conc_prompt = build_context(qs=qs_raw) + CONCLUSION_TEMPLATE.format(topic=topic)
        conc_html = self.generate_section(conc_prompt, model='gpt-4o-mini')
        
        # 7. Footer
        footer_html = "\n<footer style='font-size: 0.9em; color: #666; border-top: 1px solid #eee; padding-top: 30px; margin-top: 60px;'><em>Disclaimer: This article contains affiliate links. If you click a link and make a purchase, we may earn a small commission at no extra cost to you.</em></footer>\n"
        
        # Assemble parts in requested order
        parts = [
            '<div class="blog-container">',
            style_block,
            intro_html,
            qs_html,
            reviews_html,
            comparison_html,
            faq_html,
            conc_html,
            footer_html,
            '</div>'
        ]

        combined_html = "\n".join(parts)
        
        # Apply de-templating to vary prose across product sections
        combined_html = detemplate_article(combined_html)
        
        # Generate author byline and research methodology
        author_signals = generate_author_signals(
            author=DEFAULT_AUTHOR,
            methodology=DEFAULT_METHODOLOGY,
            include_top_byline=True,
            include_bottom_byline=False,
            include_methodology=True
        )
        
        # Insert author byline after intro
        soup = BeautifulSoup(combined_html, 'html.parser')
        intro_section = soup.find('div', class_='blog-container')
        if intro_section:
            # Find the intro content (first few paragraphs after style)
            first_h2 = soup.find('h2')
            if first_h2:
                # Insert top byline before first H2
                byline_soup = BeautifulSoup(author_signals['top_byline'], 'html.parser')
                first_h2.insert_before(byline_soup)
        
        # Insert methodology section before FAQ
        faq_section = soup.find('h2', string=re.compile(r'Frequently Asked Questions', re.I))
        if faq_section and author_signals['methodology']:
            methodology_soup = BeautifulSoup(author_signals['methodology'], 'html.parser')
            faq_section.insert_before(methodology_soup)
        
        # Generate Product/Review schema JSON-LD
        schema_html = self.schema_generator.generate_inline_json_ld(products, topic, keyword)
        
        # Generate long-tail heading variants
        products_summary = "\n".join([f"- {p['title']} ({p['price']})" for p in products])
        long_tail_prompt = LONG_TAIL_HEADING_VARIANTS_PROMPT.format(
            topic=topic,
            keyword=keyword,
            products_summary=products_summary
        )
        try:
            long_tail_response = self.generate_section(long_tail_prompt, model="deepseek-v4-flash")
            long_tail_data = json.loads(long_tail_response)
            
            # Insert long-tail headings into appropriate sections
            for variant in long_tail_data:
                heading_html = f'<h2>{variant["heading"]}</h2>'
                # Find suggested placement
                placement = variant.get("suggested_placement", "").lower()
                if "quick summary" in placement or "bottom line" in placement:
                    qs_div = soup.find('div', class_='quick-summary-box')
                    if qs_div:
                        qs_div.insert_after(BeautifulSoup(heading_html, 'html.parser'))
                elif "how we evaluated" in placement:
                    eval_h2 = soup.find('h2', string=re.compile(r'How We Evaluated', re.I))
                    if eval_h2:
                        eval_h2.insert_after(BeautifulSoup(heading_html, 'html.parser'))
                elif "product review" in placement:
                    first_product = soup.find('section', class_='product-section')
                    if first_product:
                        first_product.insert_before(BeautifulSoup(heading_html, 'html.parser'))
        except Exception as e:
            logger.warning(f"Failed to generate/insert long-tail headings: {e}")
        
        # Add schema at the end
        final_html = str(soup) + "\n" + schema_html
        
        return self._apply_quality_corrections(final_html, topic, keyword)
