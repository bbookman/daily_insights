"""Service for therapy session detection and analysis."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from daily_insights.config import (
    LIFELOGS_DIR,
    PSYCHOLOGIST_DIR,
    PSYCHOLOGIST_PROMPT_FILE,
    LLM_PROVIDER
)
from daily_insights.models.therapy_detection import detect_therapy_sessions
from daily_insights.models.conversation_parser import extract_transcript
from daily_insights.api.llm_client import generate_clinical_notes
from daily_insights.utils.file_utils import read_prompt_file, write_file


def load_processed_tracker() -> Dict:
    """
    Load the tracking file for processed lifelogs.

    Returns
    -------
    Dict mapping date to processing metadata

    Example
    -------
    >>> tracker = load_processed_tracker()
    >>> print(len(tracker))
    42
    """
    tracker_file = os.path.join(PSYCHOLOGIST_DIR, "processed_lifelogs.json")
    if os.path.exists(tracker_file):
        with open(tracker_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_processed_tracker(tracker: Dict) -> None:
    """
    Save the tracking file for processed lifelogs.

    Args
    ----
    tracker: Dict mapping date to processing metadata

    Returns
    -------
    None

    Example
    -------
    >>> tracker = {"2025-10-28": {"checked_at": "...", "status": "..."}}
    >>> save_processed_tracker(tracker)
    # Saves tracker to JSON file
    """
    tracker_file = os.path.join(PSYCHOLOGIST_DIR, "processed_lifelogs.json")
    with open(tracker_file, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, sort_keys=True)


def process_therapy_sessions(force_recheck: bool = False) -> None:
    """
    Process all lifelog files to detect and analyze therapy sessions.

    Args
    ----
    force_recheck: If True, reprocess all lifelogs even if checked

    Returns
    -------
    None

    Example
    -------
    >>> process_therapy_sessions()
    # Detects and analyzes therapy sessions
    """
    print("\nStarting therapy session detection and analysis...")

    if force_recheck:
        print("Force recheck enabled - will reprocess all lifelogs")

    prompt_text = read_prompt_file(PSYCHOLOGIST_PROMPT_FILE)
    if not prompt_text:
        return

    tracker = load_processed_tracker()
    initial_tracker_size = len(tracker)

    lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))

    sessions_found = 0
    sessions_analyzed = 0
    lifelogs_skipped = 0
    lifelogs_checked = 0

    for lifelog_file in lifelog_files:
        date_str = lifelog_file.stem

        if not force_recheck and date_str in tracker:
            lifelogs_skipped += 1
            continue

        lifelogs_checked += 1

        sessions = detect_therapy_sessions(lifelog_file, verbose=False)

        tracker[date_str] = {
            "checked_at": datetime.now().isoformat(),
            "sessions_found": len(sessions),
            "status": "analyzed" if sessions else "no_sessions"
        }

        if not sessions:
            save_processed_tracker(tracker)
            continue

        sessions_found += len(sessions)

        print(f"\nFound {len(sessions)} therapy session(s) in {lifelog_file.name}")

        for i, session in enumerate(sessions, 1):
            print(
                f"  Session {i}: {session['start_time']} - "
                f"{session['end_time']} "
                f"({session['duration_minutes']:.0f} min, "
                f"score: {session['score']})"
            )

            transcript = extract_transcript(session["conversation"])

            # Use system/user message format for better instruction following
            system_prompt = prompt_text
            user_message = (
                f"Here is the therapy session transcript. "
                f"Write your clinical notes:\n\n{transcript}"
            )

            try:
                print(f"  Sending to {LLM_PROVIDER.upper()} for analysis...")
                output_text = generate_clinical_notes(
                    system_prompt,
                    user_message
                )

                if len(sessions) > 1:
                    output_file = os.path.join(
                        PSYCHOLOGIST_DIR,
                        f"{date_str}-psychologist-session{i}.md"
                    )
                else:
                    output_file = os.path.join(
                        PSYCHOLOGIST_DIR,
                        f"{date_str}-psychologist.md"
                    )

                analysis_content = (
                    f"# Therapy Session Analysis - {date_str}\n\n"
                    f"**Session Time:** {session['start_time']} - "
                    f"{session['end_time']}\n"
                    f"**Duration:** {session['duration_minutes']:.0f} "
                    "minutes\n"
                    f"**Detection Score:** {session['score']}\n\n"
                    "---\n\n"
                    "{output_text}"
                ).format(output_text=output_text)

                write_file(output_file, analysis_content)
                print(f"  Saved analysis: {output_file}")
                sessions_analyzed += 1

            except Exception as e:
                print(f"  Error analyzing session: {e}")
                continue

        save_processed_tracker(tracker)

    save_processed_tracker(tracker)

    print("\nTherapy session processing complete:")
    print(f"  Lifelogs checked: {lifelogs_checked}")
    print(f"  Lifelogs skipped (already processed): {lifelogs_skipped}")
    print(f"  Sessions found: {sessions_found}")
    print(f"  Sessions analyzed: {sessions_analyzed}")
    print(
        f"  Total tracked lifelogs: {len(tracker)} "
        f"(was {initial_tracker_size})"
    )
