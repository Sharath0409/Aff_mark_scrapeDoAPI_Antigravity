import os
import logging
from bs4 import BeautifulSoup
from config import settings
from core.blogger_publisher import BloggerPublisher
from utils.image_engine import ImageEngine
from utils.image_uploader import CloudinaryUploader
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_cleanup")

class HistoricalCleanup:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.engine = ImageEngine()
        self.uploader = CloudinaryUploader(
            cloud_name=settings.CLOUDINARY_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        self.backup_dir = "backups_html"
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

        if not posts:
            logger.info("No posts found to process.")
            return

        logger.info(f"Found {len(posts)} posts. Starting migration...")

        for post in posts:
            post_id = post['id']
            title = post['title']
            content = post['content']
            
            logger.info(f"--- Processing: {title} (ID: {post_id}) ---")
            
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            if not images:
                logger.info(f"No images found in post: {title}")
                continue

            changes_made = False
            for img in images:
                src = img.get('src', '')
                
                # Check if it's an external Amazon or unoptimized URL
                if "amazon.com" in src or "ssl-images-amazon" in src:
                    logger.info(f"Found unoptimized image: {src}")
                    
                    # 1. Optimize
                    local_webp = self.engine.download_and_optimize(src, title)
                    if local_webp:
                        # 2. Upload
                        optimized_url = self.uploader.upload(local_webp)
                        if optimized_url:
                            # 3. Replace
                            img['src'] = optimized_url
                            changes_made = True
                            logger.info(f"Replaced image with optimized version.")

                # 4. Add Lazy Loading if missing
                if not img.get('loading'):
                    img['loading'] = 'lazy'
                    changes_made = True
                    logger.info("Added loading='lazy' to image.")

            if changes_made:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update post: {title}")
                else:
                    # Backup before update
                    self.backup_post(post_id, title, content)
                    
                    # Update post on Blogger
                    updated_html = str(soup)
                    self.publisher.service.posts().patch(
                        blogId=self.publisher.blog_id,
                        postId=post_id,
                        body={'content': updated_html}
                    ).execute()
                    logger.info(f"Successfully updated post: {title}")
            else:
                logger.info(f"No changes needed for post: {title}")

if __name__ == "__main__":
    # Example execution
    import argparse
    parser = argparse.ArgumentParser(description="Migrate historical Blogger posts to optimized images.")
    parser.add_argument("--limit", type=int, help="Limit number of posts to process")
    parser.add_argument("--dry-run", action="store_true", help="Run without updating Blogger")
    
    args = parser.parse_args()
    
    cleanup = HistoricalCleanup()
    cleanup.process_posts(limit=args.limit, dry_run=args.dry_run)
