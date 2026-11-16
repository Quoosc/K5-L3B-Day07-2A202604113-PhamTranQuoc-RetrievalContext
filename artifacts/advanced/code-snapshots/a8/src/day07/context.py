"""Context packing with a stable citation registry and explicit decisions."""
from __future__ import annotations

from .retrieval import tokens


def pack(candidates: list[dict], question: str, budget: int, count_tokens,
         policy: str = 'rank') -> dict:
    if budget < 1 or policy not in ('rank', 'coverage'):
        raise ValueError('Invalid context budget or policy')
    candidates = list(candidates)
    if policy == 'coverage':
        query = set(tokens(question))
        candidates.sort(key=lambda c: (-len(query.intersection(tokens(c['text']))),
                                       c.get('rank', 0), c['id']))
    blocks, entries, decisions, seen_ids, seen_text = [], [], [], set(), set()
    for c in candidates:
        normalized = ' '.join(c['text'].split()).casefold()
        if c['id'] in seen_ids or (policy == 'coverage' and normalized in seen_text):
            decisions.append({'id': c['id'], 'decision': 'drop_duplicate'})
            continue
        seen_ids.add(c['id'])
        seen_text.add(normalized)
        alias = 'e' + str(len(entries) + 1)
        header = (f"[{alias}] {c['source_id']} | RST unit {c['page']} | "
                  f"offset {c['start_offset']}-{c['end_offset']} | {c['source']}")
        block = header + '\n' + c['text']
        trial = '\n\n'.join(blocks + [block])
        measured = count_tokens(trial)
        if measured > budget:
            decisions.append({'id': c['id'], 'decision': 'drop_budget', 'trial_tokens': measured})
            continue
        blocks.append(block)
        entries.append({'alias': alias, **c})
        decisions.append({'id': c['id'], 'decision': 'keep', 'alias': alias})
    content = '\n\n'.join(blocks)
    return {'text': content, 'entries': entries, 'decisions': decisions,
            'tokens': count_tokens(content), 'budget': budget, 'policy': policy}
