from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def inject_affiliate_tag(amazon_url, affiliate_tag):
    """Injects or replaces the affiliate tag in an Amazon URL."""
    try:
        parsed_url = urlparse(amazon_url)
        query_params = parse_qs(parsed_url.query)
        query_params['tag'] = [affiliate_tag]
        
        new_query = urlencode(query_params, doseq=True)
        new_url = parsed_url._replace(query=new_query)
        return urlunparse(new_url)
    except Exception:
        return amazon_url
