"""Schema.org JSON-LD Generator

Generates Product, Review, and AggregateRating schema.org JSON-LD markup
for each product in the article to enable rich snippets in search results.
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.parse import urlparse


@dataclass
class ProductSchema:
    """Product schema.org data."""
    name: str
    description: str
    brand: str
    sku: str
    mpn: Optional[str] = None
    gtin: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    price: Optional[str] = None
    price_currency: str = "USD"
    availability: str = "https://schema.org/InStock"
    seller_name: str = "Amazon"
    seller_url: str = "https://www.amazon.com"
    aggregate_rating: Optional[Dict] = None
    review: Optional[Dict] = None
    category: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to schema.org JSON-LD dict."""
        data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": self.name,
            "description": self.description,
            "brand": {"@type": "Brand", "name": self.brand},
            "sku": self.sku,
        }
        
        if self.mpn:
            data["mpn"] = self.mpn
        if self.gtin:
            data["gtin"] = self.gtin
        if self.image:
            data["image"] = self.image
        if self.url:
            data["url"] = self.url
        if self.price:
            data["offers"] = {
                "@type": "Offer",
                "price": self._extract_price(self.price),
                "priceCurrency": self.price_currency,
                "availability": self.availability,
                "seller": {
                    "@type": "Organization",
                    "name": self.seller_name,
                    "url": self.seller_url
                }
            }
        if self.aggregate_rating:
            data["aggregateRating"] = self.aggregate_rating
        if self.review:
            data["review"] = self.review
        if self.category:
            data["category"] = self.category
        
        return data
    
    def _extract_price(self, price_str: str) -> str:
        """Extract numeric price from string like '$129.99'."""
        import re
        match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
        return match.group(0) if match else "0"


@dataclass
class ReviewSchema:
    """Review schema.org data."""
    author_name: str
    author_url: Optional[str] = None
    date_published: Optional[str] = None
    review_body: str = ""
    review_rating: Optional[Dict] = None
    publisher_name: str = "RemoteProstor"
    publisher_url: str = "https://remoteprostor.com"
    
    def to_dict(self) -> Dict:
        data = {
            "@type": "Review",
            "author": {"@type": "Person", "name": self.author_name},
            "reviewBody": self.review_body,
            "publisher": {
                "@type": "Organization",
                "name": self.publisher_name,
                "url": self.publisher_url
            }
        }
        
        if self.author_url:
            data["author"]["url"] = self.author_url
        if self.date_published:
            data["datePublished"] = self.date_published
        if self.review_rating:
            data["reviewRating"] = self.review_rating
        
        return data


@dataclass
class AggregateRatingSchema:
    """AggregateRating schema.org data."""
    rating_value: float
    review_count: int
    best_rating: float = 5.0
    worst_rating: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "@type": "AggregateRating",
            "ratingValue": self.rating_value,
            "reviewCount": self.review_count,
            "bestRating": self.best_rating,
            "worstRating": self.worst_rating
        }


