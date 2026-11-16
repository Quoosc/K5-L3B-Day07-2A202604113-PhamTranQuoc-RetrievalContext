"""Run the experimental local vision agent; query input never contains gold."""
import argparse
import json
from pathlib import Path
import re

from src.day07.advanced_agent import run_advanced
from src.day07.advanced_retrieval import AdvancedRetriever
from src.day07.agent import ModelClient
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.__main__ import server_model_hash

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(pdf, chunks, benchmark, config, ocr=None):
    paths = [pdf, chunks, config, ROOT / 'artifacts/advanced/elements.jsonl',
             ROOT / 'artifacts/advanced/page_inventory.jsonl', ROOT / 'artifacts/advanced/pdf_manifest.json',
             ROOT / 'src/day07/advanced_agent.py', ROOT / 'src/day07/advanced_retrieval.py',
             ROOT / 'src/day07/advanced_eval.py', ROOT / 'src/day07/agent.py', ROOT / 'src/day07/retrieval.py',
             ROOT / 'src/day07/common.py', ROOT / 'src/day07/day6.py', ROOT / 'src/day07/context.py',
             ROOT / 'scripts/run_advanced.py', ROOT / 'scripts/ocr_pdf_regions.py', ROOT / 'requirements-ocr-lock.txt']
    if ocr: paths.append(ocr)
    paths += [benchmark / folder / f'{split}.jsonl' for folder in ('queries', 'gold') for split in ('dev', 'test')]
    return {str(p.resolve().relative_to(ROOT)).replace('\\','/'): sha256(p) for p in paths}


def external_hashes(day6, model_path, qdrant, projector):
    paths = {'day6_embeddings': day6 / 'src/embeddings.py',
             'qdrant_meta': qdrant / 'meta.json',
             'qdrant_collection': qdrant / 'collection/lab7_landsat_v5/storage.sqlite',
             'vision_projector': projector}
    for path in model_path.rglob('*'):
        if path.is_file():
            paths['embedding/' + path.relative_to(model_path).as_posix()] = path
    if not any(k.startswith('embedding/') for k in paths):
        raise ValueError('Embedding snapshot missing')
    return {k: sha256(v) for k, v in sorted(paths.items())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--split', required=True, choices=('dev', 'test')); p.add_argument('--run-id', required=True)
    p.add_argument('--day6-root', required=True, type=Path); p.add_argument('--model-path', required=True, type=Path)
    p.add_argument('--qdrant', required=True, type=Path); p.add_argument('--pdf', required=True, type=Path)
    p.add_argument('--chunks', type=Path, default=ROOT / 'artifacts/advanced/search_chunks.jsonl')
    p.add_argument('--benchmark', type=Path, default=ROOT / 'benchmarks/advanced')
    p.add_argument('--config', type=Path, default=ROOT / 'configs/advanced.json')
    p.add_argument('--server', default='http://127.0.0.1:8086'); p.add_argument('--model', default='qwen2.5-vl-3b-local')
    p.add_argument('--timeout', type=int, default=180); p.add_argument('--limit', type=int); p.add_argument('--lock', type=Path)
    p.add_argument('--projector', type=Path, help='Required to validate an advanced test freeze')
    p.add_argument('--ocr', type=Path, help='Optional unverified OCR output for all indexed regions')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or '..' in args.run_id:
        raise ValueError('run-id must be a simple name')
    if args.split == 'test':
        if args.limit or not args.lock or not args.projector:
            raise ValueError('Advanced test requires a freeze, projector and complete split')
        lock = read_json(args.lock)
        if lock['hashes'] != fingerprint(args.pdf, args.chunks, args.benchmark, args.config, args.ocr) or lock['model'] != args.model:
            raise ValueError('Advanced configuration, data or code changed after freeze')
        if lock['external_hashes'] != external_hashes(args.day6_root, args.model_path, args.qdrant, args.projector):
            raise ValueError('Advanced embedding, index or projector changed after freeze')
        if lock['model_sha256'] != server_model_hash(args.server, args.model):
            raise ValueError('Advanced server model differs from freeze')
    config = read_json(args.config)
    if config['max_open_regions'] != 2 or config['temperature'] != 0 or config['retry_count'] != 0:
        raise ValueError('This runner requires the declared fixed region, temperature and retry settings')
    if config.get('use_ocr') and not args.ocr:
        raise ValueError('This configuration requires OCR output')
    ocr = {row['evidence_id']: row for row in read_jsonl(args.ocr)} if args.ocr else None
    if ocr is not None and not args.limit:
        required = {e['evidence_id'] for e in read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')
                    if e['element_type'] in ('image', 'vector_page')}
        if required - set(ocr):
            raise ValueError('Full dev/test requires an OCR record for every indexed image/vector candidate')
    queries = read_jsonl(args.benchmark / 'queries' / f'{args.split}.jsonl')
    if any(q.get('split') != args.split for q in queries): raise ValueError('Query split mismatch')
    if args.limit:
        if args.limit < 1: raise ValueError('limit must be positive')
        queries = queries[:args.limit]
    directory = ROOT / 'artifacts/advanced/runs' / args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'manifest.json', {'started_at': now(), 'run_id': args.run_id,
               'split': args.split, 'model': args.model, 'config': config,
               'model_sha256': server_model_hash(args.server, args.model),
               'projector_sha256': sha256(args.projector) if args.projector else None,
               'query_sha256': sha256(args.benchmark / 'queries' / f'{args.split}.jsonl'),
               'pdf_sha256': sha256(args.pdf), 'lock_sha256': sha256(args.lock) if args.lock else None,
               'ocr_sha256': sha256(args.ocr) if args.ocr else None,
               'ocr_error_count': sum(row.get('status') != 'ok' for row in ocr.values()) if ocr else None,
               'code_sha256': {name: sha256(ROOT / name) for name in
                               ('src/day07/advanced_agent.py', 'src/day07/advanced_retrieval.py',
                                'src/day07/agent.py', 'scripts/run_advanced.py')},
               'note': 'Candidate search uses source text, captions and unverified OCR when supplied; no gold is supplied to the model.'})
    model = ModelClient(args.server, args.model, args.timeout)
    retriever = AdvancedRetriever(args.day6_root, args.model_path, args.qdrant, args.chunks)
    try:
        with (directory / 'traces.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            for n, q in enumerate(queries, 1):
                trace = run_advanced(q, retriever, model, args.pdf, ROOT / 'artifacts/advanced/elements.jsonl',
                                     read_json(ROOT / 'artifacts/advanced/pdf_manifest.json')['pdf_sha256'],
                                     config['candidate_k'], config['branch_pool'], config['crop_dpi'], ocr,
                                     config.get('schema_mode', False), config.get('include_table_text', False))
                trace.update({'split': args.split, 'run_id': args.run_id, 'timestamp': now()})
                stream.write(json.dumps(trace, ensure_ascii=False, allow_nan=False) + '\n'); stream.flush()
                print(f"{n}/{len(queries)} {q['id']} {trace['status']}", flush=True)
    finally:
        retriever.close()


if __name__ == '__main__': main()
