"""
Phase 5b — Era/album comparison.

Groups songs by their studio album ("era"), normalizing away re-release
suffixes like "(Taylor's Version)" or "(Deluxe)" so both versions of the
same era's songs are counted together rather than as separate eras (their
lyrics are near-identical, so treating them separately would be trivial,
not informative).

For each era, computes SwiftBPE compression ratio using the PRODUCTION
tokenizer (trained on all 285 songs) — answers: does her vocabulary/style,
as measured by tokenizer efficiency, shift meaningfully across eras?

Usage:
    python3 backend/analysis/era_comparison.py
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tokenizer"))
from bpe import encode

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
SPOTIFY_METADATA_PATH = Path(__file__).resolve().parent.parent / "data" / "spotify_metadata.json"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "tokenizer" / "artifacts"


def normalize_era(album_name: str) -> str:
    """Strip anything from the first '(' or '[' onward, so re-release
    editions collapse into their base era name."""
    cut = re.split(r"[\(\[]", album_name)[0].strip()
    return cut if cut else album_name


def load_merges():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        return [tuple(pair) for pair in json.load(f)]


def main():
    with open(SPOTIFY_METADATA_PATH, "r", encoding="utf-8") as f:
        spotify_data = json.load(f)

    merges = load_merges()

    # Group songs by normalized era
    eras = defaultdict(lambda: {"songs": [], "release_dates": [], "total_chars": 0, "total_tokens": 0})

    matched_count = 0
    for path in sorted(PROCESSED_DIR.glob("*.json")):
        stem = path.stem
        if stem not in spotify_data:
            continue  # no Spotify match, skip (can't assign an era)

        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        lyrics = record.get("lyrics", "")

        album = spotify_data[stem]["album"]
        release_date = spotify_data[stem]["release_date"]
        era = normalize_era(album)

        token_ids = encode(lyrics, merges)

        eras[era]["songs"].append(record.get("title", ""))
        eras[era]["release_dates"].append(release_date)
        eras[era]["total_chars"] += len(lyrics)
        eras[era]["total_tokens"] += len(token_ids)
        matched_count += 1

    # Sort eras chronologically by their EARLIEST release date
    # (the original release, not any later re-recording)
    def earliest_date(era_data):
        return min(era_data["release_dates"])

    sorted_eras = sorted(eras.items(), key=lambda kv: earliest_date(kv[1]))

    print(f"Analyzed {matched_count} songs across {len(eras)} eras.\n")
    print("=" * 90)
    print(f"{'Era':30} {'Earliest':>10} {'Songs':>7} {'Total chars':>12} {'Compression':>13}")
    print("-" * 90)

    for era_name, data in sorted_eras:
        earliest = min(data["release_dates"])
        n_songs = len(data["songs"])
        compression = data["total_chars"] / data["total_tokens"] if data["total_tokens"] else 0

        print(f"{era_name:30} {earliest:>10} {n_songs:>7} {data['total_chars']:>12,} {compression:>12.2f}x")

    print("=" * 90)

    # Highlight the extremes
    compressions = [
        (era_name, data["total_chars"] / data["total_tokens"])
        for era_name, data in sorted_eras
        if data["total_tokens"] > 0 and len(data["songs"]) >= 3  # skip tiny eras, noisy
    ]
    if compressions:
        best = max(compressions, key=lambda x: x[1])
        worst = min(compressions, key=lambda x: x[1])
        print(f"\nMost tokenizer-efficient era (3+ songs): {best[0]} ({best[1]:.2f}x)")
        print(f"Least tokenizer-efficient era (3+ songs): {worst[0]} ({worst[1]:.2f}x)")

        # Export for the API to serve
    MIN_SONGS_MAJOR_ALBUM = 5
    major = [(name, data) for name, data in sorted_eras if len(data["songs"]) >= MIN_SONGS_MAJOR_ALBUM]

    export_data = {
        "major_albums": [
            {
                "era": era_name,
                "earliest_release": min(data["release_dates"]),
                "song_count": len(data["songs"]),
                "total_chars": data["total_chars"],
                "compression_ratio": round(data["total_chars"] / data["total_tokens"], 3) if data["total_tokens"] else 0,
            }
            for era_name, data in major
        ],
    }

    export_path = Path(__file__).resolve().parent / "era_stats.json"
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)
    print(f"\nExported -> {export_path}")

if __name__ == "__main__":
    main()