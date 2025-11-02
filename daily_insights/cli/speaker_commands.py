"""CLI commands for speaker management."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

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


def label_training_transcript(transcript_file: str) -> None:
    """
    Interactive tool to label speakers in a training transcript.

    This tool helps you manually label speaker instances in a transcript
    to create training data for the speaker identification system.

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
    file_path = Path(transcript_file)

    if not file_path.exists():
        print(f"Error: File not found: {transcript_file}")
        return

    # Load the transcript
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            transcript_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Load existing profiles to know available speakers
    profiles_data = load_speaker_profiles()
    known_speakers = list(profiles_data.get("speakers", {}).keys())

    if not known_speakers:
        print("Error: No speaker profiles found. Please create speaker profiles first.")
        print(f"Edit {SPEAKER_PROFILES_FILE} to add speaker profiles.")
        return

    print(f"\n=== Speaker Training Tool ===")
    print(f"File: {transcript_file}")
    print(f"Known speakers: {', '.join(known_speakers)}")
    print("\nThis tool will help you label speaker instances to create training data.\n")

    # Extract speaker instances
    instances = extract_speaker_instances(transcript_content)

    if not instances:
        print("No speaker instances found in transcript.")
        return

    # Filter out utterances with fewer than 6 words
    filtered_instances = []
    for speaker_label, utterance in instances:
        word_count = len(utterance.split())
        if word_count >= 6:
            filtered_instances.append((speaker_label, utterance))

    original_count = len(instances)
    filtered_count = len(filtered_instances)
    skipped_count = original_count - filtered_count

    print(f"Found {original_count} speaker instances.")
    print(f"Filtered to {filtered_count} substantial utterances (≥6 words).")
    print(f"Skipped {skipped_count} brief utterances (<6 words).\n")

    if not filtered_instances:
        print("No substantial speaker instances found after filtering.")
        return

    # Load existing training examples
    existing_examples = load_training_examples()

    # Track labeled examples from this session
    new_examples = []

    # Group instances by speaker label, but keep track of indices
    grouped = {}
    instance_indices = {}  # Maps (speaker_label, utterance) to index in filtered_instances list

    for idx, (speaker_label, utterance) in enumerate(filtered_instances):
        if speaker_label not in grouped:
            grouped[speaker_label] = []
            instance_indices[speaker_label] = []
        grouped[speaker_label].append(utterance)
        instance_indices[speaker_label].append(idx)

    # For each unique speaker label, ask for identification
    speaker_label_map = {}

    for speaker_label in sorted(grouped.keys()):
        utterances = grouped[speaker_label]
        indices = instance_indices[speaker_label]

        print(f"\n--- Speaker Label: {speaker_label} ---")
        print(f"Number of utterances: {len(utterances)}")
        print("\nSample utterances with context:")

        # Show up to 3 sample utterances with context (reduced from 5 due to more output per sample)
        num_samples = min(3, len(utterances))

        for sample_num in range(num_samples):
            print(f"\n  Example {sample_num + 1}:")
            print("  " + "-" * 70)

            # Get the index of this utterance in the filtered transcript
            utterance_idx = indices[sample_num]

            # Show 4 lines before
            context_before = max(0, utterance_idx - 4)
            for ctx_idx in range(context_before, utterance_idx):
                ctx_speaker, ctx_utterance = filtered_instances[ctx_idx]
                print(f"     {ctx_speaker}: {ctx_utterance}")

            # Show the target line (highlighted)
            target_utterance = utterances[sample_num]
            print(f"  -> {speaker_label}: {target_utterance}")

            # Show 4 lines after
            context_after = min(len(filtered_instances), utterance_idx + 5)
            for ctx_idx in range(utterance_idx + 1, context_after):
                ctx_speaker, ctx_utterance = filtered_instances[ctx_idx]
                print(f"     {ctx_speaker}: {ctx_utterance}")

            print("  " + "-" * 70)

        if len(utterances) > num_samples:
            print(f"\n  ... and {len(utterances) - num_samples} more utterances for this speaker")

        # Suggest a speaker based on simple heuristics
        suggestion = suggest_speaker(utterances, known_speakers)

        # Show numbered options for speakers
        print(f"\nWho is '{speaker_label}'?")
        if suggestion:
            print(f"(Suggested: {suggestion})")
        print("\nOptions:")
        for idx, speaker in enumerate(known_speakers, 1):
            marker = " *" if speaker == suggestion else ""
            print(f"  {idx}. {speaker}{marker}")
        print(f"  s. Skip")
        print(f"  q. Quit")

        prompt = f"\nEnter choice (1-{len(known_speakers)}, s, q): "

        while True:
            user_input = input(prompt).strip().lower()

            if user_input == 'q':
                print("\nQuitting...")
                if new_examples:
                    save_option = input(f"Save {len(new_examples)} labeled examples? (y/n): ").strip().lower()
                    if save_option == 'y':
                        all_examples = existing_examples + new_examples
                        save_training_examples(all_examples)
                        print(f"Saved {len(all_examples)} total training examples.")
                return

            if user_input == 's':
                print(f"Skipping {speaker_label}")
                break

            # Check if input is a valid number
            if user_input.isdigit():
                choice_num = int(user_input)
                if 1 <= choice_num <= len(known_speakers):
                    selected_speaker = known_speakers[choice_num - 1]
                    speaker_label_map[speaker_label] = selected_speaker
                    print(f"✓ {speaker_label} → {selected_speaker}")

                    # Add a few representative examples
                    for utterance in utterances[:3]:  # Add up to 3 examples per speaker
                        new_examples.append({
                            "source": "manual",
                            "file": str(transcript_file),
                            "snippet": f"- {selected_speaker}: {utterance}",
                            "speaker": selected_speaker,
                            "labeled_date": datetime.now().isoformat()
                        })

                    break
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {len(known_speakers)}.")
            else:
                print(f"Invalid input. Please enter a number, 's' to skip, or 'q' to quit.")

    # Summary
    print(f"\n=== Labeling Complete ===")
    print(f"Labeled {len(speaker_label_map)} speaker types")
    print(f"Created {len(new_examples)} training examples")

    if new_examples:
        # Save the new examples
        all_examples = existing_examples + new_examples
        save_training_examples(all_examples)
        print(f"\n✓ Saved {len(all_examples)} total training examples to file.")

        # Optionally update the transcript file with labels
        update_file = input(f"\nWould you like to update {transcript_file} with the labeled speakers? (y/n): ").strip().lower()

        if update_file == 'y':
            updated_content = transcript_content
            for original_label, identified_name in speaker_label_map.items():
                # Replace speaker labels in transcript
                updated_content = updated_content.replace(f"- {original_label}:", f"- {identified_name}:")
                updated_content = updated_content.replace(f"**{original_label}:**", f"**{identified_name}:**")

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
