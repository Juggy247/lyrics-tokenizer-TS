# AGENTS.md — Lyric Tokenizer Lab / SwiftBPE

Context for AI coding assistants (Claude Code, GitHub Copilot, etc.) working
in this repo. Read this before making changes — several hard-won lessons
below prevent re-introducing bugs that took real debugging time to find.

## ⚠️ Working agreement — READ FIRST, applies to every change

**Never make multiple changes at once. Never mark something "done" without
the project owner confirming it themselves.** The required loop for every
single change, no exceptions:

1. Propose ONE change (one file, one function, one fix) and explain what it
   does and why — briefly, in plain terms.
2. Show exactly what to run to test it.
3. STOP and wait. Do not move to the next change, do not touch another
   file, do not assume it worked.
4. The project owner runs it themselves and reports back the actual
   output/error.
5. Only after they confirm it worked do you move to the next change.

If something breaks, debug that one thing to resolution before proposing
anything else — don't layer a second change on top of an unverified first
one. This project has been built this way from the start (every fix in
this document was arrived at exactly this way — propose, run, paste
output, confirm, next), and several real bugs were caught specifically
*because* changes were verified one at a time rather than batched. Do not
"helpfully" batch multiple fixes into one large diff, even if you're
confident they're all correct — confidence isn't confirmation.

This applies even to changes that seem trivial or obviously correct.

## What this project is

**SwiftBPE**: a byte-pair-encoding tokenizer built completely from scratch
(no tokenizer libraries used in the implementation itself), trained on
Taylor Swift's lyrics, rigorously compared against GPT-2/GPT-3.5-4/GPT-4o,
wrapped in a FastAPI backend with a vanilla JS frontend. Portfolio/resume
project demonstrating backend + AI engineering skill. Goal: deploy on AWS
(Phase 8), learned hands-on by a beginner who prefers writing code
themselves with guidance rather than having it written for them.

## Critical: import conventions (read before touching any Python file)

This codebase has TWO import styles coexisting right now, and mixing them
causes `ModuleNotFoundError` crashes that are confusing to debug:

- **New/correct style** (used in `main.py`): absolute imports via proper
  Python packages — `from backend.tokenizer.bpe import encode`
- **Old/legacy style** (still present in most standalone scripts):
  `sys.path.insert(0, ...)` hacks followed by bare imports like
  `from bpe import encode`. This ONLY works when the script is run directly
  from its own folder. It BREAKS if that file is ever imported by something
  else (this exact bug already happened once with `swiftian_score.py` and
  was fixed — its import is now `from backend.tokenizer.bpe import encode`).

**Every folder has an `__init__.py`** (`backend/`, `backend/tokenizer/`,
`backend/tokenizer/evaluation/`, `backend/analysis/`, `backend/data_collection/`),
making this a real Python package. When you touch ANY file that still has
`from bpe import ...` or similar bare imports, update it to
`from backend.tokenizer.bpe import ...` — don't leave it as-is.

**Known files that likely STILL have the old bare-import pattern**
(fix when you next touch them, not proactively):
- `backend/tokenizer/train_tokenizer.py`
- `backend/tokenizer/export_vocab_txt.py`
- `backend/tokenizer/compute_tokens_stats.py` (filename has "tokens"
  plural, not "token" — watch for typos in commands)
- `backend/tokenizer/evaluation/*.py` (all four files)
- `backend/analysis/era_comparison.py`

## Critical: frontend file linking (the same class of bug, browser-side)

Just like Python import paths, **HTML `<link>`/`<script src>` tags must
match the ACTUAL filename on disk exactly** — this already caused one real
bug: the CSS file was saved under a different name than what `index.html`'s
`<link rel="stylesheet" href="...">` pointed to, so styles silently failed
to apply (no console error, page just rendered unstyled). Verify the exact
current filenames before assuming — check with `ls frontend/` rather than
trusting what any past instructions said the filename "should" be.

## How to run things

**Python: everything runs from the PROJECT ROOT**, using `-m`:

```bash
# Start the API server
python3 -m uvicorn backend.main:app --reload

# Run a script that's been migrated to package imports
python3 -m backend.tokenizer.swiftian_score
```

