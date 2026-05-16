import os
import sys
import logging
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_dimension_fixer")

class HistoricalDimensionFixer:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.backup_dir = "backups_dimensions"
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_post(self, post_id, title, html):
        filename = f"{self.backup_dir}/{post_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"<!-- Title: {title} -->\n{html}")
        logger.info(f"Backup saved: {filename}")

    def get_image_dimensions(self, url):
        """Fetch image and return (width, height)."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img.width, img.height
        except Exception as e:
            logger.error(f"Failed to get dimensions for {url}: {e}")
            return None, None

    def process_posts(self, limit=None, dry_run=False, post_id_test=None):
        if post_id_test:
            logger.info(f"Testing single post: {post_id_test}")
            post = self.publisher.service.posts().get(blogId=self.publisher.blog_id, postId=post_id_test).execute()
            posts = [post]
        else:
            logger.info(f"Fetching posts from Blogger... (Limit: {limit})")
            posts = self.publisher.service.posts().list(
                blogId=self.publisher.blog_id,
                maxResults=limit if limit else 500
            ).execute().get('items', [])

        if not posts:
            logger.info("No posts found.")
            return

        for post in posts:
            post_id = post['id']
            title = post['title']
            content = post['content']
            
            logger.info(f"--- Scanning: {title} (ID: {post_id}) ---")
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            changes_made = False
            for img in images:
                # Check if dimensions are missing
                has_width = img.get('width')
                has_height = img.get('height')
                src = img.get('src')

                if src and (not has_width or not has_height):
                    logger.info(f"Found image missing dimensions: {src}")
                    w, h = self.get_image_dimensions(src)
                    
                    if w and h:
                        img['width'] = str(w)
                        img['height'] = str(h)
                        
                        # Also force lazy loading while we are at it
                        if img.get('loading') != 'lazy':
                            img['loading'] = 'lazy'
                            
                        logger.info(f"Injected dimensions: {w}x{h}")
                        changes_made = True
                else:
                    # Even if it has dimensions, ensure loading="lazy"
                    if img.get('loading') != 'lazy':
                        img['loading'] = 'lazy'
                        changes_made = True

            if changes_made:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update {len(images)} images in: {title}")
                else:
                    self.backup_post(post_id, title, content)
                    updated_html = str(soup)
                    self.publisher.service.posts().patch(
                        blogId=self.publisher.blog_id,
                        postId=post_id,
                        body={'content': updated_html}
                    ).execute()
                    logger.info(f"Successfully updated dimensions for: {title}")
            else:
                logger.info(f"No changes needed for: {title}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix missing image dimensions in Blogger posts.")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Don't update live")
    parser.add_argument("--post-id", type=str, help="Update a specific post only")
    
    args = parser.parse_args()
    fixer = HistoricalDimensionFixer()
    fixer.process_posts(limit=args.limit, dry_run=args.dry_run, post_id_test=args.post_id)
