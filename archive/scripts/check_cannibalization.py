#!/usr/bin/env python3
"""Cannibalization Audit Script

Runs a cannibalization audit on published Blogger posts and generates
a report with consolidation recommendations and canonical linking structure.

Usage:
    python scripts/check_cannibalization.py --blog-id YOUR_BLOG_ID --output report.json
    python scripts/check_cannibalization.py --blog-id YOUR_BLOG_ID --threshold 0.7 --dry-run
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from core.blogger_publisher import BloggerPublisher
from core.cannibalization_checker import (
    CannibalizationChecker, 
    load_posts_from_blogger,
    run_cannibalization_audit
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("check_cannibalization")


def main():
    parser = argparse.ArgumentParser(
        description="Run cannibalization audit on Blogger posts"
    )
    parser.add_argument(
        "--blog-id", 
        default=settings.BLOGGER_BLOG_ID,
        help="Blogger blog ID"
    )
    parser.add_argument(
        "--output", 
        default="cannibalization_report.json",
        help="Output JSON report file"
    )
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=0.65,
        help="Similarity threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--max-posts", 
        type=int, 
        default=500,
        help="Maximum posts to analyze"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Print report to stdout without saving"
    )
    parser.add_argument(
        "--canonical-only", 
        action="store_true",
        help="Only output canonical linking structure"
    )
    
    args = parser.parse_args()
    
    if not args.blog_id:
        logger.error("Blog ID required. Set BLOGGER_BLOG_ID in env or pass --blog-id")
        sys.exit(1)
    
    try:
        logger.info(f"Initializing Blogger publisher for blog: {args.blog_id}")
        publisher = BloggerPublisher(args.blog_id)
        
        logger.info(f"Loading up to {args.max_posts} posts from Blogger...")
        posts = load_posts_from_blogger(publisher.service, args.blog_id, args.max_posts)
        logger.info(f"Loaded {len(posts)} posts")
        
        if not posts:
            logger.warning("No posts found. Exiting.")
            return
        
        logger.info(f"Running cannibalization analysis (threshold: {args.threshold})...")
        checker = CannibalizationChecker(similarity_threshold=args.threshold)
        checker.add_posts(posts)
        
        if args.canonical_only:
            canonical = checker.get_canonical_structure()
            output = {"canonical_structure": canonical}
        else:
            report = checker.generate_report()
            canonical = checker.get_canonical_structure()
            output = {
                "audit_timestamp": datetime.now().isoformat(),
                "blog_id": args.blog_id,
                "threshold": args.threshold,
                "posts_analyzed": len(posts),
                "report": report,
                "canonical_structure": canonical
            }
        
        if args.dry_run:
            print(json.dumps(output, indent=2))
        else:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            logger.info(f"Report saved to {args.output}")
            
            # Print summary
            if not args.canonical_only:
                r = output["report"]
                print(f"\n=== Cannibalization Audit Summary ===")
                print(f"Posts analyzed: {r['total_posts']}")
                print(f"Potential matches: {r['total_matches']}")
                print(f"\nBy recommendation:")
                for rec, matches in r['by_recommendation'].items():
                    print(f"  {rec}: {len(matches)}")
                print(f"\nIntent distribution:")
                for intent, count in r['intent_distribution'].items():
                    print(f"  {intent}: {count}")
        
    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()