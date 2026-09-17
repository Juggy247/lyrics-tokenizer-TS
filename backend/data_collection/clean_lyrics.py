import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def clean_lyrics_text(raw_lyrics: str, song_title: str) -> str:
    text = raw_lyrics

    # Build a flexible pattern from the song title: escape regex special
    # chars, then allow either straight or curly apostrophes (Genius's
    # scraped title sometimes uses ’ instead of '), and collapse whitespace
    # differences.

    #title contains regex-special characters, 
    # you don't want regex to interpret them as regex instructions. re.escape()
    escaped_title = re.escape(song_title)
    escaped_title = escaped_title.replace(r"\'", "['’]")
    title_pattern = re.compile(escaped_title + r"\s*Lyrics", re.IGNORECASE)

    marker = title_pattern.search(text)
    if marker:
        text = text[marker.end():]
    else:
        # Fallback: title match failed (formatting mismatch) — cut on the
        # generic "Lyrics" marker instead, better than nothing.
        generic_marker = re.search(r"\bLyrics\b", text)
        if generic_marker:
            text = text[generic_marker.end():] #string slicing (start from maker to the end of the string)

    read_more = re.search(r"Read More\s*", text, re.IGNORECASE)

    if read_more:
        text = text[read_more.end():]

    text = text.replace("You might also like", "")
    text = re.sub(r"\d*Embed\s*$", "", text, flags=re.IGNORECASE)

    return text.strip()


def clean_all() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("*.json"))

    if not raw_files:
        print(f"No raw files found in {RAW_DIR}. Run fetch_lyrics.py first.")
        return

    cleaned_count = 0
    for raw_path in raw_files:
        with open(raw_path, "r", encoding="utf-8") as f:
            record = json.load(f)   # return dict

        original_lyrics = record.get("lyrics", "")
        cleaned = clean_lyrics_text(original_lyrics, record.get("title", ""))

        record["lyrics"] = cleaned
        record["_original_char_count"] = len(original_lyrics)
        record["_cleaned_char_count"] = len(cleaned)

        out_path = PROCESSED_DIR / raw_path.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        cleaned_count += 1

    print(f"Cleaned {cleaned_count} files → {PROCESSED_DIR}/")
    print("Spot check a couple of files before moving on to tokenizer training.")


if __name__ == "__main__":
    clean_all()