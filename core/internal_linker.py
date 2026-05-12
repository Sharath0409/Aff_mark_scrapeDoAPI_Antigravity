import json
import logging
import re
from typing import List, Dict
from openai import OpenAI
from config import settings
from templates.prompts import INTERNAL_LINK_RELEVANCE_PROMPT, CONTEXTUAL_LINK_INJECTION_PROMPT

logger = logging.getLogger(__name__)

class InternalLinkManager:
    def __init__(self, publisher):
        self.publisher = publisher
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.corpus = [] # Cache of existing posts

    def refresh_corpus(self):
        """Fetch all posts from Blogger and store metadata."""
        try:
            logger.info("Refreshing existing posts corpus for internal linking...")
            posts = self.publisher.list_all_posts(max_results=500)
            self.corpus = [
                {
                    "title": p['title'],
                    "url": p['url'],
                    "labels": p.get('labels', []),
                    "id": p['id']
                }
                for p in posts
            ]
            logger.info(f"Indexed {len(self.corpus)} posts for internal linking.")
        except Exception as e:
            logger.error(f"Failed to refresh corpus: {e}")

    def get_related_articles(self, topic: str, labels: List[str], count: int = 3) -> List[Dict]:
        """Use AI to find the most relevant articles from the corpus."""
        if not self.corpus:
            logger.warning("No corpus available for internal link matching.")
            return []

        # Prepare corpus text for AI (Limit to titles and labels for token efficiency)
        corpus_summary = "\n".join([f"{i}. {p['title']} (Labels: {', '.join(p['labels'])})" for i, p in enumerate(self.corpus)])
        
        prompt = INTERNAL_LINK_RELEVANCE_PROMPT.format(
            topic=topic,
            labels=", ".join(labels),
            corpus=corpus_summary,
            count=count
        )

        try:
            logger.info("Asking AI to select most relevant internal links...")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.choices[0].message.content
            
            # Extract indices from AI response
            indices = [int(i) for i in re.findall(r'\d+', content)]
            
            selected = []
            seen_urls = set()
            for idx in indices:
                if 0 <= idx < len(self.corpus):
                    item = self.corpus[idx]
                    if item['url'] not in seen_urls:
                        selected.append(item)
                        seen_urls.add(item['url'])
            
            return selected[:count]
        except Exception as e:
            logger.error(f"Error finding related articles: {e}")
            return []

    def inject_internal_links(self, html_content: str, related_articles: List[Dict]) -> str:
        """Inject links into the HTML content using AI for contextual matching."""
        if not related_articles:
            return html_content

        # Prepare related articles list for AI
        articles_text = "\n".join([f"- {a['title']} | URL: {a['url']}" for a in related_articles])
        
        prompt = CONTEXTUAL_LINK_INJECTION_PROMPT.format(
            related_articles=articles_text,
            html_content=html_content
        )

        try:
            logger.info(f"Injecting {len(related_articles)} internal links into HTML content...")
            response = self.client.chat.completions.create(
                model="gpt-4o", # Use full gpt-4o for complex HTML editing
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3 # Keep it precise
            )
            
            new_html = response.choices[0].message.content
            
            # Clean markdown if AI wrapped it
            if "```html" in new_html:
                new_html = new_html.split("```html")[1].split("```")[0].strip()
            elif "```" in new_html:
                new_html = new_html.split("```")[1].split("```")[0].strip()
            
            return new_html
        except Exception as e:
            logger.error(f"Error injecting internal links: {e}")
            return html_content

    def add_related_section(self, html_content: str, related_articles: List[Dict]) -> str:
        """Append a clean 'Related Articles' section at the end."""
        if not related_articles:
            return html_content

        links_html = "".join([f'<li><a href="{a["url"]}">{a["title"]}</a></li>' for a in related_articles])
        section_html = f"""
        <div class="related-articles-section" style="margin-top: 50px; border-top: 2px solid #eee; padding-top: 30px; margin-bottom: 30px;">
            <h2 style="text-align: left; margin-bottom: 20px;">You Might Also Like</h2>
            <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">
                {links_html}
            </ul>
        </div>
        """
        
        # Insert before footer if possible
        if "<footer>" in html_content:
            return html_content.replace("<footer>", section_html + "<footer>")
        elif "<footer" in html_content:
             return html_content.replace("<footer", section_html + "<footer")
        else:
            # Otherwise just append before the closing div
            return html_content.replace("</div>", section_html + "</div>")
