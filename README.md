# Lyrics Tokenizer Lab

SwiftBPE is a byte-pair-encoding tokenizer built from scratch and trained on a Taylor Swift lyrics corpus. The project includes a FastAPI service and a small browser frontend for exploring tokenization and corpus-based statistics.

**Live demo:** [https://swiftbpe.duckdns.org](https://swiftbpe.duckdns.org)

## Features

- Train a byte-pair tokenizer from UTF-8 text without using a tokenizer library for the implementation.
- Tokenize and decode text with the trained vocabulary.
- Calculate a calibrated compression-based Swiftian score and token familiarity metrics.
- Compare compression statistics across album eras.
- View tokenization results and the era chart in a vanilla HTML, CSS, and JavaScript frontend.
- Serve the app with FastAPI, Uvicorn, and Nginx; the public deployment uses HTTPS.

## Architecture

```text
Browser -> Nginx -> static frontend
                 -> FastAPI/Uvicorn -> SwiftBPE artifacts
```

The production API loads its trained tokenizer, token statistics, and era statistics from `backend/tokenizer/artifacts/` and `backend/analysis/era_stats.json` at startup.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health message |
| `POST` | `/tokenize` | Return token IDs and compression ratio |
| `POST` | `/swiftian-score` | Return score, tokens, and familiarity metrics |
| `GET` | `/stats/eras` | Return album-era statistics for the chart |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/swiftian-score \
  -H "Content-Type: application/json" \
  -d '{"text":"Enter text to analyze"}'
```

The API accepts text from 1 to 5,000 characters. Tokenize and score endpoints are rate-limited to 20 requests per minute; era statistics are limited to 60 per minute.

## Run Locally

From the repository root, create and activate a virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the runtime packages needed by the API:

```bash
python -m pip install fastapi uvicorn pydantic slowapi python-dotenv regex
```

Create a local `.env` file in the repository root:

```dotenv
APP_ENV=development
ALLOWED_ORIGINS=*
```

Start the API from the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`. Open `backend/frontend/index.html` directly, or use VS Code Live Server on its default port `5500` to view the frontend locally.

## Tests and Evaluations

Run these commands from the repository root with the project virtual environment activated. The comparison evaluations also require `tiktoken`:

```bash
python -m pip install tiktoken
python backend/tokenizer/evaluation/test_roundtrip.py
python backend/tokenizer/evaluation/compare_tokenizers.py
python backend/tokenizer/evaluation/eval_generalization.py
python backend/tokenizer/evaluation/eval_out_of_domain.py backend/data/out_of_domain_sample.txt
```

The round-trip test checks that encoding and decoding preserve each input across 60 cases, including whitespace, punctuation, Unicode, emoji, repetition, and longer text.

The comparison scripts need local data that is excluded from Git:

- `compare_tokenizers.py` reads `backend/data/corpus.txt` and compares grouped example strings plus the full training corpus.
- `eval_generalization.py` reads the processed song JSON files, then uses a fixed seed (`42`) to split songs into 240 training and 60 held-out test songs. It trains a separate evaluation tokenizer on the training split.
- `eval_out_of_domain.py` accepts a text-file path and compares it against GPT-2, GPT-3.5/4, and GPT-4o reference encodings.

### Recorded Evaluation Results

Results below were produced locally with the checked-in production artifacts and available corpus files:

| Evaluation | SwiftBPE | Reference result |
| --- | ---: | ---: |
| Round-trip correctness | 60/60 passed | Not applicable |
| Grouped examples (20 strings) | 0 wins | GPT-2: 14 wins, 6 ties |
| Full training corpus (in-sample) | 3.20x | GPT-2: 3.52x |
| Held-out lyrics (60 songs, seed 42) | 3.14x | GPT-2: 3.51x; GPT-3.5/4: 3.65x; GPT-4o: 3.84x |
| Out-of-domain sample (748,167 characters) | 2.59x | GPT-2: 3.81x; GPT-3.5/4: 4.26x; GPT-4o: 4.29x |

Compression ratio is characters divided by token count; it is not a measure of semantic quality. The full-corpus result is in-sample because the production tokenizer was trained on that corpus. The held-out evaluation is the fairer generalization comparison. The results demonstrate the tradeoff of a small, domain-trained tokenizer; they do not show that SwiftBPE compresses better than the larger general-purpose reference tokenizers.

## Repository Layout

```text
backend/
  main.py                     FastAPI application
  frontend/                   Static browser frontend
  tokenizer/
    bpe.py                    SwiftBPE training, encoding, and decoding
    swiftian_score.py         Scoring and token-statistics helpers
    artifacts/                 Trained tokenizer artifacts
    evaluation/                Round-trip and tokenizer evaluations
  analysis/                    Era analysis and exported statistics
  data_collection/             Lyrics and metadata collection scripts
```

## Data and Credentials

Raw and processed lyrics, local environment files, and API credentials are not part of the deployment instructions and must not be committed. The `.gitignore` excludes `.env` and the raw and processed data directories.

The full `requirements.txt` includes data collection, analysis, and tokenizer-comparison dependencies in addition to the API runtime. On the small EC2 instance, installing all pinned packages under Python 3.14 attempted to build `pandas==2.2.2` from source and ran out of memory. The deployed API was installed with only the runtime package set listed above; data-pipeline dependencies are not required to serve requests.

## Deployment

The live application runs on AWS EC2. Nginx serves the frontend and proxies API routes to Uvicorn, which is managed by the `lyrics-tokenizer` systemd service. The live hostname is managed through DuckDNS and HTTPS certificates are issued and renewed with Certbot/Let's Encrypt.

Production configuration is stored in an EC2-local `.env`, not in Git. Set `APP_ENV=production` and set `ALLOWED_ORIGINS` to the exact HTTPS frontend origin. The service listens on `127.0.0.1:8000`; Nginx handles public HTTP/HTTPS traffic.