"""
Phase 5 — Spotify metadata enrichment (final version).

Fetches album name, release date, and duration for all 300 songs via
Spotify's Client Credentials flow. NOTE: popularity and all audio-features
(tempo/energy/valence) are permanently unavailable in Development Mode as
of 2024-2026 API changes — see project notes.

Key protections built in from debugging along the way:
  - requests_timeout: prevents silent hangs if a request stalls
  - time.sleep() between requests: avoids tripping Spotify's rate limiter
  - artist ID validation: confirms the match is actually Taylor Swift, not
    a same-named cover artist or unrelated track
  - two-query fallback: a strict track+artist query first, then a looser
    text-only query if that fails (recovers remixes/alternate-version
    titles that don't match the strict filter exactly)

Usage:
    python3 backend/data_collection/fetch_spotify_metadata.py
"""

import json
import os
import time
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "spotify_metadata.json"

TAYLOR_SWIFT_ID = "06HL4z0CvFAxyc27GXpf02"
REQUEST_DELAY = 0.15  # seconds between requests, avoids rate limiting


def get_spotify_client() -> spotipy.Spotify:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not found in .env")

    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=10)


def find_real_taylor_swift_track(sp: spotipy.Spotify, title: str):
    """Tries a strict query first, falls back to a looser one. Validates
    the artist ID on every candidate — a returned result isn't
    automatically the right one."""
    queries = [
        f'track:{title} artist:Taylor Swift',
        f'{title} Taylor Swift',
    ]

    for query in queries:
        try:
            result = sp.search(q=query, type="track", limit=5)
        except Exception as e:
            print(f"    (request error on '{title}': {e})")
            continue

        items = result.get("tracks", {}).get("items", [])

        for item in items:
            found_taylor = False
            for artist in item.get("artists", []):
                if artist.get("id") == TAYLOR_SWIFT_ID:
                    found_taylor = True
                    break
            if found_taylor:
                return item

    return None


def main():
    sp = get_spotify_client()
    files = sorted(PROCESSED_DIR.glob("*.json"))

    metadata = {}
    matched = 0
    unmatched_titles = []

    print(f"Searching Spotify for {len(files)} songs...")
    for i, path in enumerate(files, 1):
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        title = record.get("title", "")

        matched_track = find_real_taylor_swift_track(sp, title)

        if matched_track:
            metadata[path.stem] = {
                "title": title,
                "spotify_track_id": matched_track["id"],
                "album": matched_track["album"]["name"],
                "release_date": matched_track["album"]["release_date"],
                "duration_ms": matched_track["duration_ms"],
            }
            matched += 1
        else:
            unmatched_titles.append(title)

        if i % 25 == 0:
            print(f"  ...{i}/{len(files)} processed ({matched} matched so far)")

        time.sleep(REQUEST_DELAY)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nMatched {matched}/{len(files)} songs -> {OUTPUT_PATH}")
    if unmatched_titles:
        print(f"\n{len(unmatched_titles)} songs had no confirmed Taylor Swift match:")
        for t in unmatched_titles:
            print(f"  - {t}")


if __name__ == "__main__":
    main()