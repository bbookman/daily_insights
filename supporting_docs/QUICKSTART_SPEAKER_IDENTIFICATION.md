# Speaker Identification - Quick Start Guide

Get your speaker identification system up and running in 3 easy steps!

---

## Prerequisites

- Daily Insights system installed and working
- LLM configured (OpenAI or Ollama)
- At least a few existing transcript files (lifelogs or bee)

---

## Step 1: Add Your Speakers (5-10 minutes)

### What You're Doing
Creating profiles for people who regularly appear in your transcripts so the system knows who to look for.

### How to Do It

**1. Open the speaker profiles file:**
```bash
# Location
daily_insights/config/speaker_profiles.json
```

**2. Edit the file to add your speakers:**

You currently have Bruce and Ivette. Add more people by copying this template:

```json
,
"PersonName": {
  "relationship": "friend/colleague/spouse/family",
  "speech_patterns": {
    "vocabulary_level": "basic/conversational/college/technical",
    "speaking_style": "how they speak (e.g., direct, analytical, casual)",
    "common_topics": ["topic1", "topic2", "topic3"],
    "distinctive_phrases": ["phrase they use often"]
  },
  "added_date": "2025-10-30"
}
```

**3. Example - Adding Russell:**

```json
{
  "version": "1.0",
  "speakers": {
    "Bruce": { ... },
    "Ivette": { ... },
    "Russell": {
      "relationship": "friend/colleague",
      "speech_patterns": {
        "vocabulary_level": "technical",
        "speaking_style": "analytical, precise, systematic",
        "common_topics": ["programming", "system design", "technology"],
        "distinctive_phrases": []
      },
      "added_date": "2025-10-30"
    }
  }
}
```

**4. Important formatting rules:**

✅ **DO:**
- Add comma after previous speaker's `}`
- Use double quotes `"` not single quotes `'`
- Leave `distinctive_phrases` as `[]` if you don't know any

❌ **DON'T:**
- Forget commas between speakers
- Add comma after the last speaker
- Use single quotes or missing quotes

**5. Validate your JSON (optional but recommended):**

```bash
python3 -c "import json; json.load(open('daily_insights/config/speaker_profiles.json'))"
```

No output = valid ✅
Error message = fix formatting ❌

### Quick Reference - vocabulary_level

| Level | When to Use | Example |
|-------|-------------|---------|
| `"basic"` | Simple, everyday words | Kids, casual conversations |
| `"conversational"` | Normal speaking style | Most people |
| `"college"` | Sophisticated vocabulary | Well-educated speakers |
| `"technical"` | Specialized/technical terms | Engineers, doctors, specialists |

### How Many Speakers Should You Add?

- **Minimum**: 2-3 (whoever appears most frequently)
- **Recommended**: 5-10 (regular conversation partners)
- **Maximum**: As many as you want (system handles it)

**Pro Tip:** Start with your most frequent speakers and add more later as needed.

---

## Step 2: Label Training Transcripts (30-60 minutes)

### What You're Doing
Teaching the system how to identify speakers by manually labeling examples. The system learns patterns from these examples.

### How to Do It

**1. Pick 10-20 transcripts to label:**

Choose diverse conversations:
- Different dates
- Different people
- Different conversation types (casual, work, phone calls, etc.)

**2. Run the labeling tool:**

```bash
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-01.md
```

**3. Follow the interactive prompts:**

The tool will:
- Show you speaker instances from the transcript
- Display sample utterances for each speaker label
- Suggest who the speaker might be
- Ask you to confirm or correct

**Example Session:**

