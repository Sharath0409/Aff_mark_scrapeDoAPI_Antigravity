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
    def __init__(self, cache_dir="image_cache", output_dir="temp_optimized"):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Targets
        self.max_width = 1200
        self.quality = 85
        self.target_size_kb = 150

    def _get_hash(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def download_and_optimize(self, url, title_keyword):
        """
        Downloads, resizes, compresses, and converts an image to WebP locally.
        Returns the path to the optimized local file.
        """
        image_hash = self._get_hash(url)
        safe_filename = slugify(title_keyword)[:50]
        output_path = self.output_dir / f"{safe_filename}-{image_hash[:6]}.webp"

        # 1. Cache Check
        if output_path.exists():
            logger.info(f"Using cached optimized image: {output_path.name}")
            return str(output_path)

        try:
            # 2. Download
            logger.info(f"Downloading image from: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # 3. Open with Pillow
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary (handles PNG/RGBA)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 4. Intelligent Resize
            width, height = img.size
            if width > self.max_width:
                ratio = self.max_width / float(width)
                new_height = int(float(height) * float(ratio))
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized from {width}px to {self.max_width}px")

            # 5. Optimize & Save as WebP
            # Iterative compression to meet target size
            quality = self.quality
            img.save(output_path, "WEBP", quality=quality, method=6) # method 6 is slowest/best compression
            
            # Check size and reduce quality if still too big
            if output_path.stat().st_size > self.target_size_kb * 1024:
                quality = 70
                img.save(output_path, "WEBP", quality=quality, method=6)
                
            logger.info(f"Optimized image saved: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to optimize image {url}: {e}")
            return None

    def cleanup_temp(self):
        """Removes temporary optimized files but keeps cache metadata if needed."""
        for file in self.output_dir.glob("*.webp"):
            try:
                file.unlink()
            except:
                pass
