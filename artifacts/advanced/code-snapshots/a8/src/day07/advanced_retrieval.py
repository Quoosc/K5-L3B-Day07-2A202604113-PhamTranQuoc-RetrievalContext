"""Candidate-level Landsat search. Visual meaning still requires a vision adapter and audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import uuid

from .common import now, read_jsonl, sha256, write_json, write_jsonl
from .day6 import MODEL, REVISION, load_module
from .retrieval import Lexical, rrf

COLLECTION = 'lab7_landsat_v5'


class AdvancedRetriever:
    """Search text, captions and optional OCR/descriptions; inspect the source region."""
    def __init__(self, day6_root: Path, model_path: Path, qdrant: Path, chunks: Path):
        from qdrant_client import QdrantClient
        module = load_module(day6_root / 'src/embeddings.py', 'day6_advanced_query_embed')
        self.embedder = module.LocalEmbedder(model_name=MODEL, revision=REVISION,
                                              model_path=str(model_path), device='cpu')
        self.client = QdrantClient(path=str(qdrant))
        self.rows = read_jsonl(chunks)
        if self.client.count(COLLECTION, exact=True).count != len(self.rows):
            self.client.close()
            raise ValueError('Advanced index does not match its searchable export')
        self.lexical = Lexical(self.rows)
        self.caption_regions = {}
        seen = set()
        for row in self.rows:
            if row['metadata']['element_type'] not in ('image', 'table_candidate') or row['evidence_id'] in seen:
                continue
            match = re.match(r'^(Table|Figure)\s+([A-Za-z0-9]+)[-.](\d+)', row['text'], re.I)
            if match:
                key = (match.group(1).casefold(), match.group(2).casefold(), match.group(3))
                self.caption_regions.setdefault(key, []).append(row)
                seen.add(row['evidence_id'])

    def close(self): self.client.close()

    def search(self, query: str, method: str = 'hybrid', top_k: int = 3, pool: int = 10,
               reference_text: str = ''):
        from qdrant_client import models
        if method not in ('dense', 'lexical', 'hybrid') or not query.strip() or top_k < 1:
            raise ValueError('Invalid search arguments')
        dense = []; lexical = []
        if method in ('dense', 'hybrid'):
            vector = self.embedder.embed_query(query)
            response = self.client.query_points(COLLECTION, query=vector, limit=len(self.rows),
                                                with_payload=True, search_params=models.SearchParams(exact=True))
            candidates = [{**dict(p.payload), 'score': float(p.score), 'method': 'dense'} for p in response.points]
            candidates.sort(key=lambda x: (-x['score'], x['id']))
            dense = [{**row, 'rank': i} for i, row in enumerate(candidates[:pool if method == 'hybrid' else top_k], 1)]
        if method in ('lexical', 'hybrid'):
            lexical = self.lexical.search(query, pool if method == 'hybrid' else top_k, {})
        def annotate(row):
            if row['metadata']['element_type'] in ('image', 'vector_page'):
                return {**row, 'warning': 'Visual candidates may use captions, page text, unverified OCR or AI-observed descriptions; inspect the original region.'}
            return row
        dense = [annotate(row) for row in dense]
        lexical = [annotate(row) for row in lexical]
        raw = dense if method == 'dense' else lexical if method == 'lexical' else rrf(dense, lexical, top_k)
        # Explicit table/figure labels come from the user question, never from gold.
        references = re.findall(r'\b(Table|Figure)\s+([A-Za-z0-9]+)[-.](\d+)', reference_text or query, re.I)
        routed = []; seen = set()
        for kind, first, second in references:
            for row in self.caption_regions.get((kind.casefold(), first.casefold(), second), []):
                if row['evidence_id'] not in seen:
                    routed.append(annotate({**row, 'score': 0.0, 'method': 'caption_reference', 'route': f'{kind} {first}-{second}'}))
                    seen.add(row['evidence_id'])
        combined = routed + [row for row in raw if row['evidence_id'] not in seen]
        rows = [{**row, 'rank': i} for i, row in enumerate(combined[:top_k], 1)]
        return {'query': query, 'method': method, 'results': rows,
                'branches': {'dense': dense, 'lexical': lexical} if method == 'hybrid' else {},
                'reference_routing': [r['evidence_id'] for r in routed], 'raw_ranking': raw,
                'limitations': 'Visual search may use captions, page text, unverified OCR or AI-observed descriptions; visual facts require separate source review.'}


def snippets(text, tokenizer, size=350, overlap=32):
    offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)['offset_mapping']
    if not offsets:
        return []
    results = []
    start = 0
    while start < len(offsets):
        end = min(start + size, len(offsets))
        a, b = offsets[start][0], offsets[end - 1][1]
        results.append(text[a:b])
        if end == len(offsets):
            break
        start = end - overlap
    return results


def nearby_caption(element, page_elements):
    """Associate a region with a nearby actual caption, never benchmark gold."""
    candidates = []
    x0, y0, x1, y1 = element['bbox']
    for other in page_elements:
        if other['element_type'] != 'text': continue
        text = other['content'].strip()
        if not re.match(r'^(?:Table|Figure)\s+[A-Za-z0-9]+[-.]\d+', text, re.I): continue
        a, b, c, d = other['bbox']
        if min(x1, c) <= max(x0, a): continue
        gap = max(0, b-y1, y0-d)
        if gap <= 80:
            candidates.append((0 if b >= y1 else 1, gap, text))
    return min(candidates)[2] if candidates else ''


def build(args):
    from qdrant_client import QdrantClient, models
    embedmod = load_module(args.day6_root / 'src/embeddings.py', 'day6_advanced_embed')
    embedder = embedmod.LocalEmbedder(model_name=MODEL, revision=REVISION,
                                      model_path=str(args.model_path), device='cpu', batch_size=16)
    elements = read_jsonl(args.elements)
    ocr = {row['evidence_id']: row for row in read_jsonl(args.ocr)} if args.ocr else {}
    by_page = {}
    for e in elements: by_page.setdefault(e['pdf_page'], []).append(e)
    rows = []
    for e in elements:
        content = e['content'].strip()
        caption = nearby_caption(e, by_page[e['pdf_page']]) if e['element_type'] in ('image', 'table_candidate') else ''
        if caption:
            content = caption + '\n' + content
        ocr_row = ocr.get(e['evidence_id'])
        if ocr_row and ocr_row.get('status') == 'ok':
            content += '\nUnverified OCR: ' + ' | '.join(line['text'] for line in ocr_row.get('lines', []))
        # Any appended OCR or visual descriptions remain explicitly unverified.
        if not content:
            continue
        for i, part in enumerate(snippets(content, embedder.tokenizer), 1):
            rows.append({'id': f"{e['evidence_id']}#part-{i:03d}", 'evidence_id': e['evidence_id'],
                         'source_id': e['doc_id'], 'source': e['source'], 'page': e['pdf_page'],
                         'printed_label': e['printed_label'], 'bbox': e['bbox'], 'text': part,
                         'metadata': {'element_type': e['element_type'], 'section': e['section']},
                         'warning': ('Visual candidates may use captions, page text, unverified OCR or AI-observed descriptions; inspect the original region.'
                                     if e['element_type'] in ('image', 'vector_page') else e.get('warning'))})
    snippets_path = args.chunks_output or args.output.with_name('search_chunks.jsonl')
    if args.qdrant.exists() or args.output.exists() or snippets_path.exists():
        raise FileExistsError('Refusing to overwrite the advanced index or its manifest')
    args.qdrant.parent.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(args.qdrant))
    try:
        client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
        for start in range(0, len(rows), 64):
            batch = rows[start:start + 64]
            vectors = embedder.embed_documents([row['text'] for row in batch])
            points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, row['id'])),
                                         vector=vector, payload=row)
                      for row, vector in zip(batch, vectors)]
            client.upsert(COLLECTION, points=points, wait=True)
            print(f'Indexed {min(start + len(batch), len(rows))}/{len(rows)} snippets', flush=True)
        count = client.count(COLLECTION, exact=True).count
        if count != len(rows):
            raise RuntimeError('Advanced index count mismatch')
    finally:
        client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(snippets_path, rows)
    manifest = {'created_at': now(), 'collection': COLLECTION, 'snippets': len(rows), 'dimensions': 384,
                'model': MODEL, 'revision': REVISION, 'source_elements_sha256': sha256(args.elements),
                'search_chunks_sha256': sha256(snippets_path), 'api_cost_usd': 0.0,
                'caption_policy': 'Nearest page caption below/near an image or table region; not derived from questions.',
                'ocr_sha256': sha256(args.ocr) if args.ocr else None,
                'status': 'PARTIAL: text/caption' + (' and unverified OCR' if args.ocr else ' only') + '; visual semantics not fully audited',
                'limitations': ['No visual embeddings or fully independently verified descriptions.',
                                'Table candidates retain automatic extraction errors; verify source.',
                                'Empty caption-only regions are not searchable by text.']}
    write_json(args.output, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6-root', type=Path, required=True); p.add_argument('--model-path', type=Path, required=True)
    p.add_argument('--elements', type=Path, required=True); p.add_argument('--qdrant', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--chunks-output', type=Path)
    p.add_argument('--ocr', type=Path)
    build(p.parse_args())


if __name__ == '__main__': main()
