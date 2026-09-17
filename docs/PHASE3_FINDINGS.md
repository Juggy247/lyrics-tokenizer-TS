# Phase 3: Tokenizer Comparison — Findings

## Objective

Building a tokenizer from scratch proves you can implement the algorithm.
Comparing it against real production tokenizers (GPT-2, GPT-3.5/GPT-4,
GPT-4o) proves you understand what it's actually doing — where domain
specialization helps, where it costs you, and how vocabulary size trades
off against generalization.

## Methodology

Our tokenizer: byte-level BPE, GPT-4-style regex pre-tokenization
(`cl100k_base` pattern — case-insensitive contractions, digit runs capped
at 1–3 characters), vocab size 2,000, trained on 300 verified Taylor Swift
songs (560,547 characters) scraped via the Genius API.

Reference tokenizers (via `tiktoken`): GPT-2 (50,257 vocab), GPT-3.5/GPT-4
`cl100k_base` (100,277 vocab), GPT-4o `o200k_base` (200,019 vocab).

Four tests, in increasing order of rigor / distance from the training domain:

1. **Held-out Taylor Swift lyrics** — songs split 80/20 by song (seed=42);
   an evaluation tokenizer trained only on the 80% split, tested on the 20%
   it never saw. The one genuinely fair "in-domain" test.
2. **Out-of-domain: *Pride and Prejudice*** — public-domain 19th-century
   prose, chosen specifically because it shares essentially no vocabulary
   or stylistic overlap with pop lyrics.
3. **Out-of-domain: Wikipedia's Taylor Swift biography** — shares her name,
   song titles, and album names with the training corpus, but is written
   in a completely different register (formal encyclopedic prose).

All reference tokenizers were evaluated on text they had never seen either,
making these fair, apples-to-apples comparisons.

## Data integrity corrections (post-analysis)

The corpus went through three rounds of cleanup after the initial 300-song
scrape, each caught by a targeted audit rather than assumed correct:

1. **Artist misattribution / uncredited features (15 songs removed).**
   Cross-referencing each song's `genius_url` against Spotify's confirmed
   artist ID revealed songs either misattributed to Taylor Swift entirely
   (e.g. "deja vu" is genuinely Olivia Rodrigo's song, pulled in by an
   imprecise Genius search) or featured collaborations where primary
   billing belonged to another artist (e.g. "Half of My Heart" by John
   Mayer feat. Taylor Swift).
2. **Non-song content (6 files removed).** Genius URLs ending in
   `-annotated` rather than `-lyrics` revealed two poems, a spoken
   prologue, a spoken intro clip, and two pieces of tour logistics text
   (dates/setlist) — none of which are song lyrics.
3. **Duplicate/mixed content (1 file removed).** A "songwriting voice
   memo" version of "cardigan" mixed real spoken commentary with draft
   lyrics substantially duplicating the existing clean "cardigan" entry.

After each round, the corpus was topped back up to 300 songs using a
rewritten fetch pipeline that filters at the source — before fetching any
lyrics — on: primary-artist ID (excludes featured-only credits), URL
suffix (excludes non-song content), and title keyword markers (excludes
voice memos/work tapes). This means future top-ups (e.g. after a new
album release) shouldn't reintroduce the same categories of contamination.

Across all three rounds, corrected numbers differed from the original,
uncleaned run by under 0.1x on every test — confirming the contamination
was a data-integrity issue, not a result-distorting one. All findings below
reflect the final, corrected 300-song corpus.

**Known open item:** one newly-added song, "Anti-Hero (Remix)," has not
yet been individually checked for lyrical overlap with the original
"Anti-Hero." If it turns out to be a near-duplicate, it can be swapped out
via the same fetch script's built-in deduplication (keyed on Genius song
ID) without needing to touch anything else.

## Results

### Test 1 — Held-out Taylor Swift lyrics (240 train / 60 test songs)

