"""Read the real Day 6 embedding, vector store and payloads without re-ingestion."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import shutil

from .common import now, read_json, read_jsonl, sha256, write_json

MODEL = 'intfloat/multilingual-e5-small'
REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
COLLECTION = 'lab6_B'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapt(raw: dict) -> dict:
    required = ('chunk_id', 'document_id', 'source', 'page', 'text', 'metadata',
                'start_offset', 'end_offset', 'token_count')
    if any(key not in raw for key in required):
        raise ValueError('Incomplete Day 6 payload')
    return {'id': raw['chunk_id'], 'source_id': raw['document_id'],
            **{key: raw[key] for key in required if key not in ('chunk_id', 'document_id')}}


def snapshot(day6: Path, target: Path, output: Path) -> dict:
    day6, target, output = day6.resolve(), target.resolve(), output.resolve()
    origin = (day6 / '.local/qdrant').resolve()
    if not origin.is_dir():
        raise FileNotFoundError(f'Day 6 Qdrant not found: {origin}')
    if target == origin or target.is_relative_to(origin) or origin.is_relative_to(target):
        raise ValueError('Snapshot must be separate from the original database')
    if target.exists():
        raise FileExistsError(f'Refusing to overwrite Qdrant snapshot: {target}')
    chunks_path = day6 / 'results/chunks/B.jsonl'
    chunks = read_jsonl(chunks_path)
    if not chunks or len({c['chunk_id'] for c in chunks}) != len(chunks):
        raise ValueError('Day 6 chunk IDs are empty or not unique')
    store_module = load_module(day6 / 'src/store.py', 'day6_store')
    target.parent.mkdir(parents=True, exist_ok=True)
    # The source is exclusively locked while copying so a live writer cannot race us.
    with store_module.QdrantStore(origin, dimensions=384) as original:
        if not original.client.collection_exists(COLLECTION):
            raise ValueError('The Day 6 collection is missing')
        shutil.copytree(origin, target, ignore=shutil.ignore_patterns('.lock'))
    with store_module.QdrantStore(target, dimensions=384) as store:
        info = store.client.get_collection(COLLECTION)
        vectors = info.config.params.vectors
        if getattr(vectors, 'size', None) != 384 or str(vectors.distance).lower().split('.')[-1] != 'cosine':
            raise ValueError('Qdrant vector schema differs from the Day 6 E5 index')
        points, offset = store.client.scroll(COLLECTION, limit=len(chunks) + 1,
                                             with_payload=True, with_vectors=True)
        if offset is not None:
            raise ValueError('Unexpected extra Qdrant points')
        payloads = {p.payload['chunk_id']: p.payload for p in points}
        expected = {c['chunk_id']: c for c in chunks}
        if payloads != expected:
            raise ValueError('Qdrant payloads differ from Day 6 B chunk export')
        sample = points[0].vector
        if not isinstance(sample, list) or len(sample) != 384 or not all(math.isfinite(x) for x in sample):
            raise ValueError('Stored vector is invalid')
        norm = math.sqrt(sum(x*x for x in sample))
        if not math.isclose(norm, 1.0, abs_tol=.001):
            raise ValueError('Stored vector is not normalized')
    output.mkdir(parents=True, exist_ok=True)
    copied = output / 'chunks.jsonl'
    if copied.exists() and sha256(copied) != sha256(chunks_path):
        raise FileExistsError('Refusing to replace a different chunk export')
    if not copied.exists():
        shutil.copyfile(chunks_path, copied)
    for name in ('CPYTHON_LICENSE.txt', 'CPYTHON_DOCUMENTATION_LICENSE.rst'):
        source = day6 / 'data/licenses' / name
        dest = output / name
        if dest.exists() and sha256(dest) != sha256(source):
            raise FileExistsError(f'Refusing to replace {dest}')
        if not dest.exists():
            shutil.copyfile(source, dest)
    manifest = {
        'created_at': now(), 'collection': COLLECTION, 'chunk_count': len(chunks),
        'qdrant_payloads_equal_chunk_export': True, 'measured_vector_dimension': len(sample),
        'sample_vector_norm': norm, 'distance': 'cosine', 'source_page_semantics': 'RST unit, not PDF page',
        'model': MODEL, 'model_revision': REVISION, 'query_prefix': 'query: ',
        'document_prefix': 'passage: ', 'source': 'CPython documentation 3.12.10',
        'hashes': {'chunks': sha256(chunks_path), 'pages': sha256(day6 / 'data/normalized/pages.jsonl'),
                   'source_manifest': sha256(day6 / 'data/manifest.json'),
                   'day6_run_manifest': sha256(day6 / 'results/run_manifest.json'),
                   'day6_model_download_manifest': sha256(day6 / 'artifacts/model_download.json'),
                   'day6_config_freeze': sha256(day6 / 'artifacts/config_freeze.json')},
        'day6_selection': read_json(day6 / 'artifacts/selection.json')['selected_strategy'],
    }
    write_json(output / 'day6_manifest.json', manifest)
    return manifest
