import cloudinary
import cloudinary.uploader
import logging
import os

logger = logging.getLogger("uploader")

class CloudinaryUploader:
    def __init__(self, cloud_name, api_key, api_secret):
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        logger.info("Cloudinary Uploader initialized.")

    def upload(self, file_path, folder="affiliate_blog"):
        """
        Uploads a local file to Cloudinary and returns the secure URL.
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found for upload: {file_path}")
                return None

            response = cloudinary.uploader.upload(
                file_path,
                folder=folder,
                use_filename=True,
                unique_filename=True,
                resource_type="image"
            )
            
            secure_url = response.get("secure_url")
            logger.info(f"Successfully uploaded to Cloudinary: {secure_url}")
            return secure_url

        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            return None
