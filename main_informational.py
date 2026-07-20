import sys
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.internal_linker import InternalLinkManager
from core.notifier import EmailNotifier
from utils.image_optimizer import ImageOptimizer

logger = get_logger("main_informational")

INFORMATIONAL_WORKSHEET = "Informational_Topics"


def main():
    logger.info("Starting Informational Publishing Workflow.")

    # Connect to the Informational_Topics worksheet.
    sheets = SheetsManager(
        settings.GOOGLE_SHEET_ID,
        settings.GCP_SERVICE_ACCOUNT,
        sheet_name=INFORMATIONAL_WORKSHEET,
    )

    # Read the first pending row from Informational_Topics.
    row = sheets.get_pending_row()

    if not row:
        print(f"No pending topics found in '{INFORMATIONAL_WORKSHEET}'.")
        logger.warning(f"No pending rows found in worksheet: {INFORMATIONAL_WORKSHEET}")
        sys.exit(0)

    topic = row.get("Topic", "")
    keyword = row.get("Keyword", "")
    category = row.get("Category", "")
    row_index = row["row_index"]

    # Mark the row as Processing using the existing SheetsManager method.
    sheets.update_row_status(row_index, "Processing")
    print("Status updated to Processing.\n")

    print(f"Topic:\n{topic}\n")
    print(f"Keyword:\n{keyword}\n")
    print(f"Category:\n{category}\n")

    # Initialize shared components
    generator = ContentGenerator()
    publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
    notifier = EmailNotifier()
    optimizer = ImageOptimizer()
    link_manager = InternalLinkManager(publisher)

    try:
        # --- STAGE 1: Generate Content Blueprint ---
        logger.info("Stage 1/8: Generating content blueprint")
        print("--- STAGE 1: Generating Content Blueprint ---")
        blueprint = generator.generate_informational_blueprint(topic, keyword, category)
        logger.info("Content blueprint generated successfully")
        print("Blueprint generated successfully.\n")

        # --- STAGE 2: Generate Complete Article ---
        logger.info("Stage 2/8: Generating informational article")
        print("--- STAGE 2: Generating Informational Article ---")
        article = generator.generate_informational_article(blueprint, topic, keyword, category)
        logger.info("Informational article generated successfully")
        print("Article generated successfully.\n")

        # --- STAGE 3: Generate Image Plan ---
        logger.info("Stage 3/8: Generating image plan")
        print("--- STAGE 3: Generating Image Plan ---")
        image_plan = generator.generate_image_plan(blueprint, article, topic, keyword, category)
        logger.info("Image plan generated successfully")
        print("Image plan generated successfully.\n")

        # --- STAGE 4: Generate, Optimize, Upload Images ---
        logger.info("Stage 4/8: Generating and uploading article images")
        print("--- STAGE 4: Generating and Uploading Images ---")
        image_manifest = generator.generate_article_images(image_plan, topic)
        logger.info(f"Image manifest created with {len(image_manifest)} images")
        print(f"Image manifest created with {len(image_manifest)} images.\n")

        # --- STAGE 5: Inject Images into Article ---
        logger.info("Stage 5/8: Injecting images into article")
        print("--- STAGE 5: Injecting Images into Article ---")
        html_with_images = generator.inject_images_into_article(article, image_manifest)
        logger.info("Images injected into article successfully")
        print("Images injected successfully.\n")

        # --- STAGE 6: Internal Linking ---
        logger.info("Stage 6/8: Generating internal links")
        print("--- STAGE 6: Generating Internal Links ---")
        link_manager.refresh_corpus()
        final_html = link_manager.link_informational_article(html_with_images, topic, category)
        logger.info("Internal links generated successfully")
        print("Internal links generated successfully.\n")

        # --- STAGE 7: Blogger Publishing ---
        logger.info("Stage 7/8: Publishing to Blogger")
        print("--- STAGE 7: Publishing to Blogger ---")
        seo_labels = generator.generate_seo_tags(topic, keyword)
        if category not in seo_labels:
            seo_labels.append(category)
        
        published_url, post_id = publisher.publish_post(topic, final_html, labels=seo_labels)
        logger.info(f"Article published successfully: {published_url} (Post ID: {post_id})")
        print(f"Published to Blogger: {published_url}")
        print(f"Post ID: {post_id}\n")

        # --- STAGE 8: Google Sheets Updates ---
        logger.info("Stage 8/8: Updating Google Sheets")
        print("--- STAGE 8: Updating Google Sheets ---")
        sheets.update_row_status(row_index, "Success", url=published_url, post_id=post_id)
        sheets.update_dashboard_stats("Success")
        sheets.log_execution(topic, "Success", url=published_url, post_id=post_id)
        logger.info("Google Sheets updated successfully")
        print("Google Sheets updated successfully.\n")

        # --- SUCCESS: Send Email Notification ---
        success_message = f"Informational article published successfully.\n\nTopic: {topic}\nURL: {published_url}\nPost ID: {post_id}"
        notifier.send_report("Informational Article Published", topic, success_message)
        logger.info("Success email notification sent")

        print("\n========================================")
        print("WORKFLOW COMPLETED SUCCESSFULLY")
        print("========================================")
        print(f"Topic: {topic}")
        print(f"Published URL: {published_url}")
        print(f"Post ID: {post_id}")
        print(f"Images: {len(image_manifest)}")
        print(f"Internal Links: Added via InternalLinkManager")
        print("========================================\n")

    except Exception as e:
        logger.error(f"Informational workflow failed: {e}", exc_info=True)
        
        # Update Google Sheets with failure
        try:
            sheets.update_row_status(row_index, "Failed", error=str(e))
            sheets.update_dashboard_stats("Failed")
            sheets.log_execution(topic, "Failed", error=str(e))
        except Exception as sheet_err:
            logger.error(f"Failed to update Google Sheets on error: {sheet_err}")

        # Send failure email
        try:
            notifier.send_report("Informational Article Failed", topic, f"Failure reason: {e}")
        except Exception as email_err:
            logger.error(f"Failed to send failure email: {email_err}")

        print(f"\nWorkflow FAILED: {e}")
        sys.exit(1)
    
    finally:
        # Clean up temporary image files
        optimizer.cleanup()
        logger.info("Temporary image files cleaned up")


if __name__ == "__main__":
    main()