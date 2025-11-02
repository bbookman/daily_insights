#!/usr/bin/env python3
"""
Batch process existing lifelogs to add speaker identification.

This script processes all lifelogs that haven't been speaker-identified yet,
applying the same speaker identification logic used for new lifelogs.

Usage:
    python scripts/backfill_speaker_labels.py [--dry-run] [--limit N] [--file PATH]

Options:
    --dry-run       Show what would be processed without making changes
    --limit N       Only process N files (for testing)
    --file PATH     Process a single specific file
    --skip-recent   Skip files modified in last 24 hours (to avoid conflicts)
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from daily_insights.config import LIFELOGS_DIR
from daily_insights.services.speaker_service import (
    identify_speakers_async,
    apply_speaker_labels,
    mark_file_processed,
    is_file_processed
)


def get_unprocessed_lifelogs(skip_recent: bool = False) -> List[Path]:
    """
    Get list of lifelog files that haven't been speaker-processed.

    Parameters
    ----------
    skip_recent : bool
        If True, skip files modified in last 24 hours

    Returns
    -------
    List[Path]
        List of unprocessed lifelog file paths
    """
    if not LIFELOGS_DIR.exists():
        print(f"Error: Lifelogs directory not found: {LIFELOGS_DIR}")
        return []

    # Get all markdown files
    all_lifelogs = list(LIFELOGS_DIR.glob("*.md"))

    # Filter to unprocessed
    unprocessed = []
    cutoff_time = datetime.now() - timedelta(hours=24)

    for lifelog_path in all_lifelogs:
        # Check if already processed
        relative_path = f"lifelogs/{lifelog_path.name}"
        if is_file_processed(relative_path):
            continue

        # Skip recent files if requested
        if skip_recent:
            mod_time = datetime.fromtimestamp(lifelog_path.stat().st_mtime)
            if mod_time > cutoff_time:
                continue

        # Check if file contains "Unknown" speakers (heuristic for unprocessed)
        try:
            content = lifelog_path.read_text(encoding='utf-8')
            if "Unknown (" in content or "- Unknown:" in content:
                unprocessed.append(lifelog_path)
        except Exception as e:
            print(f"Warning: Could not read {lifelog_path.name}: {e}")
            continue

    # Sort by date (oldest first for chronological processing)
    unprocessed.sort()

    return unprocessed


async def process_single_lifelog(lifelog_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single lifelog file for speaker identification.

    Parameters
    ----------
    lifelog_path : Path
        Path to lifelog file
    dry_run : bool
        If True, don't make changes

    Returns
    -------
    bool
        True if successful
    """
    try:
        # Read existing content
        content = lifelog_path.read_text(encoding='utf-8')

        # Check if it needs processing
        if "Unknown (" not in content and "- Unknown:" not in content:
            print(f"  ⏭️  Skipping {lifelog_path.name} - no Unknown speakers found")
            return True

        print(f"  🔍 Identifying speakers in {lifelog_path.name}...")

        # Identify speakers
        speaker_mappings = await identify_speakers_async(content)

        if not speaker_mappings:
            print(f"  ⚠️  No speaker mappings generated for {lifelog_path.name}")
            return False

        print(f"     Found {len(speaker_mappings)} speaker mappings")

        # Apply labels with confidence tiers
        updated_content = apply_speaker_labels(
            content,
            speaker_mappings,
            confidence_threshold_high=0.85,
            confidence_threshold_medium=0.60
        )

        # Count replacements
        original_unknowns = content.count("Unknown (")
        remaining_unknowns = updated_content.count("Unknown (")
        replaced = original_unknowns - remaining_unknowns

        if replaced > 0:
            print(f"     ✓ Replaced {replaced}/{original_unknowns} Unknown labels")
        else:
            print(f"     ⚠️  No labels replaced (low confidence)")

        if dry_run:
            print(f"     [DRY RUN] Would save changes to {lifelog_path.name}")
            return True

        # Save updated content
        lifelog_path.write_text(updated_content, encoding='utf-8')

        # Mark as processed
        relative_path = f"lifelogs/{lifelog_path.name}"
        mark_file_processed(relative_path)

        print(f"     ✅ Saved {lifelog_path.name}")
        return True

    except Exception as e:
        print(f"  ❌ Error processing {lifelog_path.name}: {e}")
        return False


async def batch_process_lifelogs(
    lifelog_paths: List[Path],
    dry_run: bool = False,
    batch_size: int = 5
):
    """
    Process multiple lifelogs with batching and progress tracking.

    Parameters
    ----------
    lifelog_paths : List[Path]
        List of lifelog files to process
    dry_run : bool
        If True, don't make changes
    batch_size : int
        Number of files to process concurrently
    """
    total = len(lifelog_paths)
    successful = 0
    failed = 0

    print(f"\n📊 Processing {total} lifelog files...")
    if dry_run:
        print("🔶 DRY RUN MODE - No changes will be made\n")

    # Process in batches
    for i in range(0, total, batch_size):
        batch = lifelog_paths[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} files)")

        # Process batch concurrently
        tasks = [process_single_lifelog(path, dry_run) for path in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count results
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result:
                successful += 1
            else:
                failed += 1

        # Progress update
        processed_so_far = min(i + batch_size, total)
        print(f"\n   Progress: {processed_so_far}/{total} files processed")

        # Small delay between batches to avoid rate limits
        if i + batch_size < total:
            await asyncio.sleep(1)

    # Final summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Total files: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if dry_run:
        print(f"\n🔶 DRY RUN - No changes were made to files")
    else:
        print(f"\n✅ Processing complete!")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch process existing lifelogs for speaker identification"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process N files (for testing)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process a single specific file"
    )
    parser.add_argument(
        "--skip-recent",
        action="store_true",
        help="Skip files modified in last 24 hours"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of files to process concurrently (default: 5)"
    )

    args = parser.parse_args()

    print("🎯 Speaker Label Backfill Tool")
    print("=" * 60)

    # Single file mode
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Error: File not found: {args.file}")
            sys.exit(1)

        print(f"\n📄 Processing single file: {file_path.name}")
        success = await process_single_lifelog(file_path, args.dry_run)
        sys.exit(0 if success else 1)

    # Batch mode
    unprocessed = get_unprocessed_lifelogs(args.skip_recent)

    if not unprocessed:
        print("\n✅ No unprocessed lifelogs found!")
        print("   All files have already been speaker-identified.")
        sys.exit(0)

    print(f"\n📋 Found {len(unprocessed)} unprocessed lifelog files")

    # Apply limit if specified
    if args.limit and args.limit < len(unprocessed):
        print(f"⚠️  Limiting to first {args.limit} files")
        unprocessed = unprocessed[:args.limit]

    # Confirm before proceeding
    if not args.dry_run:
        print(f"\n⚠️  This will modify {len(unprocessed)} files.")
        response = input("Continue? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            sys.exit(0)

    # Process files
    await batch_process_lifelogs(
        unprocessed,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    asyncio.run(main())
