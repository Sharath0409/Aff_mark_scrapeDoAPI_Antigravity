from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator

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
        
    @get_retry_decorator()
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
            request = posts.insert(blogId=self.blog_id, body=body, isDraft=False)
            response = request.execute()
            url = response.get('url')
            post_id = response.get('id')
            logger.info(f"Post successfully published: {url} (ID: {post_id})")
            return url, post_id
        except Exception as e:
            logger.error(f"Error publishing to Blogger: {e}")
            raise

    @get_retry_decorator()
    def get_post(self, post_id):
        """Fetch a post by ID."""
        return self.service.posts().get(blogId=self.blog_id, postId=post_id).execute()

    @get_retry_decorator()
    def update_post(self, post_id, post_body):
        """Update an existing post."""
        return self.service.posts().update(blogId=self.blog_id, postId=post_id, body=post_body).execute()

    @get_retry_decorator()
    def list_all_posts(self, max_results=500):
        """Retrieve existing posts for internal link matching."""
        logger.info(f"Listing up to {max_results} existing posts...")
        posts_list = []
        page_token = None
        
        while len(posts_list) < max_results:
            request = self.service.posts().list(
                blogId=self.blog_id,
                pageToken=page_token,
                maxResults=min(max_results - len(posts_list), 500),
                fetchBodies=False # Only need metadata
            )
            response = request.execute()
            
            items = response.get('items', [])
            if not items:
                break
                
            posts_list.extend(items)
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
        logger.info(f"Successfully retrieved {len(posts_list)} posts.")
        return posts_list
