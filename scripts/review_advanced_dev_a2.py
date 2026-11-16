"""Record source review of the dev-only offline 7B text refinement pilot."""
from pathlib import Path

from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / 'artifacts/advanced/runs/advanced-dev-20261116-a2-refiner/traces.jsonl'
NOTES = {
    1: (True, 'Table 1-1 supports 378 Gbits, block-based.'),
    2: (False, 'The refiner emitted an empty abstention and the parser reported an error.'),
    3: (False, 'Correct value in raw output, but declared citation lacks an inline marker.'),
    4: (False, 'Protocol error; the raw answer also omits ±0.8 K.'),
    5: (False, 'The answerable question was refused despite TIRS being visible in Figure 2-1.'),
    6: (False, 'SCA2 is not the top band; the figure shows Band 8, panchromatic.'),
    7: (False, 'The right-hand upper SCA is SCA-1, not SCA-2.'),
    8: (False, 'The refiner emitted an empty abstention and the parser reported an error.'),
    9: (False, 'The answerable chart question was refused; about 238 is supported.'),
    10: (True, 'The cited Figure A-2 supports the blue/gray ghost meanings.'),
    11: (True, 'The cited Figure A-6 shows the yellow limit at approximately 80.'),
    12: (True, 'The cited Figure 4-3 shows wavelength in nm and atmospheric transmission in percent.'),
    13: (False, 'Original vision draft timed out; the pilot preserved the error without retry.'),
    14: (True, 'Page 18 supports Band 2 and page 19 supports SNR 364; each claim cites its source.'),
    15: (True, 'Page 18 supports Band 3 and page 19 supports SNR 302; each claim cites its source.'),
    16: (False, 'The Band 4 SNR is 227, not 238, even though both sources were cited.'),
    17: (True, 'Page 9 directly states the 2013 launch; the unrelated page 2 citation was removed.'),
    18: (True, 'Page 12 supports the 5-year design life and 10-year fuel consumables.'),
    19: (True, 'Page 60 supports both 16-bit and the same L1T dimensions.'),
    20: (True, 'Page 78 text supports conversion of angular positions into digital codes.'),
    21: (False, 'The refiner listed citations without inline markers and returned an error.'),
    22: (False, 'The refiner listed citations without inline markers and returned an error.'),
    23: (False, 'The refiner emitted an empty abstention and the parser reported an error.'),
    24: (False, 'The refiner listed citations without inline markers and returned an error.'),
    25: (False, 'An ellipsis is not an explicit user-visible refusal.'),
    26: (False, 'The refiner emitted an empty abstention and the parser reported an error.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    gold = read_jsonl(ROOT / 'benchmarks/advanced/gold/dev.jsonl')
    traces = read_jsonl(TRACE)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries]:
        raise ValueError('The pilot trace is not exactly the complete dev split')
    reviews = []
    for trace in traces:
        verdict, reason = NOTES[int(trace['query_id'].split('-')[-1])]
        reviews.append({'query_id': trace['query_id'], 'pass': verdict, 'reason': reason,
                        'reviewer': 'Codex (AI source review; no independent human review)',
                        'reviewed_at': now(), 'trace': TRACE.relative_to(ROOT).as_posix(),
                        'cited_regions': list(trace.get('citation_registry', {}).values())})
    write_jsonl(ROOT / 'artifacts/advanced/dev-review-a2-refiner.jsonl', reviews)
    summary = score(queries, gold, traces, reviews)
    summary.update({'run_id': 'advanced-dev-20261116-a2-refiner',
                    'reviewer': 'Codex (AI source review; no independent human review)',
                    'note': 'Offline dev pilot reuses the A1 opened regions and unverified vision drafts; '
                            'it is not an independent end-to-end run or an advanced test.'})
    write_json(ROOT / 'artifacts/advanced/dev-summary-a2-refiner.json', summary)
    print(summary)


if __name__ == '__main__':
    main()
