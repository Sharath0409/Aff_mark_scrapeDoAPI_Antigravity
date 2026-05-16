import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCRAPE_DO_TOKEN = os.getenv("SCRAPE_DO_TOKEN")
AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG")
GCP_SERVICE_ACCOUNT = os.getenv("GCP_SERVICE_ACCOUNT")
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
BLOGGER_CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# Validation
REQUIRED_SETTINGS = [
    "OPENAI_API_KEY", "SCRAPE_DO_TOKEN", "AMAZON_AFFILIATE_TAG", 
    "GOOGLE_SHEET_ID", "BLOGGER_BLOG_ID", "GCS_BUCKET_NAME"
]

for setting in REQUIRED_SETTINGS:
    if not globals().get(setting):
        print(f"WARNING: Missing required environment variable: {setting}")