Scripts NOT yet migrated still need the old `cd`-into-folder pattern.
Check for `sys.path.insert` at the top of a file to tell which convention
it's using.

**Frontend**: open `frontend/index.html` directly in a browser (double-
click, or drag into a tab). No build step, no dev server needed — it's
plain HTML/CSS/JS calling the FastAPI backend directly via `fetch()`.
The backend server must be running (see above) for the page to work, since
it calls `http://127.0.0.1:8000` directly. CORS is currently wide open
(`allow_origins=["*"]`) to make this work with zero config — MUST be
tightened before Phase 8 deployment (see Phase 8 notes below).

## Repo structure (current)

```
lyric-tokenizer-lab/
├── .env, .env.example, .gitignore, requirements.txt
├── DATA.md, README.md          (STATUS UNCONFIRMED — verify these exist
│                                 and are current before assuming so)
├── frontend/
│   ├── index.html               (structure only, no inline CSS/JS)
│   ├── styles.css or style.css  (VERIFY EXACT NAME — see "frontend file
│   │                             linking" warning above)
│   └── script.js                (all page logic: Swiftian Score fetch +
│                                 render, token visualization, era chart
│                                 via Chart.js CDN)
├── backend/
│   ├── __init__.py
│   ├── main.py                  (FastAPI app — see "Phase 6" below)
│   ├── data/
│   │   ├── raw/                 (gitignored — 300 scraped songs)
│   │   ├── processed/           (gitignored — cleaned, filtered lyrics)
│   │   ├── corpus.txt           (gitignored)
│   │   ├── spotify_metadata.json (gitignored — album/release_date/duration
│   │   │                          per song, keyed by filename stem)
│   │   ├── out_of_domain_sample.txt  (Pride and Prejudice, for testing)
│   │   └── taylor_swift_wiki.txt     (Wikipedia bio, for testing)
│   ├── data_collection/
│   │   ├── __init__.py
│   │   ├── fetch_lyrics.py       (Genius API — filters AT SOURCE: primary
│   │   │                          artist ID must be 1177, URL must end in
│   │   │                          "-lyrics" not "-annotated", title must not
│   │   │                          contain "voice memo"/"work tape"/etc.
│   │   │                          TOP-UP CAPABLE: safe to re-run, only
│   │   │                          fetches new songs up to TARGET_TOTAL,
│   │   │                          dedupes by genius_song_id)
│   │   ├── clean_lyrics.py       (strips Genius page boilerplate)
│   │   ├── check_processed.py    (automated sanity checker, NOT gitignored)
│   │   ├── fetch_spotify_data.py (rebuilds spotify_metadata.json from
│   │   │                          scratch every run — no top-up logic,
│   │   │                          this is intentional/fine)
│   │   ├── audit_artists_attribution.py  (checks genius_url artist slug
│   │   │                          against expected "taylor-swift-" prefix)
│   │   └── audit_content_type.py (checks genius_url ends in "-lyrics" not
│   │                              "-annotated" — catches poems/prologues/etc)
│   ├── tokenizer/
│   │   ├── __init__.py
│   │   ├── bpe.py                 (SwiftBPE core: train_bpe, encode, decode,
│   │   │                           pretokenize. Uses CL100K_SPLIT_PATTERN
│   │   │                           (GPT-4 style) as ACTIVE_SPLIT_PATTERN.
│   │   │                           GPT2_SPLIT_PATTERN also defined but unused.)
│   │   ├── build_corpus.py
│   │   ├── train_tokenizer.py     (trains PRODUCTION tokenizer on ALL
│   │   │                           songs, vocab_size=2000)
│   │   ├── export_vocab_txt.py    (human-readable vocab.txt)
│   │   ├── swiftian_score.py      ("How Swiftian is your text?" — has
│   │   │                           both a CLI interactive loop (guarded by
│   │   │                           if __name__=="__main__") AND is imported
│   │   │                           as a library by main.py for the
│   │   │                           /swiftian-score endpoint. Key functions:
│   │   │                           compression_score, tier_for, token_dna,
│   │   │                           familiarity_score, most_swift_coded_token,
│   │   │                           decode_token, build_doc_freq_distribution.
│   │   │                           MIN_COMPRESSION=2.0, MAX_COMPRESSION=4.0
│   │   │                           calibration constants.)
│   │   ├── compute_tokens_stats.py (precomputes term_frequency/
│   │   │                            document_frequency per token across
│   │   │                            corpus -> artifacts/token_stats.json.
│   │   │                            Must re-run after ANY corpus change.)
│   │   ├── artifacts/
│   │   │   ├── merges.json, vocab.json  (production tokenizer)
│   │   │   ├── vocab.txt                 (human-readable)
│   │   │   ├── token_stats.json          (per-token corpus frequency)
│   │   │   └── tokenizer_info.json       (metadata/name info)
│   │   └── evaluation/
│   │       ├── __init__.py
│   │       ├── test_roundtrip.py       (60 test cases, must stay 60/60
│   │       │                            passing after ANY bpe.py change)
│   │       ├── compare_tokenizers.py   (per-category vs GPT-2)
│   │       ├── eval_generalization.py  (RIGOROUS held-out train/test
│   │       │                            split, seed=42, 80/20 by song —
│   │       │                            THE fair generalization test)
│   │       └── eval_out_of_domain.py   (tests production tokenizer on
│   │                                    arbitrary text file arg)
│   └── analysis/
│       ├── __init__.py
│       ├── era_comparison.py    (groups songs by normalized album/era,
│       │                         exports era_stats.json for the API.
│       │                         Filters to "major albums" = 5+ songs.
│       │                         Requires spotify_metadata.json to be
│       │                         CURRENT — re-run fetch_spotify_data.py
│       │                         after any corpus change first.)
│       └── era_stats.json       (exported data, consumed by /stats/eras)
├── docs/
│   └── PHASE3_FINDINGS.md       (tokenizer comparison writeup, kept
│                                 updated through 3 corpus cleanup rounds)
└── venv/
```

