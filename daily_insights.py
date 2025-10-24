import os
import requests
from datetime import datetime
from pathlib import Path
import json
import re
from typing import Dict, List, Optional, Set
import backoff
from dateutil import parser

# === Configuration ===
CHATS_API_BASE = "https://api.limitless.ai/v1/chats"
LIFELOGS_API_BASE = "https://api.limitless.ai/v1/lifelogs"
API_KEY = "b37686e8-921a-4884-b0cd-7fa11523348f"  # replace with your actual key

INSIGHTS_DIR = "./daily_insights"
LIFELOGS_DIR = "./lifelogs"
PROMPTS_DIR = "./prompts"
WEEKLY_DIR = "./weekly"

WEEKLY_PROMPT_FILE = os.path.join(PROMPTS_DIR, "weekly_prompt.txt")
OLLAMA_MODEL = "qwen2.5"  # change to your preferred local model
OLLAMA_API = "http://localhost:11434/api/generate"

os.makedirs(INSIGHTS_DIR, exist_ok=True)
os.makedirs(LIFELOGS_DIR, exist_ok=True)
os.makedirs(PROMPTS_DIR, exist_ok=True)
os.makedirs(WEEKLY_DIR, exist_ok=True)

# === Step 1: Fetch Limitless Lifelogs ===
def get_existing_lifelog_dates() -> Set[str]:
    """
    Get set of dates from existing lifelog markdown files.
    """
    print("Scanning for existing lifelog dates...")
    dates = set()
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}).md")
    for file_path in Path(LIFELOGS_DIR).glob("*.md"):
        match = pattern.search(file_path.name)
        if match:
            dates.add(match.group(1))
    print(f"Found {len(dates)} existing lifelog files.")
    return dates

@backoff.on_exception(backoff.expo,
                      (requests.exceptions.RequestException, requests.exceptions.HTTPError),
                      max_tries=5,
                      giveup=lambda e: e.response.status_code not in [429, 500, 502, 503, 504])
