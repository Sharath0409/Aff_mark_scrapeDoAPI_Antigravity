"""De-Templater Module

Detects and rewrites repetitive boilerplate phrases across product sections
to ensure varied, natural prose throughout the article.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import random


@dataclass
class TemplatePattern:
    """A detected template pattern with replacement options."""
    pattern: str
    regex: re.Pattern
    category: str  # "opening", "transition", "closing", "verdict", "specs"
    replacements: List[str]
    weight: float = 1.0  # For weighted random selection


class DeTemplater:
    """
    Detects and rewrites repetitive boilerplate phrases across product sections.
    
    Maintains a registry of known template patterns and their varied replacements.
    Tracks usage across the article to ensure no two product sections share
    near-identical opening/closing sentences.
    """
    
    # Known template patterns with their varied replacements
    TEMPLATE_PATTERNS = {
        "opening_based_on_specs": TemplatePattern(
            pattern=r"Based on (?:manufacturer specifications|product specifications|available specifications|the specifications provided)",
            regex=re.compile(r"Based on (?:manufacturer specifications|product specifications|available specifications|the specifications provided)", re.IGNORECASE),
            category="opening",
            replacements=[
                "Drawing from the manufacturer's technical specifications",
                "According to the published product specifications",
                "Based on the official technical data provided by the manufacturer",
                "The manufacturer's specifications indicate",
                "Per the official product documentation",
                "The published specifications show",
                "According to the manufacturer's technical data",
                "The product's official specifications reveal",
            ],
            weight=1.0
        ),
        
        "opening_verified_feedback": TemplatePattern(
            pattern=r"(?:and|,) verified (?:customer|buyer|user) feedback",
            regex=re.compile(r"(?:and|,) verified (?:customer|buyer|user) feedback", re.IGNORECASE),
            category="opening",
            replacements=[
                "and verified purchaser feedback",
                "along with verified buyer reports",
                "combined with verified user experiences",
                "supplemented by verified customer reviews",
                "corroborated by verified purchaser reports",
                "validated through verified buyer input",
            ],
            weight=1.0
        ),
        
        "opening_for_us_remote": TemplatePattern(
            pattern=r"for (?:US )?remote workers?(?: and (?:creative )?professionals?)?",
            regex=re.compile(r"for (?:US )?remote workers?(?: and (?:creative )?professionals?)?", re.IGNORECASE),
            category="opening",
            replacements=[
                "for US-based remote workers",
                "for remote professionals in the US",
                "for American remote workers and freelancers",
                "for US home office users",
                "for remote workers across the US",
                "for US-based knowledge workers",
                "for hybrid and remote professionals in the US",
            ],
            weight=1.0
        ),
        
        "opening_when_comparing": TemplatePattern(
            pattern=r"When comparing (?:available options|similar products|the alternatives|other models)",
            regex=re.compile(r"When comparing (?:available options|similar products|the alternatives|other models)", re.IGNORECASE),
            category="opening",
            replacements=[
                "When evaluating the alternatives",
                "Comparing against similar models",
                "Against competing options in this category",
                "Relative to other products in this class",
                "When weighed against comparable models",
                "In comparison with similar offerings",
            ],
            weight=1.0
        ),
        
        "transition_ergonomic_perspective": TemplatePattern(
            pattern=r"From an ergonomic perspective",
            regex=re.compile(r"From an ergonomic perspective", re.IGNORECASE),
            category="transition",
            replacements=[
                "From an ergonomics standpoint",
                "Looking at ergonomics",
                "In terms of ergonomic design",
                "From a workplace ergonomics perspective",
                "Ergonomically speaking",
                "Through an ergonomic lens",
            ],
            weight=1.0
        ),
        
        "transition_workplace_best_practices": TemplatePattern(
            pattern=r"(?:Based on|Following) workplace best practices",
            regex=re.compile(r"(?:Based on|Following) workplace best practices", re.IGNORECASE),
            category="transition",
            replacements=[
                "In line with established workplace practices",
                "Consistent with professional workspace guidelines",
                "Aligned with recommended workplace standards",
                "Following recognized workplace principles",
                "Per established professional workspace practices",
            ],
            weight=1.0
        ),
        
        "verdict_best_for": TemplatePattern(
            pattern=r"(?:Best for|Ideal for|Perfect for|Great for)\s+",
            regex=re.compile(r"(?:Best for|Ideal for|Perfect for|Great for)\s+", re.IGNORECASE),
            category="verdict",
            replacements=[
                "Best suited for ",
                "Ideal for ",
                "A strong choice for ",
                "Well-matched to ",
                "Particularly good for ",
                "Recommended for ",
                "Optimized for ",
            ],
            weight=1.0
        ),
        
        "specs_intro": TemplatePattern(
            pattern=r"(?:The specs|Key specifications|Specifications):",
            regex=re.compile(r"(?:The specs|Key specifications|Specifications):", re.IGNORECASE),
            category="specs",
            replacements=[
                "Key specifications:",
                "Technical details:",
                "Spec highlights:",
                "At a glance:",
                "Core specifications:",
            ],
            weight=1.0
        ),
        
        "pros_intro": TemplatePattern(
            pattern=r"(?:Pros|Advantages|Strengths):",
            regex=re.compile(r"(?:Pros|Advantages|Strengths):", re.IGNORECASE),
            category="pros",
            replacements=[
                "What we like:",
                "Strengths:",
                "Advantages:",
                "The good:",
                "Highlights:",
            ],
            weight=1.0
        ),
        
        "cons_intro": TemplatePattern(
            pattern=r"(?:Cons|Disadvantages|Weaknesses|Drawbacks):",
            regex=re.compile(r"(?:Cons|Disadvantages|Weaknesses|Drawbacks):", re.IGNORECASE),
            category="cons",
            replacements=[
                "What could be better:",
                "Limitations:",
                "Considerations:",
                "The trade-offs:",
                "Potential drawbacks:",
            ],
            weight=1.0
        ),
        
        "closing_recommendation": TemplatePattern(
            pattern=r"(?:If you|For those who|Should you)\s+(?:prioritize|value|need|want)",
            regex=re.compile(r"(?:If you|For those who|Should you)\s+(?:prioritize|value|need|want)", re.IGNORECASE),
            category="closing",
            replacements=[
                "If you prioritize ",
                "For those who value ",
                "Should you need ",
                "When you prioritize ",
                "If your priority is ",
                "For buyers who value ",
            ],
            weight=1.0
        ),
        
        "closing_buy_this": TemplatePattern(
            pattern=r"(?:Buy this|Choose this|Get this|Go with this)\s+(?:if|when)",
            regex=re.compile(r"(?:Buy this|Choose this|Get this|Go with this)\s+(?:if|when)", re.IGNORECASE),
            category="closing",
            replacements=[
                "Choose this if ",
                "Opt for this when ",
                "This is the right pick if ",
                "Go with this model if ",
                "Select this option if ",
            ],
            weight=1.0
        ),
    }
    
    def __init__(self):
        self.used_replacements: Dict[str, Set[str]] = defaultdict(set)
        self.section_count = 0
    
    def reset(self):
        """Reset tracking for a new article."""
        self.used_replacements.clear()
        self.section_count = 0
    
    def process_section(self, html: str, section_index: int) -> str:
        """
        Process a single product section, replacing template phrases
        with varied alternatives not used in previous sections.
        """
        self.section_count = max(self.section_count, section_index + 1)
        result = html
        
        for pattern_name, pattern in self.TEMPLATE_PATTERNS.items():
            result = self._replace_pattern(result, pattern_name, pattern, section_index)
        
        return result
    
    def _replace_pattern(self, html: str, pattern_name: str, 
                         pattern: TemplatePattern, section_index: int) -> str:
        """Replace all occurrences of a pattern with unused alternatives."""
        
        def replacer(match):
            # Get available replacements not used in previous sections
            used = self.used_replacements[pattern_name]
            available = [r for r in pattern.replacements if r not in used]
            
            if not available:
                # All used - reset and allow reuse (but prefer unused)
                available = pattern.replacements
            
            # Weighted random selection
            replacement = random.choices(
                available, 
                weights=[pattern.weight] * len(available)
            )[0]
            
            # Track usage
            self.used_replacements[pattern_name].add(replacement)
            return replacement
        
        return pattern.regex.sub(replacer, html)
    
    def get_usage_report(self) -> Dict:
        """Get report of template usage across sections."""
        return {
            name: list(replacements) 
            for name, replacements in self.used_replacements.items()
        }


class SectionVariator:
    """
    Higher-level class that coordinates de-templating across all product
    sections in an article, ensuring structural variety too.
    """
    
    def __init__(self):
        self.detemplater = DeTemplater()
        self.section_structures: List[Dict] = []
    
    def process_article(self, article_html: str) -> str:
        """Process full article, de-templating all product sections."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(article_html, 'html.parser')
        self.detemplater.reset()
        
        # Find all product sections
        product_sections = soup.find_all('section', class_='product-section')
        
        for idx, section in enumerate(product_sections):
            # Process the section's HTML
            section_html = str(section)
            processed = self.detemplater.process_section(section_html, idx)
            
            # Replace in soup
            new_section = BeautifulSoup(processed, 'html.parser')
            section.replace_with(new_section)
        
        return str(soup)
    
    def get_variation_report(self) -> Dict:
        """Get report on template variations used."""
        return {
            "sections_processed": self.detemplater.section_count,
            "template_usage": self.detemplater.get_usage_report()
        }


# Convenience function
def detemplate_article(article_html: str) -> str:
    """Convenience function to de-template an entire article."""
    variator = SectionVariator()
    return variator.process_article(article_html)


if __name__ == "__main__":
    # Demo
    test_html = """
    <section class="product-section">
        <h3>Product 1</h3>
        <p>Based on manufacturer specifications and verified customer feedback, for US remote workers, this mouse excels.</p>
        <p>From an ergonomic perspective, the design supports neutral wrist position.</p>
        <p>Best for users who prioritize comfort.</p>
        <p>Buy this if you need all-day comfort.</p>
    </section>
    <section class="product-section">
        <h3>Product 2</h3>
        <p>Based on manufacturer specifications and verified customer feedback, for US remote workers, this keyboard performs well.</p>
        <p>From an ergonomic perspective, the layout reduces strain.</p>
        <p>Best for users who prioritize typing feel.</p>
        <p>Buy this if you want a great typing experience.</p>
    </section>
    """
    
    result = detemplate_article(test_html)
    print(result)