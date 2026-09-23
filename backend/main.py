"""
Phase 6 — FastAPI backend.

Run from the PROJECT ROOT (not from inside backend/):
    python3 -m uvicorn backend.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi import FastAPI , Request
from pydantic import BaseModel, Field

from backend.tokenizer.bpe import encode, decode
from backend.tokenizer.swiftian_score import (
    compression_score,
    tier_for,
    token_dna,
    familiarity_score,
    most_swift_coded_token,
    decode_token,
    build_doc_freq_distribution,
)

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Lyric Tokenizer Lab API")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app_environment = os.getenv("APP_ENV", "development")
configured_origins = os.getenv("ALLOWED_ORIGINS", "")

if app_environment == "production" and not configured_origins:
    raise RuntimeError("ALLOWED_ORIGINS must be set in production")

allowed_origins = (
    [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if configured_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARTIFACTS_DIR = Path(__file__).resolve().parent / "tokenizer" / "artifacts"


def load_tokenizer():
    with open(ARTIFACTS_DIR / "merges.json", "r", encoding="utf-8") as f:
        merges = [tuple(pair) for pair in json.load(f)]
    with open(ARTIFACTS_DIR / "vocab.json", "r", encoding="utf-8") as f:
        vocab_raw = json.load(f)
    vocab = {int(k): bytes(v) for k, v in vocab_raw.items()}
    return merges, vocab


def load_token_stats():
    stats_path = ARTIFACTS_DIR / "token_stats.json"
    with open(stats_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    token_stats = {int(k): v for k, v in raw["stats"].items()}
    total_songs = raw["total_songs"]
    return token_stats, total_songs

def load_era_stats():
    era_stats_path = Path(__file__).resolve().parent / "analysis" / "era_stats.json"
    with open(era_stats_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Load once at startup, not on every request — this is a real performance
# practice: loading ~2MB of JSON per request would be needlessly slow.
MERGES, VOCAB = load_tokenizer()
TOKEN_STATS, TOTAL_SONGS = load_token_stats()
DOC_FREQ_DIST = build_doc_freq_distribution(TOKEN_STATS)
ERA_STATS = load_era_stats()


class TokenizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class TokenizeResponse(BaseModel):
    token_ids: list[int]
    token_count: int
    compression_ratio: float


class SwiftianScoreResponse(BaseModel):
    compression_ratio: float
    swiftian_score: float
    verdict: str
    tokens: list[str]
    percent_learned_tokens: float
    familiarity_score: float
    most_swift_coded_token: dict | None
    other_notable_tokens: list[dict]


@app.get("/")
def root():
    return {"message": "Lyric Tokenizer Lab API is running. See /docs for endpoints."}


@app.post("/tokenize", response_model=TokenizeResponse)
@limiter.limit("20/minute")
def tokenize(request: Request, data: TokenizeRequest):
    token_ids = encode(data.text, MERGES)
    compression = len(data.text) / len(token_ids) if token_ids else 0.0

    return TokenizeResponse(
        token_ids=token_ids,
        token_count=len(token_ids),
        compression_ratio=round(compression, 3),
    )


@app.post("/swiftian-score", response_model=SwiftianScoreResponse)
@limiter.limit("20/minute")
def swiftian_score_endpoint(request: Request, data: TokenizeRequest):
    compression, comp_pct, token_ids = compression_score(data.text, MERGES)
    verdict = tier_for(comp_pct)

    display_tokens = [decode_token(t, VOCAB) for t in token_ids]
    pct_learned, _, _ = token_dna(token_ids)
    fam_pct = familiarity_score(token_ids, TOKEN_STATS, DOC_FREQ_DIST)

    top_info, runners_up = most_swift_coded_token(token_ids, VOCAB, TOKEN_STATS, TOTAL_SONGS)

    return SwiftianScoreResponse(
        compression_ratio=round(compression, 3),
        swiftian_score=round(comp_pct, 1),
        verdict=verdict,
        tokens=display_tokens,
        percent_learned_tokens=round(pct_learned, 1),
        familiarity_score=round(fam_pct, 1),
        most_swift_coded_token=top_info,
        other_notable_tokens=runners_up,
    )

@app.get("/stats/eras")
@limiter.limit("60/minute")
def get_era_stats(request: Request):
    return ERA_STATS