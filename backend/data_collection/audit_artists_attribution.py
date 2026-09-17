"""
Data integrity audit — checks whether every song in the processed corpus
was actually scraped from Taylor Swift's own Genius page, by inspecting the
artist slug embedded in each song's genius_url field.

This check exists because "deja vu" was discovered to be Olivia Rodrigo's
song, mistakenly pulled in during Phase 1's Genius search (search_songs()
can return loosely-related results, not just exact artist matches). This
script checks whether any OTHER songs have the same problem.

Usage:
    python3 backend/data_collection/audit_artist_attribution.py
"""

import json
from pathlib import Path
from urllib.parse import urlparse

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
EXPECTED_PREFIX = "taylor-swift-"


def main():
    files = sorted(PROCESSED_DIR.glob("*.json"))
    flagged = []

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)

        url = record.get("genius_url", "")
        slug = urlparse(url).path.lstrip("/").lower()

        if not slug.startswith(EXPECTED_PREFIX):
            flagged.append({
                "filename": path.name,
                "title": record.get("title", ""),
                "genius_url": url,
            })

    print(f"Checked {len(files)} songs.\n")

    if flagged:
        print(f"{len(flagged)} song(s) flagged as possibly misattributed:\n")
        for f in flagged:
            print(f"  File:  {f['filename']}")
            print(f"  Title: {f['title']}")
            print(f"  URL:   {f['genius_url']}")
            print()
    else:
        print("No misattributed songs found — 'deja vu' appears to have been the only one.")


if __name__ == "__main__":
    main()