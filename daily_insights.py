import os
import requests
from datetime import datetime
from pathlib import Path
import json
import re
from typing import Dict, List, Optional, Set
import backoff
from dateutil import parser
from collections import Counter

# === Configuration ===
CHATS_API_BASE = "https://api.limitless.ai/v1/chats"
LIFELOGS_API_BASE = "https://api.limitless.ai/v1/lifelogs"
API_KEY = "b37686e8-921a-4884-b0cd-7fa11523348f"  # replace with your actual key

INSIGHTS_DIR = "./daily"
LIFELOGS_DIR = "./lifelogs"
PROMPTS_DIR = "./prompts"
WEEKLY_INSIGHTS_DIR = "./weekly"
PSYCHOLOGIST_DIR = "./psychologist"

WEEKLY_INSIGHTS_PROMPT = os.path.join(PROMPTS_DIR, "weekly_prompt.txt")
PSYCHOLOGIST_PROMPT_FILE = os.path.join(PROMPTS_DIR, "psycho_analysis.txt")
OLLAMA_MODEL = "qwen2.5"  # change to your preferred local model
OLLAMA_API = "http://localhost:11434/api/generate"

os.makedirs(INSIGHTS_DIR, exist_ok=True)
os.makedirs(LIFELOGS_DIR, exist_ok=True)
os.makedirs(PROMPTS_DIR, exist_ok=True)
os.makedirs(WEEKLY_INSIGHTS_DIR, exist_ok=True)
os.makedirs(PSYCHOLOGIST_DIR, exist_ok=True)

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
                content = lifelog.get("markdown", "").strip().replace("- You", "- Bruce")
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
        weekly_filename = os.path.join(WEEKLY_INSIGHTS_DIR, f"{start_date}_to_{end_date}-weekly.md")

        if os.path.exists(weekly_filename):
            print(f"Skipping existing weekly summary: {weekly_filename}")
            continue  # already exists

        print(f"Building weekly summary for: {start_date} to {end_date}")

        # Read prompt
        if not os.path.exists(WEEKLY_INSIGHTS_PROMPT):
            print(f"Weekly prompt file missing: {WEEKLY_INSIGHTS_PROMPT}")
            return
        with open(WEEKLY_INSIGHTS_PROMPT, "r", encoding="utf-8") as f:
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

# === Step 4: Therapy Session Detection and Analysis ===

# Therapy detection configuration
THERAPY_KEYWORDS = [
    "therapy", "therapist", "session", "larry", "gerstenhaber",
    "bipolar", "depression", "anxiety", "manic", "medication",
    "depressed", "anxious", "feel", "feeling", "emotion",
    "struggle", "difficult", "challenging", "processing",
    "coping", "trigger"
]

NON_THERAPY_KEYWORDS = [
    "ips team", "i'm the peer", "peer on the", "case manager",
    "your mentor", "intake meeting", "intake appointment",
    "alexa stop", "alexa set", "alexa play", "hey siri",
    "hey google", "ok google", "what's the weather",
    "doctor appointment", "medical appointment", "dentist appointment",
    "verify your social", "social security number", "date of birth",
    "place of birth", "mother's maiden name", "under penalty of perjury",
    "eligibility interview", "disability interview", "benefits interview"
]

# Scoring weights
SCORE_DURATION_MATCH = 30
SCORE_AFTERNOON = 20
SCORE_KEYWORD = 5
SCORE_SPEAKER_NAMES = 25
SCORE_BACK_AND_FORTH = 15

# Penalties
PENALTY_TOO_MANY_SPEAKERS = -30
PENALTY_TOO_LONG = -40
PENALTY_TOO_SHORT = -20
PENALTY_TOO_MANY_MESSAGES = -20
PENALTY_JOURNAL = -50
PENALTY_NON_THERAPY = -100

# Thresholds
CONFIDENCE_THRESHOLD = 80  # Raised to 80 - requires Larry as speaker for detection
MAX_DURATION = 120
MIN_DURATION = 20
MAX_SPEAKERS = 3
MAX_MESSAGES = 1000
CONVERSATION_GAP_MINUTES = 5


