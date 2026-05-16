import os
import requests
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import settings

logger = logging.getLogger("blogger_cdn_uploader")

class BloggerCDNUploader:
    def __init__(self, service_account_path):
        """
        Uses Google Photos API / Google infrastructure to host images.
        Note: The simplest production-grade way to get 'googleusercontent.com' URLs 
        without complex Photos OAuth is to use the Google Drive 'webContentLink' 
        pattern or a public Google Cloud bucket. 
        
        HOWEVER, for pure Blogger-Native style, we'll use a logic that 
        uploads to Google Drive and converts to a direct Google CDN proxy URL 
        which is functionally identical to the Blogger native hosting.
        """
        from google.oauth2.service_account import Credentials
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.creds = Credentials.from_service_account_file(service_account_path, scopes=self.scopes)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        logger.info("Google Drive CDN Bridge initialized.")

    def upload_to_google_cdn(self, file_path):
        """
        Uploads image to Google infrastructure and returns a direct CDN URL.
        """
        try:
            filename = os.path.basename(file_path)
            file_metadata = {'name': filename}
            media = MediaFileUpload(file_path, mimetype='image/webp', resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            # Make the file public so it can be served
            self.drive_service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # Construct a direct Google CDN-style URL (Proxying through Google's infrastructure)
            # This URL format is extremely fast and serves as a 'googleusercontent' style link.
            direct_url = f"https://lh3.googleusercontent.com/u/0/d/{file_id}"
            
            logger.info(f"Image hosted on Google CDN: {direct_url}")
            return direct_url

        except Exception as e:
            logger.error(f"Google CDN upload failed: {e}")
            return None
