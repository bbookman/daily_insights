#!/usr/bin/env python3
"""
Doctor Visit Detection Validation Test

Lists all dates/files containing detected doctor visits to aid human validation
of the detection system. This test helps verify that the MVP detection approach
is working correctly and excludes psychiatrist/mental health visits.

Usage:
    python tests/test_doctor_visit_validation.py
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

from daily_insights.models.conversation_parser import (
    parse_lifelog_dialogue,
    group_into_conversations,
    is_doctor_visit,
    is_therapy_session,
    is_journal_session,
    calculate_duration_minutes,
    check_doctor_keyword_density,
    check_doctor_speaker_purity,
    check_doctor_exclusion_keywords,
    calculate_doctor_visit_confidence
)
from daily_insights.config import (
    LIFELOGS_DIR,
    EXPECTED_SPEAKERS_DOCTOR_VISIT,
    DOCTOR_KEYWORDS,
    DOCTOR_KEYWORD_MIN,
    DOCTOR_MIN_DURATION,
    DOCTOR_MAX_DURATION,
    DOCTOR_EXCLUSION_KEYWORDS
)


def get_doctor_visits_from_file(lifelog_path: Path) -> List[Dict]:
    """Extract all doctor visits from a single lifelog file.

    Args:
        lifelog_path: Path to lifelog markdown file

    Returns:
        List of detected doctor visits with metadata
    """
    visits = []

    try:
        dialogues = parse_lifelog_dialogue(lifelog_path)
        conversations = group_into_conversations(dialogues)

        for conv in conversations:
            if is_doctor_visit(conv):
                duration = calculate_duration_minutes(conv)
                speakers = set(d["speaker"] for d in conv)

                # Check validation results (Boolean AND logic)
                speaker_purity_pass = check_doctor_speaker_purity(conv)
                keyword_density_pass = check_doctor_keyword_density(conv)
                exclusion_pass = check_doctor_exclusion_keywords(conv)
                not_therapy = not is_therapy_session(conv)
                not_journal = not is_journal_session(conv)

                # Check keyword matches
                content_combined = " ".join(d["content"].lower() for d in conv)
                matched_keywords = [
                    kw for kw in DOCTOR_KEYWORDS
                    if kw.lower() in content_combined
                ]

                # Check for exclusion keyword matches (for reporting)
                exclusion_matches = [
                    kw for kw in DOCTOR_EXCLUSION_KEYWORDS
                    if kw.lower() in content_combined
                ]

                # Calculate confidence score
                confidence_score = calculate_doctor_visit_confidence(conv)

                visits.append({
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
                    "not_therapy": not_therapy,
                    "not_journal": not_journal,
                    "matched_keywords": matched_keywords,
                    "keyword_count": len(matched_keywords),
                    "exclusion_matches": exclusion_matches,
                    "confidence_score": confidence_score,
                    "first_message": conv[0]["content"][:100] + "..." if len(conv[0]["content"]) > 100 else conv[0]["content"]
                })

    except Exception as e:
        print(f"Error processing {lifelog_path.name}: {e}")

    return visits


def scan_all_lifelogs() -> Tuple[List[Dict], Dict]:
    """Scan all lifelog files for doctor visits.

    Returns:
        Tuple of (visits list, summary statistics dict)
    """
    lifelogs_path = Path(LIFELOGS_DIR)

    if not lifelogs_path.exists():
        raise FileNotFoundError(f"Lifelogs directory not found: {lifelogs_path}")

    all_visits = []
    lifelog_files = sorted(lifelogs_path.glob("*.md"))

    print(f"Scanning {len(lifelog_files)} lifelog files...")
    print(f"Detection Configuration (MVP):")
    print(f"  EXPECTED_SPEAKERS_DOCTOR_VISIT: {EXPECTED_SPEAKERS_DOCTOR_VISIT}")
    print(f"  DOCTOR_KEYWORDS: {DOCTOR_KEYWORDS}")
    print(f"  DOCTOR_KEYWORD_MIN: {DOCTOR_KEYWORD_MIN}")
    print(f"  DOCTOR_MIN_DURATION: {DOCTOR_MIN_DURATION} minutes")
    print(f"  DOCTOR_MAX_DURATION: {DOCTOR_MAX_DURATION} minutes")
    print(f"  DOCTOR_EXCLUSION_KEYWORDS: {DOCTOR_EXCLUSION_KEYWORDS}")
    print()

    for lifelog_file in lifelog_files:
        visits = get_doctor_visits_from_file(lifelog_file)
        all_visits.extend(visits)

    # Calculate summary statistics
    stats = {
        "total_lifelogs": len(lifelog_files),
        "total_visits": len(all_visits),
        "detection_rate_percent": (len(all_visits) / len(lifelog_files) * 100) if lifelog_files else 0,
        "total_duration_minutes": sum(v["duration_minutes"] for v in all_visits),
        "avg_duration_minutes": (sum(v["duration_minutes"] for v in all_visits) / len(all_visits)) if all_visits else 0,
        "avg_message_count": (sum(v["message_count"] for v in all_visits) / len(all_visits)) if all_visits else 0
    }

    return all_visits, stats


def print_visit_details(visits: List[Dict]):
    """Print detailed information about each detected visit."""
    if not visits:
        print("No doctor visits detected.")
        return

    print("=" * 80)
    print("DETECTED DOCTOR VISITS")
    print("=" * 80)
    print()

    for i, visit in enumerate(visits, 1):
        print(f"Visit {i}:")
        print(f"  Date: {visit['date']}")
        print(f"  File: {visit['file']}")
        print(f"  Time: {visit['start_time']} - {visit['end_time']}")
        print(f"  Duration: {visit['duration_minutes']:.1f} minutes")
        print(f"  Messages: {visit['message_count']}")
        print(f"  Speakers: {', '.join(sorted(visit['speakers']))}")

        # Validation checks (Boolean AND)
        print(f"  Validation Checks:")
        print(f"    Speaker Purity: {'PASS' if visit['speaker_purity_pass'] else 'FAIL'}")
        print(f"    Keyword Density: {'PASS' if visit['keyword_density_pass'] else 'FAIL'}")
        print(f"    Exclusion Check: {'PASS' if visit['exclusion_pass'] else 'FAIL'}")
        print(f"    Not Therapy Session: {'PASS' if visit['not_therapy'] else 'FAIL'}")
        print(f"    Not Journal Session: {'PASS' if visit['not_journal'] else 'FAIL'}")
        print(f"  Confidence Score: {visit['confidence_score']:.2f}")
        print(f"  Matched Keywords ({visit['keyword_count']}): {', '.join(visit['matched_keywords'])}")

        if visit['exclusion_matches']:
            print(f"  ⚠️  Exclusion Matches: {', '.join(visit['exclusion_matches'])}")

        print(f"  First Message: {visit['first_message']}")
        print()


def print_summary_table(visits: List[Dict]):
    """Print a concise summary table of all visits."""
    if not visits:
        return

    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print()
    print(f"{'Date':<12} {'Duration':<10} {'Messages':<10} {'Conf':<6} {'Spkr':<6} {'KW':<6} {'Keywords'}")
    print("-" * 80)

    for visit in visits:
        keywords_str = f"{visit['keyword_count']}: {', '.join(visit['matched_keywords'][:3])}"
        if len(visit['matched_keywords']) > 3:
            keywords_str += "..."

        confidence_display = f"{visit['confidence_score']:.2f}"
        speaker_check = "✓" if visit['speaker_purity_pass'] else "✗"
        keyword_check = "✓" if visit['keyword_density_pass'] else "✗"

        print(
            f"{visit['date']:<12} "
            f"{visit['duration_minutes']:>6.1f}min  "
            f"{visit['message_count']:>8}  "
            f"{confidence_display:<6} "
            f"{speaker_check:<6} "
            f"{keyword_check:<6} "
            f"{keywords_str}"
        )

    print()


def print_statistics(stats: Dict):
    """Print summary statistics."""
    print("=" * 80)
    print("STATISTICS (MVP)")
    print("=" * 80)
    print()
    print(f"Total Lifelogs Scanned: {stats['total_lifelogs']}")
    print(f"Total Doctor Visits Detected: {stats['total_visits']}")
    print(f"Detection Rate: {stats['detection_rate_percent']:.2f}%")
    print()

    if stats['total_visits'] > 0:
        print(f"Visit Characteristics:")
        print(f"  Total Duration: {stats['total_duration_minutes']:.1f} minutes ({stats['total_duration_minutes']/60:.1f} hours)")
        print(f"  Average Duration: {stats['avg_duration_minutes']:.1f} minutes")
        print(f"  Average Message Count: {stats['avg_message_count']:.1f} messages")

    print()


def export_to_file(visits: List[Dict], output_path: Path):
    """Export visit list to a text file for easy validation.

    Args:
        visits: List of detected visits
        output_path: Path to output file
    """
    with open(output_path, 'w') as f:
        f.write("DOCTOR VISIT DETECTION VALIDATION REPORT (MVP)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Visits Detected: {len(visits)}\n")
        f.write("\n")

        f.write("CONFIGURATION (MVP - Boolean AND Logic with Exclusion Keywords):\n")
        f.write(f"  EXPECTED_SPEAKERS_DOCTOR_VISIT: {EXPECTED_SPEAKERS_DOCTOR_VISIT}\n")
        f.write(f"  DOCTOR_KEYWORDS: {DOCTOR_KEYWORDS}\n")
        f.write(f"  DOCTOR_KEYWORD_MIN: {DOCTOR_KEYWORD_MIN}\n")
        f.write(f"  DOCTOR_MIN_DURATION: {DOCTOR_MIN_DURATION} minutes\n")
        f.write(f"  DOCTOR_MAX_DURATION: {DOCTOR_MAX_DURATION} minutes\n")
        f.write(f"  DOCTOR_EXCLUSION_KEYWORDS: {DOCTOR_EXCLUSION_KEYWORDS}\n")
        f.write("\n")

        f.write("DETECTED VISITS:\n")
        f.write("-" * 80 + "\n")

        for i, visit in enumerate(visits, 1):
            f.write(f"\nVisit {i}:\n")
            f.write(f"  Date: {visit['date']}\n")
            f.write(f"  File: {visit['file']}\n")
            f.write(f"  Time: {visit['start_time']} - {visit['end_time']}\n")
            f.write(f"  Duration: {visit['duration_minutes']:.1f} minutes\n")
            f.write(f"  Messages: {visit['message_count']}\n")
            f.write(f"  Speakers: {', '.join(sorted(visit['speakers']))}\n")

            # Validation checks (Boolean AND)
            f.write(f"  Validation Checks:\n")
            f.write(f"    Speaker Purity: {'PASS' if visit['speaker_purity_pass'] else 'FAIL'}\n")
            f.write(f"    Keyword Density: {'PASS' if visit['keyword_density_pass'] else 'FAIL'}\n")
            f.write(f"    Exclusion Check: {'PASS' if visit['exclusion_pass'] else 'FAIL'}\n")
            f.write(f"    Not Therapy Session: {'PASS' if visit['not_therapy'] else 'FAIL'}\n")
            f.write(f"    Not Journal Session: {'PASS' if visit['not_journal'] else 'FAIL'}\n")
            f.write(f"  Confidence Score: {visit['confidence_score']:.2f}\n")
            f.write(f"  Matched Keywords ({visit['keyword_count']}): {', '.join(visit['matched_keywords'])}\n")

            if visit['exclusion_matches']:
                f.write(f"  ⚠️  Exclusion Matches: {', '.join(visit['exclusion_matches'])}\n")

            f.write(f"  First Message: {visit['first_message']}\n")

    print(f"Report exported to: {output_path}")


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("DOCTOR VISIT DETECTION VALIDATION TEST")
    print("=" * 80)
    print()

    try:
        # Scan all lifelogs
        visits, stats = scan_all_lifelogs()

        # Print results
        print_statistics(stats)
        print_summary_table(visits)
        print_visit_details(visits)

        # Export to file
        output_path = Path(__file__).parent / "doctor_visit_validation_report.txt"
        export_to_file(visits, output_path)

        print("=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("1. Review the detected visits above")
        print("2. Check the exported report for detailed information")
        print("3. Validate each visit manually to identify false positives/negatives")
        print("4. Verify psychiatrist visits are correctly excluded")
        print("5. Adjust DOCTOR_KEYWORDS or DOCTOR_KEYWORD_MIN if needed")
        print()

        if stats['total_visits'] == 0:
            print("⚠️  WARNING: No doctor visits detected!")
            print("   This could indicate:")
            print("   - No doctor visits in lifelogs (expected if none occurred)")
            print("   - DOCTOR_MIN_DURATION too high")
            print("   - DOCTOR_KEYWORDS too specific")
            print("   - DOCTOR_KEYWORD_MIN too high")
            print("   - All visits being excluded (check DOCTOR_EXCLUSION_KEYWORDS)")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
