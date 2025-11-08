"""Service for doctor visit detection and analysis."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
import asyncio

from daily_insights.config import (
    LIFELOGS_DIR,
    DOCTOR_DIR,
    DOCTOR_PROMPT,
    LLM_PROVIDER
)
from daily_insights.models.conversation_parser import (
    parse_lifelog_dialogue,
    group_into_conversations,
    is_doctor_visit,
    extract_transcript,
    calculate_duration_minutes
)
from daily_insights.api.llm_client import generate_clinical_notes, generate_clinical_notes_async
from daily_insights.utils.file_utils import (
    read_prompt_file, write_file,
    read_file_async, write_file_async
)


def detect_doctor_visits_mvp(lifelog_file: Path, verbose: bool = False):
    """
    MVP doctor visit detection - wrapper for is_doctor_visit() function.

    Uses strict criteria to detect medical appointments:
    - Duration check (10-90 min)
    - Medical keywords (doctor, physician, specialist, etc.)
    - Speaker validation
    - Excludes psychiatrist/mental health visits
    - Excludes therapy and journal sessions

    Args
    ----
    lifelog_file: Path to lifelog file
    verbose: Whether to print detection details

    Returns
    -------
    List of doctor visit dicts with conversation, start_time, end_time, duration_minutes

    Example
    -------
    >>> sessions = detect_doctor_visits_mvp(Path("lifelogs/2025-11-07.md"))
    >>> print(len(sessions))
    1
    """
    # Parse lifelog into conversations
    dialogues = parse_lifelog_dialogue(lifelog_file)
    conversations = group_into_conversations(dialogues)

    doctor_visits = []

    for conversation in conversations:
        if is_doctor_visit(conversation):
            # Build visit metadata
            start_time = conversation[0]["time_str"]
            end_time = conversation[-1]["time_str"]
            duration = calculate_duration_minutes(conversation)

            visit = {
                "conversation": conversation,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration,
                "score": "MVP"  # No scoring in MVP, just pass/fail
            }

            doctor_visits.append(visit)

            if verbose:
                print(f"Found doctor visit: {start_time} - {end_time} ({duration:.0f} min)")

    return doctor_visits


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
    tracker_file = os.path.join(DOCTOR_DIR, "processed_lifelogs.json")
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
    >>> tracker = {"2025-11-07": {"checked_at": "...", "status": "..."}}
    >>> save_processed_tracker(tracker)
    # Saves tracker to JSON file
    """
    tracker_file = os.path.join(DOCTOR_DIR, "processed_lifelogs.json")
    with open(tracker_file, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, sort_keys=True)


def process_doctor_visits(force_recheck: bool = False) -> None:
    """
    Process all lifelog files to detect and analyze doctor visits.

    Args
    ----
    force_recheck: If True, reprocess all lifelogs even if checked

    Returns
    -------
    None

    Example
    -------
    >>> process_doctor_visits()
    # Detects and analyzes doctor visits
    """
    print("\nStarting doctor visit detection and analysis...")

    if force_recheck:
        print("Force recheck enabled - will reprocess all lifelogs")

    prompt_text = read_prompt_file(DOCTOR_PROMPT)
    if not prompt_text:
        return

    tracker = load_processed_tracker()
    initial_tracker_size = len(tracker)

    lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))

    visits_found = 0
    visits_analyzed = 0
    lifelogs_skipped = 0
    lifelogs_checked = 0

    for lifelog_file in lifelog_files:
        date_str = lifelog_file.stem

        if not force_recheck and date_str in tracker:
            lifelogs_skipped += 1
            continue

        lifelogs_checked += 1

        visits = detect_doctor_visits_mvp(lifelog_file, verbose=False)

        tracker[date_str] = {
            "checked_at": datetime.now().isoformat(),
            "visits_found": len(visits),
            "status": "analyzed" if visits else "no_visits"
        }

        if not visits:
            save_processed_tracker(tracker)
            continue

        visits_found += len(visits)

        print(f"\nFound {len(visits)} doctor visit(s) in {lifelog_file.name}")

        for i, visit in enumerate(visits, 1):
            print(
                f"  Visit {i}: {visit['start_time']} - "
                f"{visit['end_time']} "
                f"({visit['duration_minutes']:.0f} min)"
            )

            transcript = extract_transcript(visit["conversation"])

            # Use system/user message format for better instruction following
            system_prompt = prompt_text
            user_message = (
                f"Here is the doctor visit transcript. "
                f"Write your medical visit summary:\n\n{transcript}"
            )

            try:
                print(f"  Sending to {LLM_PROVIDER.upper()} for analysis...")
                output_text = generate_clinical_notes(
                    system_prompt,
                    user_message
                )

                if len(visits) > 1:
                    output_file = os.path.join(
                        DOCTOR_DIR,
                        f"{date_str}-doctor-visit{i}.md"
                    )
                else:
                    output_file = os.path.join(
                        DOCTOR_DIR,
                        f"{date_str}-doctor.md"
                    )

                analysis_content = (
                    f"# Doctor Visit Summary - {date_str}\n\n"
                    f"**Visit Time:** {visit['start_time']} - "
                    f"{visit['end_time']}\n\n"
                    "---\n\n"
                    "{output_text}"
                ).format(output_text=output_text)

                write_file(output_file, analysis_content)
                print(f"  Saved summary: {output_file}")
                visits_analyzed += 1

            except Exception as e:
                print(f"  Error analyzing visit: {e}")
                continue

        save_processed_tracker(tracker)

    save_processed_tracker(tracker)

    print("\nDoctor visit processing complete:")
    print(f"  Lifelogs checked: {lifelogs_checked}")
    print(f"  Lifelogs skipped (already processed): {lifelogs_skipped}")
    print(f"  Visits found: {visits_found}")
    print(f"  Visits analyzed: {visits_analyzed}")
    print(
        f"  Total tracked lifelogs: {len(tracker)} "
        f"(was {initial_tracker_size})"
    )


