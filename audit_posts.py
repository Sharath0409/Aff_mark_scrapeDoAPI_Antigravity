import os
import sys
import json
import argparse
from openai import OpenAI
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import settings
from core.blogger_publisher import BloggerPublisher

client = OpenAI(api_key=settings.OPENAI_API_KEY)
blogger = BloggerPublisher(settings.BLOGGER_BLOG_ID)

# When running locally, write artifacts to a local folder.
# GitHub Actions will upload this as an artifact.
ARTIFACTS_DIR = os.environ.get("AUDIT_ARTIFACTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_reports"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

AUTHOR_BYLINE_HTML = """
<div class="author-byline" style="margin-top:60px; padding:20px; background:#f9fafb; border-top:2px solid #e5e7eb; font-size:0.92em; color:#444;">
  <strong>About the Author:</strong> [AUTHOR_BIO]
</div>
"""

AUDIT_SYSTEM_PROMPT = """You are an expert content auditor for an affiliate site (remoteprostor.com).
Given the title and full text of a post, return a JSON object with these exact keys:
{
  "mismatch_found": true/false,
  "mismatched_category": "Category name or null",
  "pervasive_mismatch": true/false,
  "generic_claims": [{"original": "...", "rewrite": "..."}],
  "forced_links": [{"context": "...", "fix": "..."}],
  "hardcoded_prices": [{"original": "...", "rewrite": "..."}]
}

Rules:
- mismatch_found: true if Bottom Line or Final Thoughts recommends products from a DIFFERENT category than the post title.
- pervasive_mismatch: true if MULTIPLE sections (not just ending) are about the wrong category.
- generic_claims: phrases like 'In my week of testing', 'Based on product specifications and verified user feedback', 'Based on available specifications' used without any specific data point. Propose a concrete or removed rewrite.
- forced_links: internal links that are topically irrelevant (e.g., a standing-desk link inside a USB-hub FAQ answer). Describe context and fix.
- hardcoded_prices: specific dollar amounts (e.g. '$12.99') in prose paragraphs (not in comparison tables). Propose qualitative rewrite.
"""

FIX_SYSTEM_PROMPT = """You are a senior content editor for remoteprostor.com, a US-focused affiliate site.
You will receive the full HTML of a post and a list of required fixes.

Your job:
1. If the Bottom Line or Final Thoughts sections reference the wrong product category, rewrite ONLY those sections to correctly reference the actual products named in the post's own comparison table and product reviews. Do NOT invent new product names.
2. Replace each generic_claim original with its proposed rewrite throughout the HTML.
3. Remove anchor tags for forced/irrelevant internal links (keep the link text, just remove the <a> tag).
4. Replace hardcoded prices in prose paragraphs with the qualitative rewrite provided.
5. If the post's HTML does NOT already contain an author byline block at the end, append one using the placeholder HTML provided.
6. Do NOT touch images, Amazon affiliate links, the comparison table, or any section not listed above.

Return the complete, corrected HTML only — no markdown, no explanation, no backticks.
"""

def append_file(fname, text):
    """Append text to a report file in the artifacts directory."""
    with open(os.path.join(ARTIFACTS_DIR, fname), "a") as f:
        f.write(text + "\n")

def init_report_files():
    """Initialize report files with headers."""
    append_file("audit-report.md", "# Audit Report\n\n| Post URL | Title | Status | Mismatched Category | Missing Disclosure | Missing Byline | Action |\n|---|---|---|---|---|---|---|")
    append_file("fixes-applied.md", "# Fixes Applied\n")
    append_file("unpublish-candidates.md", "# Unpublish Candidates\n")
    append_file("internal-linking-fixes.md", "# Internal Linking Fixes\n")
    append_file("price-hardcoding-fixes.md", "# Price Hardcoding Fixes\n")
    append_file("label-consolidation-plan.md", "# Label Consolidation Plan\n\n## All Labels In Use\n")

def run_audit(dry_run=False):
    if dry_run:
        print("[DRY RUN MODE] No changes will be pushed to Blogger.")
    print("Connecting to Blogger API and listing all posts...")
    all_posts = blogger.list_all_posts(max_results=500)
    total = len(all_posts)
    print(f"Total posts found: {total}")

    init_report_files()
    all_labels = []
    print(f"\n--- Processing all {total} posts ---\n")

    for idx, post in enumerate(all_posts, 1):
        post_id = post['id']
        url = post.get('url', '')
        title = post.get('title', 'Untitled')
        labels = post.get('labels', [])
        all_labels.extend(labels)

        print(f"  [{idx}/{total}] Auditing: {title}")

        try:
            full_post = blogger.get_post(post_id)
            html_content = full_post.get('content', '')

            has_disclosure = "affiliate links" in html_content.lower() or "amazon associate" in html_content.lower()
            has_byline = "author-byline" in html_content.lower() or "[AUTHOR_BIO]" in html_content

            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)

            # Step 1: Audit
            audit_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Title: {title}\n\nContent:\n{text_content[:30000]}"}
                ],
                response_format={"type": "json_object"}
            )
            analysis = json.loads(audit_resp.choices[0].message.content)

            mismatch = analysis.get("mismatch_found", False)
            pervasive = analysis.get("pervasive_mismatch", False)
            mismatch_cat = analysis.get("mismatched_category") or "N/A"
            generic_claims = analysis.get("generic_claims", [])
            forced_links = analysis.get("forced_links", [])
            hardcoded_prices = analysis.get("hardcoded_prices", [])

            status = "FAIL" if mismatch else "PASS"
            action = "SKIP"

            # Determine action
            needs_fix = mismatch or generic_claims or forced_links or hardcoded_prices or not has_byline
            if pervasive:
                action = "UNPUBLISH_CANDIDATE"
            elif needs_fix:
                action = "FIXED"

            append_file("audit-report.md",
                f"| {url} | {title} | {status} | {mismatch_cat} | {not has_disclosure} | {not has_byline} | {action} |")

            if pervasive:
                append_file("unpublish-candidates.md",
                    f"- **[{title}]({url})**\n  - Reason: Pervasive mismatch → {mismatch_cat}")
                processed_ids.append(post_id)
                save_state(processed_ids)
                continue

            # Log fixes to report files
            if mismatch:
                append_file("fixes-applied.md",
                    f"\n### [{title}]({url})\n- **Bottom Line/Final Thoughts Mismatch**: Category drifted to `{mismatch_cat}`. Sections will be rewritten to match the actual products in the post.\n")

            if generic_claims:
                append_file("fixes-applied.md", f"#### Generic Claims Fixed in: {title}")
                for c in generic_claims:
                    append_file("fixes-applied.md",
                        f"- **Before**: {c['original']}\n- **After**: {c['rewrite']}")

            if forced_links:
                append_file("internal-linking-fixes.md", f"\n### [{title}]({url})")
                for lk in forced_links:
                    append_file("internal-linking-fixes.md",
                        f"- **Issue**: {lk['context']}\n- **Fix**: {lk['fix']}")

            if hardcoded_prices:
                append_file("price-hardcoding-fixes.md", f"\n### [{title}]({url})")
                for pr in hardcoded_prices:
                    append_file("price-hardcoding-fixes.md",
                        f"- **Before**: {pr['original']}\n- **After**: {pr['rewrite']}")

            # Step 2: Execute fixes if anything to fix
            if needs_fix:
                fixes_payload = {
                    "mismatch_found": mismatch,
                    "mismatched_category": mismatch_cat,
                    "generic_claims": generic_claims,
                    "forced_links": forced_links,
                    "hardcoded_prices": hardcoded_prices,
                    "has_byline": has_byline
                }
                fix_resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": FIX_SYSTEM_PROMPT},
                        {"role": "user", "content": (
                            f"AUTHOR_BYLINE_PLACEHOLDER:\n{AUTHOR_BYLINE_HTML}\n\n"
                            f"FIXES REQUIRED:\n{json.dumps(fixes_payload, indent=2)}\n\n"
                            f"FULL POST HTML:\n{html_content}"
                        )}
                    ]
                )
                fixed_html = fix_resp.choices[0].message.content.strip()
                # Strip any accidental markdown wrappers
                if fixed_html.startswith("```"):
                    fixed_html = "\n".join(fixed_html.split("\n")[1:])
                if fixed_html.endswith("```"):
                    fixed_html = "\n".join(fixed_html.split("\n")[:-1])

                if not dry_run:
                    # Push back to Blogger
                    post_body = {
                        "id": post_id,
                        "title": title,
                        "content": fixed_html,
                        "labels": labels
                    }
                    blogger.update_post(post_id, post_body)
                    print(f"    ✅ Fixed and updated: {title}")
                else:
                    print(f"    [DRY RUN] Would fix: {title}")
            else:
                print(f"    ✔ No issues found: {title}")

        except Exception as e:
            print(f"    ❌ ERROR on post {post_id} ({title}): {e}")

    # Append labels from all posts
    if all_labels:
        from collections import Counter
        label_counts = Counter(all_labels)
        append_file("label-consolidation-plan.md", "\n## Label Frequency (sorted)\n")
        for lbl, cnt in label_counts.most_common():
            append_file("label-consolidation-plan.md", f"- `{lbl}`: {cnt} post(s)")
        singleton_labels = [lbl for lbl, cnt in label_counts.items() if cnt <= 2]
        append_file("label-consolidation-plan.md",
            f"\n## Labels Used on ≤2 Posts (tag bloat candidates): {len(singleton_labels)}\n" +
            "\n".join([f"- `{l}`" for l in sorted(singleton_labels)]))

    print(f"\n--- All {total} posts processed. Reports written to {ARTIFACTS_DIR} ---")
    print("Review the artifact files before making any further decisions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and fix remoteprostor.com Blogger posts.")
    parser.add_argument("--dry-run", action="store_true", help="Audit only, do not push fixes to Blogger.")
    args = parser.parse_args()
    run_audit(dry_run=args.dry_run)


