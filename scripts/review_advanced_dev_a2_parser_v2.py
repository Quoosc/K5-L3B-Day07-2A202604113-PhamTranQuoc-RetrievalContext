"""Review the same dev model outputs after documented formatting normalization."""
from pathlib import Path

from scripts.review_advanced_dev_a2 import NOTES as PRIOR_NOTES
from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / 'artifacts/advanced/runs/advanced-dev-20261116-a2-parser-v2/traces.jsonl'
NOTES = {**PRIOR_NOTES,
    2: (False, 'The refiner abstained on an answerable table question.'),
    3: (True, 'The table supports 0.069; the model-declared e1 citation was rendered inline.'),
    8: (False, 'The refiner abstained on an answerable diagram question.'),
    21: (True, 'The model declared abstain; formatting rendered a visible refusal without unsupported facts.'),
    22: (True, 'The response explicitly says the requested IP is not provided in the supplied text.'),
    23: (True, 'The model declared abstain; formatting rendered a visible refusal without a numeric guess.'),
    24: (True, 'The response explicitly says there is insufficient evidence; unused citations were removed.'),
    25: (True, 'The model declared abstain; formatting rendered a visible refusal without an invented invoice.'),
    26: (True, 'The model declared abstain; formatting rendered a visible refusal without an invented serial number.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    gold = read_jsonl(ROOT / 'benchmarks/advanced/gold/dev.jsonl')
    traces = read_jsonl(TRACE)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries]:
        raise ValueError('The reparsed pilot trace is not exactly the complete dev split')
    reviews = []
    for trace in traces:
        verdict, reason = NOTES[int(trace['query_id'].split('-')[-1])]
        reviews.append({'query_id': trace['query_id'], 'pass': verdict, 'reason': reason,
                        'reviewer': 'Codex (AI source review; no independent human review)',
                        'reviewed_at': now(), 'trace': TRACE.relative_to(ROOT).as_posix(),
                        'format_normalization': trace.get('format_normalization', []),
                        'cited_regions': list(trace.get('citation_registry', {}).values())})
    write_jsonl(ROOT / 'artifacts/advanced/dev-review-a2-parser-v2.jsonl', reviews)
    summary = score(queries, gold, traces, reviews)
    summary.update({'run_id': 'advanced-dev-20261116-a2-parser-v2',
                    'reviewer': 'Codex (AI source review; no independent human review)',
                    'note': 'Dev-only reparse of the same A2 raw responses, no additional model calls. '
                            'Refusals use declared abstention status; absence audits remain provisional. '
                            'Not an independent end-to-end run or an advanced test.'})
    write_json(ROOT / 'artifacts/advanced/dev-summary-a2-parser-v2.json', summary)
    print(summary)


if __name__ == '__main__':
    main()
