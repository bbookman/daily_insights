"""
Unit tests for biography_utils module.

Tests utility functions for biographical system including filename sanitization,
file parsing, chronological entry formatting, and synthesis markers.
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from daily_insights.utils.biography_utils import (
    sanitize_biography_filename,
    parse_biography_file,
    extract_chronological_entries,
    format_chronological_entry,
    detect_category_from_content,
    mark_for_synthesis,
    needs_synthesis,
    remove_synthesis_marker
)


class TestSanitizeBiographyFilename(unittest.TestCase):
    """Test sanitize_biography_filename function."""

    def test_basic_name(self):
        """Test basic name without special characters."""
        result = sanitize_biography_filename("Mike")
        self.assertEqual(result, "Mike")

    def test_name_with_spaces(self):
        """Test name with spaces gets hyphens."""
        result = sanitize_biography_filename("Dairy Queen")
        self.assertEqual(result, "Dairy-Queen")

    def test_name_with_apostrophe(self):
        """Test apostrophes are removed."""
        result = sanitize_biography_filename("Mike's Place")
        self.assertEqual(result, "Mikes-Place")

    def test_name_with_parentheses(self):
        """Test parentheses are removed."""
        result = sanitize_biography_filename("Uncle Bob (Dad's brother)")
        self.assertEqual(result, "Uncle-Bob-Dads-brother")

    def test_multiple_spaces(self):
        """Test multiple spaces become single hyphen."""
        result = sanitize_biography_filename("Central   Park")
        self.assertEqual(result, "Central-Park")

    def test_leading_trailing_spaces(self):
        """Test leading/trailing spaces are removed."""
        result = sanitize_biography_filename("  Mike  ")
        self.assertEqual(result, "Mike")

    def test_multiple_hyphens(self):
        """Test multiple consecutive hyphens become single hyphen."""
        result = sanitize_biography_filename("Test--Name")
        self.assertEqual(result, "Test-Name")


class TestFormatChronologicalEntry(unittest.TestCase):
    """Test format_chronological_entry function."""

    def test_journal_entry(self):
        """Test formatting a journal entry."""
        result = format_chronological_entry(
            "2025-03-15",
            "journal",
            "Mike is a great friend."
        )
        self.assertIn("### 2025-03-15 (Journal)", result)
        self.assertIn("Mike is a great friend.", result)

    def test_lifelog_entry(self):
        """Test formatting a lifelog entry."""
        result = format_chronological_entry(
            "2025-06-22",
            "lifelog",
            "Saw Mike at coffee shop."
        )
        self.assertIn("### 2025-06-22 (Lifelog)", result)
        self.assertIn("Saw Mike at coffee shop.", result)

    def test_bee_entry(self):
        """Test formatting a bee transcription entry."""
        result = format_chronological_entry(
            "2025-09-10",
            "bee",
            "Mike came by today."
        )
        self.assertIn("### 2025-09-10 (Bee Transcription)", result)
        self.assertIn("Mike came by today.", result)


class TestDetectCategoryFromContent(unittest.TestCase):
    """Test detect_category_from_content function."""

    def test_person_indicators(self):
        """Test content with person indicators."""
        content = "He is a friend who always helps me."
        result = detect_category_from_content(content)
        self.assertEqual(result, "person")

    def test_place_indicators(self):
        """Test content with place indicators."""
        content = "The restaurant is located in the city where I grew up."
        result = detect_category_from_content(content)
        self.assertEqual(result, "place")

    def test_object_indicators(self):
        """Test content with object indicators."""
        content = "The watch is a cherished heirloom item my father gave me."
        result = detect_category_from_content(content)
        self.assertEqual(result, "object")

    def test_no_clear_category(self):
        """Test content without clear category indicators."""
        content = "Today was a good day."
        result = detect_category_from_content(content)
        self.assertIsNone(result)


class TestSynthesisMarkers(unittest.TestCase):
    """Test synthesis marker functions."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_mark_for_synthesis(self):
        """Test marking a file for synthesis."""
        # Create test file
        test_file = self.test_dir / "test.md"
        test_file.write_text("# Test\n\n**Last Updated**: 2025-03-15\n")

        # Mark for synthesis
        mark_for_synthesis(test_file)

        # Verify marker was added
        content = test_file.read_text()
        self.assertIn("<!-- NEEDS_SYNTHESIS -->", content)

    def test_mark_already_marked(self):
        """Test marking a file that's already marked."""
        # Create test file with marker
        test_file = self.test_dir / "test.md"
        test_file.write_text("# Test\n\n<!-- NEEDS_SYNTHESIS -->\n**Last Updated**: 2025-03-15\n")

        # Mark again
        mark_for_synthesis(test_file)

        # Verify only one marker exists
        content = test_file.read_text()
        self.assertEqual(content.count("<!-- NEEDS_SYNTHESIS -->"), 1)

    def test_needs_synthesis_true(self):
        """Test checking if file needs synthesis (true)."""
        # Create test file with marker
        test_file = self.test_dir / "test.md"
        test_file.write_text("# Test\n\n<!-- NEEDS_SYNTHESIS -->\n**Last Updated**: 2025-03-15\n")

        # Check if needs synthesis
        result = needs_synthesis(test_file)
        self.assertTrue(result)

    def test_needs_synthesis_false(self):
        """Test checking if file needs synthesis (false)."""
        # Create test file without marker
        test_file = self.test_dir / "test.md"
        test_file.write_text("# Test\n\n**Last Updated**: 2025-03-15\n")

        # Check if needs synthesis
        result = needs_synthesis(test_file)
        self.assertFalse(result)

    def test_remove_synthesis_marker(self):
        """Test removing synthesis marker."""
        # Create test file with marker
        test_file = self.test_dir / "test.md"
        test_file.write_text("# Test\n\n<!-- NEEDS_SYNTHESIS -->\n**Last Updated**: 2025-03-15\n")

        # Remove marker
        remove_synthesis_marker(test_file)

        # Verify marker was removed
        content = test_file.read_text()
        self.assertNotIn("<!-- NEEDS_SYNTHESIS -->", content)


