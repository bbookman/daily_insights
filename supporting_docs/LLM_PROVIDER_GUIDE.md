# LLM Provider Configuration Guide

This system supports two LLM providers for generating psychologist analysis:

1. **Ollama** (Local) - Free, runs on your machine
2. **OpenAI** (Cloud) - Paid API, better quality

## Quick Start

### Option 1: Use Ollama (Local, Free) - DEFAULT

The system is already configured to use Ollama by default.

1. Make sure Ollama is running with a model installed:
   ```bash
   ollama list
   ollama pull llama3.1:8b  # if not already installed
   ```

2. Run the system:
   ```bash
   python run_daily_insights.py
   ```

### Option 2: Use OpenAI (Cloud, Paid)

1. Install OpenAI library:
   ```bash
   pip install openai
   ```

2. Get API key from https://platform.openai.com/api-keys

3. Edit `daily_insights/config.py`:
   ```python
   # LLM Provider Configuration
   LLM_PROVIDER: str = "openai"  # Changed from "ollama"

   # OpenAI Configuration
   OPENAI_API_KEY: str = "sk-proj-your-actual-key-here"
   OPENAI_MODEL: str = "gpt-4o-mini"
   ```

4. Run the system:
   ```bash
   python run_daily_insights.py
   ```

## Switching Between Providers

Simply edit `daily_insights/config.py` and change the `LLM_PROVIDER` value:

### Switch to OpenAI
```python
LLM_PROVIDER: str = "openai"
OPENAI_API_KEY: str = "sk-proj-your-key-here"
```

### Switch to Ollama
```python
LLM_PROVIDER: str = "ollama"
```

## Cost Comparison

### Ollama (Local)
- **Cost**: Free
- **Speed**: Depends on your hardware (M4 Mac: ~10-20 tokens/sec)
- **Quality**: Good for summaries, struggles with complex instructions
- **Privacy**: All data stays on your machine
- **Models**: llama3.1:8b, qwen2.5, mistral, etc.

### OpenAI (Cloud)
- **Cost**: ~$0.002 per therapy session (~$0.016 for 8 sessions)
- **Speed**: Very fast (~50-100 tokens/sec)
- **Quality**: Excellent, follows complex instructions well
- **Privacy**: Data sent to OpenAI (encrypted in transit)
- **Models**: gpt-4o-mini (recommended), gpt-4o, gpt-4-turbo

## Recommended Configuration

For **best quality** psychologist analysis, edit `daily_insights/config.py`:
```python
LLM_PROVIDER: str = "openai"
OPENAI_API_KEY: str = "sk-proj-your-key-here"
OPENAI_MODEL: str = "gpt-4o-mini"
```

For **privacy and no cost**, edit `daily_insights/config.py`:
```python
LLM_PROVIDER: str = "ollama"
```
(Note: Ollama models may produce summaries instead of clinical analysis)

## Available OpenAI Models

You can use any OpenAI chat model by setting `OPENAI_MODEL` in `config.py`:

- `gpt-4o-mini` - **Recommended** - Best balance of cost/quality (~$0.002/session)
- `gpt-4o` - Highest quality, more expensive (~$0.015/session)
- `gpt-4-turbo` - Good quality, moderate cost (~$0.030/session)
- `gpt-3.5-turbo` - Cheapest, lower quality (~$0.0005/session)

## Troubleshooting

### "OpenAI library not installed"
```bash
pip install openai
```

### "OPENAI_API_KEY not configured"
Make sure you've added your API key to `daily_insights/config.py`:
```python
OPENAI_API_KEY: str = "sk-proj-your-actual-key-here"
```

### "Unsupported LLM provider"
Check that `LLM_PROVIDER` in `config.py` is set to either `"ollama"` or `"openai"`.

### Ollama connection errors
Make sure Ollama is running:
```bash
ollama list
```

If not running, start it (it usually starts automatically on Mac).

## Testing Your Configuration

Test with a single session:
```bash
# This will process one therapy session and show the output
python test_chat_api.py
```

## Architecture

The system uses a unified LLM client (`daily_insights/api/llm_client.py`) that:
1. Checks the `LLM_PROVIDER` configuration
2. Routes requests to the appropriate provider (Ollama or OpenAI)
3. Handles provider-specific API formats
4. Returns the generated text

Both providers use the same prompt format (system message + user message) for consistency.

