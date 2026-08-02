import sys
import json
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


def log_stage_start(stage_num, total_stages, stage_name):
    logger.info(f"Stage {stage_num}/{total_stages}: {stage_name}")
    print(f"--- STAGE {stage_num}: {stage_name} ---")

def log_stage_pass(stage_num, total_stages, stage_name, details=""):
    logger.info(f"Stage {stage_num}/{total_stages} PASSED: {stage_name} {details}")
    print(f"Stage {stage_num}/{total_stages} PASSED: {stage_name} {details}")

def log_stage_fail(stage_num, total_stages, stage_name, error, blocking=True):
    logger.error(f"Stage {stage_num}/{total_stages} FAILED: {stage_name} - {error}")
    print(f"Stage {stage_num}/{total_stages} FAILED: {stage_name} - {error}")
    if blocking:
        logger.error(f"Blocking failure - workflow will exit")
        print(f"Blocking failure - workflow will exit")


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

    TOTAL_STAGES = 8
    post_id = None
    published_url = None

    try:
        # --- STAGE 1: Generate Content Blueprint ---
        log_stage_start(1, TOTAL_STAGES, "Generating Content Blueprint")
        blueprint = generator.generate_informational_blueprint(topic, keyword, category)
        log_stage_pass(1, TOTAL_STAGES, "Content Blueprint", f"Blueprint length: {len(blueprint)} chars")

        # --- STAGE 2: Generate Article with Image Markers (Call 1) ---
        log_stage_start(2, TOTAL_STAGES, "Generating Informational Article with Markers")
        article_with_markers = generator.generate_informational_article(blueprint, topic, keyword, category)
        log_stage_pass(2, TOTAL_STAGES, "Article Generation", f"Article length: {len(article_with_markers)} chars")

        # --- STAGE 2.5: Monetization Validation (Publish Gate) ---
        log_stage_start(2.5, TOTAL_STAGES, "Validating Monetization Structure")
        validation_passed, validation_details = generator.validate_monetization_structure(
            article_with_markers, category, topic
        )

        if not validation_passed:
            log_stage_fail(2.5, TOTAL_STAGES, "Monetization Validation", f"Details: {validation_details}", blocking=True)
            sheets.update_row_status(row_index, "Needs Review", error=f"Monetization validation failed: {validation_details}")
            notifier.send_report("Article Needs Review - Monetization", topic, 
                                f"Auto-publish blocked. Missing monetization elements:\n{json.dumps(validation_details, indent=2)}")
            print(f"VALIDATION FAILED - Article flagged for manual review")
            print(f"Details: {validation_details}")
            sys.exit(0)

        log_stage_pass(2.5, TOTAL_STAGES, "Monetization Validation", f"Named products: {validation_details.get('named_product_count', 0)}")

        # --- STAGE 3: Publish FIRST as DRAFT to get Blogger Post ID ---
        log_stage_start(3, TOTAL_STAGES, "Publishing to Blogger as draft (get Post ID)")
        seo_labels = generator.generate_seo_tags(topic, keyword)
        if category not in seo_labels:
            seo_labels.append(category)
        
        published_url, post_id = publisher.publish_post_as_draft(topic, article_with_markers, labels=seo_labels)
        log_stage_pass(3, TOTAL_STAGES, "Draft Publish", f"Post ID: {post_id}, URL: {published_url}")
        print(f"Published as draft to Blogger: {published_url}")
        print(f"Post ID: {post_id}\n")

        # --- STAGE 4: Generate Images and UPDATE Blogger Post (Call 2 + 3) ---
        log_stage_start(4, TOTAL_STAGES, "Generating Images via HF and Updating Blogger")
        try:
            article_with_images, image_manifest = generator.generate_images_and_update_post(
                article_with_markers, post_id, topic, keyword, category, publisher
            )
            log_stage_pass(4, TOTAL_STAGES, "Image Generation", f"Images generated: {len(image_manifest)}")
        except Exception as e:
            log_stage_fail(4, TOTAL_STAGES, "Image Generation", str(e), blocking=True)
            raise

        # --- STAGE 5: Internal Linking ---
        log_stage_start(5, TOTAL_STAGES, "Generating Internal Links")
        try:
            link_manager.refresh_corpus()
            final_html = link_manager.link_informational_article(article_with_images, topic, category)
            log_stage_pass(5, TOTAL_STAGES, "Internal Linking", "Links injected and related section added")
        except Exception as e:
            log_stage_fail(5, TOTAL_STAGES, "Internal Linking", str(e), blocking=True)
            raise

        # --- STAGE 6: Update Blogger Post with Internal Links ---
        log_stage_start(6, TOTAL_STAGES, "Updating Blogger Post with Internal Links")
        try:
            publisher.update_post(post_id, {"content": final_html, "labels": seo_labels})
            log_stage_pass(6, TOTAL_STAGES, "Post Update", "Content updated with internal links")
        except Exception as e:
            log_stage_fail(6, TOTAL_STAGES, "Post Update", str(e), blocking=True)
            raise

        # --- STAGE 7: Google Sheets Updates ---
        log_stage_start(7, TOTAL_STAGES, "Updating Google Sheets")
        try:
            sheets.update_row_status(row_index, "Success", url=published_url, post_id=post_id)
            sheets.update_dashboard_stats("Success")
            sheets.log_execution(topic, "Success", url=published_url)
            log_stage_pass(7, TOTAL_STAGES, "Sheets Update", "Status, dashboard, and execution log updated")
        except Exception as e:
            log_stage_fail(7, TOTAL_STAGES, "Sheets Update", str(e), blocking=True)
            raise

        # --- STAGE 8: Publish the draft post ---
        log_stage_start(8, TOTAL_STAGES, "Publishing Draft Post to Live")
        try:
            publisher.publish_draft_post(post_id)
            log_stage_pass(8, TOTAL_STAGES, "Draft-to-Live", f"Post {post_id} now live")
        except Exception as e:
            log_stage_fail(8, TOTAL_STAGES, "Draft-to-Live", str(e), blocking=True)
            raise

        # --- SUCCESS: Send Email Notification ---
        success_message = f"Informational article published successfully.\n\nTopic: {topic}\nURL: {published_url}\nPost ID: {post_id}\nImages: {len(image_manifest)}"
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