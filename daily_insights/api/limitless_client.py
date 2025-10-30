"""Client for interacting with the Limitless API."""

import json
import requests
from typing import Dict, List, Set
import backoff
from dateutil import parser
import aiohttp
import asyncio

from daily_insights.config import (
    CHATS_API_BASE,
    LIFELOGS_API_BASE,
    API_KEY
)


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=5,
    giveup=lambda e: e.response.status_code not in [429, 500, 502, 503, 504]
)
def _make_lifelog_request(params: Dict) -> requests.Response:
    """
    Make a request to the Limitless API with backoff handling.

    Args
    ----
    params: Query parameters for the request

    Returns
    -------
    Response object from the API

    Raises
    ------
    requests.exceptions.HTTPError: If request fails after retries

    Example
    -------
    >>> params = {"timezone": "America/New_York", "limit": 100}
    >>> response = _make_lifelog_request(params)
    >>> data = response.json()
    """
    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }
    response = requests.get(
        LIFELOGS_API_BASE,
        headers=headers,
        params=params,
        timeout=60
    )
    response.raise_for_status()
    return response


def fetch_new_lifelogs(existing_dates: Set[str]) -> List[Dict]:
    """
    Fetch all new lifelogs from the Limitless API with pagination.

    Stops when an existing date is found.

    Args
    ----
    existing_dates: Set of dates that already have lifelog files

    Returns
    -------
    List of lifelog dictionaries

    Example
    -------
    >>> existing = {"2025-10-27", "2025-10-26"}
    >>> lifelogs = fetch_new_lifelogs(existing)
    >>> print(len(lifelogs))
    5
    """
    print("\nStarting to fetch new lifelogs from Limitless...")

    base_params = {
        "timezone": "America/New_York",
        "limit": 100,
        "includeMarkdown": "true"
    }

    all_lifelogs = []
    next_cursor = None
    page = 1
    max_pages = 50
    seen_ids = set()
    stop_paging = False

    while page <= max_pages and not stop_paging:
        params = dict(base_params)
        if next_cursor:
            params["cursor"] = next_cursor

        try:
            print(f"Fetching lifelogs page {page}...")
            response = _make_lifelog_request(params)
        except requests.exceptions.RequestException as e:
            print(f"Request failed on page {page}: {e}")
            break

        try:
            data = response.json()
            lifelogs = data.get("data", {}).get("lifelogs", [])
            next_cursor = data.get("meta", {}).get(
                "lifelogs", {}
            ).get("nextCursor")

            if not lifelogs:
                print("No lifelogs received. Ending pagination.")
                break

            print(f"Page {page}: Retrieved {len(lifelogs)} lifelogs.")

            for lifelog in lifelogs:
                try:
                    start_time = parser.parse(lifelog["startTime"])
                    date_str = start_time.strftime("%Y-%m-%d")

                    if date_str in existing_dates:
                        print(
                            f"Found lifelog for existing date {date_str}. "
                            "Stopping pagination."
                        )
                        stop_paging = True
                        break

                    lifelog_id = lifelog.get("id")
                    if lifelog_id not in seen_ids:
                        all_lifelogs.append(lifelog)
                        seen_ids.add(lifelog_id)

                except (KeyError, ValueError) as e:
                    print(f"Error processing lifelog for date check: {e}")

            if stop_paging:
                break

            if next_cursor:
                page += 1
            else:
                print("No more pages. Ending pagination.")
                break
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response on page {page}: {e}")
            break

    print(f"Finished fetching {len(all_lifelogs)} total new lifelogs.")
    return all_lifelogs


