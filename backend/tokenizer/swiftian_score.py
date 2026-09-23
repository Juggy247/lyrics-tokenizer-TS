"""
SwiftBPE's "How Swiftian Is Your Text?" score — full version.

Beyond the headline score, this shows:
  1. The actual tokens your text was split into
  2. "Token DNA" — what fraction of your text used a learned multi-byte
     token vs a raw, un-merged byte
  3. A two-part breakdown: Compression (the calibrated headline score) and
     Token Familiarity (how common the specific tokens you used are,
     based on real document frequency across the 300-song corpus)
  4. The single most "Swift-coded" token in your text — the learned token
     that appears in the most distinct songs — plus a few runners-up

Token Familiarity and the "most Swift-coded token" feature both require
artifacts/token_stats.json — run compute_token_stats.py first if it's
missing.

Usage:
    python3 backend/tokenizer/swiftian_score.py
    (then type text at the prompt; type 'quit' to exit)
"""

import bisect
import json
from pathlib import Path

from backend.tokenizer.bpe import encode

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

MIN_COMPRESSION = 2.0
MAX_COMPRESSION = 4.0

TIERS = [
    (90, "Certified Swiftie 💜 — this reads like a deluxe-edition bonus track"),
    (70, "Very Swift-coded ✨"),
    (50, "Somewhat Swift-ish 🎤"),
    (30, "Mild Swift energy 🎶"),
    (0,  "Definitely not a Taylor Swift lyric 📚"),
]

BAR_WIDTH = 20


