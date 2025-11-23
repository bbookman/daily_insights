# Entity Management CLI Guide

**Created**: 2025-11-23
**Status**: Production Ready

## Overview

The Entity Management system provides a unified registry for managing speakers, biographical subjects, and STT (speech-to-text) corrections. This guide covers CLI commands and procedures for managing entities and standardizing transcripts.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Entity Management Commands](#entity-management-commands)
3. [STT Correction Commands](#stt-correction-commands)
4. [Transcript Standardization Commands](#transcript-standardization-commands)
5. [Entity Resolution Commands](#entity-resolution-commands)
6. [Retroactive STT Fix-Up Procedure](#retroactive-stt-fix-up-procedure)
7. [Configuration Reference](#configuration-reference)

---

## Quick Start

```bash
# List all entities
python -m daily_insights.cli.entity_commands list

# Preview STT corrections for a transcript
python -m daily_insights.cli.entity_commands preview-fixes /path/to/transcript.md

# Apply STT corrections to all transcripts in a directory
python -m daily_insights.cli.entity_commands standardize-all /path/to/transcripts --apply

# Test entity resolution
python -m daily_insights.cli.entity_commands resolve "Joel Gilmet"
```

---

## Entity Management Commands

### `entity list`

List entities in the registry with optional filters.

```bash
# List all entities
python -m daily_insights.cli.entity_commands list

# Filter by entity type
python -m daily_insights.cli.entity_commands list --type person
python -m daily_insights.cli.entity_commands list --type pet
python -m daily_insights.cli.entity_commands list --type object

# Show only speakers
python -m daily_insights.cli.entity_commands list --speakers-only

# Show only biographical subjects
python -m daily_insights.cli.entity_commands list --biographical-only

# Show aliases and STT corrections
python -m daily_insights.cli.entity_commands list --show-aliases
```

**Output Legend:**
- `[S]` = Entity is a speaker (appears in transcripts)
- `[B]` = Entity is a biographical subject (has/needs biography file)
- `[-]` = Flag not set

**Example Output:**
```
============================================================
Entity Registry (23 entities)
============================================================

  Bruce Bookman             [person  ] [S-] self
  Ivette                    [person  ] [SB] spouse
  Joel Guilmet              [person  ] [SB] friend
  Grape                     [pet     ] [-B] pet
  TV Pow                    [object  ] [-B] childhood memory

============================================================
Legend: [S]=Speaker, [B]=Biographical Subject
============================================================
```

### `entity show`

Display detailed information for a specific entity.

```bash
python -m daily_insights.cli.entity_commands show "Joel Guilmet"
python -m daily_insights.cli.entity_commands show "Grape"
python -m daily_insights.cli.entity_commands show "Matt"  # Works with aliases
```

**Example Output:**
```
============================================================
Entity: Joel Guilmet
============================================================

  Type: person
  Is Speaker: True
  Is Biographical Subject: True
  Relationship: friend
  Context: College friend, worked at Lowe's then Walgreens
  Added: 2025-10-30

  Aliases: Joel

  STT Corrections:
    'Joel Gil' -> 'Joel'
    'Joel Gilmet' -> 'Joel Guilmet'
    'Joel Guillerme' -> 'Joel Guilmet'
    'Joel Gilhamet' -> 'Joel Guilmet'

  Relationships:
    Bruce: friend

============================================================
```

### `entity add`

Add a new entity to the registry.

```bash
# Add a person (speaker + biographical subject)
python -m daily_insights.cli.entity_commands add "New Friend" \
  --type person \
  --speaker \
  --relationship friend \
  --context "Met at conference in 2024"

# Add a pet (biographical subject only)
python -m daily_insights.cli.entity_commands add "Fluffy" \
  --type pet \
  --relationship pet \
  --context "Family dog"

# Add a place
python -m daily_insights.cli.entity_commands add "Childhood Home" \
  --type place \
  --relationship "childhood memory" \
  --context "House on Oak Street"
```

**Options:**
- `--type`: person, place, object, pet, device (default: person)
- `--speaker`: Mark as speaker (can appear in transcripts)
- `--biographical`: Mark as biographical subject (default: True)
- `--relationship`: Relationship to primary user
- `--context`: Brief biographical context

---

## STT Correction Commands

### `entity list-corrections`

List all STT (speech-to-text) corrections grouped by target.

```bash
python -m daily_insights.cli.entity_commands list-corrections
```

**Example Output:**
```
============================================================
STT Corrections (27 total)
============================================================

  Grape:
    <- 'Crape'
    <- 'Gray'
    <- 'Grabe'

  Joel Guilmet:
    <- 'Joel Gilmet'
    <- 'Joel Guillerme'
    <- 'Joel Gilhamet'

  Matt Bookman:
    <- 'Mat Bookman'
    <- 'Mathew Bookman'

============================================================
```

### `entity add-correction`

Add a new STT correction to the registry.

```bash
# Add correction (auto-detects entity from correct spelling)
python -m daily_insights.cli.entity_commands add-correction "Jole" "Joel"

# Add correction to specific entity
python -m daily_insights.cli.entity_commands add-correction "TV Paw" "TV Pow" --entity "TV Pow"
```

**Arguments:**
- `wrong`: The incorrect STT spelling to correct
- `right`: The correct spelling
- `--entity`: (Optional) Entity to add correction to

---

## Transcript Standardization Commands

### `entity preview-fixes`

Preview corrections that would be made to a file (dry-run).

```bash
python -m daily_insights.cli.entity_commands preview-fixes lifelogs/2025-03-01.md
```

**Example Output:**
```
============================================================
Corrections Preview: lifelogs/2025-03-01.md
============================================================

  'Joel Gilmet' -> 'Joel Guilmet' (2 occurrences)
  'Crape' -> 'Grape' (5 occurrences)

============================================================
Total: 7 corrections would be made
============================================================
```

### `entity standardize`

Standardize a single file by applying STT corrections.

```bash
# Preview changes (dry-run)
python -m daily_insights.cli.entity_commands standardize lifelogs/2025-03-01.md --dry-run

# Apply changes
python -m daily_insights.cli.entity_commands standardize lifelogs/2025-03-01.md
```

**Options:**
- `--dry-run`: Preview changes without applying
- `--apply`: Apply changes (default behavior)

### `entity standardize-all`

Standardize all matching files in a directory.

```bash
# Preview changes in directory (default is dry-run)
python -m daily_insights.cli.entity_commands standardize-all /path/to/transcripts

# Apply changes
python -m daily_insights.cli.entity_commands standardize-all /path/to/transcripts --apply

# Custom file pattern
python -m daily_insights.cli.entity_commands standardize-all /path/to/transcripts --pattern "*.txt" --apply
```

**Options:**
- `--pattern`: File glob pattern (default: `*.md`)
- `--dry-run`: Preview changes without applying (default)
- `--apply`: Apply changes to files

**Example Output:**
```
============================================================
Would make corrections in 15 files:
============================================================

  lifelogs/2025-03-01.md: 7 corrections
  lifelogs/2025-03-02.md: 3 corrections
  lifelogs/2025-03-05.md: 12 corrections

============================================================
Correction Summary:
============================================================

  Crape -> Grape: 15
  Joel Gilmet -> Joel Guilmet: 4
  Yvette -> Ivette: 3

Use --apply to actually make changes.
```

---

## Entity Resolution Commands

### `entity resolve`

Test entity resolution to see how a detected name would be resolved.

```bash
# Test resolution
python -m daily_insights.cli.entity_commands resolve "Joel Gilmet"
python -m daily_insights.cli.entity_commands resolve "Crape"
python -m daily_insights.cli.entity_commands resolve "Unknown Person"

# With category hint
python -m daily_insights.cli.entity_commands resolve "TV Pal" --category object
```

**Example Output (Match Found):**
```
============================================================
Resolving: 'Joel Gilmet'
============================================================

  Resolved: 'Joel Gilmet' -> 'Joel Guilmet'
  Type: person
  Relationship: friend

============================================================
```

**Example Output (No Match):**
```
============================================================
Resolving: 'Unknown Person'
============================================================

  No match found for 'Unknown Person'

  Closest match: 'Myron Meyer' (62.5% similarity)
  (Below 85% threshold for automatic matching)

  Suggestion: Add 'Unknown Person' as new entity:
    entity add "Unknown Person" --type person

============================================================
```

---

## Retroactive STT Fix-Up Procedure

This procedure standardizes existing transcripts to fix STT errors that were recorded before the standardization system was implemented.

### Step 1: Review Current STT Corrections

```bash
# See all defined corrections
python -m daily_insights.cli.entity_commands list-corrections
```

### Step 2: Preview Changes (Dry Run)

**Always preview before applying changes.**

```bash
# Lifelogs
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/lifelogs

# Bee transcriptions
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/bee

# Psychologist transcripts
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/psychologist_singles
```

### Step 3: Review the Summary

Check the correction summary output:
- Verify the corrections look correct
- Note the total number of changes per file
- Identify any unexpected corrections

### Step 4: Apply Changes

Once satisfied with the preview:

```bash
# Lifelogs
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/lifelogs --apply

# Bee transcriptions
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/bee --apply

# Psychologist transcripts
python -m daily_insights.cli.entity_commands standardize-all \
  /Users/brucebookman/bruce_vault/Transcripts/psychologist_singles --apply
```

### Step 5: Regenerate Biographies (Optional)

After standardizing transcripts, regenerate biographies with corrected names:

```bash
# Delete existing biographies
rm -rf /Users/brucebookman/bruce_vault/Transcripts/biographies/people/*.md
rm -rf /Users/brucebookman/bruce_vault/Transcripts/biographies/places/*.md
rm -rf /Users/brucebookman/bruce_vault/Transcripts/biographies/objects/*.md

# Clear processing state
rm /Users/brucebookman/bruce_vault/Transcripts/biographies/.biographical_processing_state.json

# Regenerate (run the main pipeline)
python -m daily_insights.main
```

### Complete Script

For convenience, here's a complete script to run the full procedure:

```bash
#!/bin/bash
# retroactive_stt_fixup.sh

TRANSCRIPTS_BASE="/Users/brucebookman/bruce_vault/Transcripts"

echo "=== Retroactive STT Fix-Up ==="
echo ""

# Step 1: Preview all directories
echo "Step 1: Previewing changes..."
echo ""

for dir in lifelogs bee psychologist_singles; do
  if [ -d "$TRANSCRIPTS_BASE/$dir" ]; then
    echo "--- $dir ---"
    python -m daily_insights.cli.entity_commands standardize-all "$TRANSCRIPTS_BASE/$dir"
    echo ""
  fi
done

# Step 2: Prompt for confirmation
read -p "Apply these changes? (y/n): " confirm
if [ "$confirm" != "y" ]; then
  echo "Aborted."
  exit 0
fi

# Step 3: Apply changes
echo ""
echo "Step 2: Applying changes..."

for dir in lifelogs bee psychologist_singles; do
  if [ -d "$TRANSCRIPTS_BASE/$dir" ]; then
    echo "--- $dir ---"
    python -m daily_insights.cli.entity_commands standardize-all "$TRANSCRIPTS_BASE/$dir" --apply
    echo ""
  fi
done

echo "=== Complete ==="
```

---

## Configuration Reference

### Entity Profiles Location

```
daily_insights/config/entity_profiles.json
```

### Entity Schema

```json
{
  "Entity Key": {
    "canonical_name": "Full Canonical Name",
    "entity_type": "person|place|object|pet|device",
    "is_speaker": true|false,
    "is_biographical_subject": true|false,
    "aliases": ["Alias1", "Alias2"],
    "stt_corrections": {
      "Wrong Spelling": "Correct Spelling"
    },
    "relationship": "relationship to primary user",
    "relationships": {
      "Other Entity": "relationship"
    },
    "biographical_context": "Brief description",
    "languages": {
      "English": "fluent"
    },
    "speech_patterns": {
      "vocabulary_level": "college|conversational|child like",
      "speaking_style": "descriptive text",
      "common_topics": ["topic1", "topic2"],
      "distinctive_phrases": ["phrase1", "phrase2"]
    },
    "added_date": "YYYY-MM-DD"
  }
}
```

### Entity Types

| Type | Description | Example |
|------|-------------|---------|
| `person` | Human individuals | Bruce, Ivette, Joel Guilmet |
| `pet` | Animals/pets | Grape, Peach |
| `place` | Locations | (future use) |
| `object` | Things, shows, items | TV Pow, Voice Farm |
| `device` | Voice assistants, devices | Alexa, Siri |

### Resolution Priority

When resolving entity names, the system checks in this order:

1. **Exact canonical name match** (case-insensitive)
2. **STT correction match** (wrong → right mapping)
3. **Alias match** (aliases list)
4. **Fuzzy match** (85% similarity threshold)

---

## Troubleshooting

### No corrections found

```bash
python -m daily_insights.cli.entity_commands list-corrections
```
Check if corrections are defined. If empty, add corrections with:
```bash
python -m daily_insights.cli.entity_commands add-correction "wrong" "right"
```

### Entity not found

```bash
python -m daily_insights.cli.entity_commands resolve "name"
```
This shows the closest match and suggests how to add the entity.

### Permission errors

Ensure you have write permissions to the transcript files and directories.

### Syntax verification

```bash
python -m py_compile daily_insights/services/transcript_standardizer.py
python -m py_compile daily_insights/cli/entity_commands.py
```

---

## Related Documentation

- `claudedocs/ENTITY_MANAGEMENT_DESIGN.md` - System design and architecture
- `daily_insights/config/entity_profiles.json` - Entity registry data
- `daily_insights/services/entity_registry.py` - Registry service API
- `daily_insights/services/transcript_standardizer.py` - Standardization service API
- `daily_insights/services/entity_resolver.py` - Resolution service API
