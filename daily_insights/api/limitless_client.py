"""Client for interacting with the Limitless API."""

import json
import requests
from typing import Dict, List, Set
import backoff
from dateutil import parser
import aiohttp
import asyncio

from daily_insights.logging_config import get_logger
from daily_insights.config import (
    CHATS_API_BASE,
    LIFELOGS_API_BASE,
    API_KEY
)

logger = get_logger(__name__)


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
    logger.info("Starting to fetch new lifelogs from Limitless")

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
            logger.info("Fetching lifelogs page %d", page)
            response = _make_lifelog_request(params)
        except requests.exceptions.RequestException as e:
            logger.error("Request failed on page %d", page, exc_info=True)
            break

        try:
            data = response.json()
            lifelogs = data.get("data", {}).get("lifelogs", [])
            next_cursor = data.get("meta", {}).get(
                "lifelogs", {}
            ).get("nextCursor")

            if not lifelogs:
                logger.info("No lifelogs received, ending pagination")
                break

            logger.info("Page %d: Retrieved %d lifelogs", page, len(lifelogs))

            for lifelog in lifelogs:
                try:
                    start_time = parser.parse(lifelog["startTime"])
                    date_str = start_time.strftime("%Y-%m-%d")

                    if date_str in existing_dates:
                        logger.info(
                            "Found lifelog for existing date %s, stopping pagination",
                            date_str
                        )
                        stop_paging = True
                        break

                    lifelog_id = lifelog.get("id")
                    if lifelog_id not in seen_ids:
                        all_lifelogs.append(lifelog)
                        seen_ids.add(lifelog_id)

                except (KeyError, ValueError) as e:
                    logger.warning("Error processing lifelog for date check: %s", e)

            if stop_paging:
                break

            if next_cursor:
                page += 1
            else:
                logger.info("No more pages, ending pagination")
                break
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response on page %d", page, exc_info=True)
            break

    logger.info("Finished fetching %d total new lifelogs", len(all_lifelogs))
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
    logger.info("Starting to fetch daily insights from chats")
    cursor = None
    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }
    page_count = 0
    all_chats = []

    while True:
        page_count += 1
        logger.info("Fetching page %d", page_count)
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

    logger.info("Finished fetching %d chats", len(all_chats))
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
            logger.warning(
                "Request failed (attempt %d/%d), retrying in %ds",
                attempt + 1, max_retries, wait_time, exc_info=True
            )
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
    logger.info("Starting to fetch new lifelogs from Limitless (async)")

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
                logger.info("Fetching lifelogs page %d", page)
                data = await _make_lifelog_request_async(session, params)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error("Request failed on page %d", page, exc_info=True)
                break

            lifelogs = data.get("data", {}).get("lifelogs", [])
            next_cursor = data.get("meta", {}).get(
                "lifelogs", {}
            ).get("nextCursor")

            if not lifelogs:
                logger.info("No lifelogs received, ending pagination")
                break

            logger.info("Page %d: Retrieved %d lifelogs", page, len(lifelogs))

            for lifelog in lifelogs:
                try:
                    start_time = parser.parse(lifelog["startTime"])
                    date_str = start_time.strftime("%Y-%m-%d")

                    if date_str in existing_dates:
                        logger.info(
                            "Found lifelog for existing date %s, stopping pagination",
                            date_str
                        )
                        stop_paging = True
                        break

                    lifelog_id = lifelog.get("id")
                    if lifelog_id not in seen_ids:
                        all_lifelogs.append(lifelog)
                        seen_ids.add(lifelog_id)

                except (KeyError, ValueError) as e:
                    logger.warning("Error processing lifelog for date check: %s", e)

            if stop_paging:
                break

            if next_cursor:
                page += 1
            else:
                logger.info("No more pages, ending pagination")
                break

    logger.info("Finished fetching %d total new lifelogs", len(all_lifelogs))
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
    logger.info("Starting to fetch daily insights from chats (async)")
    cursor = None
    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }
    page_count = 0
    all_chats = []

    async with aiohttp.ClientSession() as session:
        while True:
            page_count += 1
            logger.info("Fetching page %d", page_count)
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

    logger.info("Finished fetching %d chats", len(all_chats))
    return all_chats
