import os
import requests
from datetime import datetime
from pathlib import Path
import json

# === Configuration ===
API_BASE = "https://api.limitless.ai/v1/chats"
API_KEY = "b37686e8-921a-4884-b0cd-7fa11523348f"  # replace with your actual key
insights_dir = "./daily_insights"
prompts_dir = "./prompts"
weekly_dir = "./weekly"
weekly_prompt_file = os.path.join(prompts_dir, "weekly_prompt.txt")
OLLAMA_MODEL = "qwen2.5"  # change to your preferred local model
OLLAMA_API = "http://localhost:11434/api/generate"

os.makedirs(insights_dir, exist_ok=True)
os.makedirs(prompts_dir, exist_ok=True)
os.makedirs(weekly_dir, exist_ok=True)

# === Step 1: Fetch Daily Insights ===
def fetch_chats():
    print("Starting to fetch daily insights...")
    cursor = None
    headers = {"x-api-key": API_KEY}
    page_count = 0
    while True:
        page_count += 1
        print(f"Fetching page {page_count}...")
        params = {}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(API_BASE, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for chat in data.get("data", {}).get("chats", []):
            if chat.get("summary") == "Daily insights":
                created_at = chat.get("createdAt")
                if not created_at:
                    continue
                date_str = created_at.split("T")[0]
                filename = os.path.join(insights_dir, f"{date_str}.md")

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

# === Step 2: Build Weekly Summaries ===
def build_weekly_summaries():
    print("\nStarting to build weekly summaries...")
    # Collect all daily files sorted by date
    daily_files = sorted(Path(insights_dir).glob("*.md"))
    daily_dates = [f.stem for f in daily_files if not f.stem.endswith("-weekly")]

    # Group into chunks of 7
    for i in range(0, len(daily_dates), 7):
        week = daily_dates[i:i+7]
        if len(week) < 7:
            print(f"Skipping incomplete week: {week[0]} to {week[-1]}")
            continue  # incomplete week, skip

        start_date = week[0]
        end_date = week[-1]
        weekly_filename = os.path.join(weekly_dir, f"{start_date}_to_{end_date}-weekly.md")

        if os.path.exists(weekly_filename):
            print(f"Skipping existing weekly summary: {weekly_filename}")
            continue  # already exists

        print(f"Building weekly summary for: {start_date} to {end_date}")

        # Read prompt
        if not os.path.exists(weekly_prompt_file):
            print(f"Weekly prompt file missing: {weekly_prompt_file}")
            return
        with open(weekly_prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()

        # Read daily summaries
        daily_contents = []
        for date in week:
            file_path = os.path.join(insights_dir, f"{date}.md")
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
    fetch_chats()
    build_weekly_summaries()
