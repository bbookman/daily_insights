"""Unified LLM client that switches between providers."""

from typing import Optional

from daily_insights.config import LLM_PROVIDER


def generate_clinical_notes(
    system_prompt: str,
    transcript: str,
    provider: Optional[str] = None
) -> str:
    """
    Generate clinical notes using configured LLM provider.

    Args
    ----
    system_prompt: System instructions for the model
    transcript: Therapy session transcript to analyze
    provider: LLM provider to use ("ollama" or "openai")
             If None, uses LLM_PROVIDER from config

    Returns
    -------
    Generated clinical notes

    Raises
    ------
    ValueError: If provider is not supported
    Exception: If generation fails

    Example
    -------
    >>> system = "You are Dr. Larry writing clinical notes."
    >>> transcript = "Patient: I feel better today..."
    >>> notes = generate_clinical_notes(system, transcript)
    >>> print(notes[:50])
    '## Clinical Observations...'
    """
    provider_name = provider or LLM_PROVIDER

    if provider_name == "openai":
        from daily_insights.api.openai_client import generate_with_openai
        print("Using OpenAI provider")
        return generate_with_openai(system_prompt, transcript)

    elif provider_name == "ollama":
        from daily_insights.api.ollama_client import generate_with_chat
        print("Using Ollama provider")
        return generate_with_chat(system_prompt, transcript)

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Must be 'openai' or 'ollama'"
        )


def generate_summary(prompt: str, provider: Optional[str] = None) -> str:
    """
    Generate summary using configured LLM provider.

    This is a legacy function for backward compatibility.
    For therapy notes, use generate_clinical_notes instead.

    Args
    ----
    prompt: The prompt to send to the LLM
    provider: LLM provider to use ("ollama" or "openai")
             If None, uses LLM_PROVIDER from config

    Returns
    -------
    Generated text

    Raises
    ------
    ValueError: If provider is not supported
    Exception: If generation fails

    Example
    -------
    >>> prompt = "Summarize: Today was a good day."
    >>> summary = generate_summary(prompt)
    >>> print(summary[:50])
    'The day was positive and enjoyable...'
    """
    provider_name = provider or LLM_PROVIDER

    if provider_name == "openai":
        from daily_insights.api.openai_client import generate_with_openai
        # For simple prompts, use empty system message
        return generate_with_openai("You are a helpful assistant.", prompt)

    elif provider_name == "ollama":
        from daily_insights.api.ollama_client import (
            generate_summary as ollama_generate
        )
        return ollama_generate(prompt)

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Must be 'openai' or 'ollama'"
        )


# ============================================================================
# Async LLM Client Functions
# ============================================================================

async def generate_clinical_notes_async(
    system_prompt: str,
    transcript: str,
    provider: Optional[str] = None
) -> str:
    """
    Async version: Generate clinical notes using configured LLM provider.

    Args
    ----
    system_prompt: System instructions for the model
    transcript: Therapy session transcript to analyze
    provider: LLM provider to use ("ollama" or "openai")
             If None, uses LLM_PROVIDER from config

    Returns
    -------
    Generated clinical notes

    Raises
    ------
    ValueError: If provider is not supported
    Exception: If generation fails

    Example
    -------
    >>> system = "You are Dr. Larry writing clinical notes."
    >>> transcript = "Patient: I feel better today..."
    >>> notes = await generate_clinical_notes_async(system, transcript)
    >>> print(notes[:50])
    '## Clinical Observations...'
    """
    provider_name = provider or LLM_PROVIDER

    if provider_name == "openai":
        from daily_insights.api.openai_client import generate_with_openai_async
        print("Using OpenAI provider [async]")
        return await generate_with_openai_async(system_prompt, transcript)

    elif provider_name == "ollama":
        from daily_insights.api.ollama_client import generate_with_chat_async
        print("Using Ollama provider [async]")
        return await generate_with_chat_async(system_prompt, transcript)

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Must be 'openai' or 'ollama'"
        )


async def generate_summary_async(prompt: str, provider: Optional[str] = None) -> str:
    """
    Async version: Generate summary using configured LLM provider.

    This is for general summary generation tasks.
    For therapy notes, use generate_clinical_notes_async instead.

    Args
    ----
    prompt: The prompt to send to the LLM
    provider: LLM provider to use ("ollama" or "openai")
             If None, uses LLM_PROVIDER from config

    Returns
    -------
    Generated text

    Raises
    ------
    ValueError: If provider is not supported
    Exception: If generation fails

    Example
    -------
    >>> prompt = "Summarize: Today was a good day."
    >>> summary = await generate_summary_async(prompt)
    >>> print(summary[:50])
    'The day was positive and enjoyable...'
    """
    provider_name = provider or LLM_PROVIDER

    if provider_name == "openai":
        from daily_insights.api.openai_client import generate_with_openai_async
        # For simple prompts, use empty system message
        return await generate_with_openai_async("You are a helpful assistant.", prompt)

    elif provider_name == "ollama":
        from daily_insights.api.ollama_client import (
            generate_summary_async as ollama_generate_async
        )
        return await ollama_generate_async(prompt)

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Must be 'openai' or 'ollama'"
        )
