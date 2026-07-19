"""Cannibalization Checker Module

Analyzes existing posts and labels to detect keyword/topic cannibalization,
recommends consolidation strategy, and proposes canonical internal linking structure.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher
import json


@dataclass
class PostInfo:
    """Information about a published post."""
    post_id: str
    title: str
    url: str
    labels: List[str]
    published_date: str
    keywords: List[str] = field(default_factory=list)
    category: str = ""


@dataclass
class CannibalizationMatch:
    """Represents a potential cannibalization between two posts."""
    post_a: PostInfo
    post_b: PostInfo
    similarity_score: float
    match_type: str  # "title", "keyword", "label", "intent"
    shared_terms: List[str]
    recommendation: str  # "consolidate", "differentiate", "canonical_link"


class CannibalizationChecker:
    """
    Analyzes a corpus of posts for keyword/topic cannibalization.
    
    Uses multiple signals:
    - Title similarity (fuzzy matching)
    - Keyword overlap
    - Label/tag overlap
    - Search intent classification
    """
    
    # Intent categories for classification
    INTENT_PATTERNS = {
        "best_guide": [
            r"^best\s+", r"^top\s+\d+\s+", r"^best\s+\w+\s+for\s+",
            r"^the\s+best\s+", r"^ultimate\s+guide\s+to\s+"
        ],
        "vs_comparison": [
            r"\bvs\b", r"\bversus\b", r"\bcompared\b", r"\bvs\.\b",
            r"^.*\s+vs\s+.*$", r"^.*\s+versus\s+.*$"
        ],
        "how_to": [
            r"^how\s+to\s+", r"^how\s+do\s+i\s+", r"^guide\s+to\s+",
            r"^tutorial\s+", r"^step.by.step\s+", r"^setting\s+up\s+"
        ],
        "review": [
            r"^review\s*:", r"^review\s+of\s+", r"^hands.on\s+",
            r"^first\s+look\s+", r"^impressions\s+of\s+"
        ],
        "buying_guide": [
            r"^buying\s+guide\s+", r"^what\s+to\s+look\s+for\s+",
            r"^choosing\s+the\s+right\s+", r"^how\s+to\s+choose\s+"
        ],
        "troubleshooting": [
            r"^fix\s+", r"^solve\s+", r"^troubleshoot\s+",
            r"^why\s+is\s+my\s+", r"^how\s+to\s+fix\s+"
        ],
        "ergonomics_guide": [
            r"^ergonomic\s+", r"^proper\s+", r"^correct\s+",
            r"^osha\s+", r"^posture\s+", r"^setup\s+guide\s+"
        ],
    }
    
    def __init__(self, similarity_threshold: float = 0.65):
        self.similarity_threshold = similarity_threshold
        self.posts: List[PostInfo] = []
    
    def add_post(self, post: PostInfo):
        """Add a post to the analysis corpus."""
        # Extract keywords from title
        post.keywords = self._extract_keywords(post.title)
        post.category = self._classify_intent(post.title)
        self.posts.append(post)
    
    def add_posts(self, posts: List[PostInfo]):
        """Add multiple posts."""
        for post in posts:
            self.add_post(post)
    
    def _extract_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from title."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
            'just', 'don', 'should', 'now', 'best', 'top', 'guide', 'review'
        }
        
        words = re.findall(r'\b\w+\b', title.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords
    
    def _classify_intent(self, title: str) -> str:
        """Classify search intent of a post title."""
        title_lower = title.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    return intent
        
        return "informational"
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def _keyword_overlap(self, keywords_a: List[str], keywords_b: List[str]) -> Tuple[float, List[str]]:
        """Calculate keyword overlap between two posts."""
        set_a = set(keywords_a)
        set_b = set(keywords_b)
        
        if not set_a or not set_b:
            return 0.0, []
        
        intersection = set_a & set_b
        union = set_a | set_b
        
        jaccard = len(intersection) / len(union) if union else 0.0
        return jaccard, list(intersection)
    
    def _label_overlap(self, labels_a: List[str], labels_b: List[str]) -> Tuple[float, List[str]]:
        """Calculate label overlap."""
        set_a = set(l.lower() for l in labels_a)
        set_b = set(l.lower() for l in labels_b)
        
        if not set_a or not set_b:
            return 0.0, []
        
        intersection = set_a & set_b
        union = set_a | set_b
        
        jaccard = len(intersection) / len(union) if union else 0.0
        return jaccard, list(intersection)
    
    def analyze(self) -> List[CannibalizationMatch]:
        """
        Analyze all posts for cannibalization.
        
        Returns list of matches sorted by severity (highest similarity first).
        """
        matches = []
        
        for i, post_a in enumerate(self.posts):
            for post_b in self.posts[i+1:]:
                match = self._compare_posts(post_a, post_b)
                if match:
                    matches.append(match)
        
        # Sort by similarity score descending
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches
    
    def _compare_posts(self, post_a: PostInfo, post_b: PostInfo) -> Optional[CannibalizationMatch]:
        """Compare two posts for cannibalization signals."""
        
        # Title similarity
        title_sim = self._similarity(post_a.title, post_b.title)
        
        # Keyword overlap
        kw_score, shared_kw = self._keyword_overlap(post_a.keywords, post_b.keywords)
        
        # Label overlap
        label_score, shared_labels = self._label_overlap(post_a.labels, post_b.labels)
        
        # Intent match
        intent_match = post_a.category == post_b.category
        
        # Combined score (weighted)
        combined_score = (
            title_sim * 0.4 +
            kw_score * 0.3 +
            label_score * 0.2 +
            (1.0 if intent_match else 0.0) * 0.1
        )
        
        if combined_score < self.similarity_threshold:
            return None
        
        # Determine match type
        match_types = []
        if title_sim > 0.7:
            match_types.append("title")
        if kw_score > 0.5:
            match_types.append("keyword")
        if label_score > 0.5:
            match_types.append("label")
        if intent_match:
            match_types.append("intent")
        
        match_type = "+".join(match_types) if match_types else "low"
        
        # Determine recommendation
        recommendation = self._get_recommendation(
            post_a, post_b, combined_score, match_type
        )
        
        all_shared = shared_kw + shared_labels
        
        return CannibalizationMatch(
            post_a=post_a,
            post_b=post_b,
            similarity_score=combined_score,
            match_type=match_type,
            shared_terms=all_shared,
            recommendation=recommendation
        )
    
    def _get_recommendation(self, post_a: PostInfo, post_b: PostInfo,
                           score: float, match_type: str) -> str:
        """Determine consolidation strategy."""
        
        # High similarity + same intent = consolidate
        if score > 0.85 and "intent" in match_type:
            return "consolidate"
        
        # High title similarity = consolidate or canonical
        if "title" in match_type and score > 0.8:
            return "consolidate"
        
        # Keyword/label overlap with same intent = differentiate
        if score > 0.7 and "intent" in match_type:
            return "differentiate"
        
        # Moderate overlap = canonical linking
        if score > 0.65:
            return "canonical_link"
        
        return "monitor"
    
    def generate_report(self) -> Dict:
        """Generate comprehensive cannibalization report."""
        matches = self.analyze()
        
        # Group by recommendation
        by_recommendation = defaultdict(list)
        for match in matches:
            by_recommendation[match.recommendation].append({
                "post_a": {"id": match.post_a.post_id, "title": match.post_a.title, "url": match.post_a.url},
                "post_b": {"id": match.post_b.post_id, "title": match.post_b.title, "url": match.post_b.url},
                "score": round(match.similarity_score, 3),
                "type": match.match_type,
                "shared_terms": match.shared_terms
            })
        
        # Intent distribution
        intent_dist = defaultdict(int)
        for post in self.posts:
            intent_dist[post.category] += 1
        
        return {
            "total_posts": len(self.posts),
            "total_matches": len(matches),
            "by_recommendation": dict(by_recommendation),
            "intent_distribution": dict(intent_dist),
            "high_priority": [
                m for m in matches if m.similarity_score > 0.8
            ][:10]
        }
    
    def get_canonical_structure(self) -> Dict:
        """
        Propose canonical internal linking structure.
        
        Returns mapping of pillar posts -> supporting posts.
        """
        matches = self.analyze()
        
        # Group by intent category
        by_intent = defaultdict(list)
        for post in self.posts:
            by_intent[post.category].append(post)
        
        structure = {}
        
        for intent, posts in by_intent.items():
            if len(posts) <= 1:
                continue
            
            # Find the most comprehensive post as pillar
            # (longest title, most labels, earliest date = more established)
            pillar = max(posts, key=lambda p: (
                len(p.title) + len(p.labels) * 10
            ))
            
            supporting = [p for p in posts if p.post_id != pillar.post_id]
            
            structure[intent] = {
                "pillar": {
                    "id": pillar.post_id,
                    "title": pillar.title,
                    "url": pillar.url
                },
                "supporting": [
                    {
                        "id": p.post_id,
                        "title": p.title,
                        "url": p.url,
                        "link_from_pillar": True,
                        "link_to_pillar": True
                    }
                    for p in supporting
                ]
            }
        
        return structure


def load_posts_from_blogger(blogger_service, blog_id: str, max_posts: int = 500) -> List[PostInfo]:
    """Load posts from Blogger API into PostInfo objects."""
    posts = []
    page_token = None
    
    while len(posts) < max_posts:
        request = blogger_service.posts().list(
            blogId=blog_id,
            maxResults=min(50, max_posts - len(posts)),
            pageToken=page_token
        )
        response = request.execute()
        
        for item in response.get('items', []):
            post = PostInfo(
                post_id=item['id'],
                title=item['title'],
                url=item['url'],
                labels=item.get('labels', []),
                published_date=item.get('published', '')
            )
            posts.append(post)
        
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    
    return posts


def run_cannibalization_audit(blogger_service, blog_id: str, 
                              output_file: str = "cannibalization_report.json") -> Dict:
    """Run full cannibalization audit and save report."""
    posts = load_posts_from_blogger(blogger_service, blog_id)
    
    checker = CannibalizationChecker()
    checker.add_posts(posts)
    
    report = checker.generate_report()
    canonical = checker.get_canonical_structure()
    
    full_report = {
        "audit_timestamp": datetime.now().isoformat(),
        "blog_id": blog_id,
        "report": report,
        "canonical_structure": canonical
    }
    
    with open(output_file, 'w') as f:
        json.dump(full_report, f, indent=2)
    
    return full_report


if __name__ == "__main__":
    # Demo with sample posts
    sample_posts = [
        PostInfo("1", "Best Ergonomic Chairs for 2024", "https://example.com/1", 
                 ["chairs", "ergonomics", "best"], "2024-01-15"),
        PostInfo("2", "Top 10 Ergonomic Office Chairs Reviewed", "https://example.com/2",
                 ["chairs", "reviews", "office"], "2024-02-20"),
        PostInfo("3", "Best Office Chairs for Back Pain", "https://example.com/3",
                 ["chairs", "back-pain", "ergonomics"], "2024-03-10"),
        PostInfo("4", "Herman Miller Aeron vs Steelcase Leap", "https://example.com/4",
                 ["chairs", "comparison", "herman-miller"], "2024-04-01"),
        PostInfo("5", "How to Set Up an Ergonomic Workstation", "https://example.com/5",
                 ["ergonomics", "setup", "guide"], "2024-05-15"),
        PostInfo("6", "Best Standing Desks for Home Office 2024", "https://example.com/6",
                 ["desks", "standing", "best"], "2024-01-20"),
        PostInfo("7", "Standing Desk vs Sitting Desk: Which is Better?", "https://example.com/7",
                 ["desks", "comparison", "standing"], "2024-02-25"),
    ]
    
    checker = CannibalizationChecker(similarity_threshold=0.6)
    checker.add_posts(sample_posts)
    
    report = checker.generate_report()
    print(json.dumps(report, indent=2))
    
    print("\n=== CANONICAL STRUCTURE ===")
    canonical = checker.get_canonical_structure()
    print(json.dumps(canonical, indent=2))