"""
Phase 2 (optional) — Human-readable vocab export.

Reads the machine-readable vocab.json (source of truth, used by encode/decode)
and writes a companion vocab.txt in the GPT-2-style format: one token per
line, id + tab + display string. This file is not used by any code — it's
purely for browsing/debugging the learned vocabulary.

Usage:
    python3 backend/tokenizer/export_vocab_txt.py
"""

import json
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def display_string(byte_list: list[int]) -> str:
    b = bytes(byte_list)
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        # Partial multi-byte sequence from a mid-training merge — show as
        # a raw bytes literal instead of crashing.
        return repr(b)

    # Escape control/whitespace chars so each line stays on one line.
    return (
        s.replace("\\", "\\\\")
         .replace("\n", "\\n")
         .replace("\t", "\\t")
         .replace("\r", "\\r")
    )


def main() -> None:
    vocab_path = ARTIFACTS_DIR / "vocab.json"
    if not vocab_path.exists():
        print(f"{vocab_path} not found. Run train_tokenizer.py first.")
        return

    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab = json.load(f)

    txt_path = ARTIFACTS_DIR / "vocab.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for k in sorted(vocab, key=lambda x: int(x)):
            f.write(f"{k}\t{display_string(vocab[k])}\n")

    print(f"Wrote human-readable vocab → {txt_path}")


if __name__ == "__main__":
    main()
