"""Source review for the offline, modality-routed dev policy pilot."""
from pathlib import Path

from scripts.review_advanced_dev_a1 import NOTES as VISION_NOTES
from scripts.review_advanced_dev_a2_parser_v2 import NOTES as REFINED_NOTES
from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / 'artifacts/advanced/runs/advanced-dev-20261116-a3-policy-v2/traces.jsonl'
NOTES = {**REFINED_NOTES, **{n:VISION_NOTES[n] for n in range(5,13)},
    1:(True, 'Table 1-1 supports 378 Gbits, block-based.'),
    2:(True, 'Table 2-2 supports OLI Band 2 performance 364.'),
    3:(True, 'Table 2-3 supports NEΔT 0.069 for TIRS Band 10 at 240.'),
    4:(True, 'Table A-1 supports −2.1 ± 0.8 K at 300 K for Band 10.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    gold = read_jsonl(ROOT / 'benchmarks/advanced/gold/dev.jsonl')
    traces = read_jsonl(TRACE)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries]:
        raise ValueError('Policy trace must be the complete ordered dev split')
    reviews = []
    for trace in traces:
        verdict, reason = NOTES[int(trace['query_id'].split('-')[-1])]
        reviews.append({'query_id':trace['query_id'],'pass':verdict,'reason':reason,
                        'reviewer':'Codex (AI source review; no independent human review)',
                        'reviewed_at':now(),'trace':TRACE.relative_to(ROOT).as_posix(),
                        'policy_branch':trace['policy_branch'],
                        'cited_regions':list(trace.get('citation_registry',{}).values())})
    write_jsonl(ROOT / 'artifacts/advanced/dev-review-a3-policy.jsonl',reviews)
    summary = score(queries,gold,traces,reviews)
    summary.update({'run_id':'advanced-dev-20261116-a3-policy-v2',
                    'reviewer':'Codex (AI source review; no independent human review)',
                    'note':'Dev-only policy pilot reuses earlier vision/refiner results; four single-table questions '
                           'were newly evaluated with a text model. No independent end-to-end test. '
                           'Absence audit remains provisional.'})
    write_json(ROOT / 'artifacts/advanced/dev-summary-a3-policy.json',summary)
    print(summary)


if __name__ == '__main__': main()
