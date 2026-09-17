"""
Phase 2d — Round-trip test.

Confirms the tokenizer is correct: encoding text into token IDs and then
decoding those IDs back must produce the exact original text. If this ever
fails, something is wrong with encode() or decode() in bpe.py — this should
be run any time either function changes.

Usage:
    python3 backend/tokenizer/test_roundtrip.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpe import encode, decode

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"

TEST_STRINGS = [
    # Basic
    "I remember it all too well",
    "You're the reason I can't sleep at night",
    "Hello, world! 123",

    # Empty / whitespace
    "",
    " ",
    "  ",
    "\n",
    "\t",
    "hello  world",
    " hello ",
    "hello\nworld",
    "hello\tworld",

    # Punctuation
    "Hello... world!!!",
    "What's this?",
    "(hello)",
    "[hello]",
    "{hello}",
    "hello: world",
    "hello; world",
    "hello - world",
    "hello—world",
    "hello_world",
    "hello/world",

    # Numbers / symbols
    "123456789",
    "3.1415926535",
    "-123",
    "2026-09-06",
    "99.99%",
    "$100 € £ ¥",
    "email@example.com",

    # Apostrophes
    "You're",
    "I'm",
    "don't",
    "can't",
    "it's",
    "Taylor's",
    "Taylor’s",
    "rock'n'roll",

    # Unicode
    "café",
    "naïve",
    "日本語",
    "中文",
    "한국어",
    "Привет",
    "مرحبا",

    # Emoji
    "Emoji test: 🎸🎤",
    "🚀🔥💻",
    "❤️",
    "こんにちは 👋",

    # Repetition
    "aaaaaaaaaaaaaaaa",
    "a" * 100,
    "ab" * 50,
    "abc" * 50,
    "the the the the the",

    # Mixed
    "Hello, world! 123 🎸",
    "Taylor's song — 1989 🎵",
    "Python 3.14 🐍",
    "Hello\n世界\n🌍",
    "abc123!@#$%^&*()",

    # Long
    "Hello world! " * 100,
]


def load_artifacts():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        merges_raw = json.load(f)
    merges = [tuple(pair) for pair in merges_raw]

    with open(ARTIFACTS_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab_raw = json.load(f)
    vocab = {int(k): bytes(v) for k, v in vocab_raw.items()}

    return merges, vocab


def main() -> None:
    merges, vocab = load_artifacts()

    passed_count = 0
    failed = []

    for text in TEST_STRINGS:
        token_ids = encode(text, merges)
        decoded = decode(token_ids, vocab)

        if decoded == text:
            passed_count += 1
            compression = len(text) / len(token_ids) if token_ids else 0
            print(f"[PASS] {text[:40]!r:45} tokens={len(token_ids):<5} compression={compression:.2f}x")
        else:
            failed.append((text, token_ids, decoded))
            print(f"[FAIL] {text[:40]!r}")

    print(f"\n{passed_count}/{len(TEST_STRINGS)} passed")

    if failed:
        print("\n--- FAILURE DETAILS ---")
        for text, token_ids, decoded in failed:
            print(f"\n  input:   {text!r}")
            print(f"  tokens:  {token_ids}")
            print(f"  decoded: {decoded!r}")
    else:
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()