def fetch_chats() -> List[Dict]:
    """
    Fetch all chats from the Limitless API.

    Returns
    -------
    List of chat dictionaries

    Example
    -------
    >>> chats = fetch_chats()
    >>> print(len(chats))
    42
    """
    print("\nStarting to fetch daily insights from chats...")
    cursor = None
    headers = {"x-api-key": API_KEY}
    page_count = 0
    all_chats = []

    while True:
        page_count += 1
        print(f"Fetching page {page_count}...")
        params = {}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(CHATS_API_BASE, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        chats = data.get("data", {}).get("chats", [])
        all_chats.extend(chats)

        cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not cursor:
            break

    print(f"Finished fetching {len(all_chats)} chats.")
    return all_chats


# ============================================================================
# Async API Functions
# ============================================================================

async def _make_lifelog_request_async(
    session: aiohttp.ClientSession,
    params: Dict
) -> Dict:
    """
    Make an async request to the Limitless API with backoff handling.

    Args
    ----
    session: aiohttp ClientSession
    params: Query parameters for the request

    Returns
    -------
    JSON response data from the API

    Raises
    ------
    aiohttp.ClientError: If request fails after retries

    Example
    -------
    >>> async with aiohttp.ClientSession() as session:
    ...     params = {"timezone": "America/New_York", "limit": 100}
    ...     data = await _make_lifelog_request_async(session, params)
    """
    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }

    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with session.get(
                LIFELOGS_API_BASE,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff
            wait_time = 2 ** attempt
            print(f"Request failed (attempt {attempt + 1}/{max_retries}), "
                  f"retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)


async def fetch_new_lifelogs_async(existing_dates: Set[str]) -> List[Dict]:
    """
    Async version: Fetch all new lifelogs from the Limitless API with pagination.

    Stops when an existing date is found.

    Args
    ----
    existing_dates: Set of dates that already have lifelog files

    Returns
    -------
    List of lifelog dictionaries

    Example
    -------
    >>> existing = {"2025-10-27", "2025-10-26"}
    >>> lifelogs = await fetch_new_lifelogs_async(existing)
    >>> print(len(lifelogs))
    5
    """
    print("\nStarting to fetch new lifelogs from Limitless (async)...")

    base_params = {
        "timezone": "America/New_York",
        "limit": 100,
        "includeMarkdown": "true"
    }

    all_lifelogs = []
    next_cursor = None
    page = 1
    max_pages = 50
    seen_ids = set()
    stop_paging = False

    async with aiohttp.ClientSession() as session:
        while page <= max_pages and not stop_paging:
            params = dict(base_params)
            if next_cursor:
                params["cursor"] = next_cursor

            try:
                print(f"Fetching lifelogs page {page}...")
                data = await _make_lifelog_request_async(session, params)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Request failed on page {page}: {e}")
                break

            lifelogs = data.get("data", {}).get("lifelogs", [])
            next_cursor = data.get("meta", {}).get(
                "lifelogs", {}
            ).get("nextCursor")

            if not lifelogs:
                print("No lifelogs received. Ending pagination.")
                break

            print(f"Page {page}: Retrieved {len(lifelogs)} lifelogs.")

            for lifelog in lifelogs:
                try:
                    start_time = parser.parse(lifelog["startTime"])
                    date_str = start_time.strftime("%Y-%m-%d")

                    if date_str in existing_dates:
                        print(
                            f"Found lifelog for existing date {date_str}. "
                            "Stopping pagination."
                        )
                        stop_paging = True
                        break

                    lifelog_id = lifelog.get("id")
                    if lifelog_id not in seen_ids:
                        all_lifelogs.append(lifelog)
                        seen_ids.add(lifelog_id)

                except (KeyError, ValueError) as e:
                    print(f"Error processing lifelog for date check: {e}")

            if stop_paging:
                break

            if next_cursor:
                page += 1
            else:
                print("No more pages. Ending pagination.")
                break

    print(f"Finished fetching {len(all_lifelogs)} total new lifelogs.")
    return all_lifelogs


async def fetch_chats_async() -> List[Dict]:
    """
    Async version: Fetch all chats from the Limitless API.

    Returns
    -------
    List of chat dictionaries

    Example
    -------
    >>> chats = await fetch_chats_async()
    >>> print(len(chats))
    42
    """
    print("\nStarting to fetch daily insights from chats (async)...")
    cursor = None
    headers = {"x-api-key": API_KEY}
    page_count = 0
    all_chats = []

    async with aiohttp.ClientSession() as session:
        while True:
            page_count += 1
            print(f"Fetching page {page_count}...")
            params = {}
            if cursor:
                params["cursor"] = cursor

            async with session.get(
                CHATS_API_BASE,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            chats = data.get("data", {}).get("chats", [])
            all_chats.extend(chats)

            cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
            if not cursor:
                break

    print(f"Finished fetching {len(all_chats)} chats.")
    return all_chats
