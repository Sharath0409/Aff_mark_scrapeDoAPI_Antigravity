#!/usr/bin/env python3
"""
Blog HTML Cleaner — Removes unused CSS, JS, and HTML from all published Blogger posts.

Cleans:
  1. Unused CSS rules (selectors that don't match any HTML in the post)
  2. Unused @import statements (Google Fonts not referenced in remaining CSS)
  3. Empty / dead <script> tags
  4. Empty HTML container elements (<div>, <span>, <p>, <section> with no content)
  5. HTML comments
  6. Unused external <link> stylesheets

Usage:
  python scripts/blog_html_cleaner.py              # Dry run (shows what would change)
  python scripts/blog_html_cleaner.py --apply       # Apply changes to all published posts
"""

import os
import sys
import re
import logging
import argparse
import time
from datetime import datetime

# ── Project path setup ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup, Comment
from config import settings
from core.blogger_publisher import BloggerPublisher

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("blog_cleaner")


# ═══════════════════════════════════════════════════════════════════════════
#  CSS Parser
# ═══════════════════════════════════════════════════════════════════════════

class CSSAnalyzer:
    """Lightweight CSS parser for extracting and checking rule usage."""

    # ── @import helpers ──────────────────────────────────────────────────

    @staticmethod
    def extract_font_family_from_import(import_stmt):
        """Pull the font-family name out of an @import Google Fonts URL."""
        match = re.search(r"family=([^&'\")\s]+)", import_stmt)
        if match:
            family = match.group(1).replace("+", " ")
            return family.split(":")[0]          # Inter:wght@400;700 → Inter
        return None

    # ── Rule parsing ─────────────────────────────────────────────────────

    @staticmethod
    def parse_stylesheet(css_text):
        """
        Split raw CSS into:
          imports  — list of @import strings
          rules    — list of {selector, body, full} dicts
          media    — list of raw @media block strings
        """
        imports = re.findall(r"@import\s+[^;]+;", css_text)
        clean = re.sub(r"@import\s+[^;]+;", "", css_text)

        # ── Extract @media blocks (brace-depth aware) ────────────────
        media_blocks = []
        remaining = clean
        while "@media" in remaining:
            start = remaining.index("@media")
            brace = remaining.index("{", start)
            depth, pos = 1, brace + 1
            while depth > 0 and pos < len(remaining):
                if remaining[pos] == "{":
                    depth += 1
                elif remaining[pos] == "}":
                    depth -= 1
                pos += 1
            media_blocks.append(remaining[start:pos])
            remaining = remaining[:start] + remaining[pos:]

        # ── Extract regular rules ────────────────────────────────────
        rules = []
        for m in re.finditer(r"([^{}]+?)\s*\{([^{}]*)\}", remaining):
            sel = m.group(1).strip()
            if sel and not sel.startswith("@"):
                rules.append(
                    {"selector": sel, "body": m.group(2).strip(), "full": m.group(0)}
                )

        return imports, rules, media_blocks

    # ── Selector matching ────────────────────────────────────────────────

    @staticmethod
    def selector_used_in_html(selector, soup):
        """Return True if *any* sub-selector matches an element in `soup`."""
        for sub in selector.split(","):
            # Strip pseudo-classes / pseudo-elements BS4 can't handle
            clean = re.sub(r"::?[\w-]+(\([^)]*\))?", "", sub).strip()
            if not clean:
                return True                       # ambiguous → keep
            try:
                if soup.select(clean):
                    return True
            except Exception:
                return True                        # parse error → keep
        return False

    @staticmethod
    def font_referenced(font_family, css_body):
        """Case-insensitive check for font-family name inside CSS text."""
        if not font_family:
            return True
        return bool(re.search(re.escape(font_family), css_body, re.IGNORECASE))


# ═══════════════════════════════════════════════════════════════════════════
#  Main Cleaner
# ═══════════════════════════════════════════════════════════════════════════

