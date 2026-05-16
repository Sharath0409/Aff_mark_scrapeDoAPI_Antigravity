import os
import logging
from bs4 import BeautifulSoup
from config import settings
from core.blogger_publisher import BloggerPublisher
from utils.image_engine import ImageEngine
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_cleanup")

class HistoricalCleanup:
    def __init__(self):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.engine = ImageEngine(
            github_user=settings.GITHUB_USERNAME,
            github_repo=settings.GITHUB_REPO_NAME
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

        logger.info(f"Found {len(posts)} posts. Starting GitHub Pages migration...")

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
                
                # Detect unoptimized Amazon/External URLs
                if "amazon.com" in src or "ssl-images-amazon" in src or "cloudinary" in src:
                    logger.info(f"Optimizing: {src}")
                    
                    # 1. Optimize and Save to Repo
                    # We use "historical" as category for old posts organization
                    optimized_url = self.engine.download_and_optimize(src, title, category="historical")
                    
                    if optimized_url:
                        img['src'] = optimized_url
                        changes_made = True

                # 2. Force Lazy Loading
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Blogger images to GitHub Pages.")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Don't update live")
    
    args = parser.parse_args()
    HistoricalCleanup().process_posts(limit=args.limit, dry_run=args.dry_run)
