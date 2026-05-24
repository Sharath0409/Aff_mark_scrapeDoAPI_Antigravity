import os
import sys
import logging
from bs4 import BeautifulSoup
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_pagespeed_fixer")

class HistoricalPageSpeedFixer:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.optimizer = ImageOptimizer()
        self.uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
        self.backup_dir = "backups_pagespeed"
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
            
            logger.info(f"--- Processing: {title} (ID: {post_id}) ---")
            
            changes_made = False
            
            # 1. Update Inline CSS (Aspect Ratio & Contrast)
            old_img_css = ".product-image-centered img { max-width: 100%; height: auto; border-radius: 8px; max-height: 400px; }"
            new_img_css = ".product-image-centered img { max-width: 100%; height: auto; width: auto; border-radius: 8px; max-height: 400px; object-fit: contain; }"
            if old_img_css in content:
                content = content.replace(old_img_css, new_img_css)
                logger.info("Updated image CSS for aspect-ratio.")
                changes_made = True

            old_badge_css = ".price-badge { display: inline-block; background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 15px; }"
            new_badge_css = ".price-badge { display: inline-block; background: #fef3c7; color: #451a03; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 15px; }"
            if old_badge_css in content:
                content = content.replace(old_badge_css, new_badge_css)
                logger.info("Updated price badge CSS for contrast.")
                changes_made = True

            # Parse with BeautifulSoup for Image Resizing
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            for img in images:
                src = img.get('src')
                width = img.get('width')
                
                # Check if image is 1200px or larger, it needs downsizing to 800px
                if src and (width == '1200' or (width and int(width) > 800)):
                    logger.info(f"Found oversized image (Width: {width}). Re-optimizing to 800px max.")
                    
                    # Download from GCS, resize, upload back to GCS
                    temp_webp, img_w, img_h = self.optimizer.process_from_url(src, title)
                    
                    if temp_webp:
                        cdn_url = self.uploader.upload_to_google_cdn(temp_webp, bucket_name=settings.GCS_BUCKET_NAME)
                        if cdn_url:
                            img['src'] = cdn_url
                            img['width'] = str(img_w)
                            img['height'] = str(img_h)
                            changes_made = True
                            logger.info(f"Resized image to {img_w}x{img_h} and uploaded.")

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
                    logger.info(f"Updated live post: {title}")
                    
            self.optimizer.cleanup()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix PageSpeed issues on historical posts.")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Don't update live")
    
    args = parser.parse_args()
    HistoricalPageSpeedFixer().process_posts(limit=args.limit, dry_run=args.dry_run)