| Tokenizer | Vocab | Tokens | Compression |
|---|---|---|---|
| Ours (held-out) | 2,000 | 35,870 | **3.14x** |
| GPT-2 | 50,257 | 32,071 | 3.51x |
| GPT-3.5 / GPT-4 | 100,277 | 30,806 | 3.65x |
| GPT-4o | 200,019 | 29,292 | 3.84x |

### Test 2 — *Pride and Prejudice* (748,167 characters)

| Tokenizer | Vocab | Tokens | Compression |
|---|---|---|---|
| Ours (Swift-trained) | 2,000 | 289,044 | **2.59x** |
| GPT-2 | 50,257 | 196,243 | 3.81x |
| GPT-3.5 / GPT-4 | 100,277 | 175,627 | 4.26x |
| GPT-4o | 200,019 | 174,392 | 4.29x |

### Test 3 — Wikipedia: Taylor Swift biography (61,184 characters)

| Tokenizer | Vocab | Tokens | Compression |
|---|---|---|---|
| Ours (Swift-trained) | 2,000 | 26,412 | **2.32x** |
| GPT-2 | 50,257 | 13,025 | 4.70x |
| GPT-3.5 / GPT-4 | 100,277 | 13,266 | 4.61x |
| GPT-4o | 200,019 | 13,180 | 4.64x |

## Key findings

**1. Vocabulary size shows real but diminishing returns.** Across all three
reference tokenizers, doubling vocab size from 50K→100K bought +4.0%
compression on held-out lyrics; doubling again from 100K→200K bought
+5.2%. Bigger helps, but not proportionally.

**2. Domain specialization is efficient but fragile.** Our 2,000-token
tokenizer achieves ~89% of GPT-2's compression on held-out lyrics
(3.14x vs 3.51x) despite having 4% of its vocabulary — a strong result in
its narrow lane. But that advantage narrows outside the training domain:
compression drops to 2.59x on 19th-century prose (a 17.5% relative decline
from the 3.14x held-out baseline) and 2.32x on Wikipedia text (a 26.1%
decline). GPT-2/4/4o barely move by comparison, and actually compress
*better* on both out-of-domain texts than on lyrics.

**3. Topic overlap doesn't help — register does.** The Wikipedia article
shares Taylor Swift's name, song titles, and album names with the training
corpus, yet our tokenizer performed *worse* on it (2.32x) than on Jane
Austen (2.59x). Formal encyclopedic prose — dates, chart figures, award
names — shares almost no *stylistic* pattern with song lyrics, regardless
of shared subject matter. What mattered was how the text was written, not
what it was about.

**4. The reference tokenizers likely have a home-field advantage on
Wikipedia specifically.** Wikipedia is a well-documented major component of
GPT-2/3.5/4's training data, which likely explains why their compression is
*highest* on that test — it isn't a fair "out-of-domain" test for them, only
for ours. Worth noting as an asymmetry in the comparison rather than a
clean apples-to-apples result on that one test.

## Limitations & honest caveats

- **Register vs. topic is a hypothesis, not a controlled experiment.** The
  Wikipedia and Austen texts differ in more than one way at once (era,
  formality, sentence length, punctuation conventions) — this data is
  suggestive, not a clean isolation of the "register" variable.
- **An earlier version of this analysis (before pre-tokenization was
  added) suggested our tokenizer slightly *beat* GPT-2 on the full
  training corpus.** That result doesn't hold up: it tested our tokenizer
  on its own training data, a methodological flaw caught before being
  reported as a real finding — the held-out test above is the fair,
  correct version.
- **Our BPE implementation is intentionally naive** — no priority-queue
  optimization during training (full corpus rescan per merge), which makes
  training noticeably slower with pre-tokenization enabled (~88s at vocab
  2,000 on the current 300-song corpus). A production implementation would
  avoid this.
- **Correctness was re-verified after every corpus change**: all 60
  round-trip encode/decode tests pass on the current implementation and
  final 300-song dataset.
- **The corpus underwent three rounds of data-integrity cleanup** (see
  above) before reaching its final state. Each round changed the numbers
  by less than 0.1x, suggesting the underlying findings are stable rather
  than sensitive to small corpus composition changes.