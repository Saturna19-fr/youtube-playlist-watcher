#!/usr/bin/env python3

import os
import sys
import json
import time
import logging
from pathlib import Path

import requests
from yt_dlp import YoutubeDL

# --- Configuration -----------------------------------------------------

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLn9NglFd5iCqbOWQnHxQ-6iK2Ruj3fLtR"
TA_REFRESH_URL = "https://tubearchivist.eu.saturna19.fr/api/task/by-name/update_subscribed/"
TA_USERNAME = "saturna19"
CHECK_INTERVAL = 90  # seconds (1 min 30 s)
STATE_DIR = Path(os.environ.get("STATE_DIR", Path(__file__).parent))
STATE_FILE = STATE_DIR / "playlist_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("playlist_watcher")


def get_ta_password() -> str:
    token = os.environ.get("TA_TOKEN")
    if not token:
        log.error("Environment variable TA_TOKEN is not set.")
        sys.exit(1)
    return token


def fetch_playlist_video_ids(playlist_url: str) -> list:
    """Return the ordered list of video IDs currently in the playlist."""
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    entries = info.get("entries") or []
    return [entry["id"] for entry in entries if entry and entry.get("id")]


def load_previous_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read state file (%s), ignoring it.", exc)
    return None


def save_state(video_ids: list) -> None:
    try:
        STATE_FILE.write_text(json.dumps(video_ids))
    except OSError as exc:
        log.warning("Could not write state file: %s", exc)


def trigger_tubearchivist_refresh() -> None:
    try:
        resp = requests.post(
            TA_REFRESH_URL,
            headers={"Authorization": f"Token {os.environ.get("TA_TOKEN", None)}"},
            timeout=30,
        )
        resp.raise_for_status()
        log.info("TubeArchivist refresh triggered successfully (HTTP %s).", resp.status_code)
    except requests.RequestException as exc:
        log.error("Failed to trigger TubeArchivist refresh: %s", exc)


def main() -> None:
    get_ta_password()
    previous_ids = load_previous_state()

    log.info("Starting playlist watcher for %s", PLAYLIST_URL)
    log.info("Checking every %d seconds.", CHECK_INTERVAL)

    while True:
        log.debug("Starting scraping")
        try:
            current_ids = fetch_playlist_video_ids(PLAYLIST_URL)
        except Exception as exc:
            log.error("Failed to fetch playlist info: %s", exc)
            time.sleep(CHECK_INTERVAL)
            continue

        if previous_ids is None:
            log.info("No previous state found, saving initial state (%d videos).", len(current_ids))
            save_state(current_ids)
            previous_ids = current_ids
        elif current_ids != previous_ids:
            log.info(
                "Playlist changed: %d -> %d videos. Triggering TubeArchivist refresh.",
                len(previous_ids),
                len(current_ids),
            )
            trigger_tubearchivist_refresh()
            save_state(current_ids)
            previous_ids = current_ids
        else:
            log.info("No change detected (%d videos).", len(current_ids))

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
