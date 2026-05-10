from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config.logger import get_logger
from config import settings

logger = get_logger(__name__)

class BloggerPublisher:
    def __init__(self, blog_id):
        self.blog_id = blog_id
        
        try:
            # Construct Credentials using the refresh token
            creds = Credentials(
                token=None,
                refresh_token=settings.BLOGGER_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.BLOGGER_CLIENT_ID,
                client_secret=settings.BLOGGER_CLIENT_SECRET
            )
            self.service = build('blogger', 'v3', credentials=creds)
            logger.info("Successfully connected to Blogger API.")
        except Exception as e:
            logger.error(f"Failed to initialize Blogger API: {e}")
            raise
        
    def publish_post(self, title, content, labels=None):
        """Publish HTML payload to Blogger."""
        logger.info(f"Publishing post to Blogger: {title}")
        
        if labels is None:
            labels = []
            
        body = {
            "kind": "blogger#post",
            "title": title,
            "content": content,
            "labels": labels
        }
        
        try:
            posts = self.service.posts()
            # isDraft=False publishes the post immediately
            request = posts.insert(blogId=self.blog_id, body=body, isDraft=False)
            response = request.execute()
            url = response.get('url')
            logger.info(f"Post successfully published to Blogger: {url}")
            return url
        except Exception as e:
            logger.error(f"Error publishing to Blogger: {e}")
            raise
