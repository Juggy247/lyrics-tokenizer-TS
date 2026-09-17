"""
Phase 1 — Data collection (v2: filter-at-source + top-up capable).

Two upgrades over the original version:
  1. Filters at the METADATA level, before fetching any lyrics: excludes
     songs where Taylor Swift is only a featured artist (wrong
     primary_artist.id) and non-song content like poems/prologues/setlists
     (url doesn't end in "-lyrics"). These were previously caught only
     after the fact via separate audit scripts — now they're never fetched
     or saved in the first place.
  2. Top-up capable: checks which songs are already saved (by their unique
     genius_song_id, not by title) and only fetches the additional NEW
     songs needed to reach TARGET_TOTAL. Safe to re-run any time (e.g.
     after a new album releases) without creating duplicates.

Usage:
    python3 backend/data_collection/fetch_lyrics.py
"""

import json
import os
import time
from pathlib import Path

import lyricsgenius
from dotenv import load_dotenv

# ---- Config ----
ARTIST_NAME = "Taylor Swift"
TAYLOR_SWIFT_ARTIST_ID = 1177
TARGET_TOTAL = 300
NON_LYRIC_TITLE_MARKERS = [
    "voice memo",
    "work tape",
    "songwriting demo",
]
# ----------------

load_dotenv()

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def get_genius_client() -> lyricsgenius.Genius:
    token = os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "GENIUS_ACCESS_TOKEN not found. Make sure you have a .env file "
            "(copied from .env.example) with your real Genius access token."
        )
    genius = lyricsgenius.Genius(
        token,
        remove_section_headers=True,
        timeout=15,
        retries=3,
        sleep_time=1.0,
    )
    genius.verbose = True

    # Override the default LyricsGenius user-agent, which Cloudflare
    # recognizes and blocks on lyric-page requests.
    genius._session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })
    return genius


def load_existing_song_ids() -> set[int]:
    """Scans raw/ for songs already saved, keyed by their unique Genius
    song ID (not filename/title, which could theoretically collide)."""
    existing_ids = set()
    for path in RAW_DATA_DIR.glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        song_id = record.get("genius_song_id")
        if song_id is not None:
            existing_ids.add(song_id)
    return existing_ids


def get_new_songs(genius: lyricsgenius.Genius, artist_id: int,
                   num_new_needed: int, existing_ids: set[int]) -> list[dict]:
    """Paginates through artist_songs, filtering at the metadata level
    BEFORE fetching any lyrics:
      - must be a real song page (url ends in "-lyrics", not "-annotated")
      - Taylor Swift must be the PRIMARY artist (excludes featured-only
        collaborations and misattributed search results)
      - must not already be saved (by genius_song_id)
    """
    new_songs = []
    page = 1

    while len(new_songs) < num_new_needed:
        response = genius.artist_songs(artist_id, sort="popularity", per_page=20, page=page)
        page_songs = response.get("songs", [])
        if not page_songs:
            break

        for song in page_songs:
            title_lower = song.get("title", "").lower()
            
            if not song.get("url", "").rstrip("/").endswith("-lyrics"):
                continue
            if song.get("primary_artist", {}).get("id") != TAYLOR_SWIFT_ARTIST_ID:
                continue
            if song.get("id") in existing_ids:
                continue

            if any(marker in title_lower for marker in NON_LYRIC_TITLE_MARKERS):
                continue

            new_songs.append(song)
            if len(new_songs) >= num_new_needed:
                break

        next_page = response.get("next_page")
        if not next_page:
            break
        page = next_page
        time.sleep(0.5)

    return new_songs[:num_new_needed]


def fetch_and_save(artist_name: str, target_total: int) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    genius = get_genius_client()

    existing_ids = load_existing_song_ids()
    existing_count = len(existing_ids)
    print(f"Already have {existing_count} songs saved.")

    num_new_needed = target_total - existing_count
    if num_new_needed <= 0:
        print(f"Target of {target_total} already met or exceeded. Nothing to do.")
        return

    print(f"Need {num_new_needed} new songs to reach target of {target_total}.\n")

    new_songs_meta = get_new_songs(genius, TAYLOR_SWIFT_ARTIST_ID, num_new_needed, existing_ids)
    print(f"Found {len(new_songs_meta)} new qualifying songs. Fetching lyrics...\n")

    # Pre-populate with existing filenames so new songs never overwrite them
    used_filenames = {p.stem for p in RAW_DATA_DIR.glob("*.json")}

    saved_count = 0
    for song_meta in new_songs_meta:
        title = song_meta["title"]
        song_url = song_meta["url"]
        song_id = song_meta["id"]

        print(f"  Fetching lyrics: {title}")
        try:
            lyrics = genius.lyrics(song_url=song_url, remove_section_headers=True)
        except Exception as e:
            print(f"    Skipped '{title}' — could not fetch lyrics ({e})")
            continue

        if not lyrics:
            print(f"    Skipped '{title}' — no lyrics returned")
            continue

        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).strip().replace(" ", "_")

        filename = safe_title
        suffix = 2
        while filename in used_filenames:
            filename = f"{safe_title}_{suffix}"
            suffix += 1
        used_filenames.add(filename)

        out_path = RAW_DATA_DIR / f"{filename}.json"
        record = {
            "artist": artist_name,
            "title": title,
            "lyrics": lyrics,
            "genius_song_id": song_id,
            "genius_url": song_url,
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        saved_count += 1
        time.sleep(0.5)

    print(f"\nDone. Added {saved_count} new songs.")
    print(f"Total corpus size: {existing_count + saved_count} songs.")
    print("Reminder: run clean_lyrics.py next to process the new raw files.")


if __name__ == "__main__":
    fetch_and_save(ARTIST_NAME, TARGET_TOTAL)