import requests
from bs4 import BeautifulSoup
from config.logger import get_logger
from utils.retry import get_retry_decorator
from config import settings
from urllib.parse import urljoin
from utils.affiliate import inject_affiliate_tag
import time
import random

logger = get_logger(__name__)

class AmazonScraper:
    def __init__(self):
        self.scrape_do_token = settings.SCRAPE_DO_TOKEN
        self.base_url = "http://api.scrape.do"
        
    def _fetch_via_scraped(self, target_url):
        if not self.scrape_do_token or self.scrape_do_token == "your_scrape_do_token":
            logger.warning("Scrape.do token not set. Skipping real request.")
            return None
            
        params = {
            "token": self.scrape_do_token,
            "url": target_url,
            "geoCode": "us"
        }
        
        logger.info(f"Fetching via Scrape.do: {target_url}")
        # Add random sleep to be polite even with proxies
        time.sleep(random.uniform(1.5, 3.5))
        
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.text

    @get_retry_decorator()
    def search_products(self, keyword):
        """Search Amazon and return top product URLs."""
        logger.info(f"Searching Amazon for keyword: {keyword}")
        amazon_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
        
        html = self._fetch_via_scraped(amazon_url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        
        product_urls = []
        # Amazon search results usually have data-component-type="s-search-result"
        results = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for result in results:
            # Skip sponsored products if possible
            sponsored_tag = result.find('span', class_='a-color-secondary')
            if sponsored_tag and "sponsored" in sponsored_tag.text.lower():
                continue
                
            link_tag = result.find('a', class_='a-link-normal s-no-outline')
            if link_tag and 'href' in link_tag.attrs:
                url = urljoin("https://www.amazon.com", link_tag['href'])
                # Remove query parameters from url to make it cleaner
                clean_url = url.split('?')[0] if '?' in url else url
                if clean_url not in product_urls:
                    product_urls.append(clean_url)
                    
            if len(product_urls) >= 5: # Limit to top 5
                break
                
        logger.info(f"Found {len(product_urls)} products for keyword '{keyword}'")
        return product_urls

    @get_retry_decorator()
    def scrape_product_details(self, url):
        """Extract title, price, rating, features from an ASIN."""
        logger.info(f"Scraping product details from: {url}")
        
        html = self._fetch_via_scraped(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        details = {
            "title": "Unknown Title",
            "price": "Price not found",
            "rating": "No rating",
            "review_count": "0",
            "features": "No features found",
            "image_url": "",
            "url": inject_affiliate_tag(url, settings.AMAZON_AFFILIATE_TAG)
        }
        
        try:
            # Extract High-Resolution Image
            img_tag = soup.find('img', id='landingImage') or soup.find('img', id='imgBlkFront')
            if img_tag:
                # Try to get high-res source
                hi_res = img_tag.get('data-old-hires') or img_tag.get('data-a-dynamic-image')
                if hi_res and hi_res.startswith('{'):
                    try:
                        import json
                        images = json.loads(hi_res)
                        # Get the URL with the largest dimensions
                        details['image_url'] = max(images.items(), key=lambda x: x[1][0])[0]
                    except:
                        details['image_url'] = img_tag.get('src', '')
                else:
                    details['image_url'] = hi_res or img_tag.get('src', '')
            
            # Extract Delivery Location (to ensure it's not India)
            delivery_tag = soup.find('span', id='glow-ingress-line2')
            if delivery_tag and "India" in delivery_tag.text:
                logger.warning(f"Product shows delivery to India, skipping: {url}")
                return None
            
            # Extract Title
            title_tag = soup.find('span', id='productTitle')
            if title_tag:
                details['title'] = title_tag.text.strip()
                
            # Extract Price (multiple possible selectors)
            price_tag = soup.find('span', class_='a-offscreen')
            if not price_tag:
                # Try finding fractional price
                whole = soup.find('span', class_='a-price-whole')
                fraction = soup.find('span', class_='a-price-fraction')
                if whole and fraction:
                    details['price'] = f"${whole.text.strip()}{fraction.text.strip()}"
            if price_tag:
                details['price'] = price_tag.text.strip()
                
            # Extract Rating
            rating_tag = soup.find('span', class_='a-icon-alt')
            if rating_tag:
                details['rating'] = rating_tag.text.strip()
                
            # Extract Review Count
            review_tag = soup.find('span', id='acrCustomerReviewText')
            if review_tag:
                details['review_count'] = review_tag.text.strip().split()[0]
                
            # Extract Features
            feature_bullets = soup.find('div', id='feature-bullets')
            if feature_bullets:
                bullets = feature_bullets.find_all('span', class_='a-list-item')
                feature_texts = [b.text.strip() for b in bullets if b.text.strip() and "Make sure this fits" not in b.text]
                details['features'] = "\n- " + "\n- ".join(feature_texts[:5]) # Take top 5
                
        except Exception as e:
            logger.error(f"Error parsing product details for {url}: {e}")
            
        return details
