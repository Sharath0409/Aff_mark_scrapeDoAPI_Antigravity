from openai import OpenAI
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from templates.prompts import (
    SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE, 
    COMPARISON_TEMPLATE, FAQ_TEMPLATE, SEO_TAGS_TEMPLATE,
    QUICK_SUMMARY_TEMPLATE, CONCLUSION_TEMPLATE, RELATED_ARTICLES_TEMPLATE,
    REVIEWS_HEADER_TEMPLATE
)
from utils.text_cleaner import sanitize_html
import re

logger = get_logger(__name__)

class ContentGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
    @get_retry_decorator()
    def generate_section(self, prompt, model="gpt-4o"):
        """Call OpenAI API to generate content."""
        logger.info(f"Generating content with model {model}")
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
            
            # OpenAI sometimes wraps HTML in markdown blocks, let's clean it
            if content.startswith("```html"):
                content = content.replace("```html", "").replace("```", "")
            
            return sanitize_html(content)
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
            
    def generate_seo_tags(self, topic, keyword):
        """Generate SEO labels for Blogger."""
        logger.info("Generating SEO optimized labels...")
        prompt = SEO_TAGS_TEMPLATE.format(topic=topic, keyword=keyword)
        result = self.generate_section(prompt, model="gpt-4o-mini")
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
            .product-image-centered img { max-width: 100%; height: auto; border-radius: 8px; max-height: 400px; }
            .product-summary-full { margin-bottom: 30px; }
            .price-badge { display: inline-block; background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 15px; }
            .verdict-box { background: #f9fafb; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; font-style: italic; }
            .pros-cons-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 25px 0; }
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
        
        # 1. Intro
        intro_prompt = INTRO_TEMPLATE.format(topic=topic, keyword=keyword)
        intro_html = self.generate_section(intro_prompt, model="gpt-4o-mini")
        
        # 2. Quick Summary (New)
        qs_prompt = QUICK_SUMMARY_TEMPLATE.format(topic=topic)
        qs_html = f'<div class="quick-summary-box">{self.generate_section(qs_prompt, model="gpt-4o-mini")}</div>'
        
        # 3. Comparison Table (Moved Up)
        products_summary = "\n".join([f"- {p['title']} | {p['price']} | {p['rating']} | URL: {p.get('url', '#')}" for p in products])
        comparison_prompt = COMPARISON_TEMPLATE + f"\n\nHere are the products:\n{products_summary}"
        comparison_html = f'<div class="comparison-table-wrapper">{self.generate_section(comparison_prompt, model="gpt-4o")}</div>'
        
        # 4. Detailed Reviews
        rh_prompt = REVIEWS_HEADER_TEMPLATE.format(topic=topic)
        reviews_header = self.generate_section(rh_prompt, model="gpt-4o-mini")
        reviews_html = f"<h2>{reviews_header}</h2>"
        for p in products:
            r_prompt = REVIEW_TEMPLATE.format(
                title=p['title'], price=p['price'], 
                rating=p['rating'], review_count=p['review_count'], 
                features=p['features']
            )
            
            review_content = self.generate_section(r_prompt, model="gpt-4o")
            image_html = f'<div class="product-image-centered"><img src="{p["image_url"]}" alt="{p["title"]}"></div>' if p.get('image_url') else ''
            
            reviews_html += f"""
            <section class="product-section">
                <h3 class="product-title">{p['title']}</h3>
                <div class="product-image-centered">
                    {image_html}
                </div>
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
        faq_prompt = FAQ_TEMPLATE.format(topic=topic)
        faq_html = self.generate_section(faq_prompt, model='gpt-4o-mini')
        
        # 6. Conclusion (New)
        conc_prompt = CONCLUSION_TEMPLATE.format(topic=topic)
        conc_html = self.generate_section(conc_prompt, model='gpt-4o-mini')
        
        # 7. Related Articles (New)
        rel_prompt = RELATED_ARTICLES_TEMPLATE.format(topic=topic, keyword=keyword)
        rel_html = self.generate_section(rel_prompt, model='gpt-4o-mini')
        
        # 8. Footer
        footer_html = "\n<footer style='font-size: 0.9em; color: #666; border-top: 1px solid #eee; padding-top: 30px; margin-top: 60px;'><em>Disclaimer: This article contains affiliate links. If you click a link and make a purchase, we may earn a small commission at no extra cost to you.</em></footer>\n"
        
        # Assemble parts in requested order
        parts = [
            '<div class="blog-container">',
            f'<h1 style="font-size: 2.5em; text-align: center; margin-bottom: 40px;">{topic}</h1>',
            style_block,
            intro_html,
            qs_html,
            comparison_html,
            reviews_html,
            faq_html,
            conc_html,
            rel_html,
            footer_html,
            '</div>'
        ]
        
        return "\n".join(parts)
