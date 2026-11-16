"""Reproducible CLI: runtime receives queries only, evaluation receives gold separately."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import statistics
import time
import urllib.request

from .agent import ModelClient, run_agent
from .common import now, read_json, read_jsonl, sha256, write_json
from .day6 import snapshot
from .evaluation import retrieval_metrics, validate
from .retrieval import Retriever

ROOT = Path(__file__).resolve().parents[2]


def configurations(path: Path) -> dict:
    return {c['id']: c for c in read_json(path)['configurations']}


def code_hashes(config_path: Path, chunks_path: Path, benchmark: Path) -> dict:
    base_modules = ('__init__.py', '__main__.py', 'common.py', 'day6.py', 'retrieval.py',
                    'context.py', 'agent.py', 'evaluation.py')
    paths = [ROOT / 'src/day07' / name for name in base_modules] + [config_path, chunks_path]
    paths += [benchmark / folder / f'{split}.jsonl' for folder in ('queries', 'gold') for split in ('dev', 'test')]
    return {str(p.resolve().relative_to(ROOT)).replace('\\', '/'): sha256(p) for p in paths}


def external_hashes(day6_root: Path, model_path: Path, qdrant: Path) -> dict:
    paths = {'day6/src/embeddings.py': day6_root / 'src/embeddings.py',
             'day6/src/store.py': day6_root / 'src/store.py',
             'qdrant/meta.json': qdrant / 'meta.json'}
    for path in sorted(model_path.rglob('*')):
        if path.is_file():
            paths['embedding/' + str(path.relative_to(model_path)).replace('\\', '/')] = path
    for path in sorted((qdrant / 'collection/lab6_B').rglob('*')):
        if path.is_file() and path.name != '.lock':
            paths['qdrant/lab6_B/' + str(path.relative_to(qdrant / 'collection/lab6_B')).replace('\\', '/')] = path
    if not any(k.startswith('embedding/') for k in paths) or not any(k.startswith('qdrant/lab6_B/') for k in paths):
        raise ValueError('Embedding snapshot or Qdrant collection files missing')
    return {name: sha256(path) for name, path in paths.items()}


def server_model_hash(server: str, model: str) -> str:
    # ModelClient rejects non-loopback URLs so this does not disclose a local path remotely.
    ModelClient(server, model)
    with urllib.request.urlopen(server.rstrip('/') + '/props', timeout=10) as response:
        props = json.load(response)
    if props.get('model_alias') != model:
        raise ValueError('The server reports a different model alias')
    return sha256(Path(props['model_path']))


def check_lock(args, config_ids):
    if not args.lock:
        raise ValueError('A freeze lock is required before running test')
    lock = read_json(args.lock)
    if lock['hashes'] != code_hashes(args.configs, args.chunks, args.benchmark):
        raise ValueError('Code, benchmark, config or corpus changed after freeze')
    if set(config_ids) - {lock['baseline'], lock['chosen']}:
        raise ValueError('Test may run only the frozen baseline and chosen configuration')
    if args.model != lock['model']:
        raise ValueError('Model differs from frozen model')
    if lock['external_hashes'] != external_hashes(args.day6_root, args.model_path, args.qdrant):
        raise ValueError('Day 6 code, embedding snapshot or Qdrant collection changed after freeze')
    if server_model_hash(args.server, args.model) != lock['model_sha256']:
        raise ValueError('The actual server model does not match the frozen GGUF hash')


def command_run(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or '..' in args.run_id:
        raise ValueError('run-id must be a simple name')
    config_map = configurations(args.configs)
    selected = args.config.split(',')
    if not selected or any(c not in config_map for c in selected) or len(set(selected)) != len(selected):
        raise ValueError('Invalid or duplicate configuration ID')
    if args.split == 'test':
        if args.limit:
            raise ValueError('Test must include the entire locked split')
        check_lock(args, selected)
    queries = read_jsonl(args.benchmark / 'queries' / f'{args.split}.jsonl')
    if any(q.get('split') != args.split for q in queries):
        raise ValueError('Incorrect split in query file')
    if args.limit:
        queries = queries[:args.limit]
    output = args.output / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    model = ModelClient(args.server, args.model, timeout=args.timeout)
    started = time.perf_counter()
    retriever = Retriever(args.day6_root, args.qdrant, args.model_path, args.chunks)
    startup_ms = (time.perf_counter() - started) * 1000
    meta = {'run_id': args.run_id, 'started_at': now(), 'split': args.split, 'configs': selected,
            'model': args.model, 'server': args.server, 'mode': 'local', 'api_cost_usd': 0.0,
            'query_file_sha256': sha256(args.benchmark / 'queries' / f'{args.split}.jsonl'),
            'config_sha256': sha256(args.configs), 'lock_sha256': sha256(args.lock) if args.lock else None,
            'startup_ms': startup_ms, 'retry_policy': 'zero retries', 'case_count': len(queries)}
    write_json(output / 'manifest.json', meta)
    try:
        for config_id in selected:
            config = config_map[config_id]
            with (output / f'{config_id}.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
                for index, q in enumerate(queries, 1):
                    try:
                        ranking = retriever.search(q['question'], config['method'], top_k=3,
                                                   scope=q.get('scope'), pool=config.get('pool', 10))
                        trace = run_agent(q, retriever, model, config)
                        trace['original_ranking'] = ranking
                    except Exception as exc:
                        trace = {'query_id': q['id'], 'question': q['question'], 'config': config_id,
                                 'status': 'error', 'error': f'{type(exc).__name__}: {exc}',
                                 'stop_reason': 'retrieval_or_runtime_error', 'events': [], 'citations': []}
                    trace.update({'run_id': args.run_id, 'split': args.split, 'timestamp': now()})
                    stream.write(json.dumps(trace, ensure_ascii=False, allow_nan=False) + '\n')
                    stream.flush()
                    print(f"{config_id} {index}/{len(queries)} {q['id']}: {trace['status']}", flush=True)
    finally:
        retriever.close()


def command_score(args):
    queries = read_jsonl(args.benchmark / 'queries' / f'{args.split}.jsonl')
    gold = read_jsonl(args.benchmark / 'gold' / f'{args.split}.jsonl')
    traces = read_jsonl(args.traces)
    result = retrieval_metrics(queries, gold, traces)
    elapsed = sorted(t['elapsed_ms'] for t in traces if 'elapsed_ms' in t)
    result['runtime'] = {'median_ms': statistics.median(elapsed) if elapsed else None,
                         'p95_ms_nearest_rank': elapsed[max(0, (95 * len(elapsed) + 99) // 100 - 1)] if elapsed else None,
                         'api_cost_usd': sum(t.get('api_cost_usd', 0) for t in traces),
                         'prompt_tokens': sum(t.get('usage', {}).get('prompt_tokens', 0) for t in traces),
                         'completion_tokens': sum(t.get('usage', {}).get('completion_tokens', 0) for t in traces)}
    write_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, ensure_ascii=False, indent=2))


def command_freeze(args):
    config_map = configurations(args.configs)
    if args.chosen not in config_map or args.baseline not in config_map:
        raise ValueError('Unknown configuration')
    review = read_json(args.dev_review)
    if not review.get('selection_rationale') or review.get('chosen') != args.chosen:
        raise ValueError('Dev review must justify and name the chosen configuration')
    if not review.get('reviewer') or not review.get('per_config'):
        raise ValueError('Dev review must include reviewer and per-configuration results')
    if set(review['per_config']) != set(config_map):
        raise ValueError('Dev review must cover every declared configuration')
    queries = read_jsonl(args.benchmark / 'queries/dev.jsonl')
    gold = {g['id']: g for g in read_jsonl(args.benchmark / 'gold/dev.jsonl')}
    expected = {q['id'] for q in queries}
    for config, data in review['per_config'].items():
        labels = data.get('labels', [])
        if len(labels) != len(expected) or {r.get('query_id') for r in labels} != expected:
            raise ValueError(f'{config}: dev review has missing or duplicate cases')
        selection_score = 0
        for row in labels:
            case = gold[row['query_id']]
            if not row.get('reason'):
                raise ValueError(f"{config}: review reason missing for {row['query_id']}")
            if case['answerable']:
                grade = row.get('answer_grade')
                if type(grade) is not int or grade not in (0, 1, 2):
                    raise ValueError(f"{config}: invalid grade for {row['query_id']}")
                if row['status'] in ('error', 'abstain') and grade != 0:
                    raise ValueError('An error or false abstention must count as zero')
                selection_score += grade == 2
            else:
                correct = row.get('abstention_correct')
                if type(correct) is not bool or (correct and row['status'] != 'abstain'):
                    raise ValueError('Invalid abstention review')
                selection_score += correct
        if selection_score != data['selection_score']:
            raise ValueError(f'{config}: selection score does not agree with labels')
    def ordering(item):
        name, data = item
        return (-data['selection_score'], -data['context_rate'], -data['hit3'], -data['hit1'],
                data['p95_ms'], data['api_cost_usd'], name)
    ranking = [name for name, _ in sorted(review['per_config'].items(), key=ordering)]
    if ranking[0] != args.chosen or ranking != review.get('ranking'):
        raise ValueError('Chosen configuration does not follow the declared dev selection rule')
    lock = {'frozen_at': now(), 'baseline': args.baseline, 'chosen': args.chosen,
            'model': args.model, 'model_sha256': server_model_hash(args.server, args.model),
            'selection_policy': read_json(args.configs)['selection_policy'],
            'dev_review_sha256': sha256(args.dev_review),
            'hashes': code_hashes(args.configs, args.chunks, args.benchmark),
            'external_hashes': external_hashes(args.day6_root, args.model_path, args.qdrant),
            'notes': 'Frozen before test; the model server and backend must match the recorded identity.'}
    write_json(args.output, lock)
    print(json.dumps(lock, ensure_ascii=False, indent=2))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('snapshot')
    s.add_argument('--day6-root', type=Path, required=True); s.add_argument('--qdrant-copy', type=Path, required=True)
    s.add_argument('--output', type=Path, default=ROOT / 'artifacts/base')
    s = sub.add_parser('validate')
    s.add_argument('--benchmark', type=Path, default=ROOT / 'benchmarks/base')
    s.add_argument('--chunks', type=Path, default=ROOT / 'artifacts/base/chunks.jsonl')
    s.add_argument('--split', choices=('dev', 'test'), required=True)
    s = sub.add_parser('run')
    s.add_argument('--benchmark', type=Path, default=ROOT / 'benchmarks/base')
    s.add_argument('--chunks', type=Path, default=ROOT / 'artifacts/base/chunks.jsonl')
    s.add_argument('--configs', type=Path, default=ROOT / 'configs/base.json')
    s.add_argument('--day6-root', type=Path, required=True); s.add_argument('--qdrant', type=Path, required=True)
    s.add_argument('--model-path', type=Path, required=True)
    s.add_argument('--server', default='http://127.0.0.1:8085'); s.add_argument('--model', default='qwen2.5-7b-local')
    s.add_argument('--timeout', type=int, default=120); s.add_argument('--config', required=True)
    s.add_argument('--split', choices=('dev', 'test'), required=True); s.add_argument('--run-id', required=True)
    s.add_argument('--output', type=Path, default=ROOT / 'artifacts/base/runs')
    s.add_argument('--lock', type=Path); s.add_argument('--limit', type=int)
    s = sub.add_parser('score')
    s.add_argument('--benchmark', type=Path, default=ROOT / 'benchmarks/base')
    s.add_argument('--split', choices=('dev', 'test'), required=True); s.add_argument('--traces', type=Path, required=True)
    s.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('freeze')
    s.add_argument('--benchmark', type=Path, default=ROOT / 'benchmarks/base')
    s.add_argument('--chunks', type=Path, default=ROOT / 'artifacts/base/chunks.jsonl')
    s.add_argument('--configs', type=Path, default=ROOT / 'configs/base.json')
    s.add_argument('--dev-review', type=Path, required=True); s.add_argument('--chosen', required=True)
    s.add_argument('--baseline', default='D0'); s.add_argument('--model', default='qwen2.5-7b-local')
    s.add_argument('--server', default='http://127.0.0.1:8085')
    s.add_argument('--day6-root', type=Path, required=True); s.add_argument('--model-path', type=Path, required=True)
    s.add_argument('--qdrant', type=Path, required=True); s.add_argument('--output', type=Path, required=True)
    return p


def main():
    args = parser().parse_args()
    if args.command == 'snapshot':
        print(json.dumps(snapshot(args.day6_root, args.qdrant_copy, args.output), ensure_ascii=False, indent=2))
    elif args.command == 'validate':
        print(json.dumps(validate(read_jsonl(args.benchmark / 'queries' / f'{args.split}.jsonl'),
                                  read_jsonl(args.benchmark / 'gold' / f'{args.split}.jsonl'),
                                  read_jsonl(args.chunks), args.split), ensure_ascii=False, indent=2))
    elif args.command == 'run': command_run(args)
    elif args.command == 'score': command_score(args)
    elif args.command == 'freeze': command_freeze(args)


if __name__ == '__main__':
    main()
