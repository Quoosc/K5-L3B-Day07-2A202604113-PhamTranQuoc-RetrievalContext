"""Create the fixed Day 7 base split before experiments; never used by runtime."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.day07.common import now, read_jsonl, sha256, write_json, write_jsonl
from src.day07.evaluation import validate

TEST = [
    ('b-test-01', 'In the documented example, what key order does json.dumps produce for {"c": 0, "b": 0, "a": 0} when sort_keys=True?',
     'The JSON keys are ordered a, b, c: {"a": 0, "b": 0, "c": 0}.', 'library-json', 1,
     '>>> print(json.dumps({"c": 0, "b": 0, "a": 0}, sort_keys=True))\n    {"a": 0, "b": 0, "c": 0}'),
    ('b-test-02', 'For PureWindowsPath, which of c:/a/b and /a/b is absolute, and what is the documented condition?',
     'c:/a/b is absolute, /a/b is not; a path needs a root and, where the flavour allows it, a drive.', 'library-pathlib', 4,
     "Return whether the path is absolute or not.  A path is considered absolute\n   if it has both a root and (if the flavour allows) a drive::\n\n      >>> PurePosixPath('/a/b').is_absolute()\n      True\n      >>> PurePosixPath('a/b').is_absolute()\n      False\n\n      >>> PureWindowsPath('c:/a/b').is_absolute()\n      True\n      >>> PureWindowsPath('/a/b').is_absolute()\n      False"),
    ('b-test-03', 'What does IOBase.flush() do on read-only and non-blocking streams?',
     'It does nothing on read-only and non-blocking streams.', 'library-io', 4,
     'Flush the write buffers of the stream if applicable.  This does nothing\n      for read-only and non-blocking streams.'),
    ('b-test-04', 'What does list.index(x) return, and what happens when no item equals x?',
     'It returns the zero-based index of the first equal item and raises ValueError if none exists.', 'tutorial-datastructures', 1,
     'Return zero-based index in the list of the first item whose value is equal to *x*.\n   Raises a ValueError if there is no such item.'),
    ('b-test-05', 'Which input types does json.loads accept, and which encodings are documented for byte input?',
     'str, bytes or bytearray; the input encoding should be UTF-8, UTF-16 or UTF-32.', 'library-json', 4,
     'deserialize *s* (a str, bytes or bytearray\n   instance containing a JSON document) to a Python object using this\n   conversion table.\n\n   Version changed: 3.6\n\n      *s* can now be of type bytes or bytearray. The\n      input encoding should be UTF-8, UTF-16 or UTF-32.')
]

ABSENCES = [
    ('b-dev-m01', 'dev', 'According to these Python docs, what is the configured timeout of the fictional Acme-Lab07 JSON service?', 'Acme-Lab07', ['acme-lab07', 'acme lab07']),
    ('b-dev-m02', 'dev', 'Which office city maintains the custom Northstar-Pathlib extension described in these documents?', 'Northstar-Pathlib', ['northstar-pathlib', 'northstar pathlib']),
    ('b-dev-m03', 'dev', 'What benchmark latency in milliseconds does this documentation report for json.loads on the fictional Orion-Lab-X7 machine?', 'Orion-Lab-X7', ['orion-lab-x7', 'orion lab x7']),
    ('b-test-m01', 'test', 'On what date did the fictional Sapphire-Ledger project migrate its file paths to pathlib, according to these documents?', 'Sapphire-Ledger', ['sapphire-ledger', 'sapphire ledger']),
    ('b-test-m02', 'test', 'Which API endpoint receives the fictional Lakewood-Observatory 2027 data after json.loads, according to these documents?', 'Lakewood-Observatory', ['lakewood-observatory', 'lakewood observatory']),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--day6-root', required=True, type=Path)
    parser.add_argument('--out', default='benchmarks/base', type=Path)
    args = parser.parse_args()
    chunks = read_jsonl(args.day6_root / 'results/chunks/B.jsonl')
    old = [q for q in read_jsonl(args.day6_root / 'benchmark/questions.jsonl') if q['split'] == 'dev']
    queries = {'dev': [], 'test': []}; gold = {'dev': [], 'test': []}
    for q in old:
        qid = 'b-dev-' + q['id']
        queries['dev'].append({'id': qid, 'split': 'dev', 'question': q['question'], 'scope': {}})
        raw = [{'source_id': q['gold_source_id'], 'page': q['gold_page'], 'quote': q['evidence_quote']}]
        raw += [{'source_id': e['source_id'], 'page': e['page'], 'quote': e['evidence_quote']}
                for e in q.get('alternatives', [])]
        gold['dev'].append({'id': qid, 'split': 'dev', 'answerable': True,
                            'expected_answer': q['expected_answer'], 'evidence_groups': [raw],
                            'provenance': f"Day 6 dev {q['id']}; alternatives retained; scope removed",
                            'review_reason': 'Exact quote/source/RST unit checked against B chunks; semantic review remains AI-assisted.'})
    for qid, question, answer, source, page, quote in TEST:
        queries['test'].append({'id': qid, 'split': 'test', 'question': question, 'scope': {}})
        gold['test'].append({'id': qid, 'split': 'test', 'answerable': True,
                             'expected_answer': answer, 'evidence_groups': [[{'source_id': source, 'page': page, 'quote': quote}]],
                             'provenance': 'New Day 7 question based on CPython 3.12.10 B corpus',
                             'review_reason': 'Exact source, unit and quote checked by validator; AI-authored and AI-reviewed.'})
    text = '\n'.join(c['text'] for c in chunks).casefold()
    for qid, split, question, entity, terms in ABSENCES:
        found = [term for term in terms if term.casefold() in text]
        if found:
            raise ValueError(f'{qid}: purportedly absent entity found: {found}')
        queries[split].append({'id': qid, 'split': split, 'question': question, 'scope': {}})
        gold[split].append({'id': qid, 'split': split, 'answerable': False,
                            'expected_behavior': 'search_and_abstain',
                            'absence_reason': f"The fictional entity {entity} and its variants {terms} do not occur in the complete 156-chunk snapshot; no project-specific facts can be inferred from generic Python documentation.",
                            'review_reason': 'Full corpus exact-name/variant scan; AI-authored and AI-reviewed.'})
    stats = {}
    for split in ('dev', 'test'):
        stats[split] = validate(queries[split], gold[split], chunks, split)
        write_jsonl(args.out / 'queries' / f'{split}.jsonl', queries[split])
        write_jsonl(args.out / 'gold' / f'{split}.jsonl', gold[split])
    normalized = lambda q: ' '.join(q['question'].casefold().split())
    if set(map(normalized, queries['dev'])) & set(map(normalized, queries['test'])):
        raise ValueError('Exact duplicate across splits')
    files = [args.out / category / f'{split}.jsonl' for category in ('queries', 'gold') for split in ('dev', 'test')]
    write_json(args.out / 'manifest.json', {'created_at': now(), 'author_reviewer': 'Codex (AI-assisted; human review not claimed)',
               'source': 'CPython 3.12.10 Day 6 snapshot B', 'stats': stats,
               'split_overlap': 'No exact duplicate question; Day 7 test facts manually chosen distinct from Day 6 dev/test facts.',
               'sha256': {str(p.relative_to(args.out)).replace('\\', '/'): sha256(p) for p in files}})
    print(stats)


if __name__ == '__main__':
    main()
