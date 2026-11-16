"""Benchmark validation and deterministic evidence matching; no semantic judging."""
from __future__ import annotations

from collections import Counter

from .day6 import adapt
from .retrieval import validate_scope


def validate(queries: list[dict], gold: list[dict], raw_chunks: list[dict], split: str,
             enforce_minimum: bool = True) -> dict:
    if split not in ('dev', 'test'):
        raise ValueError('Invalid split')
    if not queries or len({q.get('id') for q in queries}) != len(queries):
        raise ValueError('Missing queries or duplicate query IDs')
    if len({g.get('id') for g in gold}) != len(gold):
        raise ValueError('Duplicate gold IDs')
    if {q['id'] for q in queries} != {g['id'] for g in gold}:
        raise ValueError('Query and gold IDs differ')
    chunks = [adapt(c) for c in raw_chunks]
    forbidden = {'gold', 'answerable', 'expected_answer', 'evidence_groups',
                 'absence_reason', 'expected_behavior', 'primary_group'}
    for q in queries:
        if set(q) & forbidden:
            raise ValueError('Query file leaks a gold-only field')
        if q.get('split') != split or not isinstance(q.get('question'), str) or not q['question'].strip():
            raise ValueError(f"Invalid query {q.get('id')}")
        validate_scope(q.get('scope'))
    counts = Counter()
    for g in gold:
        if g.get('split') != split or not isinstance(g.get('answerable'), bool):
            raise ValueError(f"Invalid gold {g.get('id')}")
        counts['answerable' if g['answerable'] else 'unanswerable'] += 1
        if not g['answerable']:
            if not g.get('absence_reason') or not g.get('expected_behavior'):
                raise ValueError(f"Missing absence audit: {g['id']}")
            if g.get('evidence_groups'):
                raise ValueError('Unanswerable case cannot have answer evidence groups')
            continue
        groups = g.get('evidence_groups')
        if not g.get('expected_answer') or not isinstance(groups, list) or not groups:
            raise ValueError(f"Missing answer or groups: {g['id']}")
        for group in groups:
            if not isinstance(group, list) or not group:
                raise ValueError('Every AND group must contain at least one OR alternative')
            for ev in group:
                if not all(ev.get(k) is not None for k in ('source_id', 'page', 'quote')) or not ev['quote']:
                    raise ValueError('Incomplete evidence locator')
                if not any(matches(c, ev) for c in chunks):
                    raise ValueError(f"Evidence not found in corpus: {g['id']} {ev['source_id']}:{ev['page']}")
    if enforce_minimum:
        minima = (15, 2) if split == 'dev' else (5, 2)
        if counts['answerable'] < minima[0] or counts['unanswerable'] < minima[1]:
            raise ValueError(f'{split} does not meet minimum counts {minima}')
    return {'split': split, 'queries': len(queries), 'answerable': counts['answerable'],
            'unanswerable': counts['unanswerable'], 'evidence_validation': 'all alternatives resolved'}


def matches(chunk: dict, ev: dict) -> bool:
    return (chunk.get('source_id') == ev['source_id'] and chunk.get('page') == ev['page']
            and ev['quote'] in chunk.get('text', ''))


def group_hits(chunks: list[dict], groups: list[list[dict]]) -> list[bool]:
    return [any(matches(chunk, ev) for ev in alternatives for chunk in chunks) for alternatives in groups]


def fraction(n: int, total: int) -> dict:
    return {'n': n, 'N': total, 'rate': n / total if total else None}


def retrieval_metrics(queries: list[dict], gold: list[dict], traces: list[dict]) -> dict:
    by_gold = {g['id']: g for g in gold}
    by_trace = {t['query_id']: t for t in traces}
    if len(by_trace) != len(traces):
        raise ValueError('Duplicate trace query IDs')
    n = sum(1 for q in queries if by_gold[q['id']]['answerable'])
    hit1 = hit3 = all3 = context = errors = 0
    rows = []
    for q in queries:
        g = by_gold[q['id']]
        trace = by_trace.get(q['id'])
        if trace is None or trace.get('status') == 'error':
            errors += 1
        if not g['answerable']:
            continue
        ranking = (trace or {}).get('original_ranking', {}).get('results', [])
        packed = (trace or {}).get('context', {}).get('entries', [])
        h1 = any(group_hits(ranking[:1], g['evidence_groups']))
        h3 = any(group_hits(ranking[:3], g['evidence_groups']))
        a3 = all(group_hits(ranking[:3], g['evidence_groups']))
        ctx = all(group_hits(packed, g['evidence_groups']))
        hit1 += h1; hit3 += h3; all3 += a3; context += ctx
        rows.append({'query_id': q['id'], 'hit1': h1, 'hit3': h3, 'all_groups_hit3': a3,
                     'context_all_groups': ctx, 'missing_or_error': not trace or trace.get('status') == 'error'})
    return {'total_queries': len(queries), 'errors_or_missing': errors,
            'hit1': fraction(hit1, n), 'evidence_hit3': fraction(hit3, n),
            'all_groups_hit3': fraction(all3, n), 'context_evidence_rate': fraction(context, n),
            'cases': rows}
