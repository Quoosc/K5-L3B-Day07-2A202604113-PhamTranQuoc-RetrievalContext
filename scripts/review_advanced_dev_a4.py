"""Conservative source review of a fresh, staged dev run with logged fallback tools."""
from pathlib import Path

from scripts.review_advanced_dev_a3 import NOTES as PRIOR_NOTES
from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT=Path(__file__).resolve().parents[1]
TRACE=ROOT/'artifacts/advanced/runs/advanced-dev-20261116-a4-final/traces.jsonl'
VISION=ROOT/'artifacts/advanced/runs/advanced-dev-20261116-a4-vision/traces.jsonl'
NOTES={**PRIOR_NOTES,
    6:(True,'The unique OCR geometry result says Band 8, panchromatic; confirmed against Figure 2-5.'),
    7:(True,'The unique same-row OCR result says SCA-1; confirmed against Figure 2-7.'),
    13:(True,'The OCR/table join returns Band 1 and SNR 238; both cited source regions were checked.'),
    14:(True,'The OCR/table join returns Band 2 and SNR 364; both cited source regions were checked.'),
    15:(True,'The OCR/table join returns Band 3 and SNR 302; both cited source regions were checked.'),
    16:(True,'The OCR/table join returns Band 4 and SNR 227; both cited source regions were checked.'),
}


def main():
    queries=read_jsonl(ROOT/'benchmarks/advanced/queries/dev.jsonl')
    gold=read_jsonl(ROOT/'benchmarks/advanced/gold/dev.jsonl')
    traces=read_jsonl(TRACE); vision=read_jsonl(VISION)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries] or [t['query_id'] for t in vision] != [q['id'] for q in queries]:
        raise ValueError('Both trace files must contain exactly the complete ordered dev split')
    initial={t['query_id']:t for t in vision}; reviews=[]
    for trace in traces:
        first=initial[trace['query_id']]
        verdict,reason=NOTES[int(trace['query_id'].split('-')[-1])]
        reviews.append({'query_id':trace['query_id'],'pass':verdict,'reason':reason,
                        'reviewer':'Codex (AI source review; no independent human review)',
                        'reviewed_at':now(),'trace':TRACE.relative_to(ROOT).as_posix(),
                        'policy_branch':trace['policy_branch'],'vision_stage_status':first['status'],
                        'vision_stage_error':first.get('error'),
                        'cited_regions':list(trace.get('citation_registry',{}).values())})
    write_jsonl(ROOT/'artifacts/advanced/dev-review-a4-final.jsonl',reviews)
    summary=score(queries,gold,traces,reviews)
    summary.update({'run_id':'advanced-dev-20261116-a4-final',
                    'reviewer':'Codex (AI source review; no independent human review)',
                    'vision_stage_errors':sum(t['status']=='error' for t in vision),
                    'note':'Fresh vision/refiner dev outputs, followed by policy and deterministic tools developed on dev. '
                           'Intermediate vision protocol errors are recorded separately and may be recovered; '
                           'this is not a frozen end-to-end test and absence audit remains provisional.'})
    write_json(ROOT/'artifacts/advanced/dev-summary-a4-final.json',summary)
    print(summary)


if __name__=='__main__': main()
