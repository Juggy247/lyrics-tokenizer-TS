"""
Phase 2a — Corpus aggregation.

Reads all cleaned song JSON from backend/data/processed/ and concatenates
their lyrics into a single plain-text training corpus for the tokenizer.
Songs are separated by a blank line so the tokenizer doesn't learn spurious
merges across song boundaries.

Usage:
    python3 backend/tokenizer/build_corpus.py
"""

import json
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "corpus.txt"

def build_corpus() -> None:

    files = sorted(PROCESSED_DIR.glob("*.json"))
    if not files:
        print(f"No processed files found in {PROCESSED_DIR}.")
        return
    
    song_texts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        song_texts.append(record.get("lyrics",""))

    corpus = "\n\n".join(song_texts)

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        f.write(corpus)

    print(f"Built corpus from {len(files)} songs → {CORPUS_PATH}")
    print(f"Total corpus size: {len(corpus):,} characters")


if __name__ == "__main__":
    build_corpus()