```
=== Speaker Training Tool ===
File: lifelogs/2025-03-01.md
Known speakers: Bruce, Ivette, Russell

Found 45 speaker instances.

--- Speaker Label: Speaker 1 ---
Number of utterances: 23

Sample utterances:
  1. I almost never see you drink water, so you got to drink.
  2. Just something I need to clean up in the, search, I don't know.
  3. Oh, here you go, Peach.
  ... and 20 more

Who is 'Speaker 1'? (suggested: Bruce)
Enter name from [Bruce, Ivette, Russell], 'skip', or 'quit': Bruce
✓ Speaker 1 → Bruce

--- Speaker Label: Speaker 2 ---
Number of utterances: 22

Sample utterances:
  1. I didn't forget about her. Don't tell me what to do with my dog.
  2. It's not nice that you say that.
  ... and 20 more

Who is 'Speaker 2'? (suggested: Ivette)
Enter name from [Bruce, Ivette, Russell], 'skip', or 'quit': Ivette
✓ Speaker 2 → Ivette

=== Labeling Complete ===
Labeled 2 speaker types
Created 6 training examples

✓ Saved 6 total training examples to file.

Would you like to update lifelogs/2025-03-01.md with the labeled speakers? (y/n): y
✓ Updated lifelogs/2025-03-01.md with speaker labels
```

**4. Repeat for 10-20 transcripts:**

```bash
# Label more transcripts
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-05.md
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-10.md
python -m daily_insights.cli.speaker_commands label-training bee/2025-05-05_bee.md
# ... continue with more files
```

### Pro Tips for Labeling

**How to choose which transcripts to label:**
- ✅ Pick conversations with different people
- ✅ Choose clear conversations where context reveals who's speaking
- ✅ Include both lifelogs and bee transcripts
- ❌ Don't pick very short or unclear conversations

**During labeling:**
- Read the sample utterances carefully
- If you're not sure, type `skip` and move on
- The suggestion is just a hint - trust your judgment
- You can type `quit` anytime (it will offer to save progress)

**How many to label:**
- **Minimum**: 5 transcripts (enough to start)
- **Good**: 10-15 transcripts (recommended)
- **Best**: 20+ transcripts (highest accuracy)

### What Gets Saved?

The tool creates training examples in:
```
daily_insights/config/speaker_training_examples.json
```

You don't need to look at this file - it's managed automatically.

---

## Step 3: Test the System (5 minutes)

### What You're Doing
Running your normal lifelog fetch to see automatic speaker identification in action.

### How to Do It

**1. Fetch new lifelogs (your normal process):**

```bash
python -m daily_insights.main
# Or however you normally fetch lifelogs
```

**2. Watch for speaker identification messages:**

You'll see output like:
```
Processing 5 new lifelogs for 2025-10-30
Identifying speakers in 2025-10-30...
Found 2 speaker mappings for 2025-10-30
```

**3. Check the results:**

Open a newly created lifelog file:
```bash
cat lifelogs/2025-10-30.md
# or open in your editor
```

**Look for the confidence tiers:**

**High confidence (≥85%)** - Direct replacement:
```markdown
- Bruce: I need to take Peach outside.
- Ivette: Don't forget her water.
```

**Medium confidence (60-85%)** - Shows percentage:
```markdown
- Russell [72%]: Let me think about the system architecture.
- Bruce: That makes sense.
```

**Low confidence (<60%)** - Unchanged:
```markdown
- Speaker 1: Hello there.
- Unknown: Hi.
```

### What to Expect

**First few runs:**
- May have more medium/low confidence labels
- System is still learning patterns
- You may see some mistakes

**After more training:**
- More high-confidence labels
- Better accuracy
- Fewer "Unknown" labels

### Troubleshooting

**Problem: No speaker labels are changing**

Possible causes:
- Training examples file is empty (did you complete Step 2?)
- LLM not responding (check your API configuration)
- No speakers in profiles (check Step 1)

**Solution:**
```bash
# Check training examples exist
cat daily_insights/config/speaker_training_examples.json
# Should show your labeled examples

# Check speaker profiles exist
cat daily_insights/config/speaker_profiles.json
# Should show your speakers
```

**Problem: All labels are low confidence**

