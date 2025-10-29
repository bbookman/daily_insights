"""Client for interacting with the OpenAI API."""

from typing import Optional

from daily_insights.config import OPENAI_API_KEY, OPENAI_MODEL


def generate_with_openai(
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None
) -> str:
    """
    Generate text using OpenAI API.

    Args
    ----
    system_prompt: System instructions for the model
    user_message: User message/content to process
    model: Model name to use (defaults to config value)

    Returns
    -------
    Generated text from OpenAI

    Raises
    ------
    ImportError: If openai library is not installed
    Exception: If API key is not configured
    Exception: If API request fails

    Example
    -------
    >>> system = "You are a helpful assistant."
    >>> user = "Hello!"
    >>> response = generate_with_openai(system, user)
    >>> print(response[:20])
    'Hello! How can I...'
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI library not installed. "
            "Install with: pip install openai"
        )

    if not OPENAI_API_KEY:
        raise Exception(
            "OPENAI_API_KEY not configured. "
            "Set environment variable OPENAI_API_KEY or add to .env file"
        )

    model_name = model or OPENAI_MODEL
    print(f"Sending to OpenAI ({model_name})...")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise
