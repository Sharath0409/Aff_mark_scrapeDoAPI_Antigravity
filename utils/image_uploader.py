import os
import requests
import json
import logging
from config.logger import get_logger
from config import settings

logger = get_logger(__name__)

class ImageUploader:
    """Base class for image uploaders. Can be extended for Cloudinary, ImgBB, etc."""
    
    def upload(self, local_path):
        raise NotImplementedError("Subclasses must implement upload method.")

class CloudinaryUploader(ImageUploader):
    def __init__(self, cloud_name, api_key, api_secret):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.upload_url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/upload"

    def upload(self, local_path):
        """Upload to Cloudinary and return the secure URL."""
        if not local_path or not os.path.exists(local_path):
            return None
            
        try:
            logger.info(f"Uploading {local_path} to Cloudinary...")
            
            # Simple unsigned upload (requires an unsigned upload preset in Cloudinary)
            # or signed upload. For automation, signed is better.
            # Using a simplified approach here; in production, use 'cloudinary' python lib.
            
            # For this implementation, we assume the user might use the official lib or a simple POST.
            # To avoid extra dependencies, we use a simple POST if possible, 
            # but usually 'cloudinary' lib is better.
            
            # Since I added Pillow to requirements, I'll stick to requests for the API call.
            files = {'file': open(local_path, 'rb')}
            data = {
                'upload_preset': 'ml_default', # User needs to set this to 'Unsigned' in Cloudinary settings
                'api_key': self.api_key,
            }
            
            response = requests.post(self.upload_url, files=files, data=data)
            response.raise_for_status()
            
            res_json = response.json()
            secure_url = res_json.get('secure_url')
            
            logger.info(f"Upload successful: {secure_url}")
            return secure_url
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            return None

class ImgBBUploader(ImageUploader):
    """Easy alternative using ImgBB (Free, simple API)."""
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.imgbb.com/1/upload"

    def upload(self, local_path):
        if not local_path or not os.path.exists(local_path):
            return None
            
        try:
            logger.info(f"Uploading {local_path} to ImgBB...")
            with open(local_path, "rb") as file:
                payload = {
                    "key": self.api_key,
                    "image": base64.b64encode(file.read()),
                }
                res = requests.post(self.url, payload)
                res.raise_for_status()
                url = res.json()["data"]["url"]
                logger.info(f"Upload successful: {url}")
                return url
        except Exception as e:
            logger.error(f"ImgBB upload failed: {e}")
            return None