def parse_lifelog_dialogue(filepath: Path) -> List[Dict]:
    """
    Parse dialogue lines from a lifelog markdown file.

    Returns list of dicts with: speaker, time, content, datetime_obj
    """
    dialogues = []
    pattern = re.compile(r"^- (.+?) \((\d+/\d+/\d+) (\d+:\d+ (?:AM|PM))\): (.+)")

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                speaker = match.group(1)
                date_str = match.group(2)
                time_str = match.group(3)
                content = match.group(4)

                # Parse datetime
                datetime_str = f"{date_str} {time_str}"
                try:
                    dt = datetime.strptime(datetime_str, "%m/%d/%y %I:%M %p")
                except ValueError:
                    continue

                dialogues.append({
                    "speaker": speaker,
                    "time_str": time_str,
                    "content": content,
                    "datetime": dt
                })

    return dialogues


def group_into_conversations(
    dialogues: List[Dict],
    max_gap_minutes: int = CONVERSATION_GAP_MINUTES
) -> List[List[Dict]]:
    """
    Group dialogue lines into conversations based on time gaps.
    """
    if not dialogues:
        return []

    conversations = []
    current_conversation = [dialogues[0]]

    for i in range(1, len(dialogues)):
        prev_time = dialogues[i - 1]["datetime"]
        curr_time = dialogues[i]["datetime"]
        gap_minutes = (curr_time - prev_time).total_seconds() / 60

        if gap_minutes <= max_gap_minutes:
            current_conversation.append(dialogues[i])
        else:
            conversations.append(current_conversation)
            current_conversation = [dialogues[i]]

    if current_conversation:
        conversations.append(current_conversation)

    return conversations


def calculate_duration_minutes(conversation: List[Dict]) -> float:
    """Calculate duration of conversation in minutes."""
    if len(conversation) < 2:
        return 0.0
    start = conversation[0]["datetime"]
    end = conversation[-1]["datetime"]
    return (end - start).total_seconds() / 60


def is_journal_session(conversation: List[Dict]) -> bool:
    """Check if conversation is a journal session (monologue)."""
    content_combined = " ".join(d["content"].lower() for d in conversation)
    if "journal" in content_combined:
        return True

    speakers = [d["speaker"] for d in conversation]
    if not speakers:
        return False

    speaker_counts = Counter(speakers)
    max_speaker_count = max(speaker_counts.values())

    if max_speaker_count / len(speakers) > 0.8:
        return True

    return False


def is_non_therapy_session(conversation: List[Dict]) -> bool:
    """Check if conversation contains non-therapy indicators."""
    content_combined = " ".join(d["content"].lower() for d in conversation)

    for keyword in NON_THERAPY_KEYWORDS:
        if keyword.lower() in content_combined:
            return True

    return False


def get_speaker_count(conversation: List[Dict]) -> int:
    """Get number of unique speakers in conversation."""
    speakers = set(d["speaker"] for d in conversation)
    return len(speakers)


def get_message_count(conversation: List[Dict]) -> int:
    """Get total number of messages in conversation."""
    return len(conversation)


