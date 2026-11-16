"""Record conservative source review of the interrupted/continued A1 dev run."""
from pathlib import Path

from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRACE_FILES = [
    ROOT / 'artifacts/advanced/runs/advanced-dev-20261115-a1/traces.jsonl',
    ROOT / 'artifacts/advanced/runs/advanced-dev-20261115-a1-continuation-v2/traces.jsonl',
]
NOTES = {
    1: (True, 'The cited Table 1-1 supports 378 Gbits, block-based, and the additional Landsat 8 comparison.'),
    2: (False, '40 is the ETM+ performance column; OLI Band 2 performance is 364.'),
    3: (True, 'Table 2-3 supports 0.069 for TIRS 10 at 240.'),
    4: (False, 'Protocol error; the raw response also omits the required ±0.8 K uncertainty.'),
    5: (True, 'The upper-left arrow in the cited Figure 2-1 identifies TIRS.'),
    6: (False, 'The model answered SCA2; the top band is Band 8, panchromatic.'),
    7: (False, 'The right-hand upper SCA is SCA-1, not SCA-2.'),
    8: (False, 'The next processing system is GPS; the answer repeats RPS.'),
    9: (True, 'Approximately 240 is within 20 of the Coastal/Aerosol value on the cited chart.'),
    10: (True, 'The cited Figure A-2 associates blue with ghosts and gray with no ghosts.'),
    11: (True, 'The cited Figure A-6 shows the yellow limit at approximately 80.'),
    12: (True, 'The cited Figure 4-3 shows wavelength in nm and atmospheric transmission in percent.'),
    13: (False, 'Timeout after opening both regions; no final answer was returned.'),
    14: (False, 'Citation protocol error: the raw two-sentence answer has no inline markers.'),
    15: (False, 'Citation protocol error: the raw two-sentence answer has no inline markers.'),
    16: (False, 'Citation protocol error; the raw SNR 238 is also wrong for Band 4, which is 227.'),
    17: (False, 'The page 9 text supports 2013, but the additional cited page 2 title does not.'),
    18: (False, 'The page 12 text supports the answer, but the additional cited page 96 region does not.'),
    19: (False, 'The page 60 text supports the answer, but the additional cited page 63 image does not establish its dimensions.'),
    20: (False, 'The page 78 text supports the answer, but the additional cited cutaway image does not establish the conversion claim.'),
    21: (False, 'Protocol error: the abstention lists citations without corresponding inline markers.'),
    22: (False, 'The model says the value is not provided but labels the response answered, not abstain.'),
    23: (False, 'It invents a list of numeric values for a fictional scene.'),
    24: (True, 'Explicit abstention without an unsupported value or name.'),
    25: (False, 'Status is abstain but the entire user-visible answer is an ellipsis, not an explicit refusal.'),
    26: (False, 'LSDS-1574 is a handbook identifier, not a serial number for the fictional sensor.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    gold = read_jsonl(ROOT / 'benchmarks/advanced/gold/dev.jsonl')
    traces = [row for path in TRACE_FILES for row in read_jsonl(path)]
    if [t['query_id'] for t in traces] != [q['id'] for q in queries]:
        raise ValueError('The original trace and continuation are not exactly the complete dev split')
    reviews = []
    for trace in traces:
        n = int(trace['query_id'].split('-')[-1]); verdict, reason = NOTES[n]
        source = TRACE_FILES[1] if trace.get('continuation') else TRACE_FILES[0]
        reviews.append({'query_id': trace['query_id'], 'pass': verdict, 'reason': reason,
                        'reviewer': 'Codex (AI source review; no independent human review)',
                        'reviewed_at': now(), 'trace': source.relative_to(ROOT).as_posix(),
                        'cited_regions': list(trace.get('citation_registry', {}).values())})
    write_jsonl(ROOT / 'artifacts/advanced/dev-review-a1.jsonl', reviews)
    summary = score(queries, gold, traces, reviews)
    summary.update({'run_id': 'advanced-dev-20261115-a1',
                    'reviewer': 'Codex (AI source review; no independent human review)',
                    'note': 'Strict binary review; errors, unsupported extra citations and non-explicit refusals fail. '
                            'The interrupted run was continued without retry; elapsed times across the restart are not directly comparable.'})
    write_json(ROOT / 'artifacts/advanced/dev-summary-a1.json', summary)
    print(summary)


if __name__ == '__main__':
    main()