def _make_lifelog_request(params: Dict) -> requests.Response:
    """Make a request to the Limitless API with backoff handling."""
    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }
    response = requests.get(LIFELOGS_API_BASE, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response

def fetch_new_lifelogs() -> List[Dict]:
    """
    Fetch all new lifelogs from the Limitless API with pagination, 
    stopping when an existing date is found.
    """
    print("\nStarting to fetch new lifelogs from Limitless...")
    existing_dates = get_existing_lifelog_dates()
    
    base_params = {
        "timezone": "America/New_York",
        "limit": 100,
        "includeMarkdown": "true"
    }

    all_lifelogs = []
    next_cursor = None
    page = 1
    max_pages = 50  # Safety break
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
            next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")

            if not lifelogs:
                print("No lifelogs received. Ending pagination.")
                break

            print(f"Page {page}: Retrieved {len(lifelogs)} lifelogs.")

            for lifelog in lifelogs:
                try:
                    start_time = parser.parse(lifelog["startTime"])
                    date_str = start_time.strftime("%Y-%m-%d")

                    if date_str in existing_dates:
                        print(f"Found lifelog for existing date {date_str}. Stopping pagination.")
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

def save_lifelogs(lifelogs: List[Dict]):
    """
    Groups lifelogs by date and saves them to markdown files.
    """
    if not lifelogs:
        print("No new lifelogs to save.")
        return

    print("\nSaving new lifelogs to markdown files...")
    # Group lifelogs by date
    lifelogs_by_date = {}
    for log in lifelogs:
        try:
            date_str = parser.parse(log["startTime"]).strftime("%Y-%m-%d")
            if date_str not in lifelogs_by_date:
                lifelogs_by_date[date_str] = []
            lifelogs_by_date[date_str].append(log)
        except (KeyError, ValueError):
            print(f"Could not process lifelog due to missing/invalid startTime: {log.get('id')}")

    # Process and save new lifelogs, date by date
    files_created_or_updated = set()
    for date_str, logs_for_day in lifelogs_by_date.items():
        # Sort logs by time before saving
        logs_for_day.sort(key=lambda x: x["startTime"])
        print(f"Processing {len(logs_for_day)} new lifelogs for {date_str}")
        
        filename = f"{date_str}.md"
        filepath = Path(LIFELOGS_DIR) / filename
        
        # Use append mode, and write header only if file is new
        is_new_file = not filepath.exists()
        with open(filepath, "a", encoding="utf-8") as f:
            if is_new_file:
                file_date = parser.parse(date_str)
                date_header = f"# {file_date.strftime('%A, %B %d, %Y')}\n"
                f.write(date_header)
            
            for lifelog in logs_for_day:
                start_time = parser.parse(lifelog["startTime"])
                time_str = start_time.strftime("%H:%M")
                content = lifelog.get("markdown", "").strip()
                if content:
                    entry_content = f"\n\n---\n\n### {time_str}\n\n{content}"
                    f.write(entry_content)

        files_created_or_updated.add(filepath.name)

    if files_created_or_updated:
        print(f"Lifelog export complete. {len(files_created_or_updated)} files created/updated in {LIFELOGS_DIR}")
    else:
        print("No new lifelogs were saved.")


# === Step 2: Fetch Daily Insights (from Chats) ===
def fetch_chats():
    print("\nStarting to fetch daily insights from chats...")
    cursor = None
    headers = {"x-api-key": API_KEY}
    page_count = 0
    while True:
        page_count += 1
        print(f"Fetching page {page_count}...")
        params = {}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(CHATS_API_BASE, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for chat in data.get("data", {}).get("chats", []):
            if chat.get("summary") == "Daily insights":
                created_at = chat.get("createdAt")
                if not created_at:
                    continue
                date_str = created_at.split("T")[0]
                filename = os.path.join(INSIGHTS_DIR, f"{date_str}.md")

                if os.path.exists(filename):
                    print(f"Skipping existing insight: {filename}")
                    continue

                print(f"Saving new insight: {filename}")
                messages = chat.get("messages", [])
                if len(messages) > 1 and "text" in messages[1]:
                    text_content = messages[1]["text"]
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(text_content)

        cursor = data.get("meta", {}).get("chats", {}).get("nextCursor")
        if not cursor:
            break
    print("Finished fetching daily insights.")

# === Step 3: Build Weekly Summaries ===
def build_weekly_summaries():
    print("\nStarting to build weekly summaries...")
    # Collect all daily files sorted by date
    daily_files = sorted(Path(INSIGHTS_DIR).glob("*.md"))
    daily_dates = [f.stem for f in daily_files if not f.stem.endswith("-weekly")]

    # Group into chunks of 7
    for i in range(0, len(daily_dates), 7):
        week = daily_dates[i:i+7]
        if len(week) < 7:
            print(f"Skipping incomplete week: {week[0]} to {week[-1]}")
            continue  # incomplete week, skip

        start_date = week[0]
        end_date = week[-1]
        weekly_filename = os.path.join(WEEKLY_DIR, f"{start_date}_to_{end_date}-weekly.md")

        if os.path.exists(weekly_filename):
            print(f"Skipping existing weekly summary: {weekly_filename}")
            continue  # already exists

        print(f"Building weekly summary for: {start_date} to {end_date}")

        # Read prompt
        if not os.path.exists(WEEKLY_PROMPT_FILE):
            print(f"Weekly prompt file missing: {WEEKLY_PROMPT_FILE}")
            return
        with open(WEEKLY_PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_text = f.read()

        # Read daily summaries
        daily_contents = []
        for date in week:
            file_path = os.path.join(INSIGHTS_DIR, f"{date}.md")
            with open(file_path, "r", encoding="utf-8") as f:
                daily_contents.append(f"# {date}\n\n{f.read()}")

        combined_input = f"{prompt_text}\n\n" + "\n\n".join(daily_contents)

        # Send to Ollama
        print("Sending to Ollama for summarization...")
        payload = {"model": OLLAMA_MODEL, "prompt": combined_input}
        resp = requests.post(OLLAMA_API, json=payload, stream=True)
        resp.raise_for_status()

        # Collect streamed response
        output_text = ""
        for line in resp.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    j = json.loads(data)
                    output_text += j.get("response", "")
                except Exception:
                    continue

        # Save weekly file
        with open(weekly_filename, "w", encoding="utf-8") as f:
            f.write(output_text)

        print(f"Saved weekly summary: {weekly_filename}")
    print("Finished building weekly summaries.")

# === Main ===
if __name__ == "__main__":
    new_lifelogs = fetch_new_lifelogs()
    save_lifelogs(new_lifelogs)
    fetch_chats()
    build_weekly_summaries()