def load_everything():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        merges = [tuple(pair) for pair in json.load(f)]

    with open(ARTIFACTS_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab_raw = json.load(f)
    vocab = {int(k): bytes(v) for k, v in vocab_raw.items()}

    stats_path = ARTIFACTS_DIR / "token_stats.json"
    if not stats_path.exists():
        print("(No token_stats.json found — Token Familiarity and 'Most "
              "Swift-coded token' will be unavailable. Run "
              "compute_token_stats.py first.)\n")
        token_stats = {}
        total_songs = 0
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        token_stats = {int(k): v for k, v in raw["stats"].items()}
        total_songs = raw["total_songs"]

    return merges, vocab, token_stats, total_songs


def build_doc_freq_distribution(token_stats):
    """Sorted list of document frequencies for all MERGED tokens (id >= 256)
    that actually appear in the corpus — used to compute percentile rank
    for the Token Familiarity metric."""
    values = sorted(
        v["document_frequency"]
        for token_id, v in token_stats.items()
        if token_id >= 256
    )
    return values


def decode_token(token_id: int, vocab: dict) -> str:
    b = vocab[token_id]
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return repr(b)
    return (
        s.replace("\n", "\\n")
         .replace("\t", "\\t")
         .replace("\r", "\\r")
    )


def bar(pct: float, width: int = BAR_WIDTH) -> str:
    filled = round(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def compression_score(text: str, merges) -> tuple[float, float, list[int]]:
    token_ids = encode(text, merges)
    if not token_ids:
        return 0.0, 0.0, []

    compression = len(text) / len(token_ids)
    clamped = max(MIN_COMPRESSION, min(MAX_COMPRESSION, compression))
    pct = (clamped - MIN_COMPRESSION) / (MAX_COMPRESSION - MIN_COMPRESSION) * 100

    return compression, pct, token_ids


def tier_for(pct: float) -> str:
    for threshold, label in TIERS:
        if pct >= threshold:
            return label
    return TIERS[-1][1]


def token_dna(token_ids: list[int]) -> tuple[float, int, int]:
    merged = sum(1 for t in token_ids if t >= 256)
    raw_byte = sum(1 for t in token_ids if t < 256)
    total = len(token_ids)
    pct_learned = (merged / total * 100) if total else 0.0
    return pct_learned, merged, raw_byte


def familiarity_score(token_ids: list[int], token_stats: dict, doc_freq_dist: list[int]) -> float:
    merged_ids = [t for t in token_ids if t >= 256 and t in token_stats]
    if not merged_ids or not doc_freq_dist:
        return 0.0

    percentiles = []
    for t in merged_ids:
        doc_freq = token_stats[t]["document_frequency"]
        rank = bisect.bisect_right(doc_freq_dist, doc_freq)
        percentiles.append(rank / len(doc_freq_dist) * 100)

    return sum(percentiles) / len(percentiles)


def most_swift_coded_token(token_ids, vocab, token_stats, total_songs):
    merged_ids = sorted(set(t for t in token_ids if t >= 256 and t in token_stats))
    if not merged_ids:
        return None, []

    ranked = sorted(
        merged_ids,
        key=lambda t: (token_stats[t]["document_frequency"], token_stats[t]["term_frequency"]),
        reverse=True,
    )

    top = ranked[0]
    top_info = {
        "text": decode_token(top, vocab),
        "doc_freq": token_stats[top]["document_frequency"],
        "term_freq": token_stats[top]["term_frequency"],
        "length": len(vocab[top]),
    }

    runners_up = []
    for t in ranked[1:4]:
        runners_up.append({
            "text": decode_token(t, vocab),
            "term_freq": token_stats[t]["term_frequency"],
        })

    return top_info, runners_up


def main():
    print("=== How Swiftian Is Your Text? ===")
    print("Type a sentence and see how 'Taylor Swift' it sounds to SwiftBPE.")
    print("Type 'quit' to exit.\n")

    merges, vocab, token_stats, total_songs = load_everything()
    doc_freq_dist = build_doc_freq_distribution(token_stats) if token_stats else []

    while True:
        text = input("Enter text: ").strip()

        if text.lower() in ("quit", "exit", "q"):
            print("Bye! 👋")
            break

        if len(text) < 15:
            print("(Heads up: very short text gives a noisy score — try a full sentence.)")

        compression, comp_pct, token_ids = compression_score(text, merges)
        label = tier_for(comp_pct)

        print(f"\nCompression ratio: {compression:.2f}x")
        print(f"Swiftian Score: {comp_pct:.0f}%")
        print(f"Verdict: {label}")

        # 1. Show the actual tokens
        display_tokens = " ".join(f"[{decode_token(t, vocab)}]" for t in token_ids)
        print(f"\nTokens:\n{display_tokens}")

        # 2. Token DNA
        pct_learned, merged_count, byte_count = token_dna(token_ids)
        print(f"\nToken DNA:")
        print(f"{bar(pct_learned)}  {pct_learned:.0f}% learned")
        print(f"{bar(100 - pct_learned)}  {100 - pct_learned:.0f}% character-level")
        print(f"Learned tokens: {merged_count}   Character tokens: {byte_count}")

        # 3. Breakdown: Compression + Token Familiarity (two real, distinct metrics)
        if token_stats:
            fam_pct = familiarity_score(token_ids, token_stats, doc_freq_dist)
            print(f"\nSWIFTIANESS BREAKDOWN")
            print(f"  Compression        {bar(comp_pct, 15)} {comp_pct:.0f}%")
            print(f"  Token familiarity  {bar(fam_pct, 15)} {fam_pct:.0f}%")
            print(f"  (familiarity = how common your tokens are across "
                  f"the {total_songs}-song corpus)")

            # 4. Most Swift-coded token
            top_info, runners_up = most_swift_coded_token(token_ids, vocab, token_stats, total_songs)
            if top_info:
                print(f"\n✨ Most Swift-coded token")
                print(f'  "{top_info["text"]}"')
                print(f'  Found in: {top_info["doc_freq"]} / {total_songs} songs')
                print(f'  Token frequency: {top_info["term_freq"]}')
                print(f'  Token length: {top_info["length"]}')

                if runners_up:
                    print(f"\n  Other notable tokens:")
                    for r in runners_up:
                        print(f'    "{r["text"]}"   {r["term_freq"]} occurrences')
            else:
                print(f"\n(No learned SwiftBPE tokens found in this text — "
                      f"it's entirely made of raw, un-merged characters.)")

        print()


if __name__ == "__main__":
    main()