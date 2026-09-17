"""
Precompute per-token corpus statistics: how often each learned SwiftBPE
token appears in total (term frequency) and how many distinct songs it
appears in (document frequency). Powers swiftian_score.py's "Token
Familiarity" metric and "Most Swift-coded token" feature.

Run this once (and again any time the production tokenizer is retrained).

Usage:
    python3 backend/tokenizer/compute_token_stats.py
"""

import json
from collections import Counter
from pathlib import Path

from bpe import encode

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def load_merges():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        return [tuple(pair) for pair in json.load(f)]


def main():
    merges = load_merges()
    files = sorted(PROCESSED_DIR.glob("*.json"))

    if not files:
        print(f"No processed songs found in {PROCESSED_DIR}.")
        return

    term_freq = Counter()
    doc_freq = Counter()

    print(f"Encoding {len(files)} songs to build token statistics...")
    for i, path in enumerate(files, 1):
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        lyrics = record.get("lyrics", "")

        token_ids = encode(lyrics, merges)
        term_freq.update(token_ids)
        doc_freq.update(set(token_ids))

        if i % 50 == 0:
            print(f"  ...{i}/{len(files)} songs processed")

    stats = {
        str(token_id): {
            "term_frequency": term_freq[token_id],
            "document_frequency": doc_freq[token_id],
        }
        for token_id in term_freq
    }

    out = {
        "total_songs": len(files),
        "stats": stats,
    }

    out_path = ARTIFACTS_DIR / "token_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f)

    print(f"\nSaved token stats for {len(stats)} unique tokens -> {out_path}")
    print(f"(computed across {len(files)} songs)")


if __name__ == "__main__":
    main()