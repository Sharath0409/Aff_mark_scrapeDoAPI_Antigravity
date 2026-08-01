import json
import logging
import re
from typing import List, Dict
from core.deepseek_client import DeepseekHttpClient
from config import settings
from templates.prompts import INTERNAL_LINK_RELEVANCE_PROMPT, CONTEXTUAL_LINK_INJECTION_PROMPT

logger = logging.getLogger(__name__)


def _extract_indices_from_response(content: str) -> List[int]:
    """Extract article indices from AI response.
    
    Expects a JSON array like [0, 2, 5] or space/comma separated numbers.
    """
    # First try to parse as JSON array
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [int(i) for i in parsed if isinstance(i, (int, str)) and str(i).isdigit()]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Fallback: look for array-like pattern [0, 1, 2] or (0, 1, 2)
    array_match = re.search(r'[\[\(]\s*(\d+(?:\s*[,\s]\s*\d+)*)\s*[\]\)]', content)
    if array_match:
        return [int(x.strip()) for x in re.split(r'[,\s]+', array_match.group(1)) if x.strip()]
    
    # Last resort: find standalone numbers (but this is fragile)
    # Only use if the response looks like just a list of numbers
    numbers = [int(i) for i in re.findall(r'\b\d+\b', content)]
    # Filter to reasonable indices (0-499 for max 500 posts)
    return [n for n in numbers if 0 <= n < 500]


