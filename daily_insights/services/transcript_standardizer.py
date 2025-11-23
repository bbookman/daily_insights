"""
Service for standardizing transcripts with STT corrections.

Applies speech-to-text error corrections at the earliest point in the
processing pipeline, before speaker labeling or biography extraction.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from daily_insights.services.entity_registry import (
    get_all_stt_corrections,
    get_all_aliases
)

logger = logging.getLogger(__name__)


def load_stt_corrections() -> Dict[str, str]:
    """
    Build aggregated correction map from entity registry.

    Returns
    -------
    Dict[str, str]
        Map of incorrect spellings to correct spellings

    Example
    -------
    >>> corrections = load_stt_corrections()
    >>> corrections.get('Crape')
    'Grape'
    >>> corrections.get('Joel Gilmet')
    'Joel Guilmet'
    """
    corrections = get_all_stt_corrections()
    logger.debug("Loaded %d STT corrections from entity registry", len(corrections))
    return corrections


def standardize_transcript(
    content: str,
    corrections: Optional[Dict[str, str]] = None
) -> str:
    """
    Apply STT corrections to transcript content with word-boundary awareness.

    Corrections are applied in order of decreasing length to prevent
    partial replacements (e.g., "Joel Gilmet" before "Joel").

    Parameters
    ----------
    content : str
        The transcript content to standardize
    corrections : Optional[Dict[str, str]]
        Custom corrections map. If None, loads from entity registry.

    Returns
    -------
    str
        Standardized transcript with corrections applied

    Example
    -------
    >>> content = "Bruce was talking to Joel Gilmet about Crape the cat"
    >>> standardize_transcript(content)
    'Bruce was talking to Joel Guilmet about Grape the cat'
    """
    if corrections is None:
        corrections = load_stt_corrections()

    if not corrections:
        logger.debug("No STT corrections to apply")
        return content

    result = content

    # Sort by length descending to match longest phrases first
    # e.g., "Joel Gilmet" before "Joel"
    sorted_corrections = sorted(corrections.items(), key=lambda x: -len(x[0]))

    for wrong, right in sorted_corrections:
        # Word-boundary aware replacement using regex
        # This prevents partial matches within words
        pattern = r'\b' + re.escape(wrong) + r'\b'
        result = re.sub(pattern, right, result, flags=re.IGNORECASE)

    return result


def report_corrections(
    content: str,
    corrections: Optional[Dict[str, str]] = None
) -> List[Dict]:
    """
    Dry-run: report corrections that would be made without applying them.

    Parameters
    ----------
    content : str
        The transcript content to analyze
    corrections : Optional[Dict[str, str]]
        Custom corrections map. If None, loads from entity registry.

    Returns
    -------
    List[Dict]
        List of corrections that would be made, each with keys:
        - wrong: str - The incorrect text found
        - right: str - The correction that would be applied
        - count: int - Number of occurrences found
        - positions: List[int] - Character positions of matches

    Example
    -------
    >>> content = "Crape jumped on Joel Gilmet"
    >>> report = report_corrections(content)
    >>> report[0]
    {'wrong': 'Joel Gilmet', 'right': 'Joel Guilmet', 'count': 1, 'positions': [17]}
    """
    if corrections is None:
        corrections = load_stt_corrections()

    if not corrections:
        return []

    report = []

    # Sort by length descending for consistent reporting order
    sorted_corrections = sorted(corrections.items(), key=lambda x: -len(x[0]))

    for wrong, right in sorted_corrections:
        pattern = r'\b' + re.escape(wrong) + r'\b'
        matches = list(re.finditer(pattern, content, flags=re.IGNORECASE))

        if matches:
            report.append({
                'wrong': wrong,
                'right': right,
                'count': len(matches),
                'positions': [m.start() for m in matches]
            })

    return report


def standardize_file(
    file_path: Path,
    dry_run: bool = False
) -> Tuple[bool, List[Dict]]:
    """
    Standardize a transcript file in place.

    Parameters
    ----------
    file_path : Path
        Path to the transcript file
    dry_run : bool
        If True, report changes without applying them

    Returns
    -------
    Tuple[bool, List[Dict]]
        - bool: True if changes were made (or would be made in dry_run)
        - List[Dict]: Report of corrections made/to be made

    Example
    -------
    >>> made_changes, report = standardize_file(Path("lifelog.md"))
    >>> if made_changes:
    ...     print(f"Made {len(report)} corrections")
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error("Error reading file %s: %s", file_path, e)
        return False, []

    corrections = load_stt_corrections()
    report = report_corrections(content, corrections)

    if not report:
        logger.debug("No corrections needed for %s", file_path)
        return False, []

    if dry_run:
        logger.info("Dry run: Would make %d corrections in %s", len(report), file_path)
        return True, report

    # Apply corrections
    standardized = standardize_transcript(content, corrections)

    try:
        file_path.write_text(standardized, encoding='utf-8')
        logger.info("Applied %d corrections to %s", len(report), file_path)
        return True, report
    except Exception as e:
        logger.error("Error writing file %s: %s", file_path, e)
        return False, report


def standardize_directory(
    directory: Path,
    pattern: str = "*.md",
    dry_run: bool = False
) -> Dict[str, List[Dict]]:
    """
    Standardize all matching files in a directory.

    Parameters
    ----------
    directory : Path
        Directory to process
    pattern : str
        Glob pattern for files to process (default: "*.md")
    dry_run : bool
        If True, report changes without applying them

    Returns
    -------
    Dict[str, List[Dict]]
        Map of file paths to their correction reports

    Example
    -------
    >>> results = standardize_directory(Path("lifelogs/"), dry_run=True)
    >>> for file_path, corrections in results.items():
    ...     print(f"{file_path}: {len(corrections)} corrections")
    """
    if not directory.exists():
        logger.error("Directory not found: %s", directory)
        return {}

    results = {}

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            made_changes, report = standardize_file(file_path, dry_run=dry_run)
            if report:
                results[str(file_path)] = report

    total_corrections = sum(len(r) for r in results.values())
    action = "Would apply" if dry_run else "Applied"
    logger.info("%s %d corrections across %d files", action, total_corrections, len(results))

    return results


def get_correction_summary(results: Dict[str, List[Dict]]) -> Dict[str, int]:
    """
    Summarize corrections by type across all files.

    Parameters
    ----------
    results : Dict[str, List[Dict]]
        Results from standardize_directory()

    Returns
    -------
    Dict[str, int]
        Map of "wrong -> right" to total count across all files

    Example
    -------
    >>> results = standardize_directory(Path("lifelogs/"), dry_run=True)
    >>> summary = get_correction_summary(results)
    >>> summary
    {'Crape -> Grape': 15, 'Joel Gilmet -> Joel Guilmet': 3}
    """
    summary = {}

    for corrections in results.values():
        for correction in corrections:
            key = f"{correction['wrong']} -> {correction['right']}"
            summary[key] = summary.get(key, 0) + correction['count']

    # Sort by count descending
    return dict(sorted(summary.items(), key=lambda x: -x[1]))