class TestParseBiographyFile(unittest.TestCase):
    """Test parse_biography_file function."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_parse_valid_biography(self):
        """Test parsing a valid biography file."""
        # Create test biography file
        test_file = self.test_dir / "mike.md"
        content = """# Mike - Biographical Profile

**Last Updated**: 2025-03-15

---

## Current Understanding (Auto-synthesized)

Mike is a great friend who has been there for me.

---

## Chronological Insights

### 2025-03-01 (Journal)

First memory of Mike from elementary school.

### 2025-03-15 (Lifelog)

Saw Mike at the coffee shop today.
"""
        test_file.write_text(content)

        # Parse the file
        result = parse_biography_file(test_file)

        # Verify parsing
        self.assertIsNotNone(result)
        self.assertEqual(result['subject_name'], "Mike")
        self.assertEqual(result['last_updated'], "2025-03-15")
        self.assertIn("great friend", result['current_understanding'])
        self.assertEqual(len(result['chronological_entries']), 2)

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        test_file = self.test_dir / "nonexistent.md"
        result = parse_biography_file(test_file)
        self.assertIsNone(result)


class TestExtractChronologicalEntries(unittest.TestCase):
    """Test extract_chronological_entries function."""

    def test_extract_multiple_entries(self):
        """Test extracting multiple chronological entries."""
        content = """# Mike - Biographical Profile

**Last Updated**: 2025-03-15

---

## Current Understanding (Auto-synthesized)

Mike is a great friend.

---

## Chronological Insights

### 2025-03-01 (Journal)

First memory of Mike.

### 2025-03-15 (Lifelog)

Saw Mike today.

### 2025-03-22 (Bee Transcription)

Talked with Mike about old times.
"""
        entries = extract_chronological_entries(content)

        # Verify extraction
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]['date'], "2025-03-01")
        self.assertEqual(entries[0]['source_type'], "journal")
        self.assertIn("First memory", entries[0]['content'])

        self.assertEqual(entries[1]['date'], "2025-03-15")
        self.assertEqual(entries[1]['source_type'], "lifelog")

        self.assertEqual(entries[2]['date'], "2025-03-22")
        self.assertEqual(entries[2]['source_type'], "bee transcription")

    def test_extract_no_entries(self):
        """Test extracting from content with no chronological entries."""
        content = """# Mike - Biographical Profile

**Last Updated**: 2025-03-15

---

## Current Understanding (Auto-synthesized)

Mike is a great friend.
"""
        entries = extract_chronological_entries(content)
        self.assertEqual(len(entries), 0)


if __name__ == '__main__':
    unittest.main()
