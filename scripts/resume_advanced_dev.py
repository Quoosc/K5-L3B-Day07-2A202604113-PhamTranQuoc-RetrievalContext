"""Continue an interrupted development run without retrying or replacing any case.

The continuation is written to a separate directory. It never reads gold and is
limited to dev, so an interrupted evaluation cannot silently become a new test.
"""
import argparse
import json
from pathlib import Path

from scripts.run_advanced import ROOT
from src.day07.__main__ import server_model_hash
from src.day07.advanced_agent import run_advanced
from src.day07.advanced_retrieval import AdvancedRetriever
from src.day07.agent import ModelClient
from src.day07.common import now, read_json, read_jsonl, sha256, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--original', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--day6-root', required=True, type=Path)
    p.add_argument('--model-path', required=True, type=Path)
    p.add_argument('--qdrant', required=True, type=Path)
    p.add_argument('--chunks', required=True, type=Path)
    p.add_argument('--index-manifest', required=True, type=Path)
    p.add_argument('--pdf', required=True, type=Path)
    p.add_argument('--ocr', required=True, type=Path)
    p.add_argument('--projector', required=True, type=Path)
    p.add_argument('--server', default='http://127.0.0.1:8086')
    p.add_argument('--timeout', type=int, default=180)
    args = p.parse_args()

    manifest = read_json(args.original / 'manifest.json')
    if manifest['split'] != 'dev':
        raise ValueError('Only an interrupted development run may be continued')
    queries_path = ROOT / 'benchmarks/advanced/queries/dev.jsonl'
    queries = read_jsonl(queries_path)
    previous = read_jsonl(args.original / 'traces.jsonl')
    if not 0 < len(previous) < len(queries):
        raise ValueError('Original run must be a nonempty, incomplete development run')
    if [t['query_id'] for t in previous] != [q['id'] for q in queries[:len(previous)]]:
        raise ValueError('Original traces are not a prefix of the development queries')
    checks = {
        'query_sha256': sha256(queries_path), 'pdf_sha256': sha256(args.pdf),
        'ocr_sha256': sha256(args.ocr), 'projector_sha256': sha256(args.projector),
        'model_sha256': server_model_hash(args.server, manifest['model']),
    }
    if any(manifest[key] != value for key, value in checks.items()):
        raise ValueError('A required input or the serving model changed since the original run')
    if read_json(ROOT / 'configs/advanced.json') != manifest['config']:
        raise ValueError('Configuration changed since the original run')
    if any(sha256(ROOT / name) != value for name, value in manifest['code_sha256'].items()):
        raise ValueError('A recorded code file changed since the original run')
    index = read_json(args.index_manifest)
    if index['search_chunks_sha256'] != sha256(args.chunks) or index['ocr_sha256'] != checks['ocr_sha256']:
        raise ValueError('Search chunks or OCR do not match the index manifest')
    ocr = {row['evidence_id']: row for row in read_jsonl(args.ocr)}
    required = {e['evidence_id'] for e in read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')
                if e['element_type'] in ('image', 'vector_page')}
    if required - set(ocr):
        raise ValueError('Missing OCR records')

    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / 'manifest.json', {
        'started_at': now(), 'original': str(args.original), 'original_trace_sha256': sha256(args.original / 'traces.jsonl'),
        'index_manifest_sha256': sha256(args.index_manifest), 'search_chunks_sha256': sha256(args.chunks),
        'qdrant_collection_sha256': sha256(args.qdrant / 'collection/lab7_landsat_v5/storage.sqlite'),
        'continuation_code_sha256': sha256(Path(__file__)), 'input_checks': checks,
        'original_count': len(previous), 'total_count': len(queries),
        'note': 'Only the missing suffix is run; original errors and earlier answers are retained without retry.',
    })
    cfg = manifest['config']
    model = ModelClient(args.server, manifest['model'], args.timeout)
    retriever = AdvancedRetriever(args.day6_root, args.model_path, args.qdrant, args.chunks)
    try:
        with (args.output / 'traces.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            for n, q in enumerate(queries[len(previous):], len(previous) + 1):
                trace = run_advanced(q, retriever, model, args.pdf, ROOT / 'artifacts/advanced/elements.jsonl',
                                     checks['pdf_sha256'], cfg['candidate_k'], cfg['branch_pool'], cfg['crop_dpi'],
                                     ocr, cfg['schema_mode'], cfg['include_table_text'])
                trace.update({'split': 'dev', 'run_id': manifest['run_id'], 'timestamp': now(), 'continuation': True})
                stream.write(json.dumps(trace, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                print(f"{n}/{len(queries)} {q['id']} {trace['status']}", flush=True)
    finally:
        retriever.close()


if __name__ == '__main__':
    main()