## Data pipeline history (why the corpus looks the way it does)

The corpus went through several real data-quality issues, each caught by a
dedicated audit rather than assumed correct:

1. **Genius search returns loosely-related results, not just exact artist
   matches.** `genius.search_artist()`/`genius.search()` route through a
   blocked public endpoint (403s) — must use `genius.search_songs()`
   (authenticated) instead. Even then, `artist_songs()` can return songs
   where the target artist is only a FEATURE, not primary — e.g. "deja vu"
   (actually Olivia Rodrigo's song) got pulled into an early scrape.
2. **Genius's lyrics scraping requires a browser User-Agent override** —
   the default `lyricsgenius` UA gets blocked by Cloudflare on the
   individual lyrics-page requests (search/metadata endpoints are fine).
3. **Not everything with a "-lyrics"-adjacent URL is a song** — poems and
   spoken prologues use a `-annotated` URL suffix instead of `-lyrics`.
4. **`fetch_lyrics.py` now filters ALL of the above at the metadata level,
   before fetching any lyrics** — this is the current, correct state. If
   asked to re-fetch or expand the corpus, use the existing script, don't
   reimplement fetching from scratch.
5. **The corpus currently sits at 300 songs**, having been cleaned three
   times (15 misattributed/collab songs removed, 6 non-song content files
   removed, 1 duplicate voice-memo removed) then topped back up to 300
   each time using the pre-filtered fetch script. One open item: a
   recently-added "Anti-Hero (Remix)" was never manually verified for
   lyrical duplication with the original "Anti-Hero" — check this if
   asked to do further corpus cleanup.

## Phase 6 — FastAPI backend: COMPLETE

- `GET /` — health check
- `POST /tokenize` — validated (`Field(min_length=1, max_length=5000)` on
  `text`), rate limited (20/min via slowapi)
- `POST /swiftian-score` — full feature response: compression ratio, 0-100
  Swiftian score, verdict tier, decoded token list, Token DNA, familiarity
  score, most-Swift-coded token + runners-up. Rate limited (20/min).
- `GET /stats/eras` — serves precomputed `era_stats.json`. Rate limited
  (60/min).
- CORS enabled (`allow_origins=["*"]` — fine for local dev, MUST be
  tightened before Phase 8).

**slowapi gotcha, already solved, keep in mind if adding new endpoints**:
every rate-limited endpoint needs a parameter literally named `request` of
type `Request` (from `fastapi`) — slowapi inspects the function signature
for it. Since `request` was already taken by convention for the Pydantic
body in earlier drafts, the body parameter is now named `data` instead
(see current `main.py` — `def tokenize(request: Request, data:
TokenizeRequest)`) to avoid the collision.

## Phase 7 — Frontend dashboard: MOSTLY COMPLETE

Single-page vanilla JS/HTML/CSS site in `frontend/`, no framework, no
build step — calls the Phase 6 API directly via `fetch()`.

**Done:**
- Swiftian Score input box — textarea + button, calls `/swiftian-score`,
  renders score/verdict/compression/familiarity live.
- Visual token display — each token rendered as a colored `<span class="
  token token-N">`, cycling through 6 CSS color classes via `i % 6`.
  Leading spaces in tokens are shown as a visible `·` (via
  `tok.replace(/^ /, "·")`) so word boundaries are visible — otherwise a
  leading space token is invisible and confusing.
- Era comparison bar chart — Chart.js (loaded via CDN script tag, must
  load BEFORE `script.js` in the HTML), fed by `/stats/eras`, one distinct
  color per bar via a 13-color palette cycled with `i % palette.length`,
  bold rotated x-axis labels, bold chart title, legend hidden (not
  meaningful with per-bar coloring).
- CSS and JS both externalized into their own files (not inline) for
  readability — see the filename-matching warning above.

**Not yet done (optional polish, not blocking Phase 8):**
- Mobile-responsive layout — currently a fixed `max-width` desktop layout,
  never tested on/adapted for small screens.
- No shared page layout between the score section and the chart section
  beyond basic stacking — could look more like a cohesive "dashboard" with
  better visual hierarchy.

## Phase 8 — AWS deployment (not started)

This is the part the project owner specifically wants hands-on experience
with — walk through concepts, don't just hand over finished config.
- AWS account + IAM user (never use root credentials)
- EC2 instance, SSH, security groups
- Deploy backend: gunicorn/uvicorn + systemd service
- Nginx reverse proxy
- S3 static hosting for frontend (or serve `frontend/` from the same EC2
  instance via Nginx — simpler for a first deployment, worth discussing
  which approach before starting)
- Domain + HTTPS (Let's Encrypt or CloudFront)
- Billing alerts
- **Critical**: tighten CORS `allow_origins` from `"*"` to the real
  deployed frontend domain once it exists — this is currently wide open
  ONLY because local dev needs it; don't ship it this way.
- **Also update**: `API_BASE` constant in `frontend/script.js` currently
  hardcodes `http://127.0.0.1:8000` — this needs to become the real
  deployed backend URL once Phase 8 is live.

## Phase 9 — Polish (not started)

- Final README with architecture diagram + live demo link
- Remove scratch files (`test.py`, `investigate.py` if still present)
- Resolve `compute_tokens_stats.py` naming inconsistency
- Fix any remaining old-style Python imports (see list above)
- Verify `DATA.md`/`README.md` exist, are accurate, and reflect the final
  300-song corpus with its cleanup history
- Full clean-clone verification (does the project actually work from a
  fresh `git clone` + `pip install -r requirements.txt`, including the
  frontend pointing at the right backend URL?)

## General working style for this project

- The project owner is a beginner learning by building — prefers
  understanding *why* before *what*, but has explicitly asked to move
  faster once fundamentals were covered. Match pace to what's being asked.
- Strong internal norm of verifying claims empirically rather than
  assuming (checking actual API responses before building around assumed
  field names, confirming file counts before trusting downstream output,
  checking actual filenames on disk rather than trusting what a past
  instruction said they should be named). Continue that norm.
- Never commit raw lyrics, `corpus.txt`, or `.env` — `.gitignore` should
  cover `backend/data/raw/`, `backend/data/processed/`, `backend/data/*.json`,
  `backend/data/*.txt`, `backend/data/*.csv`, and `.env`. This was violated
  once already and the repo had to be deleted and recreated — verify with
  `git add -n .` (dry run) before every real commit, not just the first one.
