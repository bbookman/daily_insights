"""CLI commands for entity management.

Expanded CLI for managing the unified entity registry including:
- Entity management (add, list, show)
- STT correction management
- Transcript standardization
- Entity resolution testing
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from daily_insights.logging_config import get_logger
from daily_insights.services.entity_registry import (
    load_entity_registry,
    save_entity_registry,
    get_entity,
    get_speakers,
    get_biographical_subjects,
    get_entities_by_type,
    get_all_stt_corrections,
    get_all_aliases,
    add_entity,
    add_stt_correction,
    update_entity,
    ENTITY_PROFILES_FILE
)
from daily_insights.services.entity_resolver import (
    resolve_entity,
    resolve_and_categorize,
    fuzzy_match_entity,
    suggest_new_entity
)
from daily_insights.services.transcript_standardizer import (
    standardize_transcript,
    standardize_file,
    standardize_directory,
    report_corrections,
    get_correction_summary
)

logger = get_logger(__name__)


# ============================================================================
# Entity Management Commands
# ============================================================================

def cmd_list_entities(args):
    """List entities in the registry."""
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # Filter by type if specified
    if args.type:
        entities = {
            k: v for k, v in entities.items()
            if v.get('entity_type') == args.type
        }

    # Filter by speaker status if specified
    if args.speakers_only:
        entities = {
            k: v for k, v in entities.items()
            if v.get('is_speaker', False)
        }

    if args.biographical_only:
        entities = {
            k: v for k, v in entities.items()
            if v.get('is_biographical_subject', False)
        }

    if not entities:
        print("No entities found matching criteria.")
        return

    print(f"\n{'='*60}")
    print(f"Entity Registry ({len(entities)} entities)")
    print(f"{'='*60}\n")

    for key, entity in sorted(entities.items()):
        canonical = entity.get('canonical_name', key)
        entity_type = entity.get('entity_type', 'unknown')
        is_speaker = "S" if entity.get('is_speaker', False) else "-"
        is_bio = "B" if entity.get('is_biographical_subject', False) else "-"
        relationship = entity.get('relationship', '-')

        print(f"  {canonical:<25} [{entity_type:<8}] [{is_speaker}{is_bio}] {relationship}")

        if args.show_aliases:
            aliases = entity.get('aliases', [])
            if aliases:
                print(f"    Aliases: {', '.join(aliases)}")

            stt_corrections = entity.get('stt_corrections', {})
            if stt_corrections:
                corrections_str = ', '.join(f"'{k}'" for k in stt_corrections.keys())
                print(f"    STT Corrections: {corrections_str}")

    print(f"\n{'='*60}")
    print("Legend: [S]=Speaker, [B]=Biographical Subject")
    print(f"{'='*60}\n")


def cmd_show_entity(args):
    """Show detailed information for an entity."""
    entity = get_entity(args.name)

    if not entity:
        print(f"Entity not found: {args.name}")
        print("\nTry searching with fuzzy matching:")
        print(f"  entity resolve \"{args.name}\"")
        return

    canonical = entity.get('canonical_name', args.name)
    print(f"\n{'='*60}")
    print(f"Entity: {canonical}")
    print(f"{'='*60}\n")

    print(f"  Type: {entity.get('entity_type', 'unknown')}")
    print(f"  Is Speaker: {entity.get('is_speaker', False)}")
    print(f"  Is Biographical Subject: {entity.get('is_biographical_subject', False)}")
    print(f"  Relationship: {entity.get('relationship', '-')}")

    if entity.get('biographical_context'):
        print(f"  Context: {entity.get('biographical_context')}")

    if entity.get('added_date'):
        print(f"  Added: {entity.get('added_date')}")

    aliases = entity.get('aliases', [])
    if aliases:
        print(f"\n  Aliases: {', '.join(aliases)}")

    stt_corrections = entity.get('stt_corrections', {})
    if stt_corrections:
        print(f"\n  STT Corrections:")
        for wrong, right in stt_corrections.items():
            print(f"    '{wrong}' -> '{right}'")

    relationships = entity.get('relationships', {})
    if relationships:
        print(f"\n  Relationships:")
        for other, rel in relationships.items():
            print(f"    {other}: {rel}")

    languages = entity.get('languages', {})
    if languages:
        print(f"\n  Languages:")
        for lang, level in languages.items():
            print(f"    {lang}: {level}")

    speech_patterns = entity.get('speech_patterns', {})
    if speech_patterns:
        print(f"\n  Speech Patterns:")
        for key, value in speech_patterns.items():
            if isinstance(value, list):
                print(f"    {key}: {', '.join(value[:5])}...")
            else:
                print(f"    {key}: {value}")

    print(f"\n{'='*60}\n")


def cmd_add_entity(args):
    """Add a new entity to the registry."""
    # Check if entity already exists
    existing = get_entity(args.name)
    if existing:
        print(f"Entity '{args.name}' already exists.")
        print("Use 'entity show' to view or edit manually in entity_profiles.json")
        return

    success = add_entity(
        name=args.name,
        entity_type=args.type,
        is_speaker=args.speaker,
        is_biographical_subject=args.biographical,
        relationship=args.relationship,
        biographical_context=args.context
    )

    if success:
        print(f"Successfully added entity: {args.name}")
        print(f"  Type: {args.type}")
        print(f"  Is Speaker: {args.speaker}")
        print(f"  Is Biographical Subject: {args.biographical}")
        if args.relationship:
            print(f"  Relationship: {args.relationship}")
    else:
        print(f"Failed to add entity: {args.name}")


# ============================================================================
# STT Correction Commands
# ============================================================================

def cmd_list_corrections(args):
    """List all STT corrections."""
    corrections = get_all_stt_corrections()

    if not corrections:
        print("No STT corrections defined.")
        return

    print(f"\n{'='*60}")
    print(f"STT Corrections ({len(corrections)} total)")
    print(f"{'='*60}\n")

    # Sort by correction value to group related corrections
    sorted_corrections = sorted(corrections.items(), key=lambda x: (x[1], x[0]))

    current_target = None
    for wrong, right in sorted_corrections:
        if right != current_target:
            current_target = right
            print(f"\n  {right}:")
        print(f"    <- '{wrong}'")

    print(f"\n{'='*60}\n")


def cmd_add_correction(args):
    """Add an STT correction."""
    success = add_stt_correction(args.wrong, args.right, args.entity)

    if success:
        print(f"Successfully added STT correction: '{args.wrong}' -> '{args.right}'")
    else:
        entity_hint = f" (entity: {args.entity})" if args.entity else ""
        print(f"Failed to add STT correction: '{args.wrong}' -> '{args.right}'{entity_hint}")
        print("\nMake sure the correct value matches an existing entity's canonical name or alias.")


# ============================================================================
# Transcript Standardization Commands
# ============================================================================

def cmd_preview_fixes(args):
    """Preview corrections that would be made to a file."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"File not found: {args.file}")
        return

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    report = report_corrections(content)

    if not report:
        print(f"No corrections needed for: {args.file}")
        return

    print(f"\n{'='*60}")
    print(f"Corrections Preview: {args.file}")
    print(f"{'='*60}\n")

    total_count = 0
    for correction in report:
        count = correction['count']
        total_count += count
        print(f"  '{correction['wrong']}' -> '{correction['right']}' ({count} occurrences)")

    print(f"\n{'='*60}")
    print(f"Total: {total_count} corrections would be made")
    print(f"{'='*60}\n")


