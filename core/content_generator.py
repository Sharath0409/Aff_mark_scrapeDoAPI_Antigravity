from core.deepseek_client import DeepseekHttpClient
from config.logger import get_logger
from config import settings
from utils.retry import get_retry_decorator
from templates.prompts import (
    SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE,
    COMPARISON_TEMPLATE, FAQ_TEMPLATE, SEO_TAGS_TEMPLATE,
    QUICK_SUMMARY_TEMPLATE, CONCLUSION_TEMPLATE,
    REVIEWS_HEADER_TEMPLATE, INFORMATIONAL_BLUEPRINT_TEMPLATE,
    INFORMATIONAL_ARTICLE_TEMPLATE, INFORMATIONAL_IMAGE_PROMPT_PLAN_TEMPLATE,
    LONG_TAIL_HEADING_VARIANTS_PROMPT
)
from utils.text_cleaner import sanitize_html
import re
import json
import time
import tempfile
import math
import io
from bs4 import BeautifulSoup
from utils.image_optimizer import ImageOptimizer
from utils.image_uploader import BloggerCDNUploader
from core.author_signals import generate_author_signals, DEFAULT_AUTHOR, DEFAULT_METHODOLOGY
from core.detemplater import detemplate_article, SectionVariator
from core.schema_generator import SchemaGenerator, generate_product_schemas
from core.cannibalization_checker import CannibalizationChecker

# HF InferenceClient for image generation and CLIP embeddings
try:
    from huggingface_hub import InferenceClient
    from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError
except ImportError:
    InferenceClient = None
    HfHubHTTPError = None
    InferenceTimeoutError = None

logger = get_logger(__name__)

# Banned negation words (case-insensitive check)
NEGATION_WORDS = [
    "free", "without", "no", "not", "clutter-free", "clutter free",
    "devoid of", "lacking", "absent", "exclude", "excluding",
    "never", "none", "nothing", "nowhere", "neither", "nor"
]

STYLE_SUFFIX = ", clean flat-style technical illustration, labeled, high clarity, white background"
MAX_PROMPT_WORDS = 150