class SchemaGenerator:
    """Generates schema.org JSON-LD for products in an article."""
    
    def __init__(self, author_name: str = "RemoteProstor Editorial Team",
                 author_url: str = "https://remoteprostor.com/about",
                 publisher_name: str = "RemoteProstor",
                 publisher_url: str = "https://remoteprostor.com"):
        self.author_name = author_name
        self.author_url = author_url
        self.publisher_name = publisher_name
        self.publisher_url = publisher_url
    
    def generate_product_schema(self, product: Dict, topic: str, 
                                article_url: str, position: int) -> Dict:
        """
        Generate Product schema for a single product.
        
        Args:
            product: Product dict with keys: title, price, rating, review_count, 
                    features, image_url, url, asin
            topic: Article topic
            article_url: Canonical URL of the article
            position: Position in the article (1-based)
        
        Returns:
            Product schema dict
        """
        # Extract ASIN from URL
        asin = product.get('asin') or self._extract_asin(product.get('url', ''))
        
        # Build description from features
        features = product.get('features', '')
        desc = self._build_description(product.get('title', ''), features)
        
        # Parse rating
        rating_val, review_count = self._parse_rating(product.get('rating', ''), 
                                                       product.get('review_count', ''))
        
        # Aggregate rating
        agg_rating = None
        if rating_val and review_count:
            agg_rating = AggregateRatingSchema(
                rating_value=rating_val,
                review_count=review_count
            ).to_dict()
        
        # Review
        review = None
        if rating_val:
            review = ReviewSchema(
                author_name="RemoteProstor Editorial Team",
                author_url="https://remoteprostor.com/about",
                date_published=datetime.now().strftime("%Y-%m-%d"),
                review_body=self._build_review_body(product.get('title', ''), features),
                review_rating={
                    "@type": "Rating",
                    "ratingValue": rating_val,
                    "bestRating": 5,
                    "worstRating": 1
                }
            ).to_dict()
        
        # Price
        price = product.get('price', '')
        price_clean = self._clean_price(price)
        
        # Brand extraction
        brand = self._extract_brand(product.get('title', ''))
        
        product_schema = ProductSchema(
            name=product.get('title', ''),
            description=desc,
            brand=brand,
            sku=asin or f"RP-{position}",
            mpn=asin,
            image=product.get('image_url'),
            url=product.get('url'),
            price=price_clean,
            price_currency="USD",
            availability="https://schema.org/InStock" if price_clean else "https://schema.org/OutOfStock",
            seller_name="Amazon.com",
            seller_url="https://www.amazon.com",
            aggregate_rating=agg_rating,
            review=review,
            category=topic
        )
        
        return product_schema.to_dict()
    
    def generate_all_schemas(self, products: List[Dict], topic: str, 
                             article_url: str) -> List[Dict]:
        """Generate schemas for all products in article."""
        schemas = []
        for i, product in enumerate(products, 1):
            schema = self.generate_product_schema(product, topic, article_url, i)
            schemas.append(schema)
        return schemas
    
    def generate_json_ld(self, products: List[Dict], topic: str, 
                         article_url: str) -> str:
        """Generate complete JSON-LD script block for all products."""
        schemas = self.generate_all_schemas(products, topic, article_url)
        
        # Wrap in ItemList for multiple products
        item_list = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "item": schema
                }
                for i, schema in enumerate(schemas)
            ]
        }
        
        # Combine individual product schemas with ItemList
        # Output as array for multiple script tags or single combined
        all_schemas = schemas + [item_list]
        
        return json.dumps(all_schemas, indent=2, ensure_ascii=False)
    
    def generate_inline_json_ld(self, products: List[Dict], topic: str,
                                 article_url: str) -> str:
        """Generate inline JSON-LD script tags for each product."""
        scripts = []
        for i, product in enumerate(products, 1):
            schema = self.generate_product_schema(product, topic, article_url, i)
            script = f'<script type="application/ld+json">\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n</script>'
            scripts.append(script)
        
        # Add ItemList
        item_list = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "item": schema}
                for i, schema in enumerate(
                    [self.generate_product_schema(p, topic, article_url, i) 
                     for i, p in enumerate(products, 1)], 1)
            ]
        }
        scripts.append(f'<script type="application/ld+json">\n{json.dumps(item_list, indent=2, ensure_ascii=False)}\n</script>')
        
        return "\n\n".join(scripts)
    
    # Helper methods
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        import re
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/ASIN/([A-Z0-9]{10})',
            r'[?&]asin=([A-Z0-9]{10})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _build_description(self, title: str, features: str) -> str:
        """Build product description from title and features."""
        base = f"{title}. "
        if features:
            # Take first 2-3 feature lines
            feature_lines = [f.strip() for f in features.split('\n') if f.strip()]
            base += " ".join(feature_lines[:3])
        return base[:500]  # Limit length
    
    def _build_review_body(self, title: str, features: str) -> str:
        """Build review body text."""
        return f"Our evaluation of the {title} based on manufacturer specifications, verified buyer feedback, and ergonomic best practices. {features[:300]}"
    
    def _parse_rating(self, rating_str: str, review_count_str: str) -> tuple:
        """Parse rating and review count from strings."""
        import re
        rating = None
        count = None
        
        if rating_str:
            match = re.search(r'(\d+\.?\d*)\s*(?:out of|\/)\s*5', rating_str)
            if match:
                rating = float(match.group(1))
            else:
                match = re.search(r'(\d+\.?\d*)', rating_str)
                if match:
                    rating = float(match.group(1))
        
        if review_count_str:
            match = re.search(r'([\d,]+)', review_count_str.replace(',', ''))
            if match:
                count = int(match.group(1).replace(',', ''))
        
        return rating, count
    
    def _clean_price(self, price_str: str) -> str:
        """Extract clean price number."""
        import re
        if not price_str:
            return ""
        match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
        return match.group(0) if match else ""
    
    def _extract_brand(self, title: str) -> str:
        """Extract brand from product title."""
        # Common brands - first word is often the brand
        known_brands = {
            'logitech', 'razer', 'steelseries', 'corsair', 'hyperx',
            'microsoft', 'apple', 'dell', 'hp', 'lenovo', 'asus',
            'samsung', 'lg', 'benq', 'viewsonic', 'aoc', 'aoc',
            'herman miller', 'steelcase', 'haworth', 'knoll',
            'uplift', 'vari', 'fully', 'autonomous', 'branch',
            'secretlab', 'dxracer', 'noblechairs', 'vertagear',
            'keychron', 'nuphy', 'epomaker', 'akko', 'gateron',
            'kinesis', 'ergodox', 'moonlander', 'glove80'
        }
        
        title_lower = title.lower()
        for brand in known_brands:
            if brand in title_lower:
                return brand.title()
        
        # Fallback: first word
        words = title.split()
        return words[0] if words else "Unknown"


# Convenience function
def generate_product_schemas(products: List[Dict], topic: str, 
                             article_url: str) -> str:
    """Convenience function to generate JSON-LD for products."""
    generator = SchemaGenerator()
    return generator.generate_inline_json_ld(products, topic, article_url)


if __name__ == "__main__":
    # Demo
    test_products = [
        {
            "title": "Logitech MX Master 3S Wireless Mouse",
            "price": "$99.99",
            "rating": "4.7 out of 5 stars",
            "review_count": "12,345",
            "features": "8000 DPI sensor\nMagSpeed scrolling\n70-day battery\nFlow cross-computer control",
            "image_url": "https://example.com/mouse.jpg",
            "url": "https://amazon.com/dp/B0B1234567",
            "asin": "B0B1234567"
        },
        {
            "title": "Keychron K2 Mechanical Keyboard",
            "price": "$79.99",
            "rating": "4.5 out of 5 stars",
            "review_count": "8,901",
            "features": "75% layout\nHot-swappable switches\nRGB backlight\nMac/Windows compatible",
            "image_url": "https://example.com/keyboard.jpg",
            "url": "https://amazon.com/dp/B0B7654321",
            "asin": "B0B7654321"
        }
    ]
    
    generator = SchemaGenerator()
    json_ld = generator.generate_inline_json_ld(test_products, "Best Wireless Mouse", "https://remoteprostor.com/best-wireless-mouse")
    print(json_ld)