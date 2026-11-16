"""Check restored local inputs against the frozen experiment without running test."""
import argparse
from pathlib import Path

from src.day07.__main__ import code_hashes, external_hashes, server_model_hash
from src.day07.common import now, read_json, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--day6-root', required=True, type=Path); p.add_argument('--model-path', required=True, type=Path)
    p.add_argument('--qdrant', required=True, type=Path); p.add_argument('--output', required=True, type=Path)
    p.add_argument('--server', default='http://127.0.0.1:8085'); p.add_argument('--model', default='qwen2.5-7b-local')
    args = p.parse_args()
    lock = read_json('artifacts/base/freeze.json')
    result = {'checked_at': now(),
              'code_benchmark_corpus_match': code_hashes(Path('configs/base.json'), Path('artifacts/base/chunks.jsonl'), Path('benchmarks/base')) == lock['hashes'],
              'day6_model_and_restored_qdrant_match': external_hashes(args.day6_root, args.model_path, args.qdrant) == lock['external_hashes'],
              'server_model_match': server_model_hash(args.server, args.model) == lock['model_sha256'],
              'test_rerun': False,
              'scope': 'Local restored archive and current machine only; not an independent clean-machine reproduction.'}
    write_json(args.output, result)
    print(result)
    if not all(result[k] for k in ('code_benchmark_corpus_match', 'day6_model_and_restored_qdrant_match', 'server_model_match')):
        raise SystemExit(1)


if __name__ == '__main__': main()