class InternalLinkManager:
    def __init__(self, publisher):
        self.publisher = publisher
        self.client = DeepseekHttpClient(api_key=settings.DEEPSEEK_API_KEY)
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
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.choices[0].message.content
            
            # Extract indices from AI response using robust parser
            indices = _extract_indices_from_response(content)
            
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
                model="deepseek-v4-flash",
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

    # Configuration for commercial guide linking
    COMMERCIAL_RELEVANCE_THRESHOLD = getattr(settings, "CLIP_SIMILARITY_THRESHOLD", 0.25)
    MAX_COMMERCIAL_LINKS = 5
    MIN_COMMERCIAL_LINKS = 2

    def is_same_article(self, item, topic: str) -> bool:
        """Check if an article is the same as the current topic."""
        clean_item = re.sub(r'[^a-z0-9]', '', item['title'].lower())
        clean_topic = re.sub(r'[^a-z0-9]', '', topic.lower())
        return clean_item == clean_topic

    def is_commercial(self, item) -> bool:
        """Heuristic for commercial vs informational classification."""
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

    def get_commercial_embeddings(self, texts: list) -> list:
        """Get embeddings for commercial post titles + summaries using existing CLIP pipeline."""
        from core.content_generator import ContentGenerator
        generator = ContentGenerator()
        embeddings = []
        for text in texts:
            emb = generator.get_clip_embeddings(text=text)
            embeddings.append(emb)
        return embeddings

    def find_related_commercial_guides(self, html_content: str, topic: str, category: str, 
                                        current_article_title: str) -> list:
        """
        Find relevant commercial product guides using CLIP embeddings.
        Returns list of dicts with: title, url, relevance_score, anchor_text_suggestion
        """
        if not self.corpus:
            self.refresh_corpus()
        
        # Filter to commercial posts only
        commercial_posts = [
            item for item in self.corpus 
            if self.is_commercial(item) and not self.is_same_article(item, current_article_title)
        ]
        
        if not commercial_posts:
            logger.info("No commercial posts in corpus")
            return []
        
        # Prepare texts for embedding: title + first 200 chars of summary
        commercial_texts = [
            f"{p['title']}. {p.get('summary', '')[:200]}" 
            for p in commercial_posts
        ]
        
        # Get embeddings for commercial posts
        try:
            commercial_embeddings = self.get_commercial_embeddings(commercial_texts)
        except Exception as e:
            logger.error(f"Failed to get commercial embeddings: {e}")
            return []
        
        # Get query embedding (current article topic + category)
        from core.content_generator import ContentGenerator
        generator = ContentGenerator()
        query_text = f"{topic} {category}"
        query_embedding = generator.get_clip_embeddings(text=query_text)
        
        # Compute similarities
        scored_posts = []
        for i, (post, emb) in enumerate(zip(commercial_posts, commercial_embeddings)):
            sim = generator.cosine_similarity(query_embedding, emb)
            
            # Log every decision
            logger.info(f"COMMERCIAL LINK SCORE: '{post['title']}' -> {sim:.4f} "
                        f"(threshold: {self.COMMERCIAL_RELEVANCE_THRESHOLD})")
            
            if sim >= self.COMMERCIAL_RELEVANCE_THRESHOLD:
                scored_posts.append({
                    "title": post['title'],
                    "url": post['url'],
                    "relevance_score": sim,
                    "post_id": post['id']
                })
            else:
                logger.debug(f"REJECTED commercial link: '{post['title']}' ({sim:.4f})")
        
        # Sort by relevance descending, take top 5
        scored_posts.sort(key=lambda x: x['relevance_score'], reverse=True)
        selected = scored_posts[:self.MAX_COMMERCIAL_LINKS]
        
        if len(selected) < self.MIN_COMMERCIAL_LINKS:
            logger.info(f"Only {len(selected)} commercial guides cleared threshold ({self.COMMERCIAL_RELEVANCE_THRESHOLD}), skipping section")
            return []
        
        logger.info(f"Selected {len(selected)} commercial guides for 'Related Product Guides' section")
        return selected

    def _generate_commercial_guides_section(self, commercial_guides: list) -> str:
        """Generate HTML for 'Related Product Guides' section."""
        if not commercial_guides:
            return ""
        
        links_html = "".join([
            f'<li><a href="{g["url"]}">{g["title"]}</a> '
            f'<span class="relevance-badge" style="font-size:0.8em;color:#666;"> '
            f'(relevance: {g["relevance_score"]:.2f})</span></li>'
            for g in commercial_guides
        ])
        
        return f"""
        <div class="related-product-guides" style="margin-top: 50px; border-top: 2px solid #eee; padding-top: 30px; margin-bottom: 30px;">
            <h2 style="text-align: left; margin-bottom: 20px; font-size: 1.5em;">Related Product Guides</h2>
            <p style="color: #666; margin-bottom: 20px; font-size: 0.95em;">
                Based on this guide's topic, we've selected these product reviews and buying guides 
                that may help you complete your setup:
            </p>
            <ul style="list-style-type: disc; padding-left: 20px; line-height: 2.0;">
                {links_html}
            </ul>
        </div>
        """

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

        # Find related informational articles using existing AI method (target 3)
        related_info = []
        if self.corpus:
            # Filter out current article
            filtered = [item for item in self.corpus if not self.is_same_article(item, topic)]
            informational = [item for item in filtered if not self.is_commercial(item)]
            if informational:
                original_corpus = self.corpus
                self.corpus = informational
                related_info = self.get_related_articles(topic, [category], count=3)
                self.corpus = original_corpus
        
        # Find relevant commercial articles using CLIP embeddings (new logic)
        commercial_guides = self.find_related_commercial_guides(html_content, topic, category, topic)
        
        logger.info(f"Selected related informational: {[a['title'] for a in related_info]}")
        logger.info(f"Selected commercial guides: {[g['title'] for g in commercial_guides]}")

        # Combine selected articles for contextual injection
        all_selected = related_info + [{"title": g["title"], "url": g["url"]} for g in commercial_guides]
        
        if not all_selected:
            return html_content

        # Contextually inject links using the existing AI method
        html_with_links = self.inject_internal_links(html_content, all_selected)

        # Generate the 'Related Articles' section at the end (informational + commercial guides)
        related_section_html = self._generate_split_related_section(related_info, commercial_guides)

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

    def _generate_split_related_section(self, related_info: List[Dict], commercial_guides: List[Dict]) -> str:
        """Generate HTML block containing split list of related guides and recommendations."""
        info_links = "".join([f'<li><a href="{a["url"]}">{a["title"]}</a></li>' for a in related_info])
        comm_links = "".join([
            f'<li><a href="{g["url"]}">{g["title"]}</a> '
            f'<span class="relevance-badge" style="font-size:0.8em;color:#666;"> '
            f'(relevance: {g["relevance_score"]:.2f})</span></li>'
            for g in commercial_guides
        ])
        
        sections = []
        if info_links:
            sections.append(f"""
            <div class="related-guides" style="margin-bottom: 20px;">
                <h3 style="text-align: left; font-size: 1.3em;">Related Guides & Tutorials</h3>
                <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">
                    {info_links}
                </ul>
            </div>
            """)
        if comm_links:
            sections.append(f"""
            <div class="related-recommendations" style="margin-bottom: 20px;">
                <h3 style="text-align: left; font-size: 1.3em;">Recommended Gear & Product Reviews</h3>
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