# ============================================================================
# Async Service Functions
# ============================================================================

async def load_processed_tracker_async() -> Dict:
    """
    Async version: Load the tracking file for processed lifelogs.

    Returns
    -------
    Dict mapping date to processing metadata

    Example
    -------
    >>> tracker = await load_processed_tracker_async()
    >>> print(len(tracker))
    42
    """
    tracker_file = os.path.join(DOCTOR_DIR, "processed_lifelogs.json")
    if os.path.exists(tracker_file):
        content = await read_file_async(tracker_file)
        return json.loads(content)
    return {}


async def save_processed_tracker_async(tracker: Dict) -> None:
    """
    Async version: Save the tracking file for processed lifelogs.

    Args
    ----
    tracker: Dict mapping date to processing metadata

    Returns
    -------
    None

    Example
    -------
    >>> tracker = {"2025-11-07": {"checked_at": "...", "status": "..."}}
    >>> await save_processed_tracker_async(tracker)
    # Saves tracker to JSON file
    """
    tracker_file = os.path.join(DOCTOR_DIR, "processed_lifelogs.json")
    content = json.dumps(tracker, indent=2, sort_keys=True)
    await write_file_async(tracker_file, content)


async def process_doctor_visits_async(force_recheck: bool = False) -> None:
    """
    Async version: Process all lifelog files to detect and analyze doctor visits.

    Args
    ----
    force_recheck: If True, reprocess all lifelogs even if checked

    Returns
    -------
    None

    Example
    -------
    >>> await process_doctor_visits_async()
    # Detects and analyzes doctor visits
    """
    print("\nStarting doctor visit detection and analysis (async)...")

    if force_recheck:
        print("Force recheck enabled - will reprocess all lifelogs")

    # Read prompt file
    if not os.path.exists(DOCTOR_PROMPT):
        print(f"ERROR: Prompt file missing: {DOCTOR_PROMPT}")
        return

    prompt_text = await read_file_async(DOCTOR_PROMPT)

    tracker = await load_processed_tracker_async()
    initial_tracker_size = len(tracker)

    lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))

    visits_found = 0
    visits_analyzed = 0
    lifelogs_skipped = 0
    lifelogs_checked = 0

    # Semaphore to limit concurrent LLM calls
    semaphore = asyncio.Semaphore(3)

    async def process_single_lifelog(lifelog_file: Path) -> None:
        nonlocal visits_found, visits_analyzed, lifelogs_skipped, lifelogs_checked

        date_str = lifelog_file.stem

        if not force_recheck and date_str in tracker:
            lifelogs_skipped += 1
            return

        lifelogs_checked += 1

        visits = detect_doctor_visits_mvp(lifelog_file, verbose=False)

        tracker[date_str] = {
            "checked_at": datetime.now().isoformat(),
            "visits_found": len(visits),
            "status": "analyzed" if visits else "no_visits"
        }

        if not visits:
            await save_processed_tracker_async(tracker)
            return

        visits_found += len(visits)

        print(f"\nFound {len(visits)} doctor visit(s) in {lifelog_file.name}")

        for i, visit in enumerate(visits, 1):
            print(
                f"  Visit {i}: {visit['start_time']} - "
                f"{visit['end_time']} "
                f"({visit['duration_minutes']:.0f} min)"
            )

            transcript = extract_transcript(visit["conversation"])

            # Use system/user message format for better instruction following
            system_prompt = prompt_text
            user_message = (
                f"Here is the doctor visit transcript. "
                f"Write your medical visit summary:\n\n{transcript}"
            )

            try:
                async with semaphore:
                    print(f"  Sending to {LLM_PROVIDER.upper()} for analysis...")
                    output_text = await generate_clinical_notes_async(
                        system_prompt,
                        user_message
                    )

                if len(visits) > 1:
                    output_file = os.path.join(
                        DOCTOR_DIR,
                        f"{date_str}-doctor-visit{i}.md"
                    )
                else:
                    output_file = os.path.join(
                        DOCTOR_DIR,
                        f"{date_str}-doctor.md"
                    )

                analysis_content = (
                    f"# Doctor Visit Summary - {date_str}\n\n"
                    f"**Visit Time:** {visit['start_time']} - "
                    f"{visit['end_time']}\n\n"
                    "---\n\n"
                    "{output_text}"
                ).format(output_text=output_text)

                await write_file_async(output_file, analysis_content)
                print(f"  Saved summary: {output_file}")
                visits_analyzed += 1

            except Exception as e:
                print(f"  Error analyzing visit: {e}")
                continue

        await save_processed_tracker_async(tracker)

    # Process all lifelogs concurrently
    await asyncio.gather(*[process_single_lifelog(lf) for lf in lifelog_files])

    await save_processed_tracker_async(tracker)

    print("\nDoctor visit processing complete:")
    print(f"  Lifelogs checked: {lifelogs_checked}")
    print(f"  Lifelogs skipped (already processed): {lifelogs_skipped}")
    print(f"  Visits found: {visits_found}")
    print(f"  Visits analyzed: {visits_analyzed}")
    print(
        f"  Total tracked lifelogs: {len(tracker)} "
        f"(was {initial_tracker_size})"
    )
