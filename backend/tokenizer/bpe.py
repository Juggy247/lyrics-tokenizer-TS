"""
Phase 2b — BPE tokenizer core.

A byte-pair-encoding tokenizer built from scratch (no external tokenizer
libraries used for the implementation itself — tiktoken is only used later,
in Phase 3, purely for comparison).

Core idea: text is first converted to raw UTF-8 bytes (values 0-255). We then
repeatedly find the most frequent adjacent pair of tokens in the corpus and
merge it into a new token with the next available ID. Repeating this process
builds up a vocabulary of increasingly large sub-word units.
"""

from collections import Counter
import regex

# GPT-2's original pre-tokenization pattern.
GPT2_SPLIT_PATTERN = (
    r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
)
# GPT-4 / GPT-3.5's pattern (cl100k_base).
CL100K_SPLIT_PATTERN = (
    r"""(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}"""
    r"""| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"""
)

ACTIVE_SPLIT_PATTERN = CL100K_SPLIT_PATTERN
_SPLIT_RE = regex.compile(ACTIVE_SPLIT_PATTERN)

def pretokenize(text: str) -> list[str]:
    """Split text into chunks so BPE merges never cross chunk boundaries."""
    return _SPLIT_RE.findall(text)

def get_pair_stats(chunks: list[int]) -> Counter:
    
    counts = Counter()
    for chunk in chunks:
        for pair in zip(chunk, chunk[1:]):
            counts[pair] += 1
    return counts

def merge_pair(chunk: list[int], pair: tuple[int, int], new_id: int) -> list[int]:

    merged = []
    i = 0 
    while i < len(chunk):
        if i < len(chunk) - 1 and chunk[i] == pair[0] and chunk[i+1] == pair[1]:
            merged.append(new_id)
            i += 2
        else:
            merged.append(chunk[i])
            i += 1
    
    return merged

def train_bpe(text: str, vocab_size: int):

    if vocab_size < 256:
        raise ValueError("vocab_size must be at least 256 (the base byte range).")
    
    str_chunks = pretokenize(text)
    chunks = [list(chunk.encode("utf-8")) for chunk in str_chunks]
    #bytes() expects an iterable of integers
    vocab = {idx: bytes([idx]) for idx in range(256)}
    merges = []

    num_merges = vocab_size - 256
    for i in range(num_merges):
        pair_stats = get_pair_stats(chunks)
        if not pair_stats:
            break

        best_pair = max(pair_stats,key=pair_stats.get)
        new_id = 256 + i

        chunks = [merge_pair(c, best_pair, new_id) for c in chunks]
        vocab[new_id] = vocab[best_pair[0]] + vocab[best_pair[1]]
        merges.append(best_pair)
    
    return merges, vocab

def encode(text: str, merges):

    
    merge_rank = {pair: 256+ i for i,pair in enumerate(merges)}
    
    str_chunks = pretokenize(text)
    token_ids = []

    for chunk_str in str_chunks:
        chunk = list(chunk_str.encode("utf-8"))

        while len(chunk) >= 2:
            pair_stats = get_pair_stats([chunk])

            candidate = min((p for p in pair_stats if p in merge_rank), 
                            key=lambda p: merge_rank[p],default=None)
            
            if candidate is None:
                break
            chunk = merge_pair(chunk, candidate, merge_rank[candidate])
        token_ids.extend(chunk)
    return token_ids

def decode(token_ids: list[int], vocab: dict[int, bytes]) -> str:
    """Decode token IDs back into the original text."""
    raw_bytes = b"".join(vocab[idx] for idx in token_ids)
    return raw_bytes.decode("utf-8", errors="replace")