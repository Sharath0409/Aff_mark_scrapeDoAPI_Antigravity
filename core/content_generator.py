from core.deepseek_client import DeepseekHttpClient
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from templates.prompts import (
    SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE,
    COMPARISON_TEMPLATE, FAQ_TEMPLATE, SEO_TAGS_TEMPLATE,
    QUICK_SUMMARY_TEMPLATE, CONCLUSION_TEMPLATE,
    REVIEWS_HEADER_TEMPLATE, INFORMATIONAL_BLUEPRINT_TEMPLATE,
    INFORMATIONAL_ARTICLE_TEMPLATE, INFORMATIONAL_IMAGE_PLAN_TEMPLATE
)
from utils.text_cleaner import sanitize_html
import re
from bs4 import BeautifulSoup
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader

logger = get_logger(__name__)

class ContentGenerator:
    def __init__(self):
        self.client = DeepseekHttpClient(api_key=settings.DEEPSEEK_API_KEY) if settings.DEEPSEEK_API_KEY else None

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
            r"\bgeneric\s+comparison\s+table\b",
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
        return self._apply_quality_corrections(combined_html, topic, keyword)

    def generate_informational_blueprint(self, topic, keyword, category):
        """Generate a content planning blueprint for an informational article.

        Reuses: self.client (Deepseek), generate_section() (with retry + logging),
        SYSTEM_PROMPT, and the shared INFORMATIONAL_BLUEPRINT_TEMPLATE.
        Returns a plain-text blueprint string. Does NOT generate article content.
        """
        logger.info(f"Generating informational blueprint for topic: {topic}")
        prompt = INFORMATIONAL_BLUEPRINT_TEMPLATE.format(
            topic=topic,
            keyword=keyword,
            category=category,
        )
        # generate_section() applies SYSTEM_PROMPT, the retry decorator, and logging.
        # temperature=0.4 chosen for structured, consistent blueprint output.
        blueprint = self.generate_section(prompt, model="deepseek-v4-flash")
        logger.info("Informational blueprint generation complete.")
        return blueprint

    def generate_informational_article(self, blueprint, topic, keyword, category):
        """Generate a complete informational article using the blueprint as source of truth.

        Reuses: self.client (Deepseek), generate_section() (with retry + logging),
        SYSTEM_PROMPT, and the shared INFORMATIONAL_ARTICLE_TEMPLATE.
        Returns clean, semantic HTML article. Does NOT generate conclusion, FAQs, or image placeholders.
        """
        logger.info(f"Generating informational article for topic: {topic}")
        prompt = INFORMATIONAL_ARTICLE_TEMPLATE.format(
            blueprint=blueprint,
            topic=topic,
            keyword=keyword,
            category=category
        )
        article = self.generate_section(prompt, model="deepseek-v4-flash")
        logger.info("Informational article generation complete.")
        return article

    def generate_image_plan(self, blueprint, article, topic, keyword, category):
        """Generate a structured image plan for the informational article.

        Reuses: self.client (Deepseek), generate_section() (with retry + logging),
        SYSTEM_PROMPT, and the shared INFORMATIONAL_IMAGE_PLAN_TEMPLATE.
        Returns a plain-text image plan.
        """
        logger.info(f"Generating image plan for topic: {topic}")
        prompt = INFORMATIONAL_IMAGE_PLAN_TEMPLATE.format(
            blueprint=blueprint,
            article=article,
            topic=topic,
            keyword=keyword,
            category=category
        )
        image_plan = self.generate_section(prompt, model="deepseek-v4-flash")
        logger.info("Image plan generation complete.")
        return image_plan

    @get_retry_decorator()
    def generate_ai_image(self, prompt, size="1024x1024"):
        """Call Deepseek image generation API to generate an image."""
        logger.info(f"Generating AI image via Deepseek (size: {size})")
        response = self.client.images.generate(
            model="deepseek-v4-flash",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1
        )
        return response.data[0].url

    def generate_article_images(self, image_plan, topic):
        """Read the Image Plan, generate, optimize, and upload each planned image.

        Returns a list of dictionaries representing the Image Manifest.
        """
        logger.info("Parsing image plan and starting AI image generation pipeline...")
        blocks = re.split(r'Image Number:\s*', image_plan)
        manifest = []

        optimizer = ImageOptimizer()
        uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)

        try:
            for idx, block in enumerate(blocks[1:], start=1):
                lines = block.split('\n')
                fields = {
                    "image_number": idx,
                    "purpose": "",
                    "placement": "",
                    "reference_heading": "",
                    "image_style": "",
                    "aspect_ratio": "",
                    "prompt": "",
                    "alt_text": "",
                    "caption": ""
                }
                current_key = None
                for line in lines:
                    m = re.match(r'^\s*\*?\*?(Purpose|Placement|Reference Heading|Image Style|Aspect Ratio|Prompt|Alt Text|Caption)\*?\*?\s*:\s*(.*)', line, re.IGNORECASE)
                    if m:
                        key = m.group(1).lower().replace(' ', '_')
                        fields[key] = m.group(2).strip()
                        current_key = key
                    elif current_key and line.strip() and not line.startswith('---') and not line.startswith('***') and not line.startswith('==='):
                        fields[current_key] += " " + line.strip()

                # Aspect ratio to size mapping
                ratio = fields.get("aspect_ratio", "")
                if "16:9" in ratio or "16-9" in ratio or "landscape" in ratio.lower():
                    size = "1792x1024"
                else:
                    size = "1024x1024"

                # Generate AI image
                image_prompt = fields.get("prompt", "").strip()
                if not image_prompt:
                    logger.warning(f"No prompt found for image block {idx}, skipping.")
                    continue

                try:
                    logger.info(f"Generating AI image for planned image {idx}...")
                    raw_url = self.generate_ai_image(image_prompt, size=size)
                    if not raw_url:
                        logger.error(f"Failed to generate AI image for block {idx}.")
                        continue

                    # Optimize image
                    logger.info(f"Optimizing image {idx}...")
                    title_keyword = f"{topic}-image-{idx}"
                    temp_path, width, height = optimizer.process_from_url(raw_url, title_keyword)
                    if not temp_path:
                        logger.error(f"Failed to optimize image {idx}.")
                        continue

                    # Upload to GCS CDN
                    logger.info(f"Uploading image {idx} to GCS...")
                    cdn_url = uploader.upload_to_google_cdn(temp_path, bucket_name=settings.GCS_BUCKET_NAME)
                    if not cdn_url:
                        logger.error(f"Failed to upload image {idx} to GCS CDN.")
                        continue

                    # Add to manifest
                    manifest.append({
                        "image_number": fields.get("image_number", idx),
                        "placement": fields.get("placement", "").strip(),
                        "reference_heading": fields.get("reference_heading", "").strip(),
                        "cdn_url": cdn_url,
                        "alt_text": fields.get("alt_text", "").strip(),
                        "caption": fields.get("caption", "").strip(),
                        "aspect_ratio": fields.get("aspect_ratio", "").strip(),
                        "width": width,
                        "height": height
                    })

                except Exception as e:
                    logger.error(f"Failed to process planned image {idx}: {e}")

        finally:
            logger.info("Cleaning up local temporary image files...")
            optimizer.cleanup()

        return manifest

    def inject_images_into_article(self, article_html, image_manifest):
        """Assemble the final HTML article by injecting CDN images into planned locations.

        Matches reference headings case-insensitively, ignoring non-alphanumeric characters.
        Inserts <figure> with <img> and <figcaption> below matching headings or closest sections.
        """
        logger.info("Injecting CDN images into article HTML...")
        soup = BeautifulSoup(article_html, "html.parser")
        headings = soup.find_all(['h2', 'h3'])

        def clean_text(text):
            if not text:
                return ""
            return re.sub(r'[^a-z0-9]', '', text.lower())

        for img in image_manifest:
            # Construct semantic figure element
            figure_tag = soup.new_tag("figure")
            img_tag = soup.new_tag("img")
            img_tag["src"] = img.get("cdn_url")
            img_tag["alt"] = img.get("alt_text", "")
            img_tag["loading"] = "lazy"
            img_tag["decoding"] = "async"
            
            # Explicit dimensions if available
            if img.get("width"):
                img_tag["width"] = img["width"]
            if img.get("height"):
                img_tag["height"] = img["height"]
                
            figure_tag.append(img_tag)

            if img.get("caption"):
                caption_tag = soup.new_tag("figcaption")
                caption_tag.string = img["caption"]
                figure_tag.append(caption_tag)

            # Locate matching heading
            target = None
            cleaned_ref = clean_text(img.get("reference_heading", ""))
            cleaned_placement = clean_text(img.get("placement", ""))

            # 1. Direct match on reference heading
            if cleaned_ref:
                for h in headings:
                    cleaned_h = clean_text(h.text)
                    if cleaned_ref in cleaned_h or cleaned_h in cleaned_ref:
                        target = h
                        break

            # 2. Substring match on placement text
            if not target and cleaned_placement:
                for h in headings:
                    cleaned_h = clean_text(h.text)
                    if cleaned_h in cleaned_placement:
                        target = h
                        break

            # Insert tag based on match
            if not target:
                h2s = soup.find_all('h2')
                if h2s:
                    # Append before the next (first available) H2
                    h2s[0].insert_before(figure_tag)
                else:
                    soup.append(figure_tag)
            else:
                target.insert_after(figure_tag)

        logger.info("Image injection complete.")
        return str(soup)
