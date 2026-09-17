"""
Removes the 15 songs identified by audit_artist_attribution.py as either
misattributed (not actually Taylor Swift's song) or featured collaborations
(she performs, but primary billing/songwriting belongs to another artist).
Decision: stricter solo-only corpus.

Deletes from both raw/ and processed/, and cleans up any now-stale entries
in spotify_metadata.json.

Usage:
    python3 backend/data_collection/remove_flagged_songs.py
"""

import json
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
SPOTIFY_METADATA_PATH = Path(__file__).resolve().parent.parent / "data" / "spotify_metadata.json"

FLAGGED_FILENAMES = [
    "1_step_forward_3_steps_back.json",
    "Babe.json",
    "Better_Man.json",
    "Birch.json",
    "Both_of_Us.json",
    "Half_of_My_Heart.json",
    "Highway_Dont_Care.json",
    "I_Dont_Wanna_Live_Forever.json",
    "Renegade.json",
    "Riff_Off.json",
    "The_Alcott.json",
    "This_Is_What_You_Came_For.json",
    "Youll_Always_Find_Your_Way_Back_Home.json",
    "deja_vu.json",
    "us.json",
]


def main():
    removed_count = 0

    for filename in FLAGGED_FILENAMES:
        raw_path = RAW_DIR / filename
        processed_path = PROCESSED_DIR / filename

        if raw_path.exists():
            raw_path.unlink()
            print(f"Removed: raw/{filename}")
        if processed_path.exists():
            processed_path.unlink()
            print(f"Removed: processed/{filename}")
            removed_count += 1

    print(f"\nRemoved {removed_count} songs.")

    # Clean stale entries out of spotify_metadata.json, if it exists
    if SPOTIFY_METADATA_PATH.exists():
        with open(SPOTIFY_METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        stems_to_remove = [Path(f).stem for f in FLAGGED_FILENAMES]
        before = len(metadata)
        metadata = {k: v for k, v in metadata.items() if k not in stems_to_remove}
        after = len(metadata)

        with open(SPOTIFY_METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"Cleaned spotify_metadata.json: {before} -> {after} entries")

    remaining = len(list(PROCESSED_DIR.glob("*.json")))
    print(f"\nRemaining corpus size: {remaining} songs")


if __name__ == "__main__":
    main()