def cmd_standardize_file(args):
    """Standardize a single file."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"File not found: {args.file}")
        return

    made_changes, report = standardize_file(file_path, dry_run=args.dry_run)

    if not report:
        print(f"No corrections needed for: {args.file}")
        return

    action = "Would make" if args.dry_run else "Made"
    print(f"\n{action} {len(report)} corrections in: {args.file}")

    for correction in report:
        print(f"  '{correction['wrong']}' -> '{correction['right']}' ({correction['count']}x)")

    if args.dry_run:
        print("\nUse --apply to actually make changes.")


def cmd_standardize_directory(args):
    """Standardize all files in a directory."""
    dir_path = Path(args.directory)

    if not dir_path.exists():
        print(f"Directory not found: {args.directory}")
        return

    results = standardize_directory(dir_path, pattern=args.pattern, dry_run=args.dry_run)

    if not results:
        print(f"No corrections needed in: {args.directory}")
        return

    action = "Would make" if args.dry_run else "Made"
    print(f"\n{'='*60}")
    print(f"{action} corrections in {len(results)} files:")
    print(f"{'='*60}\n")

    for file_path, corrections in results.items():
        total = sum(c['count'] for c in corrections)
        print(f"  {file_path}: {total} corrections")

    # Summary
    summary = get_correction_summary(results)
    print(f"\n{'='*60}")
    print("Correction Summary:")
    print(f"{'='*60}\n")

    for correction_str, count in summary.items():
        print(f"  {correction_str}: {count}")

    if args.dry_run:
        print("\nUse --apply to actually make changes.")


# ============================================================================
# Entity Resolution Commands
# ============================================================================

def cmd_resolve_entity(args):
    """Test entity resolution for a name."""
    detected_name = args.name
    category = args.category

    print(f"\n{'='*60}")
    print(f"Resolving: '{detected_name}'")
    if category:
        print(f"Category hint: {category}")
    print(f"{'='*60}\n")

    # Try resolution
    canonical = resolve_entity(detected_name, category)

    if canonical:
        print(f"  Resolved: '{detected_name}' -> '{canonical}'")
        entity = get_entity(canonical)
        if entity:
            print(f"  Type: {entity.get('entity_type')}")
            print(f"  Relationship: {entity.get('relationship', '-')}")
    else:
        print(f"  No match found for '{detected_name}'")

        # Show fuzzy match candidates
        registry = load_entity_registry()
        entities = registry.get('entities', {})
        match, ratio = fuzzy_match_entity(detected_name, entities, category)

        if match and ratio > 0.5:
            print(f"\n  Closest match: '{match}' ({ratio*100:.1f}% similarity)")
            print("  (Below 85% threshold for automatic matching)")

        # Show suggestion for adding
        print(f"\n  Suggestion: Add '{detected_name}' as new entity:")
        suggestion = suggest_new_entity(detected_name, category or "person")
        print(f"    entity add \"{detected_name}\" --type {suggestion['entity_type']}")

    print(f"\n{'='*60}\n")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """CLI entry point for entity management commands."""
    parser = argparse.ArgumentParser(
        prog='entity',
        description='Entity management commands for the unified entity registry'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # list command
    list_parser = subparsers.add_parser('list', help='List entities')
    list_parser.add_argument('--type', choices=['person', 'place', 'object', 'pet', 'device'],
                            help='Filter by entity type')
    list_parser.add_argument('--speakers-only', action='store_true',
                            help='Show only speakers')
    list_parser.add_argument('--biographical-only', action='store_true',
                            help='Show only biographical subjects')
    list_parser.add_argument('--show-aliases', action='store_true',
                            help='Show aliases and STT corrections')
    list_parser.set_defaults(func=cmd_list_entities)

    # show command
    show_parser = subparsers.add_parser('show', help='Show entity details')
    show_parser.add_argument('name', help='Entity name to show')
    show_parser.set_defaults(func=cmd_show_entity)

    # add command
    add_parser = subparsers.add_parser('add', help='Add new entity')
    add_parser.add_argument('name', help='Entity name')
    add_parser.add_argument('--type', default='person',
                           choices=['person', 'place', 'object', 'pet', 'device'],
                           help='Entity type (default: person)')
    add_parser.add_argument('--speaker', action='store_true',
                           help='Mark as speaker')
    add_parser.add_argument('--biographical', action='store_true', default=True,
                           help='Mark as biographical subject (default: True)')
    add_parser.add_argument('--relationship', help='Relationship to primary user')
    add_parser.add_argument('--context', help='Brief biographical context')
    add_parser.set_defaults(func=cmd_add_entity)

    # list-corrections command
    list_corr_parser = subparsers.add_parser('list-corrections', help='List STT corrections')
    list_corr_parser.set_defaults(func=cmd_list_corrections)

    # add-correction command
    add_corr_parser = subparsers.add_parser('add-correction', help='Add STT correction')
    add_corr_parser.add_argument('wrong', help='Incorrect spelling')
    add_corr_parser.add_argument('right', help='Correct spelling')
    add_corr_parser.add_argument('--entity', help='Entity to add correction to')
    add_corr_parser.set_defaults(func=cmd_add_correction)

    # preview-fixes command
    preview_parser = subparsers.add_parser('preview-fixes', help='Preview transcript corrections')
    preview_parser.add_argument('file', help='File to preview')
    preview_parser.set_defaults(func=cmd_preview_fixes)

    # standardize command
    std_parser = subparsers.add_parser('standardize', help='Standardize a file')
    std_parser.add_argument('file', help='File to standardize')
    std_parser.add_argument('--dry-run', action='store_true',
                           help='Preview changes without applying')
    std_parser.add_argument('--apply', action='store_false', dest='dry_run',
                           help='Apply changes (default)')
    std_parser.set_defaults(func=cmd_standardize_file, dry_run=False)

    # standardize-all command
    std_all_parser = subparsers.add_parser('standardize-all', help='Standardize all files in directory')
    std_all_parser.add_argument('directory', help='Directory to process')
    std_all_parser.add_argument('--pattern', default='*.md',
                               help='File pattern to match (default: *.md)')
    std_all_parser.add_argument('--dry-run', action='store_true',
                               help='Preview changes without applying')
    std_all_parser.add_argument('--apply', action='store_false', dest='dry_run',
                               help='Apply changes')
    std_all_parser.set_defaults(func=cmd_standardize_directory, dry_run=True)

    # resolve command
    resolve_parser = subparsers.add_parser('resolve', help='Test entity resolution')
    resolve_parser.add_argument('name', help='Name to resolve')
    resolve_parser.add_argument('--category', choices=['person', 'place', 'object', 'pet'],
                               help='Category hint')
    resolve_parser.set_defaults(func=cmd_resolve_entity)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
