import unittest
from core.content_generator import ContentGenerator


class ContentQualityTests(unittest.TestCase):
    def test_corrects_placeholder_and_ai_phrases(self):
        generator = ContentGenerator()
        html = """
        <h1>Sample Product Review</h1>
        <p>I tested this product for a week and it was amazing.</p>
        <p>XYZ Product is the best choice for everyone.</p>
        <p>This article is about chairs, but also includes a webcam comparison.</p>
        <p>Lorem Ipsum placeholder text.</p>
        """

        corrected = generator._apply_quality_corrections(html, "Ergonomic office chair", "ergonomic office chair")

        self.assertNotIn("I tested this", corrected)
        self.assertNotIn("XYZ Product", corrected)
        self.assertNotIn("Lorem Ipsum", corrected)
        self.assertNotIn("webcam comparison", corrected.lower())
        self.assertIn("ergonomic office chair", corrected.lower())
        self.assertIn("osha", corrected.lower())


if __name__ == "__main__":
    unittest.main()