# CLIP Configuration for image-text relevance verification
# PLACEHOLDER THRESHOLD - REQUIRES CALIBRATION AGAINST REAL OUTPUT BEFORE PRODUCTION USE
CLIP_MODEL_NAME = getattr(settings, "CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
CLIP_SIMILARITY_THRESHOLD = getattr(settings, "CLIP_SIMILARITY_THRESHOLD", 0.25)
CLIP_MAX_RETRIES = 1  # One retry on low score

class ContentGenerator:
    def __init__(self):
        self.client = DeepseekHttpClient(api_key=settings.DEEPSEEK_API_KEY) if settings.DEEPSEEK_API_KEY else None
        self.schema_generator = SchemaGenerator()
        self.section_variator = SectionVariator()
        self.cannibalization_checker = CannibalizationChecker()

    @get_retry_decorator()
    def generate_section(self, prompt: str, model: str = "deepseek-v4-flash") -> str:
        """Call Deepseek API to generate a content section."""
        if not self.client:
            logger.error("Deepseek client not initialized - API key missing")
            return "<p>Content generation skipped because no Deepseek API key is configured.</p>"
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            
            # Deepseek sometimes wraps HTML in markdown blocks, let's clean it
            if content.startswith("```html"):
                content = content.replace("```html", "").replace("```", "")
            
            return sanitize_html(content)
        except Exception as e:
            logger.error(f"Error calling Deepseek API: {e}")
            raise

    def _apply_quality_corrections(self, html, topic, keyword):
        """Clean generated HTML so it stays topic-focused, US-focused, and EEAT-safe."""
        if not html:
            return html

        soup = BeautifulSoup(html, "html.parser")
        topic_text = f"{topic} {keyword}".strip()
        topic_lower = topic_text.lower()

        placeholder_patterns = [
            r"\bxyz\s+product\b",
            r"\babc\s+chair\b",
            r"\bsample\s+product\b",
            r"\blorem\s+ipsum\b",
            r"\bexample\s+product\b",
            r"\bdummy\s+specifications\b",
            r"\bgeneric\s+premium\s+choice\b",
            r"\btravel\s+chair\b",
        ]
        ai_phrase_replacements = [
            (r"\bi\s+tested\s+this\b", "Based on manufacturer specifications, verified customer feedback, and industry best practices"),
            (r"\bi've\s+used\s+this\b", "Based on manufacturer specifications, verified customer feedback, and industry best practices"),
            (r"\bmy\s+experience\b", "Verified customer feedback"),
            (r"\bmy\s+week\s+of\s+testing\b", "verified customer feedback and industry best practices"),
            (r"\bi\s+personally\s+recommend\b", "This guide recommends"),
            (r"\bin\s+my\s+week\s+of\s+testing\b", "based on verified customer feedback and industry best practices"),
        ]
        unrelated_patterns = [
            r"\bwebcam\s+comparison\b",
            r"\bchair\s+recommendation\b",
            r"\bkeyboard\s+buying\s+guide\b",
            r"\bstanding\s+desk\s+advice\b",
            r"\bmouse\s+recommendation\b",
            r"\bnas\s+recommendation\b",
        ]

        human_phrases = [
            (r"\bin\s+today's\s+fast-paced\s+world\b", "For many US remote workers"),
            (r"\bwhen\s+it\s+comes\s+to\b", "with"),
            (r"\bit\s+is\s+important\s+to\s+note\b", "remember"),
            (r"\bthis\s+guide\s+will\s+show\s+you\b", "this article explains"),
            (r"\bone\s+of\s+the\s+best\s+options\b", "a strong choice"),
            (r"\busers\s+can\b", "you can"),
            (r"\bfor\s+remote\s+workers\b", "for US remote workers"),
            (r"\bin\s+the\s+us\b", "for the US"),
            (r"\bamerican\s+office\b", "US home office"),
        ]

        for text_node in soup.find_all(string=True):
            if text_node.parent and text_node.parent.name in {"script", "style"}:
                continue

            original = str(text_node)
            updated = original
            for pattern in placeholder_patterns:
                updated = re.sub(pattern, "the featured option", updated, flags=re.IGNORECASE)
            for pattern, replacement in ai_phrase_replacements + human_phrases:
                updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
            if re.search(r"\b(xyz|abc|sample|lorem|example|dummy|generic)\b", updated, flags=re.IGNORECASE):
                updated = re.sub(r"\b(xyz|abc|sample|lorem|example|dummy|generic)\b", "the featured option", updated, flags=re.IGNORECASE)
            if any(re.search(pattern, updated, flags=re.IGNORECASE) for pattern in unrelated_patterns):
                updated = ""

            if updated != original:
                text_node.replace_with(updated)

        def is_empty_removable_tag(tag):
            if tag.name in {"img", "br", "hr", "input", "meta", "link", "source", "track", "wbr", "area"}:
                return False
            if tag.get_text(" ", strip=True):
                return False
            if tag.find(["img", "iframe", "video", "audio", "picture", "svg"]):
                return False
            return True

        for tag in soup.find_all(True):
            if is_empty_removable_tag(tag):
                tag.decompose()

        if not soup.find(["h1", "h2", "p"]):
            wrapper = soup.new_tag("p")
            wrapper.string = f"This guide focuses on {topic} and helps US readers make an informed, practical decision."
            soup.append(wrapper)

        intro_target = soup.find(["h1", "h2", "p"])
        if intro_target and topic_lower and topic_lower not in intro_target.get_text(" ", strip=True).lower():
            if not intro_target.find("strong"):
                topic_sentence = soup.new_tag("p")
                topic_sentence.string = f"This article is focused on {topic} and is written for US readers looking for practical, topic-specific guidance."
                intro_target.insert_after(topic_sentence)

        text_content = " ".join([tag.get_text(" ", strip=True) for tag in soup.find_all(["p", "li", "h2", "h3"])])
        if "united states" not in text_content.lower() and "us " not in text_content.lower() and "u.s." not in text_content.lower():
            us_note = soup.new_tag("p")
            us_note.string = "This article is tailored for US buyers and home office setups, with practical advice for American remote work and workplace environments."
            if intro_target is not None:
                intro_target.insert_after(us_note)
            else:
                soup.insert(0, us_note)

        if "verified product specifications" not in text_content.lower() and "customer feedback" not in text_content.lower():
            eeat_note = soup.new_tag("p")
            eeat_note.string = "The review is based on verified product specifications, customer feedback, and workplace best practices to provide trustworthy guidance."
            if intro_target is not None:
                intro_target.insert_after(eeat_note)
            else:
                soup.insert(0, eeat_note)

        if any(term in topic_lower for term in ["ergonomic", "chair", "desk", "standing desk", "keyboard", "mouse", "monitor", "lighting", "workstation", "workspace", "office furniture"]):
            if "osha" not in text_content.lower() and "neutral wrist" not in text_content.lower():
                anchor = soup.find("p") or soup.find("h2") or soup.find("h3")
                if anchor is not None:
                    safety_note = soup.new_tag("p")
                    safety_note.string = "For US work setups, OSHA-aligned ergonomic guidance favors neutral wrist positioning, a monitor at roughly eye level, and a setup that reduces repetitive strain while supporting balanced sitting and standing habits."
                    anchor.insert_after(safety_note)

        # Evergreen validation: Remove marketing-style years while preserving factual years
        self._remove_marketing_years(soup, topic)

        return str(soup).strip()

    def _remove_marketing_years(self, soup: BeautifulSoup, topic: str):
        """Remove marketing-style years from content while preserving factual years.
        
        Factual years to PRESERVE:
        - OSHA guidance updates (e.g., "OSHA updated guidance in 2024")
        - Product release years (e.g., "released in 2025")
        - Version numbers (e.g., "Windows 11 24H2", "23H2")
        
        Marketing years to REMOVE:
        - "Best of 2024", "2025 Guide", "for 2024", "in 2025"
        - "Updated for 2024", "2024 Review", "Top Picks 2025"
        - Any year used for marketing freshness rather than factual accuracy
        """
        import re
        
        # Pattern to match years 2020-2099
        year_pattern = re.compile(r'\b(20\d{2})\b')
        
        # Factual year context patterns that should be preserved
        factual_contexts = [
            r'OSHA.*?(?:updated|guidance|standard).*?\b20\d{2}\b',
            r'\b20\d{2}\b.*?OSHA.*?(?:updated|guidance|standard)',
            r'(?:released|launched|introduced|announced).*?\b20\d{2}\b',
            r'\b20\d{2}\b.*?(?:released|launched|introduced|announced)',
            r'Windows\s+\d+\s+\d{2}H\d',  # Windows 11 24H2
            r'version\s+\d{2}H\d',  # version 24H2
            r'\b20\d{2}\s*(?:version|release|model)',  # 2024 version
            r'(?:firmware|driver|software)\s+\d{4}',  # firmware 2024
        ]
        
        for text_node in soup.find_all(string=True):
            if text_node.parent and text_node.parent.name in {"script", "style"}:
                continue
            
            original = str(text_node)
            updated = original
            
            # Check if this text contains any factual year contexts
            has_factual_context = False
            for pattern in factual_contexts:
                if re.search(pattern, original, re.IGNORECASE):
                    has_factual_context = True
                    break
            
            if not has_factual_context:
                # Remove marketing-style years
                # Pattern: "Best of 2024", "2025 Guide", "for 2024", "in 2025", "Updated for 2024", "2024 Review", "Top Picks 2025"
                marketing_year_patterns = [
                    r'\b(?:Best|Top|Updated|Review|Guide|Picks?)\s+(?:of\s+|for\s+|in\s+)?(20\d{2})\b',
                    r'\b(20\d{2})\s+(?:Guide|Review|Update|Edition|Version)\b',
                    r'\b(?:for|in)\s+(20\d{2})\b',  # "for 2024", "in 2025"
                    r'\b(?:Updated|Refreshed)\s+(?:for|in)\s+(20\d{2})\b',
                    r'\b(20\d{2})\s*(?:Edition|Update)\b',
                ]
                
                for pattern in marketing_year_patterns:
                    updated = re.sub(pattern, '', updated, flags=re.IGNORECASE)
                
                # Clean up any double spaces left by removals
                updated = re.sub(r'\s+', ' ', updated).strip()
            
            if updated != original:
                text_node.replace_with(updated)
        
    def validate_image_prompt(self, prompt: str, marker_id: str) -> tuple[str, bool]:
        """
        Check prompt for negation words and token budget.
        Returns: (sanitized_prompt, was_corrected)
        """
        was_corrected = False
        sanitized = prompt
        
        # 1. Negation word check - remove the negation word and any attached punctuation/dash
        lower = sanitized.lower()
        for neg in NEGATION_WORDS:
            if neg in lower:
                # Find and remove the specific negation word with word boundaries
                # Also handle compound words like "clutter-free" -> remove "free" part
                pattern = re.compile(r'\b' + re.escape(neg) + r'(?:-\w+)?\b', re.IGNORECASE)
                if pattern.search(sanitized):
                    sanitized = pattern.sub('', sanitized)
                    was_corrected = True
                    logger.warning(f"[{marker_id}] Negation word '{neg}' detected. Sanitized: '{prompt}' -> '{sanitized}'")
        
        # Clean up any double spaces or orphaned punctuation from removal
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        sanitized = re.sub(r'\s+([.,!?])', r'\1', sanitized)  # fix spacing before punctuation
        sanitized = re.sub(r'-\s*', '-', sanitized)  # fix trailing dashes
        sanitized = re.sub(r'\s+-', '', sanitized)  # remove leading dashes
        
        # If sanitization left us with nothing or very little, use a fallback
        if len(sanitized.split()) < 10:
            logger.warning(f"[{marker_id}] Prompt too short after sanitization ({len(sanitized.split())} words), using fallback")
            sanitized = "Professional workspace setup with relevant equipment, organized layout, natural lighting"
            was_corrected = True
        
        # 2. Word budget (rough token estimate)
        word_count = len(sanitized.split())
        if word_count > MAX_PROMPT_WORDS:
            # Truncate to last complete sentence within budget
            sentences = re.split(r'(?<=[.!?])\s+', sanitized)
            truncated = []
            count = 0
            for s in sentences:
                if count + len(s.split()) > MAX_PROMPT_WORDS:
                    break
                truncated.append(s)
                count += len(s.split())
            if truncated:
                sanitized = " ".join(truncated)
                was_corrected = True
                logger.warning(f"[{marker_id}] Prompt exceeded {MAX_PROMPT_WORDS} words. Truncated: '{prompt}' -> '{sanitized}'")
        
        return sanitized.strip(), was_corrected


    @get_retry_decorator()
    def get_clip_embeddings(self, image_bytes: bytes = None, text: str = None) -> list:
        """
        Get CLIP embeddings from Hugging Face InferenceClient.
        Provide either image_bytes OR text (not both).
        Returns embedding vector as list of floats.
        
        Note: Currently only text embeddings are supported via hf-inference provider.
        For image embeddings, we fall back to using the text prompt as a proxy.
        """
        if InferenceClient is None:
            raise RuntimeError("huggingface_hub package not installed. Install with: pip install huggingface_hub")
        
        # Use hf-inference provider for text embeddings (only provider that works for feature-extraction)
        client = InferenceClient(provider="hf-inference", api_key=settings.HF_API_TOKEN)
        
        try:
            # For image embeddings, fall back to using the text prompt as proxy
            # since no provider currently supports multimodal feature-extraction
            if image_bytes is not None and text is not None:
                # Use text as proxy for image embedding
                logger.info("Using text prompt as proxy for image embedding (multimodal not supported)")
                embeddings = client.feature_extraction(text, model=CLIP_MODEL_NAME)
            elif image_bytes is not None:
                # No text provided, use a generic description
                logger.warning("Image embeddings not supported, using generic description as proxy")
                embeddings = client.feature_extraction("A professional workspace setup with relevant equipment", model=CLIP_MODEL_NAME)
            elif text is not None:
                embeddings = client.feature_extraction(text, model=CLIP_MODEL_NAME)
            else:
                raise ValueError("Must provide either image_bytes or text")
            
            # feature_extraction returns a list of embeddings (for batched input)
            # We want the first (and only) embedding
            if isinstance(embeddings, list) and len(embeddings) > 0:
                if isinstance(embeddings[0], list):
                    return embeddings[0]
            return embeddings
            
        except InferenceTimeoutError as e:
            logger.warning(f"CLIP Inference timeout: {e}. Retrying...")
            raise Exception("Inference timeout - retry")
        except HfHubHTTPError as e:
            status = e.response.status_code if e.response is not None else "N/A"
            response_text = e.response.text if e.response is not None else "N/A"
            logger.error(f"CLIP Inference HTTP error: status={status}, response={response_text}, model={CLIP_MODEL_NAME}, provider=hf-inference")
            if e.response is not None and e.response.status_code == 503:
                # Cold start
                try:
                    data = e.response.json()
                    wait_time = data.get("estimated_time", 20)
                    logger.info(f"CLIP model loading, waiting {wait_time}s")
                    time.sleep(wait_time)
                    raise Exception("Model loading - retry")
                except:
                    time.sleep(20)
                    raise Exception("Model loading - retry")
            raise


    def cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Compute cosine similarity between two vectors."""
        import numpy as np
        # Convert to numpy arrays if needed
        v1 = np.array(vec1) if not isinstance(vec1, np.ndarray) else vec1
        v2 = np.array(vec2) if not isinstance(vec2, np.ndarray) else vec2
        
        if v1.size == 0 or v2.size == 0 or v1.shape != v2.shape:
            return 0.0
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))


    def verify_image_relevance(self, image_bytes: bytes, prompt_text: str, section_text: str, marker_id: str) -> tuple[float, float, bool]:
        """
        CALL 4: Verify image relevance using CLIP embeddings.
        
        Computes:
        1. prompt_similarity: cosine similarity between image and prompt_text embeddings
        2. section_similarity: cosine similarity between image and section_text embeddings
        
        Returns: (prompt_similarity, section_similarity, passed)
        """
        try:
            # Get embeddings
            image_emb = self.get_clip_embeddings(image_bytes=image_bytes)
            prompt_emb = self.get_clip_embeddings(text=prompt_text)
            section_emb = self.get_clip_embeddings(text=section_text)
            
            if not image_emb or not prompt_emb or not section_emb:
                logger.warning(f"[{marker_id}] Failed to get CLIP embeddings")
                return 0.0, 0.0, False
            
            # Compute similarities
            prompt_sim = self.cosine_similarity(image_emb, prompt_emb)
            section_sim = self.cosine_similarity(image_emb, section_emb)
            
            passed = prompt_sim >= CLIP_SIMILARITY_THRESHOLD and section_sim >= CLIP_SIMILARITY_THRESHOLD
            
            # Log both scores for calibration (mandatory)
            logger.info(
                f"[{marker_id}] CLIP scores: prompt_sim={prompt_sim:.4f}, "
                f"section_sim={section_sim:.4f}, threshold={CLIP_SIMILARITY_THRESHOLD}, "
                f"passed={passed}"
            )
            
            return prompt_sim, section_sim, passed
            
        except Exception as e:
            logger.error(f"[{marker_id}] CLIP verification failed: {e}")
            return 0.0, 0.0, False


    def validate_monetization_structure(self, html: str, category: str, topic: str) -> tuple[bool, dict]:
        """
        Validate that generated HTML contains required monetization structure for equipment/product posts.
        Returns: (passed, details_dict)
        
        Requirements:
        - Must have 5-7 specific named products with Amazon affiliate links, price ranges, and brief reasoning
        - Must have recommendations comparison table covering all 5-7 products
        - Must have real OSHA/NIOSH citations with actual URLs
        - Must have FAQ section
        - Every equipment/product mention must tie back to named products
        """
        from bs4 import BeautifulSoup
        import re
        
        # Configuration: 5-7 named products required
        MIN_NAMED_PRODUCTS_THRESHOLD = 5
        MAX_NAMED_PRODUCTS_THRESHOLD = 7
        
        # Equipment/product keywords - broader detection based on content, not just category
        equipment_keywords = [
            "chair", "desk", "monitor", "keyboard", "mouse", "webcam", "headset",
            "microphone", "lighting", "ergonomic", "standing desk", "monitor arm",
            "footrest", "laptop stand", "dock", "hub", "cable", "printer", "scanner",
            "webcam", "microphone", "headset", "speaker", "router", "modem", "nas",
            "hard drive", "ssd", "gpu", "cpu", "laptop", "tablet", "phone", "case",
            "stand", "mount", "arm", "mat", "pad", "wrist rest", "foot rest"
        ]
        
        # Check if content discusses equipment (not just category)
        text_lower = (topic + " " + category).lower()
        html_lower = html.lower()
        content_discusses_equipment = any(kw in text_lower for kw in equipment_keywords) or \
                                       any(kw in html_lower for kw in ["best ", "top ", "review", "buying guide", "vs ", "comparison"])
        
        if not content_discusses_equipment:
            return True, {"skipped": True, "reason": "Content does not discuss equipment/products"}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Count named product mentions with price ranges and Amazon links
        # Look for: "Product Name ($150–$200)" with affiliate link nearby
        product_patterns = [
            # Pattern 1: "Product Name ($150–$200)" with affiliate link
            r'[A-Z][a-zA-Z0-9\s\-\.]+?\s*\(?\s*\$?\d+\s*[–\-]\s*\$?\d+\s*\)?',
            # Pattern 2: "Product Name — $150" or "Product Name - $150"
            r'[A-Z][a-zA-Z0-9\s\-\.]+?\s*[—\-]\s*\$?\d+',
            # Pattern 3: "Product Name approx. $150"
            r'[A-Z][a-zA-Z0-9\s\-\.]+?\s+approx\.\s*\$?\d+',
            # Pattern 4: "Product Name around $150"
            r'[A-Z][a-zA-Z0-9\s\-\.]+?\s+around\s+\$?\d+',
            # Pattern 5: "Product Name $150–$200" (no parentheses)
            r'[A-Z][a-zA-Z0-9\s\-\.]+?\s+\$?\d+\s*[–\-]\s*\$?\d+',
            # Pattern 6: Table cell with product name and price
            r'<td[^>]*>\s*[A-Z][a-zA-Z0-9\s\-\.]+?\s*</td>\s*<td[^>]*>\s*\$?\d+',
        ]
        
        named_products = set()
        for pattern in product_patterns:
            matches = re.findall(pattern, html)
            for m in matches:
                clean = re.sub(r'\s*[\(—\-]\s*\$?\d+.*$', '', m).strip()
                clean = re.sub(r'\s+\$?\d+\s*[–\-].*$', '', clean).strip()
                clean = re.sub(r'^<td[^>]*>\s*|\s*</td>$', '', clean).strip()
                clean = clean.strip('.,;:')
                if len(clean) > 3:
                    named_products.add(clean)
        
        named_count = len(named_products)
        
        # 2. Check for recommendations comparison table (Budget/Mid-Range/Premium) covering 5-7 products
        has_rec_table = bool(soup.find('table')) and \
                        ('budget pick' in html_lower or 'mid-range pick' in html_lower or 'mid range pick' in html_lower or 'premium pick' in html_lower)
        
        # 3. Check for at least one real OSHA/NIOSH citation with actual URL (not just acronym)
        has_real_citation = False
        citation_patterns = [
            r'OSHA\s+Guidelines?\s*\(?https?://[^\s\)]+',
            r'CDC\s+Guidelines?\s*\(?https?://[^\s\)]+',
            r'NIOSH\s*\(?https?://[^\s\)]+',
            r'https?://(www\.)?osha\.gov/[^\s\)]+',
            r'https?://(www\.)?cdc\.gov/[^\s\)]+',
            r'https?://(www\.)?niosh\.gov/[^\s\)]+',
        ]
        for pattern in citation_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                has_real_citation = True
                break
        
        # 4. Check for FAQ section
        has_faq = bool(soup.find('h2', string=re.compile(r'Frequently Asked Questions|FAQ', re.I)))
        
        # 5. Check for Amazon affiliate links (rel="nofollow sponsored" or similar)
        has_affiliate_links = bool(re.search(r'rel=["\']nofollow sponsored["\']|amazon\.com.*tag=', html, re.IGNORECASE))
        
        # 6. Check that named products have price ranges (at least 5 products)
        products_with_prices = 0
        for product in named_products:
            # Check if this product name appears near a price
            product_escaped = re.escape(product)
            price_nearby = re.search(product_escaped + r'.{0,100}\$\d+', html)
            if price_nearby:
                products_with_prices += 1
        
        # 7. Check for comparison table with 5-7 product columns
        comparison_table_cols = 0
        table = soup.find('table')
        if table:
            thead = table.find('thead')
            if thead:
                th_elements = thead.find_all('th')
                # Subtract 1 for the attribute label column
                comparison_table_cols = max(0, len(th_elements) - 1)
        
        # LOG THRESHOLD FOR DEBUGGING
        logger.info(f"Monetization validation for '{topic}': named_count={named_count}, with_prices={products_with_prices}, "
                   f"threshold={MIN_NAMED_PRODUCTS_THRESHOLD}-{MAX_NAMED_PRODUCTS_THRESHOLD}, has_rec_table={has_rec_table}, "
                   f"has_citation={has_real_citation}, has_faq={has_faq}, has_affiliate={has_affiliate_links}, "
                   f"comparison_table_cols={comparison_table_cols}")
        
        # ALL conditions must pass
        passed = (
            named_count >= MIN_NAMED_PRODUCTS_THRESHOLD and
            named_count <= MAX_NAMED_PRODUCTS_THRESHOLD and
            products_with_prices >= MIN_NAMED_PRODUCTS_THRESHOLD and
            has_rec_table and
            has_real_citation and
            has_faq and
            has_affiliate_links and
            comparison_table_cols >= MIN_NAMED_PRODUCTS_THRESHOLD
        )
        
        details = {
            "passed": passed,
            "content_discusses_equipment": content_discusses_equipment,
            "named_product_count": named_count,
            "named_products_found": list(named_products),
            "products_with_price_ranges": products_with_prices,
            "has_recommendations_table": has_rec_table,
            "has_real_citation": has_real_citation,
            "has_faq_section": has_faq,
            "has_affiliate_links": has_affiliate_links,
            "comparison_table_columns": comparison_table_cols,
            "threshold_min": MIN_NAMED_PRODUCTS_THRESHOLD,
            "threshold_max": MAX_NAMED_PRODUCTS_THRESHOLD,
        }
        
        if not passed:
            logger.warning(f"Monetization validation FAILED for '{topic}': "
                          f"named_count={named_count} (need {MIN_NAMED_PRODUCTS_THRESHOLD}-{MAX_NAMED_PRODUCTS_THRESHOLD}), "
                          f"products_with_prices={products_with_prices} (need >={MIN_NAMED_PRODUCTS_THRESHOLD}), "
                          f"rec_table={has_rec_table}, citation={has_real_citation}, "
                          f"faq={has_faq}, affiliate={has_affiliate_links}, "
                          f"comparison_cols={comparison_table_cols} (need >={MIN_NAMED_PRODUCTS_THRESHOLD})")
        else:
            logger.info(f"Monetization validation PASSED for '{topic}': "
                       f"{named_count} named products, {products_with_prices} with prices, "
                       f"{comparison_table_cols} comparison table columns")
        
        return passed, details


    def extract_section_around_marker(self, article_html: str, marker_id: str) -> str:
        """
        Extract the text content (paragraphs) surrounding the [IMG-N] marker
        to use as section context for CLIP verification.
        """
        soup = BeautifulSoup(article_html, 'html.parser')
        full_text = soup.get_text()
        
        # Find marker position
        marker_pattern = f"[{marker_id}]"
        marker_pos = full_text.find(marker_pattern)
        if marker_pos == -1:
            return ""
        
        # Extract surrounding text (500 chars before and after)
        start = max(0, marker_pos - 500)
        end = min(len(full_text), marker_pos + 500)
        section_text = full_text[start:end].strip()
        
        # Clean up
        section_text = re.sub(r'\s+', ' ', section_text)
        return section_text

    def generate_image_via_hf(self, prompt: str) -> bytes:
        """Call HF InferenceClient for FLUX.1-schnell. Returns image bytes.
        
        Tries multiple providers in order of reliability. Surfaces real HTTP status 
        and error message from provider on failure.
        """
        if InferenceClient is None:
            raise RuntimeError("huggingface_hub package not installed. Install with: pip install huggingface_hub")
        
        providers_to_try = [
            ("fal-ai", "black-forest-labs/FLUX.1-schnell"),
            ("replicate", "black-forest-labs/FLUX.1-schnell"),
            ("together", "black-forest-labs/FLUX.1-schnell"),
            ("hyperbolic", "black-forest-labs/FLUX.1-schnell"),
            ("nebius", "black-forest-labs/FLUX.1-schnell"),
        ]
        
        last_error = None
        for provider, model in providers_to_try:
            client = InferenceClient(provider=provider, api_key=settings.HF_API_TOKEN)
            try:
                logger.info(f"Attempting image generation with provider={provider}, model={model}")
                image = client.text_to_image(
                    prompt,
                    model=model,
                    num_inference_steps=4,
                )
                
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                logger.info(f"Image generation succeeded with provider={provider}")
                return img_byte_arr.getvalue()
                
            except InferenceTimeoutError as e:
                logger.warning(f"HF Inference timeout with {provider}: {e}")
                last_error = e
                continue
            except HfHubHTTPError as e:
                status = e.response.status_code if e.response is not None else "N/A"
                response_text = e.response.text if e.response is not None else "N/A"
                logger.error(f"HF Inference HTTP error with {provider}: status={status}, response={response_text}")
                
                if status == 403:
                    logger.warning(f"Provider {provider} returned 403 (likely gated model or permission issue), trying next provider")
                    last_error = e
                    continue
                elif status == 404:
                    logger.warning(f"Provider {provider} returned 404 (model not available), trying next provider")
                    last_error = e
                    continue
                elif status == 503:
                    try:
                        data = e.response.json()
                        wait_time = data.get("estimated_time", 20)
                        logger.info(f"Model loading on {provider}, waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    except:
                        time.sleep(20)
                        continue
                else:
                    last_error = e
                    continue
            except Exception as e:
                logger.error(f"HF Inference error with {provider}: {type(e).__name__}: {e}")
                last_error = e
                continue
        
        raise RuntimeError(
            f"All image generation providers failed. Last error: {type(last_error).__name__}: {last_error}"
        )


    def generate_image_prompt_plan(self, article_html: str, topic: str, keyword: str, category: str) -> str:
        """CALL 2: Generate prompt plan from full article with markers. Returns JSON string."""
        logger.info(f"Generating image prompt plan for: {topic}")
        # Escape curly braces in article_html to prevent .format() from interpreting them as placeholders
        safe_article_html = article_html.replace("{", "{{").replace("}", "}}")
        prompt = INFORMATIONAL_IMAGE_PROMPT_PLAN_TEMPLATE.format(
            article_html=safe_article_html,
            topic=topic,
            keyword=keyword,
            category=category
        )
        return self.generate_section(prompt, model="deepseek-v4-flash")


    def generate_images_and_update_post(self, article_html: str, post_id: str, topic: str, 
                                         keyword: str, category: str, publisher) -> tuple[str, list]:
        """
        CALL 3 + CALL 4: Generate images via HF, verify with CLIP, upload to GCS with post_id path, update Blogger post.
        Returns final HTML with markers replaced by <img> tags and manifest list.
        """
        # Step 1: Generate prompt plan (Call 2)
        prompt_plan_json = self.generate_image_prompt_plan(article_html, topic, keyword, category)
        try:
            prompt_plan = json.loads(prompt_plan_json)  # {"IMG-1": "prompt", ...}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse image prompt plan JSON: {e}")
            logger.error(f"Raw response: {prompt_plan_json}")
            return article_html, []
        
        # Step 2: Validate each prompt
        validated_plan = {}
        for marker_id, prompt in prompt_plan.items():
            sanitized, corrected = self.validate_image_prompt(prompt, marker_id)
            final_prompt = sanitized + STYLE_SUFFIX
            validated_plan[marker_id] = final_prompt
        
        # Step 3: Generate images (Call 3) + Verify (Call 4) - sequential
        final_html = article_html
        uploader = BloggerCDNUploader(settings.GCP_SERVICE_ACCOUNT)
        optimizer = ImageOptimizer()
        manifest = []
        
        for marker_id, final_prompt in validated_plan.items():
            # Extract the validated prompt without style suffix for CLIP verification
            validated_prompt_no_suffix = final_prompt.replace(STYLE_SUFFIX, "")
            
            # Get section text around marker for CLIP section similarity check
            section_text = self.extract_section_around_marker(article_html, marker_id)
            
            # Track retry state
            image_accepted = False
            image_bytes = None
            prompt_sim = 0.0
            section_sim = 0.0
            retry_attempted = False
            
            # Allow up to 1 retry on low CLIP score
            for attempt in range(CLIP_MAX_RETRIES + 1):
                try:
                    # Generate image (Call 3)
                    image_bytes = self.generate_image_via_hf(final_prompt)
                    
                    # CALL 4: CLIP Verification
                    prompt_sim, section_sim, passed = self.verify_image_relevance(
                        image_bytes=image_bytes,
                        prompt_text=validated_prompt_no_suffix,
                        section_text=section_text,
                        marker_id=marker_id
                    )
                    prompt_sim = prompt_sim
                    section_sim = section_sim
                    
                    if passed:
                        image_accepted = True
                        break  # Accept image, exit retry loop
                    else:
                        # Log low score
                        logger.warning(
                            f"[{marker_id}] CLIP verification failed (attempt {attempt + 1}): "
                            f"prompt_sim={prompt_sim:.4f}, section_sim={section_sim:.4f}, "
                            f"threshold={CLIP_SIMILARITY_THRESHOLD}"
                        )
                        if attempt < CLIP_MAX_RETRIES:
                            retry_attempted = True
                            logger.info(f"[{marker_id}] Retrying image generation...")
                            continue  # Retry with same prompt
                        else:
                            # Max retries exhausted
                            break
                            
                except Exception as e:
                    logger.error(f"[{marker_id}] Error during generation/verification (attempt {attempt + 1}): {e}")
                    if attempt < CLIP_MAX_RETRIES:
                        retry_attempted = True
                        continue
                    else:
                        break
            
            # Process accepted image or handle rejection
            if image_accepted and image_bytes is not None:
                try:
                    # Save to temp file, optimize to WebP
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name
                    
                    webp_path, w, h = optimizer.process_from_path(tmp_path, topic)
                    
                    # Upload to GCS with post_id path
                    gcs_path = f"{post_id}/{marker_id}.webp"
                    cdn_url = uploader.upload_to_google_cdn(webp_path, bucket_name=settings.GCS_BUCKET_NAME, blob_name=gcs_path)
                    
                    if cdn_url:
                        # Replace marker with <img> tag
                        img_tag = f'<figure style="margin: 40px 0; text-align: center;"><img src="{cdn_url}" alt="{topic} - {marker_id}" width="{w}" height="{h}" loading="lazy" decoding="async" style="max-width: 100%; height: auto; border-radius: 8px;"><figcaption style="margin-top: 12px; font-size: 0.9em; color: #666; font-style: italic;">{marker_id} illustration</figcaption></figure>'
                        final_html = final_html.replace(f"[{marker_id}]", img_tag)
                        logger.info(f"Generated and inserted {marker_id} for post {post_id}")
                        
                        manifest.append({
                            "marker_id": marker_id,
                            "prompt": final_prompt,
                            "cdn_url": cdn_url,
                            "width": w,
                            "height": h,
                            "clip_prompt_similarity": round(prompt_sim, 4),
                            "clip_section_similarity": round(section_sim, 4),
                            "clip_retry": retry_attempted
                        })
                    else:
                        logger.error(f"GCS upload failed for {marker_id}")
                        final_html = final_html.replace(f"[{marker_id}]", f"<!-- Image {marker_id} failed -->")
                        
                except Exception as e:
                    logger.error(f"Image processing failed for {marker_id}: {e}")
                    final_html = final_html.replace(f"[{marker_id}]", f"<!-- Image {marker_id} failed: {str(e)[:100]} -->")
            else:
                # Image rejected after retries - skip but log as flagged-low-relevance
                logger.warning(
                    f"[{marker_id}] FLAGGED-LOW-RELEVANCE: prompt_sim={prompt_sim:.4f}, "
                    f"section_sim={section_sim:.4f}, threshold={CLIP_SIMILARITY_THRESHOLD}, "
                    f"retry={retry_attempted}, prompt='{validated_prompt_no_suffix[:100]}...'"
                )
                final_html = final_html.replace(f"[{marker_id}]", f"<!-- Image {marker_id} skipped: low CLIP relevance (prompt={prompt_sim:.2f}, section={section_sim:.2f}) -->")
                
                manifest.append({
                    "marker_id": marker_id,
                    "prompt": final_prompt,
                    "cdn_url": None,
                    "width": 0,
                    "height": 0,
                    "clip_prompt_similarity": round(prompt_sim, 4),
                    "clip_section_similarity": round(section_sim, 4),
                    "clip_retry": retry_attempted,
                    "flagged_low_relevance": True
                })
        
        optimizer.cleanup()
        return final_html, manifest

    def generate_full_post(self, topic: str, keyword: str, products: list) -> str:
        """Assemble the complete blog post with visual styling and all requested sections."""
        logger.info("Starting full post generation")
        
        # 0. CSS Styles for a modern, fluid editorial layout
        style_block = """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
            .blog-container { max-width: 850px; margin: 0 auto; padding: 10px; color: #333; line-height: 1.8; font-family: 'Inter', -apple-system, sans-serif; text-align: justify; hyphens: auto; }
            .section-divider { margin: 60px 0; border: none; border-top: 1px solid #eee; }
            .product-section { margin-bottom: 60px; padding-bottom: 40px; border-bottom: 1px solid #eee; }
            .product-section:last-of-type { border-bottom: none; }
            .product-title { color: #111; font-size: 2em; font-weight: 800; margin-bottom: 20px; line-height: 1.2; text-align: center; }
            h1, h2 { text-align: center; margin-top: 50px; }
            .product-image-centered { text-align: center; margin-bottom: 30px; }
            .product-image-centered img { max-width: 100%; height: auto; width: auto; border-radius: 8px; max-height: 400px; object-fit: contain; }
            .product-summary-full { margin-bottom: 30px; }
            .price-badge { display: inline-block; background: #fef3c7; color: #451a03; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9em; margin-bottom: 15px; }
            .verdict-box { background: #f9fafb; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; font-style: italic; }
            .pros-cons-grid { display: block; margin: 25px 0; }
            .pros-list { margin-bottom: 20px; }
            .pros-list h4 { color: #059669; margin-top: 0; }
            .cons-list h4 { color: #dc2626; margin-top: 0; }
            .buy-button-wrapper { text-align: center; margin-top: 40px; }
            .buy-btn { display: inline-block; background: #fbbf24; color: #000 !important; padding: 16px 40px; border-radius: 4px; text-decoration: none !important; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; border: 1px solid #d97706; transition: all 0.2s; }
            .comparison-table-wrapper { overflow-x: auto; margin: 48px 0; border: 1px solid #dde3ef; border-radius: 14px; box-shadow: 0 4px 24px rgba(59,130,246,0.08); background: #fff; }
            .comparison-table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 640px; font-family: inherit; }
            .comparison-table thead tr th { background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); color: #fff; font-weight: 800; font-size: 0.92em; letter-spacing: 0.04em; text-transform: uppercase; padding: 16px 18px; border-bottom: 3px solid #1d4ed8; text-align: center; }
            .comparison-table thead tr th:first-child { text-align: left; border-radius: 14px 0 0 0; min-width: 150px; background: linear-gradient(135deg, #0f2a4a 0%, #1e3a5f 100%); }
            .comparison-table thead tr th:last-child { border-radius: 0 14px 0 0; }
            .comparison-table tbody tr:nth-child(even) { background: #f1f5fb; }
            .comparison-table tbody tr:nth-child(odd) { background: #ffffff; }
            .comparison-table tbody tr:hover { background: #dbeafe; transition: background 0.18s; }
            .comparison-table td { padding: 13px 18px; border-bottom: 1px solid #e2e8f0; font-size: 0.94em; color: #1e293b; text-align: center; vertical-align: middle; }
            .comparison-table td:first-child { font-weight: 700; color: #1e3a5f; text-align: left; background: inherit; border-right: 3px solid #dde3ef; font-size: 0.91em; text-transform: uppercase; letter-spacing: 0.03em; }
            .comparison-table tbody tr:last-child td { border-bottom: none; font-weight: 700; background: linear-gradient(135deg, #fef9ec 0%, #fef3c7 100%); color: #92400e; font-size: 0.95em; }
            .comparison-table tbody tr:last-child td:first-child { color: #78350f; border-right: 3px solid #fcd34d; }
            .comparison-table .btn { display: inline-block; background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff !important; padding: 8px 18px; border-radius: 6px; text-decoration: none !important; font-weight: 700; font-size: 0.86em; letter-spacing: 0.03em; transition: background 0.2s; white-space: nowrap; box-shadow: 0 2px 6px rgba(217,119,6,0.3); }
            .comparison-table .btn:hover { background: linear-gradient(135deg, #d97706, #b45309); }
            .quick-summary-box { background: #fffbeb; border: 1px solid #fef3c7; padding: 25px; border-radius: 12px; margin: 40px 0; }
            @media (max-width: 640px) { .pros-cons-grid { grid-template-columns: 1fr; } .product-title { font-size: 1.6em; } }
        </style>
        """
        
        # Helper for generating context blocks to maintain consistency
        products_summary = "\n".join([f"- {p['title']} | {p['price']} | {p['rating']} | URL: {p.get('url', '#')}" for p in products])
        
        def build_context(intro="", qs="", comp=""):
            ctx = f"Current Article Context\nArticle Topic: {topic}\nPrimary Keyword: {keyword}\nProducts Reviewed:\n{products_summary}\n\nPreviously Generated Sections:\n"
            if intro: ctx += f"Summary of Introduction:\n{intro}\n\n"
            if qs: ctx += f"Summary of Bottom Line:\n{qs}\n\n"
            if comp: ctx += f"Summary of Comparison:\n{comp}\n\n"
            if not intro and not qs and not comp: ctx += "(None yet)\n\n"
            ctx += "This context is read-only. The LLM must use it only to maintain consistency, avoid duplicating information, and ensure no hallucinated products or contradictory advice are added.\n\n=========================\n"
            return ctx
        
        # 1. Intro
        intro_prompt = build_context() + INTRO_TEMPLATE.format(topic=topic, keyword=keyword)
        intro_html = self.generate_section(intro_prompt, model="gpt-4o-mini")
        
        # 2. Quick Summary (New)
        qs_prompt = build_context(intro=intro_html) + QUICK_SUMMARY_TEMPLATE.format(topic=topic)
        qs_raw = self.generate_section(qs_prompt, model="gpt-4o-mini")
        qs_html = f'<div class="quick-summary-box">{qs_raw}</div>'
        
        # 3. Comparison Table (Moved Up)
        comparison_prompt = build_context(intro=intro_html, qs=qs_raw) + COMPARISON_TEMPLATE + f"\n\nHere are the products:\n{products_summary}"
        comparison_raw = self.generate_section(comparison_prompt, model="gpt-4o")
        comparison_html = f'<div class="comparison-table-wrapper">{comparison_raw}</div>'
        
        # 4. Detailed Reviews
        rh_prompt = build_context(intro=intro_html, qs=qs_raw, comp=comparison_raw) + REVIEWS_HEADER_TEMPLATE
        reviews_header = self.generate_section(rh_prompt, model="gpt-4o-mini")
        reviews_html = f"<h2>{reviews_header}</h2>"
        for p in products:
            r_prompt = build_context(qs=qs_raw) + REVIEW_TEMPLATE.format(
                title=p['title'], price=p['price'], 
                rating=p['rating'], review_count=p['review_count'], 
                features=p['features']
            )
            
            review_content = self.generate_section(r_prompt, model="deepseek-v4-flash")
            
            # Build optimized image tag with explicit dimensions
            image_html = ""
            if p.get('image_url'):
                width_attr = f' width="{p.get("image_width")}"' if p.get("image_width") else ''
                height_attr = f' height="{p.get("image_height")}"' if p.get("image_height") else ''
                image_html = f'<div class="product-image-centered"><img src="{p["image_url"]}" alt="{p["title"]}"{width_attr}{height_attr} loading="lazy"></div>'
            
            reviews_html += f"""
            <section class="product-section">
                <h3 class="product-title">{p['title']}</h3>
                {image_html}
                <div class="product-summary-full">
                    <div class="price-badge">Price: {p['price']}</div>
                    {review_content}
                </div>
                <div class="buy-button-wrapper">
                    <a href="{p['url']}" target="_blank" rel="nofollow sponsored" class="buy-btn">View Latest Price on Amazon</a>
                </div>
            </section>
            """
            
        # 5. FAQ Section
        faq_prompt = build_context(qs=qs_raw, comp=comparison_raw) + FAQ_TEMPLATE.format(topic=topic)
        faq_html = self.generate_section(faq_prompt, model='gpt-4o-mini')
        
        # 6. Conclusion
        conc_prompt = build_context(qs=qs_raw) + CONCLUSION_TEMPLATE.format(topic=topic)
conc_html = self.generate_section(conc_prompt, model='gpt-4o-mini')
        
        # 7. Footer
        footer_html = "\n<footer style='font-size: 0.9em; color: #666; border-top: 1px solid #eee; padding-top: 30px; margin-top: 60px;'><em>Disclaimer: This article contains affiliate links. If you click a link and make a purchase, we may earn a small commission at no extra cost to you.</em></footer>\n"
        
        # Assemble parts in requested order
        parts = [
            '<div class="blog-container">',
            style_block,
            intro_html,
            qs_html,
            reviews_html,
            comparison_html,
            faq_html,
            conc_html,
            footer_html,
            '</div>'
        ]
        
        combined_html = "\n".join(parts)
        
        # Apply de-templating to vary prose across product sections
        combined_html = detemplate_article(combined_html)
        
        # Insert methodology section before FAQ (no author bio per requirements)
        soup = BeautifulSoup(combined_html, 'html.parser')
        faq_section = soup.find('h2', string=re.compile(r'Frequently Asked Questions', re.I))
        if faq_section:
            methodology_signals = generate_author_signals(
                author=DEFAULT_AUTHOR,
                methodology=DEFAULT_METHODOLOGY,
                include_top_byline=False,
                include_bottom_byline=False,
                include_methodology=True
            )
            if methodology_signals['methodology']:
                methodology_soup = BeautifulSoup(methodology_signals['methodology'], 'html.parser')
                faq_section.insert_before(methodology_soup)
        
        # Generate Product/Review schema JSON-LD
        schema_html = self.schema_generator.generate_inline_json_ld(products, topic, keyword)
        
        # Generate long-tail heading variants
        products_summary = "\n".join([f"- {p['title']} ({p['price']})" for p in products])
        long_tail_prompt = LONG_TAIL_HEADING_VARIANTS_PROMPT.format(
            topic=topic,
            keyword=keyword,
            products_summary=products_summary
        )
        try:
            long_tail_response = self.generate_section(long_tail_prompt, model="deepseek-v4-flash")
            long_tail_data = json.loads(long_tail_response)
            
            # Insert long-tail headings into appropriate sections
            for variant in long_tail_data:
                heading_html = f'<h2>{variant["heading"]}</h2>'
                # Find suggested placement
                placement = variant.get("suggested_placement", "").lower()
                if "quick summary" in placement or "bottom line" in placement:
                    qs_div = soup.find('div', class_='quick-summary-box')
                    if qs_div:
                        qs_div.insert_after(BeautifulSoup(heading_html, 'html.parser'))
                elif "how we evaluated" in placement:
                    eval_h2 = soup.find('h2', string=re.compile(r'How We Evaluated', re.I))
                    if eval_h2:
                        eval_h2.insert_after(BeautifulSoup(heading_html, 'html.parser'))
                elif "product review" in placement:
                    first_product = soup.find('section', class_='product-section')
                    if first_product:
                        first_product.insert_before(BeautifulSoup(heading_html, 'html.parser'))
        except Exception as e:
            logger.warning(f"Failed to generate/insert long-tail headings: {e}")
        
        # Add schema at the end
        final_html = str(soup) + "\n" + schema_html
        
        # Insert jump break after first meaningful paragraph for consistent preview
        from core.blogger_publisher import insert_jump_break_after_first_paragraph
        final_html = insert_jump_break_after_first_paragraph(final_html)
        
        return self._apply_quality_corrections(final_html, topic, keyword)

    def generate_informational_blueprint(self, topic: str, keyword: str, category: str) -> str:
        """Generate a content planning blueprint for an informational article."""
        logger.info(f"Generating informational blueprint for: {topic}")
        prompt = INFORMATIONAL_BLUEPRINT_TEMPLATE.format(
            topic=topic,
            keyword=keyword,
            category=category
        )
        return self.generate_section(prompt, model="deepseek-v4-flash")

    def generate_informational_article(self, blueprint: str, topic: str, keyword: str, category: str) -> str:
        """Generate a complete informational article from a blueprint."""
        logger.info(f"Generating informational article for: {topic}")
        prompt = INFORMATIONAL_ARTICLE_TEMPLATE.format(
            topic=topic,
            keyword=keyword,
            category=category,
            blueprint=blueprint
        )
        article_html = self.generate_section(prompt, model="gpt-4o-mini")
        # Clean markdown if AI wrapped it
        if article_html.startswith("```html"):
            article_html = article_html.split("```html")[1].split("```")[0].strip()
        elif article_html.startswith("```"):
            article_html = article_html.split("```")[1].split("```")[0].strip()
        
        # Insert jump break after first meaningful paragraph for consistent preview
        from core.blogger_publisher import insert_jump_break_after_first_paragraph
        article_html = insert_jump_break_after_first_paragraph(article_html)
        
        return sanitize_html(article_html)

    def generate_seo_tags(self, topic: str, keyword: str) -> list:
        """Generate SEO labels for Blogger."""
        logger.info(f"Generating SEO tags for: {topic}")
        prompt = SEO_TAGS_TEMPLATE.format(topic=topic, keyword=keyword)
        result = self.generate_section(prompt, model="deepseek-v4-flash")
        # Strip HTML tags just in case
        result = result.replace('<p>', '').replace('</p>', '').replace('\n', '').strip()
        tags = [tag.strip() for tag in result.replace('"', '').split(',') if tag.strip()]
        
        # Sanitize tags and enforce Blogger's strict 200 character limit for ALL labels combined
        safe_tags = []
        total_length = 0
        for tag in tags:
            # Only allow alphanumeric, spaces, and hyphens
            safe_tag = re.sub(r'[^a-zA-Z0-9\s\-]', '', tag).strip()
            # Safety fallback: Strip any 4-digit years (e.g. 2023, 2024)
            safe_tag = re.sub(r'\b\d{4}\b', '', safe_tag).strip()
            
            if safe_tag and safe_tag not in safe_tags:
                if total_length + len(safe_tag) + 1 < 180: # Keep a safe buffer
                    safe_tags.append(safe_tag)
                    total_length += len(safe_tag) + 1
                
        return safe_tags
