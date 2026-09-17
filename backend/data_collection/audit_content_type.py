"""
Content-type audit — checks whether every song in the processed corpus is
actually a SONG page on Genius (URL ending in "-lyrics"), as opposed to a
poem, prologue, or other non-song content (which use different URL
suffixes, e.g. "-annotated").

Discovered via "If You're Anything Like Me [Poem]", whose genius_url ends
in "-annotated" rather than "-lyrics" — a real poem she wrote, correctly
attributed to her, but not song lyrics, and not something search_songs()
filtered out after we dropped skip_non_songs=True during the Phase 1
rewrite.

Usage:
    python3 backend/data_collection/audit_content_type.py
"""

import json
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def main():
    files = sorted(PROCESSED_DIR.glob("*.json"))
    flagged = []

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)

        url = record.get("genius_url", "")
        if not url.rstrip("/").endswith("-lyrics"):
            flagged.append({
                "filename": path.name,
                "title": record.get("title", ""),
                "genius_url": url,
            })

    print(f"Checked {len(files)} songs.\n")

    if flagged:
        print(f"{len(flagged)} file(s) don't end in '-lyrics':\n")
        for f in flagged:
            print(f"  File:  {f['filename']}")
            print(f"  Title: {f['title']}")
            print(f"  URL:   {f['genius_url']}")
            print()
    else:
        print("All files are genuine song-lyrics pages.")


if __name__ == "__main__":
    main()