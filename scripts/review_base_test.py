"""Record Codex's source-by-source review of the already frozen test run."""
from collections import Counter
from pathlib import Path

from src.day07.common import now, read_jsonl, write_json, write_jsonl
from src.day07.evaluation import group_hits

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'artifacts/base/runs/base-test-20261115-v1'

# Citation annotations reflect reading the cited chunks, not merely checking IDs.
AUDIT = {
    'D0': {
        'b-test-01': (0, 'Model returned an incomplete JSON answer without a citation list; counted as an error.', {}),
        'b-test-02': (2, 'Correct paths and root/drive condition; e1 supports the claim.', {'e1': True, 'e3': False}),
        'b-test-03': (2, 'The cited flush documentation states the same behavior.', {'e1': True}),
        'b-test-04': (2, 'The cited list.index documentation supports both the index and ValueError.', {'e1': True}),
        'b-test-05': (2, 'e1 supports the types and encodings; the extra example e3 does not support all of that claim.', {'e1': True, 'e3': False}),
        'b-test-m01': (True, 'Explicitly declines to provide an unsupported date.', {}),
        'b-test-m02': (True, 'Explicitly declines to invent an endpoint; individual passages cannot establish corpus-wide absence.', {'e1': False, 'e2': False, 'e3': False}),
    },
    'H0': {
        'b-test-01': (0, 'Model returned an incomplete JSON answer without a citation list; counted as an error.', {}),
        'b-test-02': (2, 'Correct paths and root/drive condition; e1 directly supports the claim.', {'e1': True, 'e3': False}),
        'b-test-03': (2, 'The cited flush documentation states the same behavior.', {'e2': True}),
        'b-test-04': (0, 'The answer is factually correct, but e1 describes list.remove/pop rather than list.index; the actual index evidence was not cited.', {'e1': False}),
        'b-test-05': (2, 'e1 supports the types and encodings; e2 is an example that does not support all of that claim.', {'e1': True, 'e2': False}),
        'b-test-m01': (True, 'Explicitly declines to provide an unsupported date.', {}),
        'b-test-m02': (True, 'Explicitly declines to invent an endpoint.', {}),
    },
}


def main():
    gold = {g['id']: g for g in read_jsonl(ROOT / 'benchmarks/base/gold/test.jsonl')}
    for config, annotations in AUDIT.items():
        traces = read_jsonl(RUN / f'{config}.jsonl')
        reviews = []
        for trace in traces:
            qid = trace['query_id']; g = gold[qid]
            verdict, reason, citation_labels = annotations[qid]
            if set(trace.get('citations', [])) != set(citation_labels):
                raise ValueError(f'{config}/{qid}: citation annotations do not match trace')
            registry = trace.get('citation_registry', {})
            citations = [{'alias': alias, 'supported': supported, **registry[alias],
                          'reason': 'Supports the claim.' if supported else 'Does not establish the cited claim in full.'}
                         for alias, supported in citation_labels.items()]
            row = {'query_id': qid, 'run_id': trace['run_id'], 'reviewer': 'Codex (AI-assisted; not human-verified)',
                   'reviewed_at': now(), 'reason': reason, 'citations': citations,
                   'trace': str((RUN / f'{config}.jsonl').relative_to(ROOT)).replace('\\', '/')}
            if g['answerable']:
                context_hits = group_hits(trace.get('context', {}).get('entries', []), g['evidence_groups'])
                row['context_grade'] = 2 if all(context_hits) else 1 if any(context_hits) else 0
                row['context_reason'] = 'Gold evidence present in actual context.' if row['context_grade'] == 2 else 'Gold evidence missing or incomplete.'
                row['answer_grade'] = verdict
            else:
                row['abstention_correct'] = verdict
            reviews.append(row)
        if set(annotations) != {r['query_id'] for r in reviews}:
            raise ValueError('Review coverage differs from the test split')
        path = ROOT / f'artifacts/base/test-review-{config}.jsonl'
        write_jsonl(path, reviews)
        grades = Counter(str(r['answer_grade']) for r in reviews if 'answer_grade' in r)
        contexts = Counter(str(r['context_grade']) for r in reviews if 'context_grade' in r)
        citation_labels = [c['supported'] for r in reviews for c in r['citations']]
        successful = [t for t in traces if t['status'] != 'error']
        answered = [t for t in successful if t['status'] == 'answered']
        summary = {'configuration': config, 'split': 'test', 'reviewer': 'Codex (AI-assisted; not human-verified)',
                   'cases': len(traces), 'errors': sum(t['status'] == 'error' for t in traces),
                   'context_grades': dict(contexts), 'grounded_grades': dict(grades),
                   'grounded_mean_all_answerable': (grades['1'] + 2*grades['2']) / 5,
                   'citation_support': {'n': sum(citation_labels), 'N': len(citation_labels)},
                   'answer_citation_coverage': {'n': sum(bool(t['citations']) for t in answered), 'N': len(answered)},
                   'abstention': {'n': sum(r.get('abstention_correct', False) for r in reviews), 'N': 2},
                   'false_abstention': {'n': sum(t['status'] == 'abstain' for t in traces if gold[t['query_id']]['answerable']), 'N': 5},
                   'tool_use_successful': {'n': sum(any(e.get('event') == 'search' for e in t['events']) for t in successful), 'N': len(successful)},
                   'review_path': str(path.relative_to(ROOT)).replace('\\', '/')}
        write_json(ROOT / f'artifacts/base/test-review-summary-{config}.json', summary)
        print(config, summary)


if __name__ == '__main__': main()
