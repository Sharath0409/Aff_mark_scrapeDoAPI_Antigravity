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
            # Otherwise just append before the closing div (last occurrence only)
            parts = html_content.rsplit("</div>", 1)
            if len(parts) == 2:
                return parts[0] + section_html + "</div>" + parts[1]
            else:
                return html_content + section_html

    def link_informational_article(self, html_content: str, topic: str, category: str) -> str:
        """Link an informational article to both related informational and commercial articles.

        Selection prioritizes topic, keyword, and category similarity using existing similarity logic.
        Avoids duplicate links and self-linking. Contextually injects links and appends a split Related Articles section.
        """
        logger.info(f"Running internal linking for informational article: {topic}")
        
        # 1. Refresh corpus if not already done
        if not self.corpus:
            self.refresh_corpus()
            
        if not self.corpus:
            logger.warning("No corpus available. Returning unmodified HTML.")
            return html_content

        # Helper to filter out the current article
        def is_same_article(item):
            clean_item = re.sub(r'[^a-z0-9]', '', item['title'].lower())
            clean_topic = re.sub(r'[^a-z0-9]', '', topic.lower())
            return clean_item == clean_topic

        # Heuristic for commercial vs informational classification
        def is_commercial(item):
            title_lower = item['title'].lower()
            commercial_keywords = [
                "best", "review", "vs", "top", "under", "buying guide", 
                "deals", "cheap", "comparison", "purchase", "shopping",
                "gear", "gadgets", "product", "affordable", "price", "buyer"
            ]
            if any(kw in title_lower for kw in commercial_keywords):
                return True
            commercial_labels = ["review", "reviews", "product", "products", "buying-guide", "comparison"]
            if any(l.lower() in commercial_labels for l in item.get('labels', [])):
                return True
            return False

        # Filter corpus
        filtered_corpus = [item for item in self.corpus if not is_same_article(item)]

        informational_corpus = [item for item in filtered_corpus if not is_commercial(item)]
        commercial_corpus = [item for item in filtered_corpus if is_commercial(item)]

        logger.info(f"Classified corpus: {len(informational_corpus)} informational, {len(commercial_corpus)} commercial posts.")

        # Find related informational articles (2-4, target 3)
        original_corpus = self.corpus
        
        related_info = []
        if informational_corpus:
            self.corpus = informational_corpus
            related_info = self.get_related_articles(topic, [category], count=3)
            
        # Find relevant commercial articles (2-3, target 2)
        related_comm = []
        if commercial_corpus:
            self.corpus = commercial_corpus
            related_comm = self.get_related_articles(topic, [category], count=2)

        # Restore original corpus
        self.corpus = original_corpus

        logger.info(f"Selected related informational: {[a['title'] for a in related_info]}")
        logger.info(f"Selected related commercial: {[a['title'] for a in related_comm]}")

        # Combine selected articles for contextual injection
        all_selected = related_info + related_comm
        
        if not all_selected:
            return html_content

        # Contextually inject links using the existing AI method
        html_with_links = self.inject_internal_links(html_content, all_selected)

        # Generate the 'Related Articles' section at the end
        related_section_html = self._generate_split_related_section(related_info, related_comm)

        # Insert section before footer or closing div
        if "<footer>" in html_with_links:
            html_with_links = html_with_links.replace("<footer>", related_section_html + "<footer>")
        elif "<footer" in html_with_links:
            html_with_links = html_with_links.replace("<footer", related_section_html + "<footer")
        else:
            parts = html_with_links.rsplit("</div>", 1)
            if len(parts) == 2:
                html_with_links = parts[0] + related_section_html + "</div>" + parts[1]
            else:
                html_with_links = html_with_links + related_section_html

        return html_with_links

    def _generate_split_related_section(self, related_info: List[Dict], related_comm: List[Dict]) -> str:
        """Generate HTML block containing split list of related guides and recommendations."""
        info_links = "".join([f'<li><a href="{a["url"]}">{a["title"]}</a></li>' for a in related_info])
        comm_links = "".join([f'<li><a href="{a["url"]}">{a["title"]}</a></li>' for a in related_comm])
        
        sections = []
        if info_links:
            sections.append(f"""
            <div class="related-guides" style="margin-bottom: 20px;">
                <h3 style="text-align: left; font-size: 1.3em;">Related Guides &amp; Tutorials</h3>
                <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">
                    {info_links}
                </ul>
            </div>
            """)
        if comm_links:
            sections.append(f"""
            <div class="related-recommendations" style="margin-bottom: 20px;">
                <h3 style="text-align: left; font-size: 1.3em;">Recommended Gear &amp; Product Reviews</h3>
                <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">
                    {comm_links}
                </ul>
            </div>
            """)
            
        inner_content = "\n".join(sections)
        
        return f"""
        <div class="related-articles-section" style="margin-top: 50px; border-top: 2px solid #eee; padding-top: 30px; margin-bottom: 30px;">
            <h2 style="text-align: left; margin-bottom: 20px; font-size: 1.8em;">Related Articles</h2>
            {inner_content}
        </div>
        """

