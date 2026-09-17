"""
Phase 3b — Rigorous train/test split evaluation.

The full-corpus comparison in compare_tokenizers.py has a scientific flaw:
our tokenizer was evaluated on the exact same text it was trained on, while
the reference tokenizers were evaluated on text they had genuinely never
seen. That's not a fair comparison of generalization.

This script fixes that: it splits songs 80/20 by song (not by character, to
avoid splitting mid-song), trains a SEPARATE evaluation-only tokenizer on
just the 80% training split, then measures compression on the held-out 20%
— text this evaluation tokenizer has never seen — for our tokenizer AND
three generations of real tokenizers (GPT-2, GPT-3.5/4, GPT-4o). This lets
us see whether growing vocab size (50K -> 100K -> 200K) keeps paying off in
compression, or hits diminishing returns, alongside how our tiny
domain-specific tokenizer stacks up against all three.

NOTE: this does NOT touch backend/tokenizer/artifacts/ (the production
tokenizer used by the actual project, trained on all 300 songs). This script
trains a separate, throwaway tokenizer purely to produce an honest
evaluation number.

Usage:
    python3 backend/tokenizer/eval_generalization.py
"""
import tiktoken
import random
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpe import train_bpe, encode, decode

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
VOCAB_SIZE = 2000
RANDOM_SEED = 42
TRAIN_FRACTION = 0.8

REFERENCE_ENCODINGS = [
    ("gpt2", "GPT-2"),
    ("cl100k_base", "GPT-3.5 / GPT-4"),
    ("o200k_base", "GPT-4o"),
]


def load_all_lyrics() -> list[str]:
    files = sorted(PROCESSED_DIR.glob("*.json"))
    lyrics = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        lyrics.append(record.get("lyrics", ""))
    return lyrics


def split_train_test(all_lyrics: list[str]) -> tuple[str, str, int, int]:
    shuffled = all_lyrics.copy()
    random.Random(RANDOM_SEED).shuffle(shuffled)

    split_idx = int(len(shuffled) * TRAIN_FRACTION)
    train_songs = shuffled[:split_idx]
    test_songs = shuffled[split_idx:]

    train_text = "\n\n".join(train_songs)
    test_text = "\n\n".join(test_songs)

    return train_text, test_text, len(train_songs), len(test_songs)


def main() -> None:
    all_lyrics = load_all_lyrics()
    print(f"Loaded {len(all_lyrics)} songs total.")

    train_text, test_text, n_train, n_test = split_train_test(all_lyrics)
    print(f"Split: {n_train} training songs, {n_test} held-out test songs "
          f"(seed={RANDOM_SEED}, fixed for reproducibility)")
    print(f"Train corpus: {len(train_text):,} chars")
    print(f"Test corpus:  {len(test_text):,} chars (never seen during training)")

    print(f"\nTraining evaluation-only tokenizer on TRAIN split "
          f"(vocab size {VOCAB_SIZE})...")
    merges, vocab = train_bpe(train_text, VOCAB_SIZE)
    print(f"Learned {len(merges)} merges.")

    train_ids = encode(train_text, merges)
    train_compression = len(train_text) / len(train_ids)

    test_ids = encode(test_text, merges)
    test_compression = len(test_text) / len(test_ids)

    results = [
        ("Ours — TRAIN (in-sample)", VOCAB_SIZE, len(train_ids), train_compression,
         "reference only, not a fair test"),
        ("Ours — TEST (held-out)", VOCAB_SIZE, len(test_ids), test_compression,
         "fair — never seen during training"),
    ]

    print("\nEncoding held-out test set with reference tokenizers...")
    for encoding_name, display_name in REFERENCE_ENCODINGS:
        enc = tiktoken.get_encoding(encoding_name)
        ref_ids = enc.encode(test_text)
        ref_compression = len(test_text) / len(ref_ids)
        results.append((
            f"{display_name} — TEST (held-out)",
            enc.n_vocab,
            len(ref_ids),
            ref_compression,
            "fair — never seen at all",
        ))

    print("\n" + "=" * 90)
    print("RESULTS (held-out test set unless noted)")
    print("=" * 90)
    print(f"{'':32} {'vocab':>10} {'tokens':>10} {'compression':>13}   note")
    for name, vocab_size, n_tokens, compression, note in results:
        print(f"{name:32} {vocab_size:>10,} {n_tokens:>10,} {compression:>12.2f}x   {note}")

    print("\n" + "=" * 90)
    print("TREND: vocab size vs. compression, across tokenizer generations")
    print("=" * 90)
    for encoding_name, display_name in REFERENCE_ENCODINGS:
        enc = tiktoken.get_encoding(encoding_name)
        ref_ids = enc.encode(test_text)
        ref_compression = len(test_text) / len(ref_ids)
        print(f"  {display_name:20} vocab={enc.n_vocab:>7,}   compression={ref_compression:.2f}x")
    print(f"  {'Ours':20} vocab={VOCAB_SIZE:>7,}   compression={test_compression:.2f}x")

    print("\nThis is the fair, apples-to-apples generalization comparison —")
    print("unlike the full-corpus number in compare_tokenizers.py, which")
    print("tested our tokenizer on its own training data.")
    print("=" * 90)


if __name__ == "__main__":
    main()