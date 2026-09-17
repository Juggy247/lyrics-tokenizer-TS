"""
Phase 1c — Sanity check.

Scans all files in backend/data/processed/ for signs that boilerplate
cleaning missed something (leftover "Contributors"/"Translations" header
text, or a trailing digit+"Embed" footer). Prints a report instead of
silently trusting that clean_lyrics.py worked on every file.

Usage:
    python3 check_processed.py
"""

import json
import re
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "processed"


def check_all() -> None:
    files = sorted(PROCESSED_DIR.glob("*.json"))
    if not files:
        print(f"No processed files found in {PROCESSED_DIR}.")
        return

    flagged = []

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        lyrics = record.get("lyrics", "")

        issues = []
        if "Contributors" in lyrics or "Translations" in lyrics:
            issues.append("leftover header boilerplate")
        if re.search(r"\d+Embed\s*$", lyrics):
            issues.append("leftover Embed footer")
        if "Read More" in lyrics:
            issues.append("leftover 'Read More' blurb")
        if "You might also like" in lyrics:
            issues.append("leftover 'You might also like'")
        if len(lyrics) < 100:
            issues.append(f"suspiciously short ({len(lyrics)} chars)")

        if issues:
            flagged.append((path.name, issues))

    print(f"Checked {len(files)} files.\n")
    if flagged:
        print(f"{len(flagged)} file(s) need attention:\n")
        for name, issues in flagged:
            print(f"  {name}")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("All files look clean. No leftover boilerplate detected.")


if __name__ == "__main__":
    check_all()