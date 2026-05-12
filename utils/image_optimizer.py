import os
import requests
import re
from PIL import Image
from io import BytesIO
from config.logger import get_logger

logger = get_logger(__name__)

class ImageOptimizer:
    def __init__(self, output_dir="temp_images", quality=80, max_width=1000):
        self.output_dir = output_dir
        self.quality = quality
        self.max_width = max_width
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created temporary image directory: {self.output_dir}")

    def normalize_filename(self, text):
        """Convert product title to SEO-friendly slug."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text).strip('-')
        return text[:50] # Keep it reasonably short

    def optimize_from_url(self, url, product_title):
        """
        Downloads, resizes, compresses, and converts to WebP.
        Returns the local path of the optimized image.
        """
        if not url:
            return None
            
        try:
            logger.info(f"Downloading image for optimization: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Open with Pillow
            img = Image.open(BytesIO(response.content))
            
            # Handle Color Mode (ensure RGB for WebP/JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Smart Resize (Preserve Aspect Ratio)
            w, h = img.size
            if w > self.max_width:
                ratio = self.max_width / float(w)
                new_h = int(float(h) * float(ratio))
                img = img.resize((self.max_width, new_h), Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {w}x{h} to {self.max_width}x{new_h}")

            # Generate SEO-friendly filename
            clean_name = self.normalize_filename(product_title)
            output_filename = f"{clean_name}.webp"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Save as WebP
            img.save(output_path, "WEBP", quality=self.quality, method=6)
            
            orig_size = len(response.content) / 1024
            opt_size = os.path.getsize(output_path) / 1024
            
            logger.info(f"Image Optimized: {output_filename} ({orig_size:.1f}KB -> {opt_size:.1f}KB)")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to optimize image from {url}: {e}")
            return None

    def cleanup(self):
        """Remove temp images after the post is published."""
        try:
            for f in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, f))
            logger.info("Cleaned up temporary optimized images.")
        except Exception as e:
            logger.error(f"Error during image cleanup: {e}")
