# Speaker Identification - Backfill Guide

## Overview

Your speaker identification system is now **fully operational**! ✅

- ✅ **Forward-looking**: New lifelogs automatically get speaker labels
- ✅ **Backfill script**: Process existing 190 unlabeled lifelogs
- ✅ **Training data**: 410 labeled examples from manual training
- ✅ **Speaker profiles**: 10 configured speakers

## Current Status

### Already Labeled
- **208 files** have speaker labels (Bruce, Ivette, etc.)
- These were manually labeled during training data creation

### Need Processing
- **190 files** still show "Unknown" speakers
- These can be batch-processed with the new script

## How to Use

### Option 1: Process All Unlabeled Files

```bash
# Dry run first (recommended) - see what would be changed
python3 scripts/backfill_speaker_labels.py --dry-run

# Process all files (will ask for confirmation)
python3 scripts/backfill_speaker_labels.py
```

### Option 2: Process in Batches (Safer)

```bash
# Process 10 files at a time for testing
python3 scripts/backfill_speaker_labels.py --limit 10

# After verifying results look good, process more
python3 scripts/backfill_speaker_labels.py --limit 50

# Continue until done
python3 scripts/backfill_speaker_labels.py
```

### Option 3: Process Single File

```bash
# Test on a specific file
python3 scripts/backfill_speaker_labels.py --file lifelogs/2025-09-29.md
```

### Option 4: Skip Recent Files

```bash
# Skip files modified in last 24 hours (avoid conflicts)
python3 scripts/backfill_speaker_labels.py --skip-recent
```

## Script Features

### Safety Features
- ✅ **Dry run mode** - Preview changes without modifying files
- ✅ **Confirmation prompt** - Asks before making changes
- ✅ **Skip processed files** - Won't re-process already labeled files
- ✅ **Graceful error handling** - Continues on failures
- ✅ **Progress tracking** - Shows real-time progress

### Confidence Tiers

The script uses the same confidence system as forward-looking processing:

- **High confidence (≥85%)**: Direct replacement
  - `Unknown` → `Bruce`

- **Medium confidence (60-85%)**: Labeled with percentage
  - `Unknown` → `Bruce [72%]`

- **Low confidence (<60%)**: Left unchanged
  - `Unknown` → `Unknown` (no change)

### Performance

- Processes **5 files concurrently** by default
- Adjustable with `--batch-size N`
- Rate-limited to avoid API throttling

## Forward-Looking System (Already Configured!)

✅ **Automatic speaker identification is ENABLED** in `lifelog_service.py:233-246`

When you fetch new lifelogs, the system will:
1. Fetch new lifelogs from Limitless API
2. Automatically identify speakers using LLM
3. Apply confidence-based labels
4. Save with speaker names
5. Mark as processed

**No action needed** - this happens automatically!

## Expected Results

### Good Results
Most files should get **high or medium confidence** labels for Bruce and Ivette since you have:
- 10 speaker profiles configured
- 410 training examples
- Detailed speech patterns

### Low Confidence Cases
Some files may have low confidence if:
- Speakers are not in your profiles (add them!)
- Very short conversations
- Unusual speech patterns
- Multiple unknown speakers

## Troubleshooting

### "No speaker mappings generated"
**Cause**: LLM couldn't identify speakers with confidence

**Solution**:
- File might have very brief conversations
- Check if speakers in the file are in your profiles
- This is normal for some files

### "No labels replaced (low confidence)"
**Cause**: All identifications were below 60% confidence

**Solution**:
- Add more training examples for those speakers
- Enhance speaker profiles with more patterns
- These files will keep "Unknown" labels (safer than guessing)

### API Rate Limits
**Cause**: Processing too many files too fast

**Solution**:
- Script has built-in delays between batches
- Reduce `--batch-size` if needed
- Process in smaller chunks

## Recommended Workflow

### First Time (Recommended)

1. **Test with dry run**:
   ```bash
   python3 scripts/backfill_speaker_labels.py --dry-run --limit 5
   ```

2. **Process small batch**:
   ```bash
   python3 scripts/backfill_speaker_labels.py --limit 10
   ```

3. **Check results**:
   - Open a few processed files
   - Verify speaker labels look correct
   - Check confidence percentages

4. **Process all remaining**:
   ```bash
   python3 scripts/backfill_speaker_labels.py
   ```

### Quick Start (If You're Confident)

```bash
# Just run it - will ask for confirmation
python3 scripts/backfill_speaker_labels.py
```

## What Happens Next

### Immediate
- Your 190 unlabeled files get processed
- Speaker names replace "Unknown" labels (where confident)
- Files marked as processed (won't be re-processed)

### Ongoing
- New lifelogs automatically get speaker labels
- No manual intervention needed
- System improves as you add more training examples

## Files Created/Modified

### Configuration Files (Read-only for script)
- `daily_insights/config/speaker_profiles.json` - Your 10 speakers
- `daily_insights/config/speaker_training_examples.json` - Your 410 training examples
- `daily_insights/config/processing_metadata.json` - Tracks processed files

### Lifelog Files (Modified by script)
- `lifelogs/*.md` - Speaker labels updated in place
- Backup not created - use git if you want to revert

## Git Recommendations

### Before Processing

```bash
# Commit current state
git add .
git commit -m "Before speaker label backfill"
```

### After Processing

```bash
# Review changes
git diff lifelogs/

# Commit if satisfied
git add lifelogs/
git commit -m "Added speaker labels to 190 lifelogs"
```

### If You Need to Revert

```bash
# Revert all changes
git checkout -- lifelogs/

# Or revert specific file
git checkout -- lifelogs/2025-09-29.md
```

## Next Steps

1. ✅ **Install dependency** - Already done! (`backoff` module)
2. ✅ **Script created** - `scripts/backfill_speaker_labels.py`
3. ⏳ **Run backfill** - Your choice when to process
4. ✅ **Forward system** - Already working for new lifelogs

## Questions?

- Check `SPEAKER_IDENTIFICATION_MVP.md` for system overview
- Check `TODO_SPEAKER_FEATURES.md` for future enhancements
- Script help: `python3 scripts/backfill_speaker_labels.py --help`
