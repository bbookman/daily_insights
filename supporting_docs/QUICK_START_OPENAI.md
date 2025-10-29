# Quick Start: Using OpenAI for Better Psychologist Analysis

## Why Use OpenAI?

The local Ollama models produce **summaries** instead of **clinical analysis**. OpenAI's GPT-4o-mini:
- ✅ Follows complex instructions correctly
- ✅ Produces actual clinical analysis
- ✅ Costs ~$0.002 per session (~2 cents for 8 sessions)
- ✅ Much faster than local models

## Setup (3 Steps)

### Step 1: Install OpenAI Library

```bash
pip install openai
```

### Step 2: Get API Key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-proj-...`)

### Step 3: Edit Configuration

Open `daily_insights/config.py` and change these lines:

```python
# LLM Provider Configuration
LLM_PROVIDER: str = "openai"  # Changed from "ollama"

# OpenAI Configuration
OPENAI_API_KEY: str = "sk-proj-paste-your-key-here"  # Add your actual key
OPENAI_MODEL: str = "gpt-4o-mini"  # This is already the default
```

## That's It!

Now run the system as normal:

```bash
python run_daily_insights.py
```

It will automatically use OpenAI instead of Ollama.

## Switch Back to Ollama

Just change one line in `config.py`:

```python
LLM_PROVIDER: str = "ollama"  # Changed from "openai"
```

## Cost Estimate

Based on your therapy sessions:
- **Per session**: ~$0.002 (less than a penny)
- **8 sessions**: ~$0.016 (about 2 cents)
- **100 sessions**: ~$0.20 (20 cents)

## Verify It's Working

Run the test script:

```bash
python test_provider_switch.py
```

You should see:
```
Current LLM Provider: openai
OpenAI API Key: sk-proj-...
✓ Successfully generated response using OPENAI
```

## Troubleshooting

### "OpenAI library not installed"
```bash
pip install openai
```

### "OPENAI_API_KEY not configured"
Make sure you pasted your actual API key in `config.py`:
```python
OPENAI_API_KEY: str = "sk-proj-your-actual-key-here"
```

### Still getting summaries?
Make sure `LLM_PROVIDER` is set to `"openai"` (not `"ollama"`).

## Need Help?

See the full guide: `LLM_PROVIDER_GUIDE.md`

