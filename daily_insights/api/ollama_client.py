"""Client for interacting with the Ollama API."""

import json
import requests
from typing import Optional
import aiohttp

from daily_insights.logging_config import get_logger
from daily_insights.config import OLLAMA_MODEL

logger = get_logger(__name__)


def generate_summary(prompt: str, model: Optional[str] = None) -> str:
    """
    Generate a summary using Ollama.

    Args
    ----
    prompt: The prompt to send to Ollama
    model: Model name to use (defaults to config value)

    Returns
    -------
    Generated text from Ollama

    Raises
    ------
    requests.exceptions.HTTPError: If request fails

    Example
    -------
    >>> prompt = "Summarize: Today was a good day."
    >>> summary = generate_summary(prompt)
    >>> print(summary[:50])
    'The day was positive and enjoyable...'
    """
    model_name = model or OLLAMA_MODEL
    logger.info("Sending to Ollama (%s) for generation", model_name)

    ollama_api = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt}

    try:
        resp = requests.post(
            ollama_api,
            json=payload,
            stream=True,
            timeout=300
        )
        resp.raise_for_status()

        output_text = ""
        for line in resp.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    j = json.loads(data)
                    output_text += j.get("response", "")
                except Exception:
                    continue

        return output_text

    except requests.exceptions.RequestException as e:
        logger.error("Error calling Ollama API", exc_info=True)
        raise


def generate_with_chat(
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None
) -> str:
    """
    Generate text using Ollama chat API with system message.

    Args
    ----
    system_prompt: System instructions for the model
    user_message: User message/content to process
    model: Model name to use (defaults to config value)

    Returns
    -------
    Generated text from Ollama

    Raises
    ------
    requests.exceptions.HTTPError: If request fails

    Example
    -------
    >>> system = "You are a helpful assistant."
    >>> user = "Hello!"
    >>> response = generate_with_chat(system, user)
    >>> print(response[:20])
    'Hello! How can I...'
    """
    model_name = model or OLLAMA_MODEL
    logger.info("Sending to Ollama (%s) via chat API", model_name)

    ollama_chat_api = "http://localhost:11434/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": True
    }

    try:
        resp = requests.post(
            ollama_chat_api,
            json=payload,
            stream=True,
            timeout=300
        )
        resp.raise_for_status()

        output_text = ""
        for line in resp.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    j = json.loads(data)
                    if "message" in j:
                        output_text += j["message"].get("content", "")
                except Exception:
                    continue

        return output_text

    except requests.exceptions.RequestException as e:
        logger.error("Error calling Ollama chat API", exc_info=True)
        raise


# ============================================================================
# Async Ollama Functions
# ============================================================================

async def generate_summary_async(prompt: str, model: Optional[str] = None) -> str:
    """
    Async version: Generate a summary using Ollama.

    Args
    ----
    prompt: The prompt to send to Ollama
    model: Model name to use (defaults to config value)

    Returns
    -------
    Generated text from Ollama

    Raises
    ------
    aiohttp.ClientError: If request fails

    Example
    -------
    >>> prompt = "Summarize: Today was a good day."
    >>> summary = await generate_summary_async(prompt)
    >>> print(summary[:50])
    'The day was positive and enjoyable...'
    """
    model_name = model or OLLAMA_MODEL
    logger.info("Sending to Ollama (%s) for generation [async]", model_name)

    ollama_api = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ollama_api,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                resp.raise_for_status()

                output_text = ""
                async for line in resp.content:
                    if line:
                        try:
                            data = line.decode("utf-8")
                            j = json.loads(data)
                            output_text += j.get("response", "")
                        except Exception:
                            continue

        return output_text

    except aiohttp.ClientError as e:
        logger.error("Error calling Ollama API", exc_info=True)
        raise


async def generate_with_chat_async(
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None
) -> str:
    """
    Async version: Generate text using Ollama chat API with system message.

    Args
    ----
    system_prompt: System instructions for the model
    user_message: User message/content to process
    model: Model name to use (defaults to config value)

    Returns
    -------
    Generated text from Ollama

    Raises
    ------
    aiohttp.ClientError: If request fails

    Example
    -------
    >>> system = "You are a helpful assistant."
    >>> user = "Hello!"
    >>> response = await generate_with_chat_async(system, user)
    >>> print(response[:20])
    'Hello! How can I...'
    """
    model_name = model or OLLAMA_MODEL
    logger.info("Sending to Ollama (%s) via chat API [async]", model_name)

    ollama_chat_api = "http://localhost:11434/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": True
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ollama_chat_api,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                resp.raise_for_status()

                output_text = ""
                async for line in resp.content:
                    if line:
                        try:
                            data = line.decode("utf-8")
                            j = json.loads(data)
                            if "message" in j:
                                output_text += j["message"].get("content", "")
                        except Exception:
                            continue

        return output_text

    except aiohttp.ClientError as e:
        logger.error("Error calling Ollama chat API", exc_info=True)
        raise
