from openai import OpenAI
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from templates.prompts import SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE, COMPARISON_TEMPLATE, FAQ_TEMPLATE, SEO_TAGS_TEMPLATE
from utils.text_cleaner import sanitize_html

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
        import re
        safe_tags = []
        total_length = 0
        for tag in tags:
            # Only allow alphanumeric, spaces, and hyphens
            safe_tag = re.sub(r'[^a-zA-Z0-9\s\-]', '', tag).strip()
            if safe_tag and safe_tag not in safe_tags:
                if total_length + len(safe_tag) + 1 < 180: # Keep a safe buffer
                    safe_tags.append(safe_tag)
                    total_length += len(safe_tag) + 1
                
        return safe_tags
        
    def generate_full_post(self, topic, keyword, products):
        """Assemble the complete blog post."""
        logger.info("Starting full post generation")
        
        # 1. Intro
        intro_prompt = INTRO_TEMPLATE.format(topic=topic, keyword=keyword)
        intro_html = self.generate_section(intro_prompt, model="gpt-4o-mini")
        
        # 2. Reviews
        reviews_html = ""
        for p in products:
            r_prompt = REVIEW_TEMPLATE.format(
                title=p['title'], price=p['price'], 
                rating=p['rating'], review_count=p['review_count'], 
                features=p['features']
            )
            # Add a heading for the product
            reviews_html += f"\n<h2>{p['title']}</h2>\n"
            reviews_html += self.generate_section(r_prompt, model="gpt-4o")
            
            # Inject Affiliate Link
            affiliate_link = p.get('url', '#')
            button_style = "display: inline-block; background-color: #ff9900; color: #fff; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 18px;"
            reviews_html += f"\n<p style='text-align:center;'><a href='{affiliate_link}' target='_blank' rel='nofollow sponsored' style='{button_style}'>Check Current Price on Amazon</a></p>\n"
            
        # 3. Comparison Table
        products_summary = "\n".join([f"- {p['title']} | {p['price']} | {p['rating']} | URL: {p.get('url', '#')}" for p in products])
        comparison_prompt = COMPARISON_TEMPLATE + f"\n\nHere are the products:\n{products_summary}"
        comparison_html = self.generate_section(comparison_prompt, model="gpt-4o")
        
        # 4. FAQ Section
        faq_prompt = FAQ_TEMPLATE.format(topic=topic)
        faq_html = self.generate_section(faq_prompt, model="gpt-4o-mini")
        
        # 5. Footer
        footer_html = "\n<p style='font-size: 0.9em; color: #666; border-top: 1px solid #ccc; padding-top: 10px;'><em>This article may contain affiliate links. We may earn a commission at no extra cost to you.</em></p>\n"
        
        full_html = f"<h1>{topic}</h1>\n{intro_html}\n{comparison_html}\n{reviews_html}\n{faq_html}\n{footer_html}"
        return full_html
