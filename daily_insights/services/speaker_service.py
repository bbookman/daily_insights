"""Service for speaker identification in transcripts."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from daily_insights.api.speaker_llm_client import (
    identify_speakers_with_llm,
    identify_speakers_with_llm_async
)

# Config file paths - relative to project root
_CONFIG_DIR = Path(__file__).parent.parent / "config"
SPEAKER_PROFILES_FILE = _CONFIG_DIR / "speaker_profiles.json"
TRAINING_EXAMPLES_FILE = _CONFIG_DIR / "speaker_training_examples.json"
PROCESSING_METADATA_FILE = _CONFIG_DIR / "processing_metadata.json"


def load_speaker_profiles() -> Dict:
    """
    Load speaker profiles from configuration file.

    Prefers the unified entity registry (entity_profiles.json) and
    filters to speakers only. Falls back to legacy speaker_profiles.json.

    Returns
    -------
    Dict
        Dictionary of speaker profiles with speech patterns and characteristics

    Example
    -------
    >>> profiles = load_speaker_profiles()
    >>> 'Bruce' in profiles['speakers']
    True
    """
    # Try unified entity registry first
    try:
        from daily_insights.services.entity_registry import get_speaker_profiles_legacy_format
        profiles = get_speaker_profiles_legacy_format()
        if profiles.get('speakers'):
            return profiles
    except ImportError:
        pass  # Entity registry not available, fall back to legacy
    except Exception as e:
        print(f"Warning: Error loading from entity registry: {e}")

    # Fall back to legacy speaker_profiles.json
    if not SPEAKER_PROFILES_FILE.exists():
        print(f"Warning: Speaker profiles file not found: {SPEAKER_PROFILES_FILE}")
        return {"version": "1.0", "speakers": {}}

    try:
        with open(SPEAKER_PROFILES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading speaker profiles: {e}")
        return {"version": "1.0", "speakers": {}}


def load_training_examples() -> List[Dict]:
    """
    Load training examples for speaker identification.

    Returns
    -------
    List[Dict]
        List of training examples with labeled speaker conversations

    Example
    -------
    >>> examples = load_training_examples()
    >>> len(examples)
    15
    """
    if not TRAINING_EXAMPLES_FILE.exists():
        print(f"Warning: Training examples file not found: {TRAINING_EXAMPLES_FILE}")
        return []

    try:
        with open(TRAINING_EXAMPLES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("examples", [])
    except Exception as e:
        print(f"Error loading training examples: {e}")
        return []


def save_training_examples(examples: List[Dict]) -> None:
    """
    Save training examples to file.

    Parameters
    ----------
    examples : List[Dict]
        List of training examples to save

    Example
    -------
    >>> examples = [{"snippet": "...", "speaker": "Bruce"}]
    >>> save_training_examples(examples)
    """
    data = {
        "version": 1,
        "last_updated": datetime.now().isoformat(),
        "examples": examples
    }

    try:
        with open(TRAINING_EXAMPLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(examples)} training examples")
    except Exception as e:
        print(f"Error saving training examples: {e}")


def identify_speakers(transcript: str) -> List[Dict]:
    """
    Identify speakers in a transcript using LLM analysis.

    Parameters
    ----------
    transcript : str
        The conversation transcript with generic speaker labels

    Returns
    -------
    List[Dict]
        Speaker identification results with keys:
        - original_label: str
        - identified_as: str
        - confidence: float
        - reasoning: str

    Example
    -------
    >>> results = identify_speakers("Speaker 1: Hello\nSpeaker 2: Hi there")
    >>> results[0]['identified_as']
    'Bruce'
    """
    profiles_data = load_speaker_profiles()
    speaker_profiles = profiles_data.get("speakers", {})

    training_examples = load_training_examples()

    if not speaker_profiles:
        print("Warning: No speaker profiles loaded. Cannot identify speakers.")
        return []

    print(f"Identifying speakers using {len(speaker_profiles)} profiles and {len(training_examples)} training examples...")

    return identify_speakers_with_llm(transcript, speaker_profiles, training_examples)


async def identify_speakers_async(transcript: str) -> List[Dict]:
    """
    Async version: Identify speakers in a transcript using LLM analysis.

    Parameters
    ----------
    transcript : str
        The conversation transcript with generic speaker labels

    Returns
    -------
    List[Dict]
        Speaker identification results

    Example
    -------
    >>> results = await identify_speakers_async("Speaker 1: Hello")
    >>> results[0]['confidence']
    0.95
    """
    profiles_data = load_speaker_profiles()
    speaker_profiles = profiles_data.get("speakers", {})

    training_examples = load_training_examples()

    if not speaker_profiles:
        print("Warning: No speaker profiles loaded. Cannot identify speakers.")
        return []

    print(f"Identifying speakers using {len(speaker_profiles)} profiles and {len(training_examples)} training examples...")

    return await identify_speakers_with_llm_async(transcript, speaker_profiles, training_examples)


def apply_speaker_labels(
    transcript: str,
    speaker_mappings: List[Dict],
    confidence_threshold_high: float = 0.85,
    confidence_threshold_medium: float = 0.60
) -> str:
    """
    Apply identified speaker labels to transcript.

    Parameters
    ----------
    transcript : str
        Original transcript with generic labels
    speaker_mappings : List[Dict]
        Speaker identification results from identify_speakers()
    confidence_threshold_high : float
        Confidence threshold for direct replacement (default: 0.85)
    confidence_threshold_medium : float
        Confidence threshold for labeled replacement (default: 0.60)

    Returns
    -------
    str
        Transcript with speaker labels replaced according to confidence tiers:
        - High (≥0.85): "Speaker 1" → "Bruce"
        - Medium (0.60-0.85): "Speaker 1" → "Bruce [72%]"
        - Low (<0.60): "Speaker 1" → unchanged

    Example
    -------
    >>> mappings = [{"original_label": "Speaker 1", "identified_as": "Bruce", "confidence": 0.95}]
    >>> result = apply_speaker_labels("- Speaker 1: Hello", mappings)
    >>> "Bruce:" in result
    True
    """
    modified_transcript = transcript

    for mapping in speaker_mappings:
        original = mapping["original_label"]
        identified = mapping["identified_as"]
        confidence = mapping["confidence"]

        # Skip if speaker could not be identified
        if identified == "Unknown":
            continue

        # Determine replacement based on confidence tier
        if confidence >= confidence_threshold_high:
            # High confidence: direct replacement
            replacement = identified
        elif confidence >= confidence_threshold_medium:
            # Medium confidence: include confidence percentage
            confidence_pct = int(confidence * 100)
            replacement = f"{identified} [{confidence_pct}%]"
        else:
            # Low confidence: leave unchanged
            continue

        # Replace all instances of the original label
        # Match patterns like "- Speaker 1:" or "**Speaker 1:**"
        patterns = [
            (f"- {original}:", f"- {replacement}:"),
            (f"**{original}:**", f"**{replacement}:**"),
            (f"{original}:", f"{replacement}:"),
        ]

        for pattern_old, pattern_new in patterns:
            modified_transcript = modified_transcript.replace(pattern_old, pattern_new)

    return modified_transcript


def extract_speaker_instances(transcript: str) -> List[Tuple[str, str]]:
    """
    Extract all speaker instances from a transcript.

    Filters out non-speaker content like markdown headers, section dividers,
    and very short utterances that don't represent actual speech.

    Parameters
    ----------
    transcript : str
        The transcript text

    Returns
    -------
    List[Tuple[str, str]]
        List of (speaker_label, utterance) tuples

    Example
    -------
    >>> instances = extract_speaker_instances("- Speaker 1: Hello\n- Speaker 2: Hi")
    >>> len(instances)
    2
    >>> instances[0]
    ('Speaker 1', 'Hello')
    """
    instances = []

    # Pattern to match speaker labels and their utterances
    # Need to handle timestamps in labels like "Unknown (3/24/25 1:00 PM)"
    # Strategy: Match until we find ): followed by space (for timestamps)
    #           OR match until : followed by space (for simple labels)

    # Pattern 1: Speaker with timestamp - "Unknown (3/24/25 1:00 PM): utterance"
    timestamp_pattern = r"^[-*\s]*(.+\)):\s*(.+)$"

    # Pattern 2: Simple speaker - "Speaker 1: utterance"
    simple_pattern = r"^[-*\s]*([^:]+):\s*(.+)$"

    for line in transcript.split('\n'):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown headers (### 06:47, ## Title, # Heading)
        if line.startswith('#'):
            continue

        # Skip section dividers (---)
        if line.startswith('---'):
            continue

        # Try timestamp pattern first (more specific)
        match = re.match(timestamp_pattern, line)

        # If no timestamp match, try simple pattern
        if not match:
            match = re.match(simple_pattern, line)

        if match:
            speaker_label = match.group(1).strip('* -#')
            utterance = match.group(2).strip()

            # Filter out false positives:
            # - Very short utterances (< 3 chars) like "47", "30"
            # - Utterances that are just numbers or punctuation
            # - Speaker labels that look like times (just digits and colons)
            if (utterance and
                len(utterance) >= 3 and
                not utterance.isdigit() and
                not re.match(r'^[\d:]+$', speaker_label)):
                instances.append((speaker_label, utterance))

    return instances


def mark_file_processed(file_path: str) -> None:
    """
    Mark a transcript file as processed in metadata.

    Parameters
    ----------
    file_path : str
        Path to the processed file

    Example
    -------
    >>> mark_file_processed("lifelogs/2025-03-01.md")
    """
    try:
        if PROCESSING_METADATA_FILE.exists():
            with open(PROCESSING_METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "processed_files": []
            }

        if file_path not in metadata["processed_files"]:
            metadata["processed_files"].append(file_path)
            metadata["last_updated"] = datetime.now().isoformat()

            with open(PROCESSING_METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Error updating processing metadata: {e}")


def is_file_processed(file_path: str) -> bool:
    """
    Check if a transcript file has been processed.

    Parameters
    ----------
    file_path : str
        Path to check

    Returns
    -------
    bool
        True if file has been processed

    Example
    -------
    >>> is_file_processed("lifelogs/2025-03-01.md")
    False
    """
    try:
        if not PROCESSING_METADATA_FILE.exists():
            return False

        with open(PROCESSING_METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            return file_path in metadata.get("processed_files", [])

    except Exception as e:
        print(f"Error checking processing metadata: {e}")
        return False


def save_speaker_profile(speaker_name: str, profile_data: Dict) -> bool:
    """
    Save or update a single speaker profile.

    Parameters
    ----------
    speaker_name : str
        Name of the speaker
    profile_data : Dict
        Speaker profile data with keys: relationship, relationships, languages, speech_patterns, added_date

    Returns
    -------
    bool
        True if saved successfully, False otherwise

    Example
    -------
    >>> profile = {"relationship": "friend", "languages": {"English": "fluent"}, ...}
    >>> save_speaker_profile("Matt", profile)
    True
    """
    try:
        # Load existing profiles
        profiles_data = load_speaker_profiles()

        # Add or update the speaker
        profiles_data["speakers"][speaker_name] = profile_data

        # Save back to file
        with open(SPEAKER_PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error saving speaker profile: {e}")
        return False


def get_reverse_relationship(relationship: str) -> str:
    """
    Get the reverse/reciprocal relationship.

    Parameters
    ----------
    relationship : str
        Original relationship (e.g., "son", "friend", "spouse")

    Returns
    -------
    str
        Reverse relationship, or "?" if unknown and needs manual input

    Example
    -------
    >>> get_reverse_relationship("son")
    'father/mother'
    >>> get_reverse_relationship("friend")
    'friend'
    >>> get_reverse_relationship("colleague")
    'colleague'
    """
    # Define common relationship mappings
    REVERSE_MAP = {
        # Family relationships
        "son": "father/mother",
        "daughter": "father/mother",
        "father": "son/daughter",
        "mother": "son/daughter",
        "parent": "son/daughter",
        "brother": "brother/sister",
        "sister": "brother/sister",
        "sibling": "sibling",
        "spouse": "spouse",
        "husband": "wife",
        "wife": "husband",
        "grandfather": "grandson/granddaughter",
        "grandmother": "grandson/granddaughter",
        "grandson": "grandfather/grandmother",
        "granddaughter": "grandfather/grandmother",
        "uncle": "nephew/niece",
        "aunt": "nephew/niece",
        "nephew": "uncle/aunt",
        "niece": "uncle/aunt",
        "cousin": "cousin",

        # In-law relationships
        "brother-in-law": "brother-in-law/sister-in-law",
        "sister-in-law": "brother-in-law/sister-in-law",
        "father-in-law": "son-in-law/daughter-in-law",
        "mother-in-law": "son-in-law/daughter-in-law",
        "son-in-law": "father-in-law/mother-in-law",
        "daughter-in-law": "father-in-law/mother-in-law",

        # Social relationships
        "friend": "friend",
        "colleague": "colleague",
        "coworker": "coworker",
        "neighbor": "neighbor",
        "classmate": "classmate",
        "roommate": "roommate",

        # Professional relationships
        "boss": "employee/subordinate",
        "employee": "boss/manager",
        "manager": "employee/subordinate",
        "mentor": "mentee",
        "mentee": "mentor",
        "teacher": "student",
        "student": "teacher",
        "doctor": "patient",
        "patient": "doctor",
        "therapist": "client",
        "psychologist": "client",
        "psychiatrist": "patient",

        # Device/Assistant
        "device": "owner",
        "assistant": "user",

        # Self
        "self": "self",
    }

    # Return mapped reverse, or "?" if unknown
    return REVERSE_MAP.get(relationship.lower(), "?")
