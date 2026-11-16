"""Dense Qdrant, lexical TF-IDF, and rank-based hybrid on identical payloads."""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import re
import time
import unicodedata

from .common import read_jsonl
from .day6 import COLLECTION, MODEL, REVISION, adapt, load_module

ALLOWED_FILTERS = frozenset({'section', 'document_type', 'language', 'version'})


def validate_scope(scope):
    if scope is None:
        return {}
    if not isinstance(scope, dict):
        raise ValueError('scope must be an object')
    for key, value in scope.items():
        if key not in ALLOWED_FILTERS or not isinstance(value, (str, int, bool)):
            raise ValueError(f'Unsupported scope: {key}')
    return scope


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+(?:\.\w+)*', unicodedata.normalize('NFC', text).casefold())


class Lexical:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        counts = [Counter(tokens(c['text'])) for c in chunks]
        df = Counter(term for row in counts for term in row)
        self.idf = {term: math.log((1 + len(chunks)) / (1 + n)) + 1 for term, n in df.items()}
        self.vectors = [self._vector(row) for row in counts]

    def _vector(self, counts):
        row = {term: n * self.idf[term] for term, n in counts.items() if term in self.idf}
        norm = math.sqrt(sum(n*n for n in row.values())) or 1
        return {term: n/norm for term, n in row.items()}

    def search(self, query: str, top_k: int, scope: dict) -> list[dict]:
        scope = validate_scope(scope)
        vector = self._vector(Counter(tokens(query)))
        rows = []
        for chunk, candidate in zip(self.chunks, self.vectors):
            if not all(chunk['metadata'].get(k) == v for k, v in scope.items()):
                continue
            score = sum(value * candidate.get(term, 0) for term, value in vector.items())
            if score > 0:
                rows.append({**chunk, 'score': score, 'method': 'lexical'})
        rows.sort(key=lambda c: (-c['score'], c['id']))
        return [{**c, 'rank': i} for i, c in enumerate(rows[:top_k], 1)]


def rrf(dense: list[dict], lexical: list[dict], top_k: int, k: int = 60) -> list[dict]:
    fused = {}
    for method, rows in (('dense', dense), ('lexical', lexical)):
        for i, row in enumerate(rows, 1):
            entry = fused.setdefault(row['id'], {**row, 'score': 0.0, 'branch_ranks': {}})
            entry['score'] += 1.0 / (k + i)
            entry['branch_ranks'][method] = i
    rows = sorted(fused.values(), key=lambda c: (-c['score'], c['id']))[:top_k]
    return [{**row, 'method': 'hybrid_rrf', 'rank': i} for i, row in enumerate(rows, 1)]


class Retriever:
    def __init__(self, day6: Path, qdrant: Path, model_path: Path, chunks_path: Path):
        self.chunks = [adapt(c) for c in read_jsonl(chunks_path)]
        if not self.chunks or len({c['id'] for c in self.chunks}) != len(self.chunks):
            raise ValueError('Chunk export is empty or IDs are not unique')
        self.lexical = Lexical(self.chunks)
        store = load_module(day6 / 'src/store.py', 'day6_store_runtime')
        embed = load_module(day6 / 'src/embeddings.py', 'day6_embed_runtime')
        self.store = store.QdrantStore(qdrant, dimensions=384)
        self.embedder = embed.LocalEmbedder(model_name=MODEL, revision=REVISION,
                                            model_path=str(model_path), device='cpu')
        if self.store.count(COLLECTION) != len(self.chunks) or self.embedder.dimensions != 384:
            raise ValueError('Collection count or embedding dimension mismatch')

    def close(self):
        self.store.close()

    def search(self, query: str, method: str, top_k: int = 3, scope=None, pool: int = 10):
        if not isinstance(query, str) or not query.strip() or not isinstance(top_k, int) or top_k < 1:
            raise ValueError('Query and top_k are invalid')
        scope = validate_scope(scope)
        if method not in ('dense', 'lexical', 'hybrid'):
            raise ValueError('Unknown retrieval method')
        started = time.perf_counter()
        dense = lexical = []
        if method in ('dense', 'hybrid'):
            vector = self.embedder.embed_query(query)
            raw = self.store.search(COLLECTION, vector, top_k=pool if method == 'hybrid' else top_k,
                                    filters=scope)
            dense = []
            for i, row in enumerate(raw, 1):
                score = float(row['score'])
                if not math.isfinite(score):
                    raise ValueError('Qdrant returned a non-finite score')
                dense.append({**adapt(row), 'score': score, 'method': 'dense', 'rank': i})
        if method in ('lexical', 'hybrid'):
            lexical = self.lexical.search(query, pool if method == 'hybrid' else top_k, scope)
        rows = dense if method == 'dense' else lexical if method == 'lexical' else rrf(dense, lexical, top_k)
        return {'query': query, 'scope': scope, 'method': method, 'results': rows,
                'branches': {'dense': dense, 'lexical': lexical} if method == 'hybrid' else {},
                'elapsed_ms': (time.perf_counter() - started) * 1000}
