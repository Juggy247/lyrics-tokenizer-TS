"""
Phase 3c — Out-of-domain long-text test.

Complements eval_generalization.py (held-out Taylor Swift lyrics) with the
opposite extreme: a long piece of text that is NOT lyrics, NOT by Taylor
Swift, and shares essentially no vocabulary overlap with the training
corpus. Shows how much domain specialization costs once fully outside its
trained domain, compared to GPT-2/GPT-3.5/4/4o's general-purpose vocabs.

Uses the PRODUCTION tokenizer (backend/tokenizer/artifacts/, trained on all
300 songs), since this is about in-domain vs out-of-domain contrast, not
training/test leakage.

Usage:
    python3 backend/tokenizer/eval_out_of_domain.py path/to/text.txt
"""
import tiktoken
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpe import encode, decode

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"


REFERENCE_ENCODINGS = [
    ("gpt2", "GPT-2"),
    ("cl100k_base", "GPT-3.5 / GPT-4"),
    ("o200k_base", "GPT-4o"),
]


def load_our_tokenizer():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        merges = [tuple(pair) for pair in json.load(f)]
    with open(ARTIFACTS_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab_size = len(json.load(f))
    return merges, vocab_size


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 eval_out_of_domain.py path/to/text.txt")
        return

    text_path = Path(sys.argv[1])
    if not text_path.exists():
        print(f"File not found: {text_path}")
        return

    with open(text_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    print(f"Loaded {len(text):,} characters from {text_path.name}")

    our_merges, our_vocab_size = load_our_tokenizer()
    our_ids = encode(text, our_merges)
    our_compression = len(text) / len(our_ids)

    print("\n" + "=" * 78)
    print(f"OUT-OF-DOMAIN TEST — {text_path.name}")
    print("(production tokenizer, trained on all 300 Taylor Swift songs)")
    print("=" * 78)
    print(f"{'':28} {'vocab':>10} {'tokens':>10} {'compression':>13}")
    print(f"{'Ours (Swift-trained)':28} {our_vocab_size:>10,} {len(our_ids):>10,} {our_compression:>12.2f}x")

    for name, display in REFERENCE_ENCODINGS:
        enc = tiktoken.get_encoding(name)
        ids = enc.encode(text)
        compression = len(text) / len(ids)
        print(f"{display:28} {enc.n_vocab:>10,} {len(ids):>10,} {compression:>12.2f}x")

    print("\nCompare this against eval_generalization.py's held-out Taylor")
    print("Swift result to see the full in-domain vs out-of-domain contrast.")
    print("=" * 78)


if __name__ == "__main__":
    main()