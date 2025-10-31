"""CLI commands for speaker management."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from daily_insights.services.speaker_service import (
    load_speaker_profiles,
    load_training_examples,
    save_training_examples,
    extract_speaker_instances,
    SPEAKER_PROFILES_FILE
)


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


def main():
    """CLI entry point for speaker training tool."""
    if len(sys.argv) < 3:
        print("Usage: python -m daily_insights.cli.speaker_commands label-training <transcript_file>")
        print("\nExample:")
        print("  python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-01.md")
        sys.exit(1)

    command = sys.argv[1]
    if command == "label-training":
        transcript_file = sys.argv[2]
        label_training_transcript(transcript_file)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: label-training")
        sys.exit(1)


if __name__ == "__main__":
    main()
