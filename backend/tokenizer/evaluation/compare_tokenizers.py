"""
Phase 3 — Comparison against a pretrained tokenizer (GPT-2, via tiktoken).

Runs categorized test strings through:
  1. Our from-scratch BPE tokenizer (trained only on Taylor Swift lyrics,
     vocab size 2000)
  2. GPT-2's real tokenizer (trained on a large, diverse web corpus,
     vocab size ~50,257)

Test strings are grouped into categories on purpose, to reveal a pattern
rather than a handful of one-off numbers:
  - Swift-specific hooks: expect OURS to win (learned these exact patterns)
  - Generic English: expect it to be closer
  - Out-of-domain (code, other languages, science): expect GPT-2 to win
  - Mixed/realistic: what a real /tokenize endpoint would actually see

   

Usage:
    python3 backend/tokenizer/compare_tokenizers.py
"""


import tiktoken

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpe import encode as our_encode

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
CORPUS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "corpus.txt"

TEST_STRINGS = {
    "Swift-specific hooks": [
        "I remember it all too well",
        "We are never ever getting back together",
        "Are we out of the woods yet",
        "It's me, hi, I'm the problem, it's me",
        "Long live all the mountains we moved",
        "Cause baby now we've got bad blood",
    ],
    "Generic English": [
        "You're the reason I can't sleep at night",
        "Hello, world! 123",
        "the the the the the",
        "I went to the store to buy some milk",
        "This is a completely ordinary sentence",
    ],
    "Out-of-domain": [
        "café naïve",
        "日本語のテスト",
        "def train_model(data, epochs=10):",
        "SELECT * FROM users WHERE id = 1;",
        "The mitochondria is the powerhouse of the cell",
        "$1,234.56 was the final invoice total",
    ],
    "Mixed/realistic": [
        "Taylor's song — 1989 was released in October",
        "omg this is literally my favorite song!!",
        "check out https://example.com for more info",
    ],
}


def load_our_tokenizer():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        merges_raw = json.load(f)
    merges = [tuple(pair) for pair in merges_raw]

    with open(ARTIFACTS_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab_raw = json.load(f)
    vocab_size = len(vocab_raw)

    return merges, vocab_size


def compare_on_strings(our_merges, gpt2_enc) -> None:
    print("=" * 78)
    print("PER-STRING COMPARISON (grouped by category)")
    print("=" * 78)

    category_wins = {}

    for category, strings in TEST_STRINGS.items():
        print(f"\n--- {category} ---")
        header = f"{'text':45} {'ours':>8} {'gpt2':>8} {'ours x':>8} {'gpt2 x':>8}"
        print(header)
        print("-" * 78)

        ours_wins = 0
        gpt2_wins = 0

        for text in strings:
            our_ids = our_encode(text, our_merges)
            gpt2_ids = gpt2_enc.encode(text)

            our_compression = len(text) / len(our_ids) if our_ids else 0
            gpt2_compression = len(text) / len(gpt2_ids) if gpt2_ids else 0

            if our_compression > gpt2_compression:
                ours_wins += 1
            elif gpt2_compression > our_compression:
                gpt2_wins += 1

            display_text = text if len(text) <= 43 else text[:40] + "..."
            print(
                f"{display_text!r:45} {len(our_ids):>8} {len(gpt2_ids):>8} "
                f"{our_compression:>7.2f}x {gpt2_compression:>7.2f}x"
            )

        category_wins[category] = (ours_wins, gpt2_wins)

    print("\n" + "=" * 78)
    print("CATEGORY SUMMARY (higher compression wins per string)")
    print("=" * 78)
    for category, (ours_wins, gpt2_wins) in category_wins.items():
        print(f"  {category:25} ours won {ours_wins}  |  gpt2 won {gpt2_wins}")


def compare_on_full_corpus(our_merges, gpt2_enc, our_vocab_size) -> None:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus_text = f.read()

    print()
    print("=" * 78)
    print("FULL CORPUS COMPARISON")
    print("=" * 78)

    our_ids = our_encode(corpus_text, our_merges)
    gpt2_ids = gpt2_enc.encode(corpus_text)

    our_compression = len(corpus_text) / len(our_ids)
    gpt2_compression = len(corpus_text) / len(gpt2_ids)

    print(f"Corpus size:        {len(corpus_text):,} characters")
    print()
    print(f"{'':20} {'vocab size':>12} {'tokens':>10} {'compression':>13}")
    print(f"{'SwiftBPE (my tokenizer)(from scratch)':20} {our_vocab_size:>12,} {len(our_ids):>10,} {our_compression:>12.2f}x")
    print(f"{'GPT-2 (tiktoken)':20} {gpt2_enc.n_vocab:>12,} {len(gpt2_ids):>10,} {gpt2_compression:>12.2f}x")


def main() -> None:
    our_merges, our_vocab_size = load_our_tokenizer()
    gpt2_enc = tiktoken.get_encoding("gpt2")

    compare_on_strings(our_merges, gpt2_enc)
    compare_on_full_corpus(our_merges, gpt2_enc, our_vocab_size)

    print()
    print("=" * 78)
    print("NOTE: our tokenizer uses GPT-4/GPT-3.5's pre-tokenization pattern")
    print("(cl100k_base), not GPT-2's own original pattern — so chunk")
    print("splitting differs slightly between the two even before BPE")
    print("merging starts. Not just a vocab-size or training-data difference.")
    print("=" * 78)


if __name__ == "__main__":
    main()