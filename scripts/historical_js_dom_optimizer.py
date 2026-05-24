import os
import sys
import logging
from bs4 import BeautifulSoup
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_js_dom_optimizer")

class HistoricalJsDomOptimizer:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.backup_dir = "backups_dom_js"
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_post(self, post_id, title, html):
        filename = f"{self.backup_dir}/{post_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"<!-- Title: {title} -->\n{html}")
        logger.info(f"Backup saved: {filename}")

    def process_posts(self, limit=None, dry_run=False):
        logger.info(f"Fetching posts from Blogger... (Limit: {limit})")
        posts = self.publisher.service.posts().list(
            blogId=self.publisher.blog_id,
            maxResults=limit if limit else 500
        ).execute().get('items', [])

        for post in posts:
            post_id = post['id']
            title = post['title']
            content = post['content']
            
            logger.info(f"--- Analyzing: {title} (ID: {post_id}) ---")
            
            soup = BeautifulSoup(content, 'html.parser')
            changes_made = False
            
            # 1. Remove unnecessary scripts (Keep JSON-LD Schema)
            for script in soup.find_all('script'):
                if script.get('type') == 'application/ld+json':
                    continue # Preserve Schema Markup
                
                logger.info(f"Removing bloated script tag: {script.get('src') or 'inline JS'}")
                script.decompose()
                changes_made = True

            # 2. Lazy load images and iframes, remove bad iframes
            for iframe in soup.find_all('iframe'):
                src = iframe.get('src', '')
                if 'facebook.com/plugins' in src or 'twitter.com/widgets' in src:
                    logger.info(f"Removing social iframe: {src}")
                    iframe.decompose()
                    changes_made = True
                else:
                    if iframe.get('loading') != 'lazy':
                        iframe['loading'] = 'lazy'
                        changes_made = True
            
            for img in soup.find_all('img'):
                if img.get('loading') != 'lazy':
                    img['loading'] = 'lazy'
                    changes_made = True

            # 3. Clean up empty divs or duplicate tracking wrappers (e.g. AddThis, ShareThis wrappers)
            for div in soup.find_all('div', class_=lambda c: c and any(bad in c.lower() for bad in ['addthis', 'sharethis', 'social-share'])):
                logger.info("Removing social sharing widget wrapper.")
                div.decompose()
                changes_made = True

            if changes_made:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update post: {title}")
                else:
                    self.backup_post(post_id, title, content)
                    updated_html = str(soup)
                    
                    self.publisher.service.posts().patch(
                        blogId=self.publisher.blog_id,
                        postId=post_id,
                        body={'content': updated_html}
                    ).execute()
                    logger.info(f"Successfully cleaned DOM and JS for live post: {title}")
            else:
                logger.info("No bloat found. DOM is clean.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Optimize JS and DOM of historical Blogger posts.")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Don't update live")
    
    args = parser.parse_args()
    HistoricalJsDomOptimizer().process_posts(limit=args.limit, dry_run=args.dry_run)
