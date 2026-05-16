import os
import sys
import logging
from datetime import datetime

# Add project root to sys.path to allow importing from core/config/utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup
from config import settings
from core.blogger_publisher import BloggerPublisher
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_cleanup")

class HistoricalCleanup:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.optimizer = ImageOptimizer()
        self.uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
        self.backup_dir = "backups_html"
        os.makedirs(self.backup_dir, exist_ok=True)
        logger.info(f"DEBUG: Loaded Folder ID from settings: '{settings.GOOGLE_DRIVE_FOLDER_ID}'")

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

        if not posts:
            logger.info("No posts found to process.")
            return

        logger.info(f"Found {len(posts)} posts. Starting Blogger CDN migration...")

        for post in posts:
            post_id = post['id']
            title = post['title']
            content = post['content']
            
            logger.info(f"--- Processing: {title} (ID: {post_id}) ---")
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            if not images:
                continue

            changes_made = False
            for img in images:
                src = img.get('src', '')
                
                # Detect unoptimized Amazon/External/GitHub URLs
                if any(x in src for x in ["amazon.com", "ssl-images-amazon", "github.io", "cloudinary"]):
                    logger.info(f"Optimizing for Blogger CDN: {src}")
                    
                    # 1. Download & Optimize Locally
                    temp_webp = self.optimizer.process_from_url(src, title)
                    
                    if temp_webp:
                        # 2. Upload to GCS CDN
                        cdn_url = self.uploader.upload_to_google_cdn(temp_webp, bucket_name=settings.GCS_BUCKET_NAME)
                        if cdn_url:
                            img['src'] = cdn_url
                            changes_made = True

                # 3. Force Lazy Loading
                if img.get('loading') != 'lazy':
                    img['loading'] = 'lazy'
                    changes_made = True

            if changes_made:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update: {title}")
                else:
                    self.backup_post(post_id, title, content)
                    updated_html = str(soup)
                    self.publisher.service.posts().patch(
                        blogId=self.publisher.blog_id,
                        postId=post_id,
                        body={'content': updated_html}
                    ).execute()
                    logger.info(f"Updated: {title}")
                    
            # Cleanup temp files after each post
            self.optimizer.cleanup()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Blogger images to Blogger CDN.")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Don't update live")
    
    args = parser.parse_args()
    HistoricalCleanup().process_posts(limit=args.limit, dry_run=args.dry_run)
