import os
import requests
import hashlib
import logging
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from pathlib import Path
from slugify import slugify

logger = logging.getLogger("image_optimizer")

class ImageOptimizer:
    def __init__(self, temp_dir="temp_processing"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Targets
        self.max_width = 800
        self.min_enhance_width = 800
        self.target_size_kb = 150

    def _get_hash(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def analyze_and_enhance(self, img_pil):
        """
        Analyzes image quality and applies lightweight enhancement if needed.
        """
        width, height = img_pil.size
        needs_enhancement = False
        
        # 1. Check if resolution is low
        if width < self.min_enhance_width:
            logger.info(f"Image width ({width}px) is below threshold. Triggering enhancement.")
            needs_enhancement = True

        if needs_enhancement:
            # A. Sharpening
            img_pil = img_pil.filter(ImageFilter.SHARPEN)
            
            # B. Contrast Enhancement
            enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = enhancer.enhance(1.2)
            
            # C. Color/Clarity
            enhancer = ImageEnhance.Color(img_pil)
            img_pil = enhancer.enhance(1.1)
            
            logger.info("Applied lightweight sharpening and contrast enhancement.")
        
        return img_pil

    def process_from_url(self, url, title_keyword):
        """
        Main pipeline: Download -> Enhance -> Optimize -> WebP
        Returns: (str: output_path, int: width, int: height)
        """
        image_hash = self._get_hash(url)
        safe_name = slugify(title_keyword)[:50]
        output_filename = f"{safe_name}-{image_hash[:6]}.webp"
        output_path = self.temp_dir / output_filename

        try:
            # 1. Download
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 2. Analyze & Enhance
            img = self.analyze_and_enhance(img)

            # 3. Intelligent Resize (Maintain Aspect Ratio)
            width, height = img.size
            if width > self.max_width:
                ratio = self.max_width / float(width)
                new_height = int(float(height) * float(ratio))
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                width, height = img.size
                logger.info(f"Resized to {width}px wide.")

            # 4. Convert to WebP & Compress
            img.save(output_path, "WEBP", quality=85, method=6)
            
            # Check size and re-compress if needed
            if output_path.stat().st_size > self.target_size_kb * 1024:
                img.save(output_path, "WEBP", quality=70, method=6)
                
            logger.info(f"Image optimized locally: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
            return str(output_path), width, height

        except Exception as e:
            logger.error(f"Failed to process image {url}: {e}")
            return None, 0, 0

    def cleanup(self):
        """Purge all temporary files."""
        for file in self.temp_dir.glob("*"):
            try:
                file.unlink()
            except:
                pass
        logger.info("Cleanup of temporary image files complete.")