def score_conversation(conversation: List[Dict]) -> tuple:
    """
    Score a conversation for likelihood of being a therapy session.

    Returns (score, breakdown_dict)
    """
    score = 0
    breakdown = {}

    # Duration scoring
    duration = calculate_duration_minutes(conversation)
    if 45 <= duration <= 75:
        score += SCORE_DURATION_MATCH
        breakdown["duration"] = SCORE_DURATION_MATCH
    else:
        breakdown["duration"] = 0

    # Afternoon timing (12 PM - 6 PM)
    start_hour = conversation[0]["datetime"].hour
    if 12 <= start_hour < 18:
        score += SCORE_AFTERNOON
        breakdown["afternoon"] = SCORE_AFTERNOON
    else:
        breakdown["afternoon"] = 0

    # Therapy keywords
    content_combined = " ".join(d["content"].lower() for d in conversation)
    keyword_count = sum(1 for kw in THERAPY_KEYWORDS if kw.lower() in content_combined)
    keyword_score = min(keyword_count * SCORE_KEYWORD, 50)
    score += keyword_score
    breakdown["keywords"] = keyword_score
    breakdown["keyword_count"] = keyword_count

    # Speaker names (Larry, Gerstenhaber) - REQUIRE Larry as speaker, not just mentioned
    has_larry_as_speaker = any(d["speaker"].lower() == "larry" for d in conversation)

    if has_larry_as_speaker:
        score += SCORE_SPEAKER_NAMES
        breakdown["speaker_names"] = SCORE_SPEAKER_NAMES
    else:
        breakdown["speaker_names"] = 0

    # Back-and-forth dialogue pattern
    speakers = [d["speaker"] for d in conversation]
    if len(speakers) >= 10:
        speaker_changes = sum(1 for i in range(1, len(speakers)) if speakers[i] != speakers[i-1])
        if speaker_changes >= 5:
            score += SCORE_BACK_AND_FORTH
            breakdown["back_and_forth"] = SCORE_BACK_AND_FORTH
        else:
            breakdown["back_and_forth"] = 0
    else:
        breakdown["back_and_forth"] = 0

    # Apply penalties
    speaker_count = get_speaker_count(conversation)
    if speaker_count > MAX_SPEAKERS:
        score += PENALTY_TOO_MANY_SPEAKERS
        breakdown["penalty_speakers"] = PENALTY_TOO_MANY_SPEAKERS
    else:
        breakdown["penalty_speakers"] = 0
    breakdown["speaker_count"] = speaker_count

    if duration > 90:
        score += PENALTY_TOO_LONG
        breakdown["penalty_too_long"] = PENALTY_TOO_LONG
    else:
        breakdown["penalty_too_long"] = 0

    if duration < 30:
        score += PENALTY_TOO_SHORT
        breakdown["penalty_too_short"] = PENALTY_TOO_SHORT
    else:
        breakdown["penalty_too_short"] = 0

    message_count = get_message_count(conversation)
    if message_count > MAX_MESSAGES:
        score += PENALTY_TOO_MANY_MESSAGES
        breakdown["penalty_messages"] = PENALTY_TOO_MANY_MESSAGES
    else:
        breakdown["penalty_messages"] = 0
    breakdown["message_count"] = message_count

    if is_journal_session(conversation):
        score += PENALTY_JOURNAL
        breakdown["penalty_journal"] = PENALTY_JOURNAL
        breakdown["is_journal"] = True
    else:
        breakdown["penalty_journal"] = 0
        breakdown["is_journal"] = False

    if is_non_therapy_session(conversation):
        score += PENALTY_NON_THERAPY
        breakdown["penalty_non_therapy"] = PENALTY_NON_THERAPY
        breakdown["is_non_therapy"] = True
    else:
        breakdown["penalty_non_therapy"] = 0
        breakdown["is_non_therapy"] = False

    breakdown["total"] = score
    breakdown["duration_minutes"] = duration

    return score, breakdown


def detect_therapy_sessions(filepath: Path, verbose: bool = False) -> List[Dict]:
    """
    Detect therapy sessions in a lifelog file.

    Returns list of detected sessions with metadata.
    """
    if verbose:
        print(f"\nAnalyzing: {filepath.name}")
        print("=" * 60)

    dialogues = parse_lifelog_dialogue(filepath)
    if verbose:
        print(f"Parsed {len(dialogues)} dialogue lines")

    conversations = group_into_conversations(dialogues)
    if verbose:
        print(f"Grouped into {len(conversations)} conversation segments")
        print()

    detected_sessions = []

    for i, conversation in enumerate(conversations, 1):
        start_time = conversation[0]["time_str"]
        end_time = conversation[-1]["time_str"]

        # Auto-exclude based on hard limits
        duration = calculate_duration_minutes(conversation)

        if duration > MAX_DURATION:
            if verbose:
                print(f"Conversation #{i}: EXCLUDED (duration {duration:.1f} min > {MAX_DURATION} min)")
            continue

        if duration < MIN_DURATION:
            if verbose:
                print(f"Conversation #{i}: EXCLUDED (duration {duration:.1f} min < {MIN_DURATION} min)")
            continue

        # Score the conversation
        score, breakdown = score_conversation(conversation)

        # Check if this is a therapy session
        if score >= CONFIDENCE_THRESHOLD:
            if verbose:
                print(f"Conversation #{i}: DETECTED AS THERAPY SESSION")
                print(f"  Time: {start_time} - {end_time}")
                print(f"  Duration: {duration:.1f} minutes")
                print(f"  Score: {score}")

            detected_sessions.append({
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration,
                "score": score,
                "breakdown": breakdown,
                "conversation": conversation
            })

    return detected_sessions


def extract_transcript(conversation: List[Dict]) -> str:
    """Extract formatted transcript from conversation."""
    lines = []
    for dialogue in conversation:
        speaker = dialogue["speaker"]
        time = dialogue["time_str"]
        content = dialogue["content"]
        lines.append(f"- {speaker} ({time}): {content}")
    return "\n".join(lines)


