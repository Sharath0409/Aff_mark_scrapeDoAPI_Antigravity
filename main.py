import sys
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.scraper import AmazonScraper
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.notifier import EmailNotifier

logger = get_logger("main")

def main():
    logger.info("Starting Autonomous Affiliate Publisher Pipeline")
    
    # 1. Initialize Modules
    sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    scraper = AmazonScraper()
    generator = ContentGenerator()
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    notifier = EmailNotifier()
    
    try:
        # 2. Check pending count & warn if necessary
        pending_count = sheets.get_pending_count()
        if pending_count <= 5:
            notifier.send_warning(pending_count)
            
        if pending_count == 0:
            logger.info("No pending rows found. Exiting.")
            sys.exit(0)
            
        # 3. Fetch next pending row
        row = sheets.get_pending_row()
        if not row:
            logger.info("No pending rows found. Pipeline finished.")
            return

        topic = row['Topic']
        keyword = row['Keyword']
        row_index = row['row_index']
        
        # 4. Scrape Products
        product_urls = scraper.search_products(keyword)
        if not product_urls:
            raise ValueError("No products found for keyword.")
            
        products_data = []
        for url in product_urls[:3]:  # Top 3 products
            data = scraper.scrape_product_details(url)
            if data:
                products_data.append(data)
                
        # 5. Generate Content
        html_content, related_topics = generator.generate_full_post(topic, keyword, products_data)
        
        # 5.5 Generate SEO Labels
        seo_labels = generator.generate_seo_tags(topic, keyword)
        category = row.get('Category', 'Review')
        if category not in seo_labels:
            seo_labels.append(category)
        
        # 6. Publish to Blogger
        # Sanitize title to help Blogger generate a cleaner slug
        clean_title = topic.strip()
        published_url, current_post_id = publisher.publish_post(clean_title, html_content, labels=seo_labels)
        
        # 7. Update Google Sheets
        sheets.update_row_status(row_index, "Success", url=published_url, post_id=current_post_id)
        
        # 7.5 Add related topics to sheet for future runs (Auto-feeding)
        if related_topics:
            sheets.add_related_topics(related_topics, parent_post_id=current_post_id, category=category)
            
        # 7.6 Link Back (Update Parent Post with the new URL)
        parent_post_id = row.get("Parent Post ID")
        if parent_post_id:
            logger.info(f"Attempting to link back to parent post: {parent_post_id}")
            try:
                parent_post = publisher.get_post(parent_post_id)
                parent_content = parent_post['content']
                # Search for the exact topic text in the related reading list and wrap it in a link
                import re
                # We escape the topic to avoid regex issues
                escaped_topic = re.escape(topic)
                # Look for the topic inside a list item
                pattern = f'<li>{escaped_topic}</li>'
                replacement = f'<li><a href="{published_url}">{topic}</a></li>'
                
                if re.search(pattern, parent_content, re.IGNORECASE):
                    new_parent_content = re.sub(pattern, replacement, parent_content, flags=re.IGNORECASE)
                    parent_post['content'] = new_parent_content
                    publisher.update_post(parent_post_id, parent_post)
                    logger.info("Successfully updated parent post with real internal link.")
                else:
                    # Fallback: just search for the text if the <li> tag varies
                    if topic in parent_content:
                         new_parent_content = parent_content.replace(topic, f'<a href="{published_url}">{topic}</a>')
                         parent_post['content'] = new_parent_content
                         publisher.update_post(parent_post_id, parent_post)
                         logger.info("Successfully updated parent post (fallback search).")
                    else:
                        logger.warning(f"Could not find topic text '{topic}' in parent post to update link.")
            except Exception as e:
                logger.error(f"Failed to update parent post link: {e}")

        logger.info(f"Pipeline finished successfully for topic: {topic}")
        
        # 8. Send Success Report
        notifier.send_report("Success", topic, f"Post published at: {published_url}\nAuto-added {len(related_topics)} topics to queue.\nLink-back to parent: {'Done' if parent_post_id else 'N/A'}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # 9. Send Fatal Failure Report (after all retries failed)
        try:
            notifier.send_report("Failure", topic if 'topic' in locals() else "Unknown", str(e))
        except:
            pass

if __name__ == "__main__":
    main()
