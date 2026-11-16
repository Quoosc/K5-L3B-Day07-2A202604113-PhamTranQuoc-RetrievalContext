"""Source review of the complete staged composite development run."""
import math
from pathlib import Path
import statistics

from scripts.review_advanced_dev_a4 import NOTES
from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT=Path(__file__).resolve().parents[1]
TRACE=ROOT/'artifacts/advanced/runs/advanced-dev-20261116-a5-final/traces.jsonl'
VISION=ROOT/'artifacts/advanced/runs/advanced-dev-20261116-a5-vision/traces.jsonl'


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
    write_jsonl(ROOT/'artifacts/advanced/dev-review-a5-final.jsonl',reviews)
    summary=score(queries,gold,traces,reviews)
    durations=sorted(t['combined_elapsed_ms']/1000 for t in traces)
    summary.update({'run_id':'advanced-dev-20261116-a5-final',
                    'reviewer':'Codex (AI source review; no independent human review)',
                    'vision_stage_errors':sum(t['status']=='error' for t in vision),
                    'vision_stage_timeouts':sum('timed out' in str(t.get('error','')).casefold() or
                                                'timeout' in str(t.get('error','')).casefold() for t in vision),
                    'latency_seconds':{'median':statistics.median(durations),
                                       'p95':durations[math.ceil(.95*len(durations))-1],
                                       'note':'Sum of per-case stage times; excludes startup and waiting between stages.'},
                    'vision_prompt_tokens':sum(t.get('usage',{}).get('prompt_tokens',0) for t in traces),
                    'refiner_prompt_tokens':sum(t.get('refiner_usage',{}).get('prompt_tokens',0) for t in traces),
                    'api_cost_usd':sum(t.get('api_cost_usd',0) for t in traces),
                    'note':'Complete staged dev run; intermediate vision protocol errors are recorded separately. '
                           'Review is AI-assisted and absence/index audit remains provisional.'})
    write_json(ROOT/'artifacts/advanced/dev-summary-a5-final.json',summary)
    print(summary)


if __name__=='__main__': main()
