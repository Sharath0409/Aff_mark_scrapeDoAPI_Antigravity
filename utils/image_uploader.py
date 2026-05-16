import os
import logging
from google.cloud import storage
from config import settings

logger = logging.getLogger("blogger_cdn_uploader")

class BloggerCDNUploader:
    def __init__(self, service_account_path):
        """
        Uses Google Cloud Storage (GCS) for professional-grade image hosting.
        Replaces Google Drive to avoid Service Account quota limitations.
        """
        import json
        import base64
        
        try:
            # Determine if service_account_path is a path or base64 string
            if service_account_path.endswith('.json'):
                self.client = storage.Client.from_service_account_json(service_account_path)
            else:
                # Assume base64 encoded JSON string
                padding = len(service_account_path) % 4
                if padding > 0:
                    service_account_path += '=' * (4 - padding)
                creds_json = json.loads(base64.b64decode(service_account_path).decode('utf-8'))
                self.client = storage.Client.from_service_account_info(creds_json)
            
            logger.info("Google Cloud Storage (GCS) Bridge initialized.")
        except Exception as e:
            logger.error(f"Failed to load credentials for BloggerCDNUploader: {e}")
            raise

    def upload_to_google_cdn(self, file_path, bucket_name=None):
        """
        Uploads image to Google Cloud Storage and returns a public URL.
        """
        if not bucket_name:
            logger.error("No GCS_BUCKET_NAME provided in settings.")
            return None

        try:
            bucket = self.client.bucket(bucket_name)
            filename = os.path.basename(file_path)
            
            # Destination path in bucket (keeping it clean)
            blob = bucket.blob(f"blog-assets/{filename}")
            
            # Upload the file
            blob.upload_from_filename(file_path, content_type='image/webp')
            
            # The public URL format for GCS
            public_url = f"https://storage.googleapis.com/{bucket_name}/blog-assets/{filename}"
            
            logger.info(f"Image hosted on GCS CDN: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"GCS CDN upload failed: {e}")
            return None
