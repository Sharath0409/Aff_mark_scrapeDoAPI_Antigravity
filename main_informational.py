import sys
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from core.content_generator import ContentGenerator
from core.blogger_publisher import BloggerPublisher
from core.internal_linker import InternalLinkManager

logger = get_logger("main_informational")

INFORMATIONAL_WORKSHEET = "Informational_Topics"


def main():
    logger.info("Starting Informational Publishing Workflow.")

    # Connect to the Informational_Topics worksheet.
    # SheetsManager already supports sheet_name as a constructor parameter,
    # so no changes to the existing commercial integration are required.
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

    # Mark the row as Processing using the existing SheetsManager method.
    # Reuses the same update_row_status() used by the commercial workflow.
    sheets.update_row_status(row["row_index"], "Processing")
    print("Status updated to Processing.\n")

    print(f"Topic:\n{topic}\n")
    print(f"Keyword:\n{keyword}\n")
    print(f"Category:\n{category}\n")

    # Generate the content blueprint using the shared ContentGenerator.
    # Reuses: existing OpenAI client, generate_section(), SYSTEM_PROMPT, retry decorator, logger.
    generator = ContentGenerator()
    blueprint = generator.generate_informational_blueprint(topic, keyword, category)

    print("--- Content Blueprint ---\n")
    print(blueprint)
    print("\n-------------------------")

    # Generate the complete informational article based on the blueprint.
    # Reuses: existing OpenAI client, generate_section(), SYSTEM_PROMPT, retry decorator, logger.
    article = generator.generate_informational_article(blueprint, topic, keyword, category)

    print("\n--- Generated Informational Article ---\n")
    print(article)
    print("\n---------------------------------------")

    # Generate the structured image plan based on the blueprint and article.
    # Reuses: existing OpenAI client, generate_section(), SYSTEM_PROMPT, retry decorator, logger.
    image_plan = generator.generate_image_plan(blueprint, article, topic, keyword, category)

    print("\n--- Generated Image Plan ---\n")
    print(image_plan)
    print("\n----------------------------")

    # Generate, optimize, and upload images based on the image plan.
    image_manifest = generator.generate_article_images(image_plan, topic)

    print("\n--- Image Manifest ---\n")
    for img in image_manifest:
        print(f"Image {img['image_number']}")
        print(f"Placement: {img['placement']}")
        print(f"Reference Heading: {img['reference_heading']}")
        print(f"CDN URL: {img['cdn_url']}")
        print(f"Alt Text: {img['alt_text']}")
        print(f"Caption: {img['caption']}")
        print("-" * 60)
    print("\n----------------------")

    # Assemble the final HTML by injecting images into the article
    final_html = generator.inject_images_into_article(article, image_manifest)

    print("\n--- Final Assembled HTML Article ---\n")
    print(final_html)
    print("\n------------------------------------")

    print("\nWorkflow completed successfully.")


if __name__ == "__main__":
    main()