def load_processed_tracker() -> Dict:
    """
    Load the tracking file for processed lifelogs.

    Returns dict mapping date -> processing metadata.
    """
    tracker_file = os.path.join(PSYCHOLOGIST_DIR, "processed_lifelogs.json")
    if os.path.exists(tracker_file):
        with open(tracker_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_processed_tracker(tracker: Dict) -> None:
    """
    Save the tracking file for processed lifelogs.

    Args:
        tracker: Dict mapping date -> processing metadata
    """
    tracker_file = os.path.join(PSYCHOLOGIST_DIR, "processed_lifelogs.json")
    with open(tracker_file, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, sort_keys=True)


def process_therapy_sessions(force_recheck: bool = False):
    """
    Process all lifelog files to detect and analyze therapy sessions.

    Args:
        force_recheck: If True, reprocess all lifelogs even if already checked
    """
    print("\nStarting therapy session detection and analysis...")

    if force_recheck:
        print("Force recheck enabled - will reprocess all lifelogs")

    # Check if prompt file exists
    if not os.path.exists(PSYCHOLOGIST_PROMPT_FILE):
        print(f"Psychologist prompt file missing: {PSYCHOLOGIST_PROMPT_FILE}")
        return

    # Read prompt
    with open(PSYCHOLOGIST_PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    # Load tracking data
    tracker = load_processed_tracker()
    initial_tracker_size = len(tracker)

    # Get all lifelog files
    lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))

    sessions_found = 0
    sessions_analyzed = 0
    lifelogs_skipped = 0
    lifelogs_checked = 0

    for lifelog_file in lifelog_files:
        # Extract date from filename (YYYY-MM-DD.md)
        date_str = lifelog_file.stem

        # Skip if already processed (unless force_recheck is True)
        if not force_recheck and date_str in tracker:
            lifelogs_skipped += 1
            continue

        lifelogs_checked += 1

        # Detect therapy sessions
        sessions = detect_therapy_sessions(lifelog_file, verbose=False)

        # Mark as processed in tracker
        tracker[date_str] = {
            "checked_at": datetime.now().isoformat(),
            "sessions_found": len(sessions),
            "status": "analyzed" if sessions else "no_sessions"
        }

        if not sessions:
            # Save tracker after each check (in case of interruption)
            save_processed_tracker(tracker)
            continue

        sessions_found += len(sessions)

        print(f"\nFound {len(sessions)} therapy session(s) in {lifelog_file.name}")

        # Process each session
        for i, session in enumerate(sessions, 1):
            print(f"  Session {i}: {session['start_time']} - {session['end_time']} "
                  f"({session['duration_minutes']:.0f} min, score: {session['score']})")

            # Extract transcript
            transcript = extract_transcript(session["conversation"])

            # Build prompt with transcript
            full_prompt = f"{prompt_text}\n\n# THERAPY SESSION TRANSCRIPT\n\n{transcript}"

            # Send to Ollama
            print(f"  Sending to Ollama for analysis...")
            payload = {"model": OLLAMA_MODEL, "prompt": full_prompt}

            try:
                resp = requests.post(OLLAMA_API, json=payload, stream=True, timeout=300)
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

                # Save analysis
                # If multiple sessions on same day, append session number
                if len(sessions) > 1:
                    output_file = os.path.join(PSYCHOLOGIST_DIR,
                                             f"{date_str}-psychologist-session{i}.md")
                else:
                    output_file = os.path.join(PSYCHOLOGIST_DIR,
                                             f"{date_str}-psychologist.md")

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# Therapy Session Analysis - {date_str}\n\n")
                    f.write(f"**Session Time:** {session['start_time']} - {session['end_time']}\n")
                    f.write(f"**Duration:** {session['duration_minutes']:.0f} minutes\n")
                    f.write(f"**Detection Score:** {session['score']}\n\n")
                    f.write("---\n\n")
                    f.write(output_text)

                print(f"  Saved analysis: {output_file}")
                sessions_analyzed += 1

            except Exception as e:
                print(f"  Error analyzing session: {e}")
                continue

        # Save tracker after processing each lifelog
        save_processed_tracker(tracker)

    # Final save
    save_processed_tracker(tracker)

    print(f"\nTherapy session processing complete:")
    print(f"  Lifelogs checked: {lifelogs_checked}")
    print(f"  Lifelogs skipped (already processed): {lifelogs_skipped}")
    print(f"  Sessions found: {sessions_found}")
    print(f"  Sessions analyzed: {sessions_analyzed}")
    print(f"  Total tracked lifelogs: {len(tracker)} (was {initial_tracker_size})")

# === Main ===
if __name__ == "__main__":
    new_lifelogs = fetch_new_lifelogs()
    save_lifelogs(new_lifelogs)
    fetch_chats()
    build_weekly_summaries()
    process_therapy_sessions()