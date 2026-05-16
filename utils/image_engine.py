import os
import requests
import hashlib
import logging
from PIL import Image
from io import BytesIO
from pathlib import Path
from slugify import slugify

logger = logging.getLogger("image_engine")

class ImageEngine:
    def __init__(self, github_user, github_repo, image_dir="assets/images"):
        self.github_user = github_user
        self.github_repo = github_repo
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # Base URL for GitHub Pages
        self.base_url = f"https://{github_user}.github.io/{github_repo}/{image_dir}"
        
        # Targets
        self.max_width = 1200
        self.quality = 85
        self.target_size_kb = 150

    def _get_hash(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def get_github_url(self, filename):
        """Constructs the public GitHub Pages URL for an image."""
        return f"{self.base_url}/{filename}"

    def download_and_optimize(self, url, title_keyword, category="general"):
        """
        Downloads, resizes, compresses, and converts to WebP.
        Saves to the local assets folder for GitHub Pages hosting.
        """
        image_hash = self._get_hash(url)
        safe_filename = slugify(title_keyword)[:50]
        
        # Organize by category if provided
        cat_dir = self.image_dir / slugify(category)
        cat_dir.mkdir(exist_ok=True)
        
        filename = f"{safe_filename}-{image_hash[:6]}.webp"
        local_path = cat_dir / filename
        
        # Relative path for URL construction
        rel_path = f"{slugify(category)}/{filename}"
        public_url = self.get_github_url(rel_path)

        # 1. Cache Check (Avoid re-processing if exists)
        if local_path.exists():
            logger.info(f"Using existing optimized image: {filename}")
            return public_url

        try:
            # 2. Download
            logger.info(f"Downloading image: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # 3. Open with Pillow
            img = Image.open(BytesIO(response.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 4. Resize
            width, height = img.size
            if width > self.max_width:
                ratio = self.max_width / float(width)
                new_height = int(float(height) * float(ratio))
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)

            # 5. Save as WebP
            img.save(local_path, "WEBP", quality=self.quality, method=6)
            
            # 6. Final Size Check
            if local_path.stat().st_size > self.target_size_kb * 1024:
                img.save(local_path, "WEBP", quality=70, method=6)
                
            logger.info(f"Optimized image ready for GitHub: {rel_path} ({local_path.stat().st_size // 1024} KB)")
            return public_url

        except Exception as e:
            logger.error(f"Failed to optimize image {url}: {e}")
            return None
