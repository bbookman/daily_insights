#!/usr/bin/env python3
"""
Therapy Detection Validation Test

Lists all dates/files containing detected therapy sessions to aid human validation
of the detection system. This test helps verify that the MVP + keyword density
enhancement is working correctly.

Usage:
    python tests/test_therapy_detection_validation.py
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

from daily_insights.models.conversation_parser import (
    parse_lifelog_dialogue,
    group_into_conversations,
    is_therapy_session,
    calculate_duration_minutes,
    check_keyword_density,
    check_speaker_purity,
    check_exclusion_keywords
)
from daily_insights.config import (
    LIFELOGS_DIR,
    EXPECTED_SPEAKERS_THERAPY_SESSION,
    THERAPY_KEYWORDS,
    THERAPY_KEYWORD_MIN,
    THERAPY_MIN_DURATION,
    THERAPY_MAX_DURATION,
    THERAPY_EXCLUSION_KEYWORDS
)


def get_therapy_sessions_from_file(lifelog_path: Path) -> List[Dict]:
    """Extract all therapy sessions from a single lifelog file.

    Args:
        lifelog_path: Path to lifelog markdown file

    Returns:
        List of detected therapy sessions with metadata
    """
    sessions = []

    try:
        dialogues = parse_lifelog_dialogue(lifelog_path)
        conversations = group_into_conversations(dialogues)

        for conv in conversations:
            if is_therapy_session(conv):
                duration = calculate_duration_minutes(conv)
                speakers = set(d["speaker"] for d in conv)

                # Check validation results (Phase 2.9 Boolean AND logic)
                speaker_purity_pass = check_speaker_purity(conv)
                keyword_density_pass = check_keyword_density(conv)
                exclusion_pass = check_exclusion_keywords(conv)

                # Check keyword matches
                content_combined = " ".join(d["content"].lower() for d in conv)
                matched_keywords = [
                    kw for kw in THERAPY_KEYWORDS
                    if kw.lower() in content_combined
                ]

                sessions.append({
                    "file": lifelog_path.name,
                    "date": lifelog_path.stem,
                    "start_time": conv[0]["time_str"],
                    "end_time": conv[-1]["time_str"],
                    "duration_minutes": duration,
                    "message_count": len(conv),
                    "speakers": speakers,
                    "speaker_purity_pass": speaker_purity_pass,
                    "keyword_density_pass": keyword_density_pass,
                    "exclusion_pass": exclusion_pass,
                    "matched_keywords": matched_keywords,
                    "keyword_count": len(matched_keywords),
                    "first_message": conv[0]["content"][:100] + "..." if len(conv[0]["content"]) > 100 else conv[0]["content"]
                })

    except Exception as e:
        print(f"Error processing {lifelog_path.name}: {e}")

    return sessions


def scan_all_lifelogs() -> Tuple[List[Dict], Dict]:
    """Scan all lifelog files for therapy sessions.

    Returns:
        Tuple of (sessions list, summary statistics dict)
    """
    lifelogs_path = Path(LIFELOGS_DIR)

    if not lifelogs_path.exists():
        raise FileNotFoundError(f"Lifelogs directory not found: {lifelogs_path}")

    all_sessions = []
    lifelog_files = sorted(lifelogs_path.glob("*.md"))

    print(f"Scanning {len(lifelog_files)} lifelog files...")
    print(f"Detection Configuration (Phase 2.9):")
    print(f"  EXPECTED_SPEAKERS_THERAPY_SESSION: {EXPECTED_SPEAKERS_THERAPY_SESSION}")
    print(f"  THERAPY_KEYWORDS: {THERAPY_KEYWORDS}")
    print(f"  THERAPY_KEYWORD_MIN: {THERAPY_KEYWORD_MIN}")
    print(f"  THERAPY_MIN_DURATION: {THERAPY_MIN_DURATION} minutes")
    print(f"  THERAPY_MAX_DURATION: {THERAPY_MAX_DURATION} minutes")
    print(f"  THERAPY_EXCLUSION_KEYWORDS: {THERAPY_EXCLUSION_KEYWORDS}")
    print()

    for lifelog_file in lifelog_files:
        sessions = get_therapy_sessions_from_file(lifelog_file)
        all_sessions.extend(sessions)

    # Calculate summary statistics
    stats = {
        "total_lifelogs": len(lifelog_files),
        "total_sessions": len(all_sessions),
        "detection_rate_percent": (len(all_sessions) / len(lifelog_files) * 100) if lifelog_files else 0,
        "total_duration_minutes": sum(s["duration_minutes"] for s in all_sessions),
        "avg_duration_minutes": (sum(s["duration_minutes"] for s in all_sessions) / len(all_sessions)) if all_sessions else 0,
        "avg_message_count": (sum(s["message_count"] for s in all_sessions) / len(all_sessions)) if all_sessions else 0
    }

    return all_sessions, stats


def print_session_details(sessions: List[Dict]):
    """Print detailed information about each detected session."""
    if not sessions:
        print("No therapy sessions detected.")
        return

    print("=" * 80)
    print("DETECTED THERAPY SESSIONS")
    print("=" * 80)
    print()

    for i, session in enumerate(sessions, 1):
        print(f"Session {i}:")
        print(f"  Date: {session['date']}")
        print(f"  File: {session['file']}")
        print(f"  Time: {session['start_time']} - {session['end_time']}")
        print(f"  Duration: {session['duration_minutes']:.1f} minutes")
        print(f"  Messages: {session['message_count']}")
        print(f"  Speakers: {', '.join(sorted(session['speakers']))}")

        # Phase 2.9 validation checks (Boolean AND)
        print(f"  Validation Checks:")
        print(f"    Speaker Purity: {'PASS' if session['speaker_purity_pass'] else 'FAIL'}")
        print(f"    Keyword Density: {'PASS' if session['keyword_density_pass'] else 'FAIL'}")
        print(f"    Exclusion Check: {'PASS' if session['exclusion_pass'] else 'FAIL'}")
        print(f"  Matched Keywords ({session['keyword_count']}): {', '.join(session['matched_keywords'])}")

        print(f"  First Message: {session['first_message']}")
        print()


def print_summary_table(sessions: List[Dict]):
    """Print a concise summary table of all sessions."""
    if not sessions:
        return

    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print()
    print(f"{'Date':<12} {'Duration':<10} {'Messages':<10} {'Spkr':<6} {'KW':<6} {'Keywords'}")
    print("-" * 80)

    for session in sessions:
        keywords_str = f"{session['keyword_count']}: {', '.join(session['matched_keywords'][:3])}"
        if len(session['matched_keywords']) > 3:
            keywords_str += "..."

        speaker_check = "✓" if session['speaker_purity_pass'] else "✗"
        keyword_check = "✓" if session['keyword_density_pass'] else "✗"

        print(
            f"{session['date']:<12} "
            f"{session['duration_minutes']:>6.1f}min  "
            f"{session['message_count']:>8}  "
            f"{speaker_check:<6} "
            f"{keyword_check:<6} "
            f"{keywords_str}"
        )

    print()


def print_statistics(stats: Dict):
    """Print summary statistics."""
    print("=" * 80)
    print("STATISTICS (Phase 2.9)")
    print("=" * 80)
    print()
    print(f"Total Lifelogs Scanned: {stats['total_lifelogs']}")
    print(f"Total Therapy Sessions Detected: {stats['total_sessions']}")
    print(f"Detection Rate: {stats['detection_rate_percent']:.2f}%")
    print()

    if stats['total_sessions'] > 0:
        print(f"Session Characteristics:")
        print(f"  Total Duration: {stats['total_duration_minutes']:.1f} minutes ({stats['total_duration_minutes']/60:.1f} hours)")
        print(f"  Average Duration: {stats['avg_duration_minutes']:.1f} minutes")
        print(f"  Average Message Count: {stats['avg_message_count']:.1f} messages")

    print()


def export_to_file(sessions: List[Dict], output_path: Path):
    """Export session list to a text file for easy validation.

    Args:
        sessions: List of detected sessions
        output_path: Path to output file
    """
    with open(output_path, 'w') as f:
        f.write("THERAPY SESSION DETECTION VALIDATION REPORT (Phase 2.9)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Sessions Detected: {len(sessions)}\n")
        f.write("\n")

        f.write("CONFIGURATION (Phase 2.9 - Boolean AND Logic with Exclusion Keywords):\n")
        f.write(f"  EXPECTED_SPEAKERS_THERAPY_SESSION: {EXPECTED_SPEAKERS_THERAPY_SESSION}\n")
        f.write(f"  THERAPY_KEYWORDS: {THERAPY_KEYWORDS}\n")
        f.write(f"  THERAPY_KEYWORD_MIN: {THERAPY_KEYWORD_MIN}\n")
        f.write(f"  THERAPY_MIN_DURATION: {THERAPY_MIN_DURATION} minutes\n")
        f.write(f"  THERAPY_MAX_DURATION: {THERAPY_MAX_DURATION} minutes\n")
        f.write(f"  THERAPY_EXCLUSION_KEYWORDS: {THERAPY_EXCLUSION_KEYWORDS}\n")
        f.write("\n")

        f.write("DETECTED SESSIONS:\n")
        f.write("-" * 80 + "\n")

        for i, session in enumerate(sessions, 1):
            f.write(f"\nSession {i}:\n")
            f.write(f"  Date: {session['date']}\n")
            f.write(f"  File: {session['file']}\n")
            f.write(f"  Time: {session['start_time']} - {session['end_time']}\n")
            f.write(f"  Duration: {session['duration_minutes']:.1f} minutes\n")
            f.write(f"  Messages: {session['message_count']}\n")
            f.write(f"  Speakers: {', '.join(sorted(session['speakers']))}\n")

            # Phase 2.9 validation checks (Boolean AND)
            f.write(f"  Validation Checks:\n")
            f.write(f"    Speaker Purity: {'PASS' if session['speaker_purity_pass'] else 'FAIL'}\n")
            f.write(f"    Keyword Density: {'PASS' if session['keyword_density_pass'] else 'FAIL'}\n")
            f.write(f"    Exclusion Check: {'PASS' if session['exclusion_pass'] else 'FAIL'}\n")
            f.write(f"  Matched Keywords ({session['keyword_count']}): {', '.join(session['matched_keywords'])}\n")

            f.write(f"  First Message: {session['first_message']}\n")

    print(f"Report exported to: {output_path}")


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("THERAPY DETECTION VALIDATION TEST")
    print("=" * 80)
    print()

    try:
        # Scan all lifelogs
        sessions, stats = scan_all_lifelogs()

        # Print results
        print_statistics(stats)
        print_summary_table(sessions)
        print_session_details(sessions)

        # Export to file
        output_path = Path(__file__).parent / "therapy_detection_validation_report.txt"
        export_to_file(sessions, output_path)

        print("=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("1. Review the detected sessions above")
        print("2. Check the exported report for detailed information")
        print("3. Validate each session manually to identify false positives/negatives")
        print("4. Adjust THERAPY_KEYWORDS or THERAPY_KEYWORD_MIN if needed")
        print()

        if stats['total_sessions'] == 0:
            print("⚠️  WARNING: No therapy sessions detected!")
            print("   This could indicate:")
            print("   - No therapy sessions in lifelogs (expected if none occurred)")
            print("   - THERAPY_MIN_DURATION too high")
            print("   - THERAPY_KEYWORDS too specific")
            print("   - THERAPY_KEYWORD_MIN too high")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
