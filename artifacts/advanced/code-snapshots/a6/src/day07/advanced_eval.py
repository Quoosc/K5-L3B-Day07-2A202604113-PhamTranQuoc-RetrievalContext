"""Validate advanced source locators and score complete reviewed runs."""
from collections import Counter
import math


def validate(queries, gold, elements, split):
    if split not in ('dev', 'test'):
        raise ValueError('Invalid split')
    if not queries or len({q.get('id') for q in queries}) != len(queries):
        raise ValueError('Missing or duplicate query IDs')
    if len({g.get('id') for g in gold}) != len(gold) or {q['id'] for q in queries} != {g['id'] for g in gold}:
        raise ValueError('Gold/query ID mismatch')
    registry = {e['evidence_id']: e for e in elements}
    if len(registry) != len(elements):
        raise ValueError('Duplicate evidence ID')
    forbidden = {'gold', 'answerable', 'expected_answer', 'expected_behavior', 'primary_group',
                 'evidence_groups', 'absence_reason', 'fact_keys'}
    for q in queries:
        if q.get('split') != split or not q.get('question') or set(q) & forbidden:
            raise ValueError('Invalid query or gold leakage')
    counts = Counter()
    for g in gold:
        if g.get('split') != split or not isinstance(g.get('answerable'), bool):
            raise ValueError('Invalid gold split or answerability')
        group = g.get('primary_group'); counts[group] += 1
        if group == 'unanswerable':
            if g['answerable'] or not g.get('absence_reason') or not g.get('expected_behavior'):
                raise ValueError('Invalid absence case')
            continue
        if group not in ('table', 'image', 'chart', 'multi_hop', 'text') or not g['answerable'] or not g.get('expected_answer'):
            raise ValueError('Invalid answerable group')
        groups = g.get('evidence_groups')
        if not isinstance(groups, list) or not groups or (group == 'multi_hop' and len(groups) < 2):
            raise ValueError('Missing required evidence groups')
        ids = set()
        for alternatives in groups:
            if not isinstance(alternatives, list) or not alternatives:
                raise ValueError('Empty evidence group')
            for ev in alternatives:
                e = registry.get(ev.get('evidence_id'))
                if not e or ev.get('pdf_page') != e['pdf_page'] or ev.get('bbox') != e['bbox'] or ev.get('printed_label') != e['printed_label']:
                    raise ValueError('Evidence locator does not match registry')
                if not ev.get('locator') or not ev.get('source_value'):
                    raise ValueError('Evidence lacks a source locator or value')
                if ev.get('absolute_tolerance', 0) < 0:
                    raise ValueError('Tolerance cannot be negative')
                ids.add(ev['evidence_id'])
        if group == 'multi_hop' and len(ids) < 2:
            raise ValueError('Multi-hop requires at least two independent regions')
    minimum = {'dev': {'table': 1, 'image': 1, 'chart': 1, 'multi_hop': 1, 'text': 1, 'unanswerable': 3},
               'test': {'table': 6, 'image': 5, 'chart': 5, 'multi_hop': 4, 'text': 4, 'unanswerable': 6}}[split]
    if any(counts[k] < n for k, n in minimum.items()) or sum(counts.values()) < (18 if split == 'dev' else 30):
        raise ValueError('Advanced benchmark does not meet minimum quota')
    return {'split': split, 'total': len(queries), 'groups': dict(counts),
            'locator_status': 'structural match only; source and semantic audit still required',
            'absence_status': 'provisional; extracted text scan is not a full visual absence audit'}


def score(queries, gold, traces, reviews):
    gs = {g['id']: g for g in gold}; ts = {t['query_id']: t for t in traces}; rs = {r['query_id']: r for r in reviews}
    ids = {q['id'] for q in queries}
    if len(ts) != len(traces) or len(rs) != len(reviews) or set(rs) != ids or set(gs) != ids:
        raise ValueError('Review, trace or query IDs are duplicate or incomplete')
    if set(ts) - ids:
        raise ValueError('Trace contains an unexpected query ID')
    result = {'total': len(queries), 'passed': 0, 'errors_or_missing': 0, 'groups': {}}
    groups = {}
    for q in queries:
        qid = q['id']; g = gs[qid]; review = rs[qid]; trace = ts.get(qid)
        if type(review.get('pass')) is not bool or not review.get('reason') or not review.get('reviewer'):
            raise ValueError('Every verdict needs boolean pass, reason and reviewer')
        failed_system = not trace or trace.get('status') == 'error'
        if failed_system and review['pass']:
            raise ValueError('A missing/error trace cannot pass')
        if review['pass'] and g['answerable'] and trace.get('status') != 'answered':
            raise ValueError('An answerable abstention cannot pass')
        if review['pass'] and not g['answerable'] and trace.get('status') != 'abstain':
            raise ValueError('An unanswerable case must abstain to pass')
        result['errors_or_missing'] += failed_system
        result['passed'] += review['pass']
        group = groups.setdefault(g['primary_group'], {'n': 0, 'N': 0})
        group['n'] += review['pass']; group['N'] += 1
    result['groups'] = {k: {**v, 'rate': v['n']/v['N']} for k, v in groups.items()}
    result['rate'] = result['passed']/result['total'] if result['total'] else None
    result['required_passes'] = math.ceil(.9 * result['total'])
    result['meets_90_percent'] = result['passed'] >= result['required_passes']
    return result
