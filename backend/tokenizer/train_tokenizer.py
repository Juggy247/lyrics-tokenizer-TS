"""
Phase 2c — Train the tokenizer on the actual lyrics corpus.

Loads backend/data/corpus.txt, trains BPE up to VOCAB_SIZE, and saves the
resulting merges + vocab to backend/tokenizer/artifacts/. These artifact
files contain only statistical merge rules and byte mappings — no lyric
text — so they are safe to commit to git (unlike the corpus itself).

Usage:
    python3 backend/tokenizer/train_tokenizer.py
"""

import json
import time
from pathlib import Path

from bpe import train_bpe

# ---- Config ----
VOCAB_SIZE = 2000
# ----------------

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "corpus.txt"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"Corpus not found at {CORPUS_PATH}. Run build_corpus.py first.")
        return

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    print(
        f"Training BPE on {len(text):,} characters, "
        f"target vocab size {VOCAB_SIZE}..."
    )

    start = time.time()

    merges, vocab = train_bpe(text, VOCAB_SIZE)

    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s. Learned {len(merges)} merges.")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save merges
    merges_path = ARTIFACTS_DIR / "merges.json"
    with open(merges_path, "w", encoding="utf-8") as f:
        f.write("[\n")

        for i, pair in enumerate(merges):
            comma = "," if i < len(merges) - 1 else ""
            f.write(f"  [{pair[0]}, {pair[1]}]{comma}\n")

        f.write("]\n")

    # Save vocabulary
    vocab_serializable = {
        str(k): list(v)
        for k, v in vocab.items()
    }

    vocab_path = ARTIFACTS_DIR / "vocab.json"
    with open(vocab_path, "w", encoding="utf-8") as f:
        f.write("{\n")

        items = list(vocab_serializable.items())

        for i, (token_id, token_bytes) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            f.write(f'  "{token_id}": {json.dumps(token_bytes)}{comma}\n')

        f.write("}\n")

    print(f"Saved merges → {merges_path}")
    print(f"Saved vocab  → {vocab_path}")


if __name__ == "__main__":
    main()