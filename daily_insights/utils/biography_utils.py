"""
Utility functions for biographical system.

Provides helper functions for:
- Filename sanitization
- Biography file parsing
- Chronological entry formatting
- Category detection
- Synthesis markers
"""

from pathlib import Path
from typing import Dict, List, Optional
import re


def sanitize_biography_filename(name: str) -> str:
    """
    Sanitize subject name for use as filename.

    Parameters
    ----------
    name : str
        Raw subject name

    Returns
    -------
    str
        Sanitized filename (e.g., "Dairy Queen" → "Dairy-Queen")

    Example
    -------
    >>> sanitize_biography_filename("Mike's Place")
    'Mikes-Place'
    >>> sanitize_biography_filename("Uncle Bob (Dad's brother)")
    'Uncle-Bob-Dads-brother'
    """
    # Remove special characters except spaces and hyphens
    cleaned = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with hyphens
    cleaned = re.sub(r'\s+', '-', cleaned.strip())
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    return cleaned


def parse_biography_file(filepath: Path) -> Optional[Dict]:
    """
    Parse biography file into structured data.

    Parameters
    ----------
    filepath : Path
        Path to biography file

    Returns
    -------
    Optional[Dict]
        Parsed biography structure or None if file doesn't exist:
        {
            'subject_name': str,
            'last_updated': str,
            'current_understanding': str,
            'chronological_entries': List[Dict[str, str]]
        }
    """
    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract subject name from header
        name_match = re.search(r'^#\s+(.+?)\s+-\s+Biographical Profile', content, re.MULTILINE)
        subject_name = name_match.group(1) if name_match else None

        # Extract last updated
        updated_match = re.search(r'\*\*Last Updated\*\*:\s+(\d{4}-\d{2}-\d{2})', content)
        last_updated = updated_match.group(1) if updated_match else None

        # Extract current understanding section
        understanding_match = re.search(
            r'## Current Understanding.*?\n\n(.*?)\n\n---\n\n## Chronological Insights',
            content,
            re.DOTALL
        )
        current_understanding = understanding_match.group(1).strip() if understanding_match else ""

        # Extract chronological entries
        chronological_entries = extract_chronological_entries(content)

        return {
            'subject_name': subject_name,
            'last_updated': last_updated,
            'current_understanding': current_understanding,
            'chronological_entries': chronological_entries
        }

    except Exception as e:
        print(f"Error parsing biography file {filepath}: {e}")
        return None


def extract_chronological_entries(content: str) -> List[Dict]:
    """
    Extract chronological entries from biography content.

    Parameters
    ----------
    content : str
        Biography file content

    Returns
    -------
    List[Dict]
        List of entries with date, source_type, and content
        [{'date': '2025-03-22', 'source_type': 'journal', 'content': '...'}, ...]
    """
    entries = []

    # Find the Chronological Insights section
    chrono_match = re.search(r'## Chronological Insights\n\n(.*)', content, re.DOTALL)
    if not chrono_match:
        return entries

    chrono_section = chrono_match.group(1)

    # Extract each entry (### YYYY-MM-DD (Source Type))
    entry_pattern = r'###\s+(\d{4}-\d{2}-\d{2})\s+\(([^)]+)\)\n\n(.*?)(?=\n###\s+\d{4}-\d{2}-\d{2}|$)'
    matches = re.finditer(entry_pattern, chrono_section, re.DOTALL)

    for match in matches:
        entries.append({
            'date': match.group(1),
            'source_type': match.group(2).strip().lower(),
            'content': match.group(3).strip()
        })

    return entries


def format_chronological_entry(
    date: str,
    source_type: str,
    content: str
) -> str:
    """
    Format new chronological entry for appending.

    Parameters
    ----------
    date : str
        Entry date (YYYY-MM-DD)
    source_type : str
        Source type (journal, lifelog, bee)
    content : str
        Biographical content

    Returns
    -------
    str
        Formatted entry for appending to biography file
    """
    # Capitalize source type for display
    source_display = source_type.title()
    if source_type == 'lifelog':
        source_display = 'Lifelog'
    elif source_type == 'bee':
        source_display = 'Bee Transcription'

    template = f"""
### {date} ({source_display})

{content}
"""
    return template


def detect_category_from_content(content: str) -> Optional[str]:
    """
    Detect if content is about person/place/object.

    Parameters
    ----------
    content : str
        Biographical content

    Returns
    -------
    Optional[str]
        Category string ('person', 'place', 'object') or None
    """
    # This is a simple heuristic - the actual detection should come from LLM
    # This function is a fallback for when category isn't explicitly provided

    person_indicators = ['friend', 'family', 'colleague', 'he ', 'she ', 'they ', 'him ', 'her ']
    place_indicators = ['location', 'place', 'where', 'room', 'building', 'restaurant', 'city']
    object_indicators = ['object', 'thing', 'item', 'gift', 'watch', 'heirloom', 'possession']

    content_lower = content.lower()

    person_count = sum(1 for indicator in person_indicators if indicator in content_lower)
    place_count = sum(1 for indicator in place_indicators if indicator in content_lower)
    object_count = sum(1 for indicator in object_indicators if indicator in content_lower)

    max_count = max(person_count, place_count, object_count)

    if max_count == 0:
        return None

    if person_count == max_count:
        return 'person'
    elif place_count == max_count:
        return 'place'
    else:
        return 'object'


def mark_for_synthesis(filepath: Path) -> None:
    """
    Mark biography file for synthesis regeneration.

    Adds marker to file indicating synthesis needed.

    Parameters
    ----------
    filepath : Path
        Biography file path
    """
    if not filepath.exists():
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already marked
        if '<!-- NEEDS_SYNTHESIS -->' in content:
            return

        # Add marker after the header
        marked_content = content.replace(
            '**Last Updated**:',
            '<!-- NEEDS_SYNTHESIS -->\n**Last Updated**:'
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(marked_content)

    except Exception as e:
        print(f"Error marking file for synthesis {filepath}: {e}")


def needs_synthesis(filepath: Path) -> bool:
    """
    Check if biography needs synthesis regeneration.

    Parameters
    ----------
    filepath : Path
        Biography file path

    Returns
    -------
    bool
        True if needs synthesis
    """
    if not filepath.exists():
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '<!-- NEEDS_SYNTHESIS -->' in content

    except Exception as e:
        print(f"Error checking synthesis marker {filepath}: {e}")
        return False


def remove_synthesis_marker(filepath: Path) -> None:
    """
    Remove synthesis marker from biography file.

    Parameters
    ----------
    filepath : Path
        Biography file path
    """
    if not filepath.exists():
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove marker
        updated_content = content.replace('<!-- NEEDS_SYNTHESIS -->\n', '')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)

    except Exception as e:
        print(f"Error removing synthesis marker {filepath}: {e}")
