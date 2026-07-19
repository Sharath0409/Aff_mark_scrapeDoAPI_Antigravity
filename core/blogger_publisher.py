from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from bs4 import BeautifulSoup

logger = get_logger(__name__)


def validate_content(content: str, min_length: int = 100) -> bool:
    """Validate that content is suitable for publishing.
    
    Args:
        content: HTML content to validate
        min_length: Minimum text content length
        
    Returns:
        True if valid, False otherwise
    """
    if not content or not content.strip():
        logger.error("Content validation failed: empty content")
        return False
    
    # Parse HTML and extract text content
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(strip=True)
    
    if len(text_content) < min_length:
        logger.error(f"Content validation failed: text content too short ({len(text_content)} < {min_length} chars)")
        return False
    
    # Check for required structural elements
    if not soup.find(['h1', 'h2', 'p']):
        logger.error("Content validation failed: no headings or paragraphs found")
        return False
    
    # Check for product sections if this is a product review post
    product_sections = soup.find_all('section', class_='product-section')
    if product_sections and len(product_sections) < 3:
        logger.warning(f"Content has only {len(product_sections)} product sections (expected at least 3)")
    
    return True


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
            
        # Validate content before publishing
        if not validate_content(content):
            raise ValueError("Content validation failed - cannot publish")
        
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
        # Validate content if present
        if 'content' in post_body:
            if not validate_content(post_body['content']):
                raise ValueError("Content validation failed - cannot update")
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
