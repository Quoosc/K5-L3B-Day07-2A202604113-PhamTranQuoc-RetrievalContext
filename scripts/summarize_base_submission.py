"""Complete operational metrics from saved base runs; never rerun or relabel test."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics

from src.day07.common import now, read_json, read_jsonl, sha256, write_json

ROOT=Path(__file__).resolve().parents[1]


def operations(traces):
    def distribution(rows):
        return dict(sorted(Counter(str(sum(e.get('event')=='search' for e in t.get('events',[]))) for t in rows).items()))
    latency=sorted(t['elapsed_ms']/1000 for t in traces)
    return {'cases':len(traces), 'status_distribution':dict(Counter(t['status'] for t in traces)),
            'retrieval_tool_call_distribution_all':distribution(traces),
            'retrieval_tool_call_distribution_successful':distribution([t for t in traces if t['status']!='error']),
            'retrieval_tool_call_distribution_errors':distribution([t for t in traces if t['status']=='error']),
            'latency_seconds':{'median':statistics.median(latency),'p95':latency[math.ceil(.95*len(latency))-1]},
            'prompt_tokens':sum(t.get('usage',{}).get('prompt_tokens',0) for t in traces),
            'completion_tokens':sum(t.get('usage',{}).get('completion_tokens',0) for t in traces),
            'api_cost_usd':sum(t.get('api_cost_usd',0) for t in traces)}


def main():
    review=read_json(ROOT/'artifacts/base/dev_review.json')
    result={'created_at':now(),'source_verification':'artifacts/source-verification.json',
            'chosen':review['chosen'],'dev':{},'test':{},
            'measurement_notes':['No model was rerun to generate this summary.',
                'All query statuses retained; tool-call distribution includes errors separately.',
                'API cost excludes local hardware and electricity.',
                'Semantic grades are the original source-reviewed labels, not inferred from matching IDs.']}
    for config,data in review['per_config'].items():
        paths={r['trace'] for r in data['labels']}
        traces=[]
        for path in sorted(paths):
            traces+=read_jsonl(ROOT/path)
        expected={r['query_id'] for r in data['labels']}
        if len(traces)!=len(expected) or {t['query_id'] for t in traces}!=expected:
            raise ValueError('Dev trace coverage mismatch: '+config)
        result['dev'][config]={'operations':operations(traces),
            'source_review':{k:v for k,v in data.items() if k!='labels'},
            'trace_sha256':{path:sha256(ROOT/path) for path in sorted(paths)}}
    for config in ('D0','H0'):
        path=ROOT/f'artifacts/base/runs/base-test-20261115-v1/{config}.jsonl'
        result['test'][config]={'operations':operations(read_jsonl(path)),
            'source_review':read_json(ROOT/f'artifacts/base/test-review-summary-{config}.json'),
            'retrieval_context':read_json(ROOT/f'artifacts/base/test-metrics-{config}.json'),
            'trace_sha256':sha256(path)}
    write_json(ROOT/'artifacts/base/submission-metrics.json',result)
    print(json.dumps({k:v['operations'] for k,v in result['test'].items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
