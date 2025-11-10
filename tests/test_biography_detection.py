"""
Test script for biography detection and extraction functions.

This script tests the detection and extraction pipeline with sample transcripts.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from daily_insights.services.biography_service import (
    detect_biographical_content,
    extract_biographical_content,
    BiographyCategory,
    ContentDepth
)


class TestBiographyDetection(unittest.TestCase):
    """Test biographical content detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.detection_prompt = "Test detection prompt"
        self.sample_transcript_biographical = """
        Journal, I want to talk about Mike. Mike and I go way back to elementary school.
        He was the kid who always had the best ideas for games during recess.
        I remember he had this way of making everyone feel included, even the kids who were usually left out.
        He had curly brown hair that was always a mess and these bright green eyes that lit up when he got excited.
        We spent countless summer afternoons building forts in my backyard, pretending we were explorers.
        One summer we even tried to dig to China in his sandbox.
        Mike taught me that friendship means showing up, even when it's hard.
        When my dad died, Mike didn't say much, he just came over every day after school and sat with me.
        That's who he is - steady, loyal, someone who understands that presence is more important than words.
        """

        self.sample_transcript_not_biographical = """
        Journal entry today. Had a good day at work. Saw Mike briefly, grabbed coffee with Sarah,
        then came home and watched TV. Feeling tired but content.
        """

    def test_detect_biographical_content_success(self):
        """Test successful detection of biographical content."""
        # Mock LLM response for biographical content
        mock_llm = Mock(return_value='''{
            "is_biographical": true,
            "subject_name": "Mike",
            "category": "person",
            "depth": "full",
            "confidence": 0.95,
            "reasoning": "Extended character portrait with vivid descriptions and deep reflection."
        }''')

        result = detect_biographical_content(
            self.sample_transcript_biographical,
            "journal",
            "2025-03-15",
            self.detection_prompt,
            mock_llm
        )

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['subject_name'], "Mike")
        self.assertEqual(result['category'], "person")
        self.assertEqual(result['depth'], "full")
        self.assertEqual(result['date'], "2025-03-15")
        self.assertEqual(result['source_type'], "journal")
        self.assertEqual(result['confidence'], 0.95)

    def test_detect_biographical_content_not_biographical(self):
        """Test detection when content is not biographical."""
        # Mock LLM response for non-biographical content
        mock_llm = Mock(return_value='''{
            "is_biographical": false,
            "reasoning": "General daily reflection with brief mentions of multiple people."
        }''')

        result = detect_biographical_content(
            self.sample_transcript_not_biographical,
            "journal",
            "2025-03-16",
            self.detection_prompt,
            mock_llm
        )

        # Verify result is None
        self.assertIsNone(result)

    def test_detect_biographical_content_with_markdown_json(self):
        """Test detection with markdown-wrapped JSON response."""
        # Mock LLM response with markdown code blocks
        mock_llm = Mock(return_value='''```json
{
    "is_biographical": true,
    "subject_name": "Dairy Queen",
    "category": "place",
    "depth": "lightweight",
    "confidence": 0.8,
    "reasoning": "Meaningful location with specific memories."
}
```''')

        result = detect_biographical_content(
            "Test transcript",
            "lifelog",
            "2025-05-12",
            self.detection_prompt,
            mock_llm
        )

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['subject_name'], "Dairy Queen")
        self.assertEqual(result['category'], "place")
        self.assertEqual(result['depth'], "lightweight")

    def test_detect_biographical_content_invalid_json(self):
        """Test detection with invalid JSON response."""
        # Mock LLM response with invalid JSON
        mock_llm = Mock(return_value="This is not valid JSON")

        result = detect_biographical_content(
            "Test transcript",
            "journal",
            "2025-03-15",
            self.detection_prompt,
            mock_llm
        )

        # Verify result is None for invalid JSON
        self.assertIsNone(result)

    def test_detect_biographical_content_missing_fields(self):
        """Test detection with missing required fields."""
        # Mock LLM response missing required fields
        mock_llm = Mock(return_value='''{
            "is_biographical": true,
            "subject_name": "Mike"
        }''')

        result = detect_biographical_content(
            "Test transcript",
            "journal",
            "2025-03-15",
            self.detection_prompt,
            mock_llm
        )

        # Verify result is None when required fields missing
        self.assertIsNone(result)

    def test_detect_biographical_content_invalid_category(self):
        """Test detection with invalid category."""
        # Mock LLM response with invalid category
        mock_llm = Mock(return_value='''{
            "is_biographical": true,
            "subject_name": "Something",
            "category": "invalid_category",
            "depth": "full",
            "confidence": 0.9
        }''')

        result = detect_biographical_content(
            "Test transcript",
            "journal",
            "2025-03-15",
            self.detection_prompt,
            mock_llm
        )

        # Verify result is None for invalid category
        self.assertIsNone(result)


class TestBiographyExtraction(unittest.TestCase):
    """Test biographical content extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.extraction_prompt = "Test extraction prompt"
        self.sample_transcript = "Test biographical transcript content"

    def test_extract_biographical_content_full(self):
        """Test full biographical content extraction."""
        # Mock LLM response
        mock_llm = Mock(return_value="""
## Portrait

Mike is a great friend with curly brown hair.

## Memory and Moments

We spent summers building forts together.

## Meaning and Impact

Mike taught me about loyalty and friendship.
""")

        result = extract_biographical_content(
            self.sample_transcript,
            ContentDepth.FULL,
            self.extraction_prompt,
            mock_llm
        )

        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("Portrait", result)
        self.assertIn("Memory and Moments", result)
        self.assertIn("Meaning and Impact", result)

    def test_extract_biographical_content_lightweight(self):
        """Test lightweight biographical content extraction."""
        # Mock LLM response
        mock_llm = Mock(return_value="""
**Key Facts:**
- Mike has curly brown hair
- We've been friends since elementary school

**Memorable Moments:**
- Building forts in the backyard
- He was there when my dad died

**Personal Significance:**
- Taught me about loyalty
""")

        result = extract_biographical_content(
            self.sample_transcript,
            ContentDepth.LIGHTWEIGHT,
            self.extraction_prompt,
            mock_llm
        )

        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("Key Facts", result)
        self.assertIn("Memorable Moments", result)
        self.assertIn("Personal Significance", result)

    def test_extract_biographical_content_llm_error(self):
        """Test extraction when LLM raises error."""
        # Mock LLM to raise exception
        mock_llm = Mock(side_effect=Exception("LLM API error"))

        with self.assertRaises(Exception):
            extract_biographical_content(
                self.sample_transcript,
                ContentDepth.FULL,
                self.extraction_prompt,
                mock_llm
            )


if __name__ == '__main__':
    unittest.main()