Possible causes:
- Not enough training examples (need 5-10 minimum)
- Training examples don't match current transcript patterns
- Speaker profiles need more detail

**Solution:**
- Label more diverse training transcripts
- Update speaker profiles with better descriptions
- Focus on your most frequent speakers

**Problem: Wrong speaker identifications**

This is normal! The system learns over time. You can:
- Label more training examples with correct identifications
- Update speaker profiles to be more specific
- Review medium-confidence labels and manually correct them

---

## Quick Reference - Complete Workflow

### One-Time Setup (First Time Only)

```bash
# 1. Add speakers to profiles
vim daily_insights/config/speaker_profiles.json
# Add your 5-10 regular speakers

# 2. Label 10-20 training transcripts
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-01.md
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-05.md
# ... repeat for 10-20 transcripts

# 3. Test with new lifelogs
python -m daily_insights.main
# Check results in newly created files
```

### Ongoing Use (Every Time)

```bash
# Just fetch lifelogs as normal
python -m daily_insights.main

# Speaker identification happens automatically!
# Check your lifelog files for labeled speakers
```

### Improving Over Time

```bash
# Add more speakers as needed
vim daily_insights/config/speaker_profiles.json

# Label more transcripts to improve accuracy
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-04-15.md

# System learns and improves automatically!
```

---

## File Locations Reference

| File | Purpose | When to Edit |
|------|---------|--------------|
| `daily_insights/config/speaker_profiles.json` | Speaker definitions | Add/edit speakers |
| `daily_insights/config/speaker_training_examples.json` | Training data | Auto-managed by tool |
| `daily_insights/config/processing_metadata.json` | Processing state | Auto-managed |

**You only edit:** `speaker_profiles.json` to add/update speakers

---

## Next Steps After Quick Start

Once you're comfortable with the basics:

1. **Refine speaker profiles** - Add more details as you observe patterns
2. **Label more transcripts** - More training = better accuracy
3. **Review medium-confidence labels** - Manually verify and correct
4. **Add new speakers** - As new people appear in conversations

### Future Features (Coming Soon)

- Interactive speaker profile creation tool
- Speaker search index (find all conversations with specific people)
- Automatic speaker candidate discovery
- Historical transcript processing (backfill old files)

Check `TODO_SPEAKER_FEATURES.md` for the roadmap!

---

## Getting Help

### Check Your Setup

```bash
# Verify speaker profiles exist
ls -la daily_insights/config/speaker_profiles.json

# View speaker profiles
cat daily_insights/config/speaker_profiles.json | python3 -m json.tool

# Check training examples count
cat daily_insights/config/speaker_training_examples.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{len(data.get('examples', []))} training examples\")"
```

### Common Issues

**JSON formatting errors:**
- Use https://jsonlint.com/ to validate
- Check for missing/extra commas
- Verify all quotes are double quotes `"`

**No speaker identifications happening:**
- Verify LLM is working (test regular insights)
- Check training examples exist
- Ensure speaker profiles are populated

**Low accuracy:**
- Label more diverse training transcripts
- Update speaker profiles with more specific details
- Focus on your most frequent speakers first

### Documentation

- **MVP Overview:** `SPEAKER_IDENTIFICATION_MVP.md`
- **Feature Roadmap:** `TODO_SPEAKER_FEATURES.md`
- **Code Documentation:** See docstrings in `speaker_service.py`

---

## Quick Start Checklist

- [ ] Added 5-10 speakers to `speaker_profiles.json`
- [ ] Validated JSON formatting
- [ ] Labeled 10-20 training transcripts
- [ ] Tested with new lifelog fetch
- [ ] Reviewed results in lifelog files
- [ ] Understand confidence tiers
- [ ] Know how to add more speakers
- [ ] Know how to label more training data

**You're ready to go!** 🚀

The system will improve over time as it learns from:
- Your training examples
- High-confidence predictions
- Patterns in your conversations

Happy speaker identification!
