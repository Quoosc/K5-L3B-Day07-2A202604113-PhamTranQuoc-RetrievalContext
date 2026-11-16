"""Freeze only after a complete source-reviewed dev run meets the readiness target."""
import argparse
import json
from pathlib import Path

from src.day07.__main__ import server_model_hash
from src.day07.advanced_eval import score
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from scripts.run_advanced import ROOT, external_hashes, fingerprint


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--traces', required=True, type=Path); p.add_argument('--reviews', required=True, type=Path)
    p.add_argument('--day6-root', required=True, type=Path); p.add_argument('--model-path', required=True, type=Path)
    p.add_argument('--qdrant', required=True, type=Path); p.add_argument('--projector', required=True, type=Path)
    p.add_argument('--pdf', required=True, type=Path); p.add_argument('--output', required=True, type=Path)
    p.add_argument('--chunks', type=Path, default=ROOT / 'artifacts/advanced/search_chunks.jsonl')
    p.add_argument('--ocr', type=Path, required=True)
    p.add_argument('--server', default='http://127.0.0.1:8086'); p.add_argument('--model', default='qwen2.5-vl-3b-local')
    p.add_argument('--rationale', required=True)
    args = p.parse_args()
    benchmark = ROOT / 'benchmarks/advanced'; chunks = args.chunks
    config = ROOT / 'configs/advanced.json'
    queries = read_jsonl(benchmark / 'queries/dev.jsonl'); gold = read_jsonl(benchmark / 'gold/dev.jsonl')
    report = score(queries, gold, read_jsonl(args.traces), read_jsonl(args.reviews))
    if report['total'] != 26 or report['passed'] < 24 or any(v['n'] == 0 for v in report['groups'].values()):
        raise ValueError('Dev readiness requires at least 24/26 and a nonzero pass in each group')
    lock = {'frozen_at': now(), 'model': args.model, 'model_sha256': server_model_hash(args.server, args.model),
            'config': read_json(config), 'dev_summary': report, 'selection_rationale': args.rationale,
            'dev_trace_sha256': sha256(args.traces), 'dev_review_sha256': sha256(args.reviews),
            'hashes': fingerprint(args.pdf, chunks, benchmark, config, args.ocr),
            'external_hashes': external_hashes(args.day6_root, args.model_path, args.qdrant, args.projector),
            'projector_attestation': 'Hash is recorded; confirm the server was started with this projector file.'}
    write_json(args.output, lock)
    print(json.dumps(lock, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