class BlogHTMLCleaner:
    """Iterates all Blogger posts and strips dead code."""

    def __init__(self, dry_run=True):
        self.publisher = BloggerPublisher(settings.BLOGGER_BLOG_ID)
        self.dry_run = dry_run
        self.css = CSSAnalyzer()
        self.stats = {
            "posts_scanned": 0,
            "posts_cleaned": 0,
            "css_rules_removed": 0,
            "css_imports_removed": 0,
            "scripts_removed": 0,
            "link_tags_removed": 0,
            "empty_elements_removed": 0,
            "comments_removed": 0,
            "total_bytes_before": 0,
            "total_bytes_after": 0,
        }

    # ── CSS cleaning ─────────────────────────────────────────────────────

    def _clean_style_tag(self, style_tag, soup):
        """Remove unused rules from a single <style> tag. Returns count removed."""
        css_text = style_tag.string or ""
        if not css_text.strip():
            return 0

        imports, rules, media_blocks = self.css.parse_stylesheet(css_text)
        removed = 0

        # ── Regular rules ────────────────────────────────────────────
        kept_rules = []
        for rule in rules:
            if self.css.selector_used_in_html(rule["selector"], soup):
                kept_rules.append(rule)
            else:
                removed += 1
                logger.debug(f"    ✂ CSS: {rule['selector']}")

        # ── @media inner rules ───────────────────────────────────────
        kept_media = []
        for block in media_blocks:
            cond_match = re.match(r"(@media[^{]+)\{", block)
            if not cond_match:
                kept_media.append(block)
                continue

            condition = cond_match.group(1).strip()
            inner_css = block[len(cond_match.group(0)) : -1]
            _, inner_rules, _ = self.css.parse_stylesheet(inner_css)

            kept_inner = []
            for r in inner_rules:
                if self.css.selector_used_in_html(r["selector"], soup):
                    kept_inner.append(r)
                else:
                    removed += 1
                    logger.debug(f"    ✂ CSS (@media): {r['selector']}")

            if kept_inner:
                inner_txt = "\n                ".join(
                    f"{r['selector']} {{ {r['body']} }}" for r in kept_inner
                )
                kept_media.append(
                    f"{condition} {{\n                {inner_txt}\n            }}"
                )

        # ── Check @import usage against remaining CSS ────────────────
        remaining_css = "\n".join(
            f"{r['selector']} {{ {r['body']} }}" for r in kept_rules
        )
        remaining_css += "\n" + "\n".join(kept_media)

        final_imports = []
        for imp in imports:
            font = self.css.extract_font_family_from_import(imp)
            if font and not self.css.font_referenced(font, remaining_css):
                removed += 1
                self.stats["css_imports_removed"] += 1
                logger.debug(f"    ✂ @import font: {font}")
            else:
                final_imports.append(imp)

        # ── Rebuild if anything changed ──────────────────────────────
        if removed > 0:
            parts = []
            parts.extend(final_imports)
            parts.extend(f"{r['selector']} {{ {r['body']} }}" for r in kept_rules)
            parts.extend(kept_media)
            style_tag.string = "\n            " + "\n            ".join(parts) + "\n        "

        return removed

    # ── Script cleaning ──────────────────────────────────────────────────

    @staticmethod
    def _clean_scripts(soup):
        """Remove empty <script> tags and scripts with only comments."""
        removed = 0
        for tag in soup.find_all("script"):
            src = tag.get("src", "")
            content = (tag.string or "").strip()

            # Truly empty
            if not src and not content:
                tag.decompose()
                removed += 1
                continue

            # Only whitespace / single-line comment
            if not src and re.fullmatch(r"[\s/\*]*", content):
                tag.decompose()
                removed += 1

        return removed

    # ── External <link> cleaning ─────────────────────────────────────────

    @staticmethod
    def _clean_link_tags(soup):
        """Remove <link rel='stylesheet'> tags whose resources aren't referenced."""
        removed = 0
        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href", "")
            if not href:
                link.decompose()
                removed += 1
                continue

            # Check if it's a Google Fonts link whose font isn't used
            if "fonts.googleapis.com" in href:
                family_match = re.search(r"family=([^&'\")\s]+)", href)
                if family_match:
                    font = family_match.group(1).replace("+", " ").split(":")[0]
                    # Gather all remaining CSS text in the document
                    all_css = " ".join(
                        (s.string or "") for s in soup.find_all("style")
                    )
                    all_css += " ".join(
                        (tag.get("style", "") or "") for tag in soup.find_all(style=True)
                    )
                    if not re.search(re.escape(font), all_css, re.IGNORECASE):
                        link.decompose()
                        removed += 1
                        continue

        return removed

    # ── Empty element cleaning ───────────────────────────────────────────

    @staticmethod
    def _clean_empty_elements(soup):
        """Remove truly empty container elements with no attrs."""
        removed = 0
        removable = ["div", "span", "p", "section", "article", "ul", "ol"]

        for _pass in range(3):          # multiple passes for nested empties
            for tag_name in removable:
                for tag in soup.find_all(tag_name):
                    # Keep if it has structural attributes
                    if tag.get("id") or tag.get("class") or tag.get("style"):
                        continue
                    if not tag.get_text(strip=True) and not tag.find_all(True):
                        tag.decompose()
                        removed += 1
        return removed

    # ── HTML comment cleaning ────────────────────────────────────────────

    @staticmethod
    def _clean_comments(soup):
        comments = soup.find_all(string=lambda t: isinstance(t, Comment))
        for c in comments:
            c.extract()
        return len(comments)

    # ── Per-post pipeline ────────────────────────────────────────────────

    def clean_post(self, post_id, title, content):
        """Clean one post. Returns (cleaned_html, did_change)."""
        if not content or not content.strip():
            return content, False

        original_bytes = len(content.encode("utf-8"))
        soup = BeautifulSoup(content, "html.parser")

        changes = {}
        changes["css"]      = sum(self._clean_style_tag(s, soup) for s in soup.find_all("style"))
        changes["scripts"]  = self._clean_scripts(soup)
        changes["links"]    = self._clean_link_tags(soup)
        changes["empties"]  = self._clean_empty_elements(soup)
        changes["comments"] = self._clean_comments(soup)

        total = sum(changes.values())
        if total == 0:
            self.stats["total_bytes_before"] += original_bytes
            self.stats["total_bytes_after"] += original_bytes
            return content, False

        cleaned = str(soup)
        new_bytes = len(cleaned.encode("utf-8"))
        saved = original_bytes - new_bytes

        logger.info(
            f"  ✓ Removed: {changes['css']} CSS rules · "
            f"{changes['scripts']} scripts · "
            f"{changes['links']} link tags · "
            f"{changes['empties']} empty els · "
            f"{changes['comments']} comments  │  "
            f"Saved {saved:,} bytes ({saved * 100 // max(original_bytes, 1)}%)"
        )

        self.stats["css_rules_removed"]      += changes["css"]
        self.stats["scripts_removed"]        += changes["scripts"]
        self.stats["link_tags_removed"]      += changes["links"]
        self.stats["empty_elements_removed"] += changes["empties"]
        self.stats["comments_removed"]       += changes["comments"]
        self.stats["total_bytes_before"]     += original_bytes
        self.stats["total_bytes_after"]      += new_bytes

        return cleaned, True

    # ── Fetch all posts WITH bodies ──────────────────────────────────────

    def _fetch_all_posts(self):
        posts, page_token = [], None
        while True:
            resp = (
                self.publisher.service.posts()
                .list(
                    blogId=self.publisher.blog_id,
                    pageToken=page_token,
                    maxResults=500,
                    fetchBodies=True,
                )
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                break
            posts.extend(items)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return posts

    # ── Main loop ────────────────────────────────────────────────────────

    def run(self):
        mode = "DRY RUN" if self.dry_run else "LIVE — CHANGES WILL BE APPLIED"
        logger.info("=" * 65)
        logger.info(f"  Blog HTML Cleaner — {mode}")
        logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 65)

        logger.info("Fetching all published posts (with bodies)...")
        posts = self._fetch_all_posts()
        logger.info(f"Found {len(posts)} posts.\n")

        for i, post in enumerate(posts, 1):
            pid   = post["id"]
            title = post.get("title", "Untitled")
            html  = post.get("content", "")

            logger.info(f"[{i}/{len(posts)}] {title}")
            self.stats["posts_scanned"] += 1

            cleaned, changed = self.clean_post(pid, title, html)

            if changed:
                self.stats["posts_cleaned"] += 1
                if not self.dry_run:
                    try:
                        post["content"] = cleaned
                        self.publisher.update_post(pid, post)
                        logger.info("  ✅ Updated on Blogger.")
                        time.sleep(1.5)          # API rate-limit buffer
                    except Exception as e:
                        logger.error(f"  ❌ Failed to update: {e}")
            else:
                logger.info("  — Already clean.")

        self._print_summary()

    # ── Summary ──────────────────────────────────────────────────────────

    def _print_summary(self):
        s = self.stats
        saved = s["total_bytes_before"] - s["total_bytes_after"]
        pct   = saved * 100 // max(s["total_bytes_before"], 1)

        logger.info(f"\n{'═' * 65}")
        logger.info(f"  SUMMARY {'(DRY RUN — nothing was modified)' if self.dry_run else '(APPLIED)'}")
        logger.info(f"{'═' * 65}")
        logger.info(f"  Posts scanned ............. {s['posts_scanned']}")
        logger.info(f"  Posts with dead code ...... {s['posts_cleaned']}")
        logger.info(f"  CSS rules removed ......... {s['css_rules_removed']}")
        logger.info(f"  @import fonts removed ..... {s['css_imports_removed']}")
        logger.info(f"  <script> tags removed ..... {s['scripts_removed']}")
        logger.info(f"  <link> tags removed ....... {s['link_tags_removed']}")
        logger.info(f"  Empty elements removed .... {s['empty_elements_removed']}")
        logger.info(f"  HTML comments removed ..... {s['comments_removed']}")
        logger.info(f"  ─────────────────────────────────────────")
        logger.info(f"  Total size before ......... {s['total_bytes_before']:>10,} bytes")
        logger.info(f"  Total size after .......... {s['total_bytes_after']:>10,} bytes")
        logger.info(f"  Total saved ............... {saved:>10,} bytes ({pct}%)")
        logger.info(f"{'═' * 65}")

        if self.dry_run and s["posts_cleaned"] > 0:
            logger.info(
                "\n  → To apply changes, re-run with:  "
                "python scripts/blog_html_cleaner.py --apply\n"
            )


# ═══════════════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Remove unused CSS, JS, and HTML from all published Blogger posts."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to Blogger (default is dry-run).",
    )
    args = parser.parse_args()

    cleaner = BlogHTMLCleaner(dry_run=not args.apply)
    cleaner.run()


if __name__ == "__main__":
    main()
