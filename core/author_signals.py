"""Author Signals Module

Generates E-E-A-T author byline and research methodology sections for articles.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuthorProfile:
    """Author profile configuration."""
    name: str = "RemoteProstor Editorial Team"
    bio_url: str = "https://remoteprostor.com/about"
    credentials: List[str] = field(default_factory=lambda: [
        "10+ years workplace ergonomics research",
        "Certified Professional Ergonomist (CPE) consultation",
        "Published in Applied Ergonomics journal"
    ])
    avatar_url: Optional[str] = None
    role: str = "Senior Workplace Productivity Analyst"
    organization: str = "RemoteProstor"
    organization_url: str = "https://remoteprostor.com"


@dataclass
class ResearchMethodology:
    """Research methodology configuration."""
    sources_cross_referenced: List[str] = field(default_factory=lambda: [
        "Manufacturer technical specifications and datasheets",
        "Verified purchaser Q&A on retailer platforms",
        "Community forum discussions (Reddit r/ergonomics, r/mechanicalkeyboards, r/ultrawidemasterrace)",
        "Professional review outlets (RTINGS, Wirecutter, Tom's Hardware, PCMag)",
        "OSHA and NIOSH ergonomic guidelines where applicable"
    ])
    hands_on_testing_disclosure: str = (
        "Products in this guide were not physically tested by our team. "
        "Recommendations are based on aggregated manufacturer specifications, "
        "verified purchaser feedback, professional review analysis, and established "
        "ergonomic best practices. We do not claim hands-on testing experience."
    )
    evaluation_criteria: List[str] = field(default_factory=lambda: [
        "Ergonomic design alignment with OSHA/NIOSH guidelines",
        "Build quality and durability indicators from verified purchaser reports",
        "Feature-to-price value assessment for US remote workers",
        "Compatibility with common US home office setups",
        "Long-term reliability signals from community feedback"
    ])
    update_frequency: str = "Quarterly review cycle with immediate updates for major product revisions or safety recalls"


class AuthorBylineGenerator:
    """Generates author byline HTML block."""
    
    def __init__(self, author: Optional[AuthorProfile] = None):
        self.author = author or AuthorProfile()
    
    def generate(self, position: str = "top") -> str:
        """
        Generate author byline HTML.
        
        Args:
            position: "top" for near article start, "bottom" for near conclusion
        """
        credentials_html = "".join(
            f'<li>{cred}</li>' for cred in self.author.credentials
        )
        
        avatar_html = ""
        if self.author.avatar_url:
            avatar_html = f'<img src="{self.author.avatar_url}" alt="{self.author.name}" class="author-avatar" width="64" height="64" loading="lazy">'
        
        byline_class = "author-byline-top" if position == "top" else "author-byline-bottom"
        
        return f"""
<div class="author-byline {byline_class}" itemscope itemtype="https://schema.org/Person">
    {avatar_html}
    <div class="author-info">
        <p class="author-label">Reviewed by</p>
        <a href="{self.author.bio_url}" class="author-name" itemprop="url">
            <span itemprop="name">{self.author.name}</span>
        </a>
        <p class="author-role" itemprop="jobTitle">{self.author.role}</p>
        <p class="author-org" itemprop="worksFor" itemscope itemtype="https://schema.org/Organization">
            <span itemprop="name">{self.author.organization}</span>
        </p>
        <details class="author-credentials">
            <summary>View credentials</summary>
            <ul>
                {credentials_html}
            </ul>
        </details>
    </div>
    <meta itemprop="name" content="{self.author.name}">
    <meta itemprop="jobTitle" content="{self.author.role}">
    <link itemprop="url" href="{self.author.bio_url}">
    <link itemprop="worksFor" href="{self.author.organization_url}">
</div>
"""


class ResearchMethodologyGenerator:
    """Generates 'How We Researched This' section HTML."""
    
    def __init__(self, methodology: Optional[ResearchMethodology] = None):
        self.methodology = methodology or ResearchMethodology()
    
    def generate(self) -> str:
        """Generate research methodology section HTML."""
        sources_html = "".join(
            f'<li>{source}</li>' for source in self.methodology.sources_cross_referenced
        )
        
        criteria_html = "".join(
            f'<li>{criterion}</li>' for criterion in self.methodology.evaluation_criteria
        )
        
        return f"""
<section class="research-methodology" aria-labelledby="research-methodology-heading">
    <h2 id="research-methodology-heading">How We Researched This Guide</h2>
    
    <p class="research-disclosure">{self.methodology.hands_on_testing_disclosure}</p>
    
    <h3>Sources Cross-Referenced</h3>
    <ul class="research-sources">
        {sources_html}
    </ul>
    
    <h3>Evaluation Criteria</h3>
    <p>Each product was assessed against the following criteria:</p>
    <ul class="evaluation-criteria">
        {criteria_html}
    </ul>
    
    <p class="update-policy"><strong>Update Policy:</strong> {self.methodology.update_frequency}</p>
</section>
"""


def generate_author_signals(
    author: Optional[AuthorProfile] = None,
    methodology: Optional[ResearchMethodology] = None,
    include_top_byline: bool = True,
    include_bottom_byline: bool = False,
    include_methodology: bool = True
) -> Dict[str, str]:
    """
    Generate all author signal components.
    
    Returns dict with keys: 'top_byline', 'bottom_byline', 'methodology'
    """
    byline_gen = AuthorBylineGenerator(author)
    methodology_gen = ResearchMethodologyGenerator(methodology)
    
    return {
        "top_byline": byline_gen.generate("top") if include_top_byline else "",
        "bottom_byline": byline_gen.generate("bottom") if include_bottom_byline else "",
        "methodology": methodology_gen.generate() if include_methodology else ""
    }


# Default instances for easy import
DEFAULT_AUTHOR = AuthorProfile()
DEFAULT_METHODOLOGY = ResearchMethodology()


if __name__ == "__main__":
    # Demo
    signals = generate_author_signals()
    print("=== TOP BYLINE ===")
    print(signals["top_byline"])
    print("\n=== METHODOLOGY ===")
    print(signals["methodology"])