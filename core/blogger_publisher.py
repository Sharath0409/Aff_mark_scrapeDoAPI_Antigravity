from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from bs4 import BeautifulSoup, Comment

logger = get_logger(__name__)


def insert_jump_break(html: str) -> str:
    """Insert Blogger jump break (<!--more-->) after the first meaningful paragraph.
    
    Standardized jump break function used consistently across all publishing paths.
    Rules:
    1. If <!--more--> already exists, return unchanged
    2. Find first <p> with meaningful content (>50 chars) and insert after it
    3. If no substantial paragraph, insert before first <h2>
    4. If no H2, append at end
    
    Args:
        html: HTML content string
        
    Returns:
        HTML with jump break inserted after first meaningful paragraph
    """
    if not html:
        return html
    
    # Check if jump break already exists
    if '<!--more-->' in html:
        return html
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Rule 1: Find first <p> tag with meaningful content
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 50:  # Meaningful paragraph threshold
            p.insert_after(Comment('more'))
            return str(soup)
    
    # Rule 2: Fallback - insert before first H2
    first_h2 = soup.find('h2')
    if first_h2:
        first_h2.insert_before(Comment('more'))
        return str(soup)
    
    # Rule 3: Last resort - append at end
    soup.append(Comment('more'))
    return str(soup)


# Alias for backward compatibility
insert_jump_break_after_first_paragraph = insert_jump_break


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
    def publish_post(self, title, content, labels=None, is_draft=False):
        """Publish HTML payload to Blogger.
        
        Args:
            title: Post title
            content: HTML content
            labels: List of labels/tags
            is_draft: If True, publish as draft. Default False for backward compatibility.
        """
        logger.info(f"Publishing post to Blogger: {title} (draft={is_draft})")
        
        if labels is None:
            labels = []
            
        # Insert jump break before publishing (consistent logic)
        content = insert_jump_break(content)
        
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
            request = posts.insert(blogId=self.blog_id, body=body, isDraft=is_draft)
            response = request.execute()
            url = response.get('url')
            post_id = response.get('id')
            status = "draft" if is_draft else "published"
            logger.info(f"Post successfully {status}: {url} (ID: {post_id})")
            return url, post_id
        except Exception as e:
            logger.error(f"Error publishing to Blogger: {e}")
            raise

    @get_retry_decorator()
    def publish_post_as_draft(self, title, content, labels=None):
        """Publish HTML payload to Blogger as a draft."""
        return self.publish_post(title, content, labels, is_draft=True)

    @get_retry_decorator()
    def set_post_status(self, post_id, is_draft):
        """Update post draft/published status.
        
        Args:
            post_id: Blogger post ID
            is_draft: True to set as draft, False to publish
        """
        logger.info(f"Setting post {post_id} status to {'draft' if is_draft else 'published'}")
        try:
            post = self.get_post(post_id)
            # Blogger API v3 uses 'status' field: 'LIVE', 'DRAFT', or 'SCHEDULED'
            post['status'] = 'DRAFT' if is_draft else 'LIVE'
            updated = self.service.posts().update(blogId=self.blog_id, postId=post_id, body=post).execute()
            logger.info(f"Post {post_id} status updated to {updated.get('status', 'unknown')}")
            return updated
        except Exception as e:
            logger.error(f"Error setting post status: {e}")
            raise

    @get_retry_decorator()
    def publish_draft_post(self, post_id):
        """Publish a previously drafted post."""
        return self.set_post_status(post_id, is_draft=False)

    @get_retry_decorator()
    def get_post(self, post_id):
        """Fetch a post by ID."""
        return self.service.posts().get(blogId=self.blog_id, postId=post_id).execute()

    @get_retry_decorator()
    def update_post(self, post_id, post_body):
        """Update an existing post."""
        # Insert jump break if content is being updated (consistent logic)
        if 'content' in post_body:
            post_body['content'] = insert_jump_break(post_body['content'])
            # Validate content if present
            if not validate_content(post_body['content']):
                raise ValueError("Content validation failed - cannot update")
        return self.service.posts().update(blogId=self.blog_id, postId=post_id, body=post_body).execute()

    @get_retry_decorator()
    def list_all_posts(self, max_results=500, fetch_bodies=False):
        """Retrieve existing posts for internal link matching or audit."""
        logger.info(f"Listing up to {max_results} existing posts...")
        posts_list = []
        page_token = None
        
        while len(posts_list) < max_results:
            request = self.service.posts().list(
                blogId=self.blog_id,
                pageToken=page_token,
                maxResults=min(max_results - len(posts_list), 500),
                fetchBodies=fetch_bodies
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