"""CLI commands for speaker management."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field

from daily_insights.logging_config import get_logger
from daily_insights.services.speaker_service import (
    load_speaker_profiles,
    load_training_examples,
    save_training_examples,
    extract_speaker_instances,
    save_speaker_profile,
    get_reverse_relationship,
    SPEAKER_PROFILES_FILE
)
from daily_insights.api.speaker_llm_client import analyze_speaker_patterns_with_llm

logger = get_logger(__name__)

# Configuration constants
MIN_UTTERANCE_WORDS = 6
MAX_SAMPLE_EXAMPLES = 3
CONTEXT_LINES_BEFORE = 4
CONTEXT_LINES_AFTER = 4
SEPARATOR_WIDTH = 70


# ============================================================================
# Data Classes for Refactored label_training_transcript
# ============================================================================

@dataclass
class FilterStatistics:
    """Statistics from utterance filtering."""
    original_count: int
    filtered_count: int
    skipped_count: int

    def __str__(self) -> str:
        return (
            f"Found {self.original_count} speaker instances.\n"
            f"Filtered to {self.filtered_count} substantial utterances "
            f"(≥{MIN_UTTERANCE_WORDS} words).\n"
            f"Skipped {self.skipped_count} brief utterances (<{MIN_UTTERANCE_WORDS} words)."
        )


@dataclass
class SpeakerGroups:
    """Grouped speaker instances with metadata."""
    grouped: Dict[str, List[str]]  # speaker_label -> utterances
    indices: Dict[str, List[int]]  # speaker_label -> indices in filtered list
    labels: List[str]  # sorted unique speaker labels

    @property
    def speaker_count(self) -> int:
        """Number of unique speaker labels."""
        return len(self.labels)


@dataclass
class UserChoice:
    """Result of user choice input."""
    choice: str  # speaker name, "skip", or "quit"
    is_quit: bool
    is_skip: bool

    @property
    def is_valid_speaker(self) -> bool:
        """Check if choice is a valid speaker name."""
        return not self.is_quit and not self.is_skip


@dataclass
class SessionStatistics:
    """Statistics from training session."""
    new_examples_count: int
    duplicates_removed: int
    unique_examples_added: int
    total_examples: int

    def __str__(self) -> str:
        return (
            f"\n=== Training Session Complete ===\n"
            f"New examples created: {self.new_examples_count}\n"
            f"Duplicates removed: {self.duplicates_removed}\n"
            f"Unique examples added: {self.unique_examples_added}\n"
            f"Total training examples: {self.total_examples}"
        )


# ============================================================================
# Helper Functions for label_training_transcript
# ============================================================================

def load_transcript_file(transcript_file: str) -> Optional[str]:
    """
    Load and validate transcript file.

    Parameters
    ----------
    transcript_file : str
        Path to transcript markdown file

    Returns
    -------
    Optional[str]
        Transcript content if successful, None otherwise

    Example
    -------
    >>> content = load_transcript_file("lifelogs/2025-03-01.md")
    >>> content is not None
    True
    """
    file_path = Path(transcript_file)

    if not file_path.exists():
        logger.error("File not found: %s", transcript_file)
        print(f"Error: File not found: {transcript_file}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error("Error reading file: %s", transcript_file, exc_info=True)
        print(f"Error reading file: {e}")
        return None


def validate_speaker_profiles() -> Optional[List[str]]:
    """
    Validate that speaker profiles exist and are configured.

    Returns
    -------
    Optional[List[str]]
        List of known speaker names if valid, None otherwise

    Example
    -------
    >>> speakers = validate_speaker_profiles()
    >>> isinstance(speakers, list)
    True
    """
    profiles_data = load_speaker_profiles()
    known_speakers = list(profiles_data.get("speakers", {}).keys())

    if not known_speakers:
        logger.error(
            "No speaker profiles found. Create profiles in %s",
            SPEAKER_PROFILES_FILE
        )
        print("Error: No speaker profiles found. Please create speaker profiles first.")
        print(f"Edit {SPEAKER_PROFILES_FILE} to add speaker profiles.")
        return None

    return known_speakers


def filter_substantial_utterances(
    instances: List[Tuple[str, str]],
    min_words: int = MIN_UTTERANCE_WORDS
) -> Tuple[List[Tuple[str, str]], FilterStatistics]:
    """
    Filter speaker instances to keep only substantial utterances.

    Parameters
    ----------
    instances : List[Tuple[str, str]]
        List of (speaker_label, utterance) tuples
    min_words : int, default=MIN_UTTERANCE_WORDS
        Minimum word count for substantial utterances

    Returns
    -------
    Tuple[List[Tuple[str, str]], FilterStatistics]
        Filtered instances and statistics

    Example
    -------
    >>> instances = [("Speaker 1", "Yes"), ("Speaker 2", "I agree with that")]
    >>> filtered, stats = filter_substantial_utterances(instances, min_words=3)
    >>> len(filtered)
    1
    """
    filtered_instances = [
        (speaker_label, utterance)
        for speaker_label, utterance in instances
        if len(utterance.split()) >= min_words
    ]

    stats = FilterStatistics(
        original_count=len(instances),
        filtered_count=len(filtered_instances),
        skipped_count=len(instances) - len(filtered_instances)
    )

    logger.debug(
        "Filtered utterances: %d original, %d filtered, %d skipped",
        stats.original_count, stats.filtered_count, stats.skipped_count
    )

    return filtered_instances, stats


def group_instances_by_speaker(
    instances: List[Tuple[str, str]]
) -> SpeakerGroups:
    """
    Group instances by speaker label with index tracking.

    Parameters
    ----------
    instances : List[Tuple[str, str]]
        List of (speaker_label, utterance) tuples

    Returns
    -------
    SpeakerGroups
        Grouped instances with metadata

    Example
    -------
    >>> instances = [("Speaker 1", "Hello"), ("Speaker 2", "Hi")]
    >>> groups = group_instances_by_speaker(instances)
    >>> groups.speaker_count
    2
    """
    grouped: Dict[str, List[str]] = {}
    indices: Dict[str, List[int]] = {}

    for idx, (speaker_label, utterance) in enumerate(instances):
        if speaker_label not in grouped:
            grouped[speaker_label] = []
            indices[speaker_label] = []
        grouped[speaker_label].append(utterance)
        indices[speaker_label].append(idx)

    return SpeakerGroups(
        grouped=grouped,
        indices=indices,
        labels=sorted(grouped.keys())
    )


def _display_single_example(
    sample_num: int,
    utterance: str,
    utterance_idx: int,
    speaker_label: str,
    all_instances: List[Tuple[str, str]]
) -> None:
    """Display a single example with context."""
    print(f"\n  Example {sample_num + 1}:")
    print("  " + "-" * SEPARATOR_WIDTH)

    # Context before
    context_start = max(0, utterance_idx - CONTEXT_LINES_BEFORE)
    for ctx_idx in range(context_start, utterance_idx):
        ctx_speaker, ctx_utterance = all_instances[ctx_idx]
        print(f"     {ctx_speaker}: {ctx_utterance}")

    # Target line (highlighted)
    print(f"  -> {speaker_label}: {utterance}")

    # Context after
    context_end = min(len(all_instances), utterance_idx + CONTEXT_LINES_AFTER + 1)
    for ctx_idx in range(utterance_idx + 1, context_end):
        ctx_speaker, ctx_utterance = all_instances[ctx_idx]
        print(f"     {ctx_speaker}: {ctx_utterance}")

    print("  " + "-" * SEPARATOR_WIDTH)


def display_speaker_examples(
    speaker_label: str,
    utterances: List[str],
    indices: List[int],
    all_instances: List[Tuple[str, str]],
    max_samples: int = MAX_SAMPLE_EXAMPLES
) -> None:
    """
    Display speaker examples with surrounding context.

    Parameters
    ----------
    speaker_label : str
        Speaker label being displayed
    utterances : List[str]
        List of utterances for this speaker
    indices : List[int]
        Indices of utterances in full instance list
    all_instances : List[Tuple[str, str]]
        Complete list of all filtered instances
    max_samples : int, default=MAX_SAMPLE_EXAMPLES
        Maximum number of examples to display

    Example
    -------
    >>> display_speaker_examples("Speaker 1", ["Hello world"], [0], instances)
    --- Speaker Label: Speaker 1 ---
    Number of utterances: 1
    ...
    """
    print(f"\n--- Speaker Label: {speaker_label} ---")
    print(f"Number of utterances: {len(utterances)}")
    print("\nSample utterances with context:")

    num_samples = min(max_samples, len(utterances))

    for sample_num in range(num_samples):
        _display_single_example(
            sample_num,
            utterances[sample_num],
            indices[sample_num],
            speaker_label,
            all_instances
        )

    if len(utterances) > num_samples:
        print(f"\n  ... and {len(utterances) - num_samples} more utterances for this speaker")


def get_user_speaker_choice(
    speaker_label: str,
    known_speakers: List[str],
    suggestion: Optional[str] = None
) -> UserChoice:
    """
    Prompt user to identify speaker with numbered menu.

    Parameters
    ----------
    speaker_label : str
        Generic speaker label to identify
    known_speakers : List[str]
        List of known speaker names
    suggestion : Optional[str]
        Suggested speaker based on heuristics

    Returns
    -------
    UserChoice
        User's choice with metadata

    Example
    -------
    >>> choice = get_user_speaker_choice("Speaker 1", ["Bruce", "Ivette"])
    >>> choice.is_valid_speaker
    True
    """
    print(f"\nWho is '{speaker_label}'?")
    if suggestion:
        print(f"(Suggested: {suggestion})")

    print("\nOptions:")
    for idx, speaker in enumerate(known_speakers, 1):
        marker = " *" if speaker == suggestion else ""
        print(f"  {idx}. {speaker}{marker}")
    print("  s. Skip")
    print("  q. Quit")

    while True:
        user_input = input(f"\nEnter choice (1-{len(known_speakers)}, s, q): ").strip().lower()

        if user_input == 'q':
            logger.info("User chose to quit labeling session")
            return UserChoice(choice="quit", is_quit=True, is_skip=False)

        if user_input == 's':
            logger.info("User chose to skip speaker: %s", speaker_label)
            return UserChoice(choice="skip", is_quit=False, is_skip=True)

        try:
            choice_num = int(user_input)
            if 1 <= choice_num <= len(known_speakers):
                chosen_speaker = known_speakers[choice_num - 1]
                logger.info("User chose speaker '%s' for label '%s'", chosen_speaker, speaker_label)
                return UserChoice(choice=chosen_speaker, is_quit=False, is_skip=False)
        except ValueError:
            pass

        print("Invalid choice. Please try again.")


def create_training_examples_for_speaker(
    speaker_label: str,
    utterances: List[str],
    transcript_file: str,
    identified_speaker: str
) -> List[Dict]:
    """
    Create training examples for an identified speaker.

    Parameters
    ----------
    speaker_label : str
        Original generic speaker label
    utterances : List[str]
        Utterances from this speaker
    transcript_file : str
        Source transcript file path
    identified_speaker : str
        The identified speaker name

    Returns
    -------
    List[Dict]
        Training example dictionaries

    Example
    -------
    >>> examples = create_training_examples_for_speaker(
    ...     "Speaker 1", ["Hello"], "file.md", "Bruce"
    ... )
    >>> len(examples)
    1
    """
    examples = []

    # Add up to 3 representative examples
    for utterance in utterances[:3]:
        examples.append({
            "source": "manual",
            "file": str(transcript_file),
            "snippet": f"- {identified_speaker}: {utterance}",
            "speaker": identified_speaker,
            "labeled_date": datetime.now().isoformat()
        })

    logger.debug(
        "Created %d training examples for speaker '%s' (label: '%s')",
        len(examples), identified_speaker, speaker_label
    )

    return examples


def interactive_labeling_session(
    groups: SpeakerGroups,
    all_instances: List[Tuple[str, str]],
    known_speakers: List[str],
    transcript_file: str,
    existing_examples: List[Dict]
) -> Tuple[List[Dict], Dict[str, str]]:
    """
    Run interactive session to label speaker instances.

    Parameters
    ----------
    groups : SpeakerGroups
        Grouped speaker instances
    all_instances : List[Tuple[str, str]]
        All filtered instances
    known_speakers : List[str]
        Known speaker names
    transcript_file : str
        Source transcript file path
    existing_examples : List[Dict]
        Existing training examples for early quit save

    Returns
    -------
    Tuple[List[Dict], Dict[str, str]]
        Newly created training examples and speaker label map

    Example
    -------
    >>> examples, mapping = interactive_labeling_session(...)
    >>> isinstance(examples, list)
    True
    """
    new_examples = []
    speaker_label_map = {}

    for speaker_label in groups.labels:
        utterances = groups.grouped[speaker_label]
        indices = groups.indices[speaker_label]

        # Display examples
        display_speaker_examples(
            speaker_label, utterances, indices, all_instances
        )

        # Get suggestion
        suggestion = suggest_speaker(utterances, known_speakers)

        # Get user choice
        choice = get_user_speaker_choice(speaker_label, known_speakers, suggestion)

        if choice.is_quit:
            # Handle early quit with save option
            if new_examples:
                save_option = input(f"\nSave {len(new_examples)} labeled examples? (y/n): ").strip().lower()
                if save_option == 'y':
                    all_examples = existing_examples + new_examples
                    save_training_examples(all_examples)
                    logger.info("Saved %d training examples after early quit", len(all_examples))
                    print(f"Saved {len(all_examples)} total training examples.")
            break

        if choice.is_skip:
            print(f"Skipping {speaker_label}")
            continue

        # Valid speaker chosen
        speaker_label_map[speaker_label] = choice.choice
        print(f"✓ {speaker_label} → {choice.choice}")

        # Create examples
        examples = create_training_examples_for_speaker(
            speaker_label, utterances, transcript_file, choice.choice
        )
        new_examples.extend(examples)

        logger.info(
            "Labeled '%s' as '%s' - created %d training examples",
            speaker_label, choice.choice, len(examples)
        )

    return new_examples, speaker_label_map


def deduplicate_examples(examples: List[Dict]) -> List[Dict]:
    """
    Remove duplicate training examples based on snippet content.

    Parameters
    ----------
    examples : List[Dict]
        List of training examples

    Returns
    -------
    List[Dict]
        Deduplicated examples

    Example
    -------
    >>> examples = [{"snippet": "A"}, {"snippet": "A"}, {"snippet": "B"}]
    >>> deduped = deduplicate_examples(examples)
    >>> len(deduped)
    2
    """
    seen_snippets = set()
    unique_examples = []

    for example in examples:
        snippet = example.get("snippet", "")
        if snippet not in seen_snippets:
            seen_snippets.add(snippet)
            unique_examples.append(example)

    duplicates_removed = len(examples) - len(unique_examples)
    if duplicates_removed > 0:
        logger.debug("Removed %d duplicate training examples", duplicates_removed)

    return unique_examples


def save_training_session(
    new_examples: List[Dict],
    existing_examples: List[Dict]
) -> SessionStatistics:
    """
    Save training examples and return statistics.

    Parameters
    ----------
    new_examples : List[Dict]
        Newly created examples from session
    existing_examples : List[Dict]
        Previously existing examples

    Returns
    -------
    SessionStatistics
        Session statistics

    Example
    -------
    >>> stats = save_training_session(new_examples, existing_examples)
    >>> stats.new_examples_count
    10
    """
    if not new_examples:
        logger.info("No new examples to save")
        return SessionStatistics(0, 0, 0, len(existing_examples))

    # Combine and deduplicate
    all_examples = existing_examples + new_examples
    unique_examples = deduplicate_examples(all_examples)

    # Calculate statistics
    duplicates_removed = len(all_examples) - len(unique_examples)
    unique_added = len(unique_examples) - len(existing_examples)

    # Save to file
    save_training_examples(unique_examples)

    stats = SessionStatistics(
        new_examples_count=len(new_examples),
        duplicates_removed=duplicates_removed,
        unique_examples_added=unique_added,
        total_examples=len(unique_examples)
    )

    logger.info(
        "Training session saved: %d new, %d duplicates removed, %d unique added, %d total",
        stats.new_examples_count, stats.duplicates_removed,
        stats.unique_examples_added, stats.total_examples
    )

    return stats


def label_training_transcript(transcript_file: str) -> None:
    """
    Interactive tool to label speakers in a training transcript.

    Orchestrates the complete labeling workflow:
    1. Load transcript file
    2. Validate speaker profiles
    3. Extract and filter instances
    4. Group instances by speaker
    5. Run interactive labeling session
    6. Save training examples

    Automatically filters out brief utterances (fewer than 6 words) to focus
    on substantial dialogue rather than acknowledgments like "Yes", "OK", etc.

    Parameters
    ----------
    transcript_file : str
        Path to the transcript markdown file to label

    Example
    -------
    >>> label_training_transcript("lifelogs/2025-03-01.md")
    # Interactive session to label speakers
    # Only shows utterances with 6+ words for labeling
    """
    # Step 1: Load transcript
    transcript_content = load_transcript_file(transcript_file)
    if transcript_content is None:
        return

    # Step 2: Validate profiles
    known_speakers = validate_speaker_profiles()
    if known_speakers is None:
        return

    # Display header
    print(f"\n=== Speaker Training Tool ===")
    print(f"File: {transcript_file}")
    print(f"Known speakers: {', '.join(known_speakers)}")
    print("\nThis tool will help you label speaker instances to create training data.\n")

    # Step 3: Extract and filter instances
    instances = extract_speaker_instances(transcript_content)
    if not instances:
        logger.warning("No speaker instances found in transcript")
        print("No speaker instances found in transcript.")
        return

    filtered_instances, filter_stats = filter_substantial_utterances(instances)
    print(str(filter_stats))

    if not filtered_instances:
        logger.warning("No substantial instances after filtering")
        print("No substantial speaker instances found after filtering.")
        return

    # Step 4: Group instances
    groups = group_instances_by_speaker(filtered_instances)

    # Step 5: Run labeling session
    existing_examples = load_training_examples()
    new_examples, speaker_label_map = interactive_labeling_session(
        groups, filtered_instances, known_speakers, transcript_file, existing_examples
    )

    # Step 6: Save results
    if new_examples:
        session_stats = save_training_session(new_examples, existing_examples)
        print(str(session_stats))

        # Optional: Update transcript file
        update_file = input(f"\nWould you like to update {transcript_file} with the labeled speakers? (y/n): ").strip().lower()
        if update_file == 'y':
            updated_content = transcript_content
            for original_label, identified_name in speaker_label_map.items():
                updated_content = updated_content.replace(f"- {original_label}:", f"- {identified_name}:")
                updated_content = updated_content.replace(f"**{original_label}:**", f"**{identified_name}:**")

            file_path = Path(transcript_file)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"✓ Updated {transcript_file} with speaker labels")


def suggest_speaker(utterances: List[str], known_speakers: List[str]) -> Optional[str]:
    """
    Simple heuristic-based speaker suggestion.

    Parameters
    ----------
    utterances : List[str]
        List of utterances from this speaker
    known_speakers : List[str]
        List of known speaker names

    Returns
    -------
    Optional[str]
        Suggested speaker name or None
    """
    # Very simple heuristic: look for speaker names mentioned in utterances
    combined_text = " ".join(utterances).lower()

    for speaker in known_speakers:
        if speaker.lower() in combined_text:
            return speaker

    # Check for common patterns (e.g., "I'm Bruce", "my name is")
    for speaker in known_speakers:
        if f"i'm {speaker.lower()}" in combined_text or f"i am {speaker.lower()}" in combined_text:
            return speaker

    return None


def collect_essential_info() -> Optional[Dict]:
    """
    Collect essential speaker information through conversation.

    Collects: name, relationship to user, languages with competency.

    Returns
    -------
    Optional[Dict]
        Dictionary with 'name', 'relationship', 'languages'
        Returns None if user cancels

    Example
    -------
    >>> info = collect_essential_info()
    >>> info['name']
    'Matt'
    >>> info['relationship']
    'brother'
    """
    print("\n=== Speaker Profile Initialization ===\n")
    print("Let's add a speaker to your profile system.\n")

    # Get speaker name
    while True:
        name = input("Speaker's name: ").strip()
        if not name:
            print("Name cannot be empty. Please try again.")
            continue

        # Check for duplicates
        existing_profiles = load_speaker_profiles()
        if name in existing_profiles.get("speakers", {}):
            overwrite = input(f"\n⚠️  '{name}' already exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                return None

        break

    # Get relationship
    print(f"\nWhat is {name}'s relationship to you?")
    print("Common options: spouse, son, daughter, parent, sibling, friend, colleague, other")
    relationship = input("> ").strip().lower()

    if not relationship:
        relationship = "other"

    # Get languages
    print(f"\nWhat language(s) does {name} speak?")
    print("For each language, specify competency: native, fluent, conversational, learning")
    print("Example: English fluent, Spanish conversational")
    print("(or just press Enter to add English as default)")

    languages = {}
    lang_input = input("> ").strip()

    if not lang_input:
        # Default to English fluent
        languages["English"] = "fluent"
    else:
        # Parse language input
        for lang_spec in lang_input.split(','):
            lang_spec = lang_spec.strip()
            parts = lang_spec.rsplit(' ', 1)  # Split from right to get competency

            if len(parts) == 2:
                lang_name = parts[0].strip().title()
                competency = parts[1].strip().lower()

                if competency in ["native", "fluent", "conversational", "learning"]:
                    languages[lang_name] = competency
                else:
                    # Default to fluent if competency not recognized
                    languages[lang_name] = "fluent"
            else:
                # Just language name, default to fluent
                languages[lang_spec.title()] = "fluent"

    print(f"\n✓ Essential info collected for {name}")

    return {
        "name": name,
        "relationship": relationship,
        "languages": languages
    }


def find_speaker_in_transcripts(speaker_name: str, max_excerpts: int = 30) -> List[str]:
    """
    Find conversation excerpts for a speaker in recent transcripts.

    Searches lifelogs and bee directories for speaker instances.

    Parameters
    ----------
    speaker_name : str
        Name of speaker to find
    max_excerpts : int
        Maximum number of excerpts to return

    Returns
    -------
    List[str]
        List of conversation excerpts featuring the speaker

    Example
    -------
    >>> excerpts = find_speaker_in_transcripts("Bruce", max_excerpts=20)
    >>> len(excerpts)
    20
    """
    excerpts = []
    project_root = Path(__file__).parent.parent.parent

    # Search lifelogs
    lifelogs_dir = project_root / "lifelogs"
    if lifelogs_dir.exists():
        # Get most recent lifelog files
        lifelog_files = sorted(lifelogs_dir.glob("*.md"), reverse=True)[:10]

        for file_path in lifelog_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                instances = extract_speaker_instances(content)

                for speaker_label, utterance in instances:
                    # Check if this matches our speaker (case-insensitive, fuzzy match)
                    if speaker_name.lower() in speaker_label.lower():
                        excerpts.append(f"{speaker_label}: {utterance}")

                        if len(excerpts) >= max_excerpts:
                            return excerpts

            except Exception as e:
                print(f"Warning: Error reading {file_path}: {e}")
                continue

    # Search bee transcripts
    bee_dir = project_root / "bee"
    if bee_dir.exists():
        bee_files = sorted(bee_dir.glob("*.md"), reverse=True)[:10]

        for file_path in bee_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                instances = extract_speaker_instances(content)

                for speaker_label, utterance in instances:
                    if speaker_name.lower() in speaker_label.lower():
                        excerpts.append(f"{speaker_label}: {utterance}")

                        if len(excerpts) >= max_excerpts:
                            return excerpts

            except Exception as e:
                print(f"Warning: Error reading {file_path}: {e}")
                continue

    return excerpts


def collect_optional_details(speaker_name: str) -> Optional[Dict]:
    """
    Collect optional detailed information with LLM-powered suggestions.

    Parameters
    ----------
    speaker_name : str
        Name of speaker for transcript analysis

    Returns
    -------
    Optional[Dict]
        Dictionary with 'speech_patterns' or None if skipped

    Example
    -------
    >>> details = collect_optional_details("Matt")
    >>> details['speech_patterns']['vocabulary_level']
    'college'
    """
    print(f"\nWould you like me to analyze transcripts to suggest speech patterns for {speaker_name}? (y/n): ", end="")
    analyze = input().strip().lower()

    if analyze != 'y':
        print("Skipping detailed pattern analysis.")
        return None

    # Find excerpts in transcripts
    print(f"\n🔍 Analyzing recent transcripts for {speaker_name}...")
    excerpts = find_speaker_in_transcripts(speaker_name, max_excerpts=30)

    if not excerpts:
        print(f"⚠️  No conversations found for {speaker_name} in recent transcripts.")
        print("You can add speech patterns manually later by editing the config file.")
        return None

    print(f"Found {len(excerpts)} conversation excerpts")

    # Use LLM to analyze patterns
    print("🤖 Analyzing speech patterns with LLM...")
    suggested_patterns = analyze_speaker_patterns_with_llm(speaker_name, excerpts)

    if not suggested_patterns:
        print("⚠️  LLM analysis failed. You can add patterns manually later.")
        return None

    # Display suggestions
    print("\n📊 Suggested patterns:")
    print(f"  Vocabulary: {suggested_patterns.get('vocabulary_level', 'N/A')}")
    print(f"  Style: {suggested_patterns.get('speaking_style', 'N/A')}")

    topics = suggested_patterns.get('common_topics', [])
    if isinstance(topics, list):
        print(f"  Topics: {', '.join(topics)}")
    else:
        print(f"  Topics: {topics}")

    phrases = suggested_patterns.get('distinctive_phrases', [])
    if isinstance(phrases, list):
        print(f"  Phrases: {', '.join(phrases)}")
    else:
        print(f"  Phrases: {phrases}")

    # Ask user to accept/edit
    print("\nAccept these suggestions? (y/n/edit): ", end="")
    choice = input().strip().lower()

    if choice == 'n':
        print("Skipping speech patterns.")
        return None
    elif choice == 'edit':
        print("\nManual editing not yet implemented - accepting suggestions for now.")
        # TODO: Implement manual editing interface
        return {"speech_patterns": suggested_patterns}
    else:
        # Accept suggestions
        return {"speech_patterns": suggested_patterns}


def update_bidirectional_relationships(
    speaker_name: str,
    relationships: Dict[str, str]
) -> bool:
    """
    Update bidirectional relationships between speakers.

    When adding "Matt → Bruce: brother", automatically updates
    "Bruce → Matt: brother".

    Parameters
    ----------
    speaker_name : str
        Name of the speaker whose relationships are being added
    relationships : Dict[str, str]
        Dictionary of {other_speaker: relationship}

    Returns
    -------
    bool
        True if all updates succeeded

    Example
    -------
    >>> update_bidirectional_relationships("Matt", {"Bruce": "brother"})
    True
    """
    try:
        profiles_data = load_speaker_profiles()
        speakers = profiles_data.get("speakers", {})

        for other_speaker, relationship in relationships.items():
            # Check if other speaker exists
            if other_speaker not in speakers:
                print(f"⚠️  Speaker '{other_speaker}' not found in profiles. Skipping bidirectional update.")
                continue

            # Get reverse relationship
            reverse_rel = get_reverse_relationship(relationship)

            if reverse_rel == "?":
                # Unknown relationship, ask user
                print(f"\n{other_speaker} → {speaker_name}: What's their relationship?")
                reverse_rel = input("> ").strip().lower()

            # Update other speaker's relationships
            if "relationships" not in speakers[other_speaker]:
                speakers[other_speaker]["relationships"] = {}

            speakers[other_speaker]["relationships"][speaker_name] = reverse_rel
            print(f"✓ Auto-updated: {other_speaker} → {speaker_name}: {reverse_rel}")

        # Save updated profiles
        with open(SPEAKER_PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error updating bidirectional relationships: {e}")
        return False


def collect_relationships(speaker_name: str) -> Dict[str, str]:
    """
    Collect relationships to other speakers.

    Parameters
    ----------
    speaker_name : str
        Name of the speaker

    Returns
    -------
    Dict[str, str]
        Dictionary of {other_speaker: relationship}

    Example
    -------
    >>> relationships = collect_relationships("Matt")
    >>> relationships["Bruce"]
    'brother'
    """
    print(f"\n{speaker_name} has relationships with other speakers. Let's add them:")
    print(f"Who else does {speaker_name} know? (comma-separated, or 'skip')")

    relationships_input = input("> ").strip()

    if relationships_input.lower() == 'skip' or not relationships_input:
        return {}

    # Parse names
    other_speakers = [name.strip() for name in relationships_input.split(',')]
    relationships = {}

    # Get existing speakers
    existing_profiles = load_speaker_profiles()
    existing_names = list(existing_profiles.get("speakers", {}).keys())

    for other_speaker in other_speakers:
        # Verify speaker exists
        if other_speaker not in existing_names:
            print(f"⚠️  '{other_speaker}' not found in profiles. Add them first, then update relationships.")
            continue

        # Get relationship
        print(f"\n{speaker_name} → {other_speaker}: What's their relationship?")
        relationship = input("> ").strip().lower()

        if relationship:
            relationships[other_speaker] = relationship

    return relationships


def init_speaker_profile() -> None:
    """
    Interactive speaker profile initialization with LLM-powered suggestions.

    Conversational workflow:
    1. Collect essential info (name, relationship, languages)
    2. Optional: LLM-powered speech pattern analysis
    3. Optional: Add relationships to other speakers
    4. Save profile with bidirectional relationship updates
    5. Batch mode: Repeat for multiple speakers

    Example
    -------
    >>> init_speaker_profile()
    # Interactive session to create speaker profiles
    """
    speakers_added = []

    while True:
        # Phase 1: Collect essential info
        essential_info = collect_essential_info()

        if not essential_info:
            # User cancelled
            print("\nCancelled.")
            break

        speaker_name = essential_info["name"]
        relationship = essential_info["relationship"]
        languages = essential_info["languages"]

        # Phase 2: Optional detailed analysis
        optional_details = collect_optional_details(speaker_name)

        # Phase 3: Collect relationships
        relationships = collect_relationships(speaker_name)

        # Build profile
        profile_data = {
            "relationship": relationship,
            "relationships": relationships if relationships else {},
            "languages": languages,
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }

        # Add speech patterns if collected
        if optional_details and "speech_patterns" in optional_details:
            profile_data["speech_patterns"] = optional_details["speech_patterns"]

        # Save the speaker profile
        if save_speaker_profile(speaker_name, profile_data):
            print(f"\n✓ Speaker profile created for {speaker_name}!")
            speakers_added.append(speaker_name)

            # Update bidirectional relationships
            if relationships:
                update_bidirectional_relationships(speaker_name, relationships)
        else:
            print(f"\n❌ Failed to save speaker profile for {speaker_name}")

        # Ask if user wants to add another
        print(f"\nAdd another speaker? (y/n): ", end="")
        continue_choice = input().strip().lower()

        if continue_choice != 'y':
            break

    # Summary
    if speakers_added:
        print(f"\n=== Summary ===")
        print(f"✓ Saved {len(speakers_added)} speaker profile(s): {', '.join(speakers_added)}")
    else:
        print("\nNo speakers added.")


def main():
    """CLI entry point for speaker management commands."""
    if len(sys.argv) < 2:
        print("Usage: python -m daily_insights.cli.speaker_commands <command> [args]")
        print("\nAvailable commands:")
        print("  init                          - Interactive speaker profile initialization")
        print("  label-training <file>         - Label speakers in training transcript")
        print("\nExamples:")
        print("  python -m daily_insights.cli.speaker_commands init")
        print("  python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-01.md")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_speaker_profile()
    elif command == "label-training":
        if len(sys.argv) < 3:
            print("Error: label-training requires a transcript file path")
            print("Usage: python -m daily_insights.cli.speaker_commands label-training <transcript_file>")
            sys.exit(1)
        transcript_file = sys.argv[2]
        label_training_transcript(transcript_file)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: init, label-training")
        sys.exit(1)


if __name__ == "__main__":
    main()
