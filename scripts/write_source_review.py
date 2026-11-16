"""Materialize explicit per-case source annotations for one exact trace file.

Annotations are supplied separately after reading the answers and original
sources. This command does not decide correctness or reuse historical verdicts.
"""
import argparse
import json
from pathlib import Path

from src.day07.common import now, read_json, read_jsonl, sha256, write_jsonl


def main():
    p=argparse.ArgumentParser()
    for flag in ('queries','gold','traces','annotations','output'):
        p.add_argument('--'+flag,type=Path,required=True)
    args=p.parse_args()
    queries=read_jsonl(args.queries);gold={g['id']:g for g in read_jsonl(args.gold)}
    traces={t['query_id']:t for t in read_jsonl(args.traces)}
    annotations=read_json(args.annotations)
    ids={q['id'] for q in queries}
    if set(annotations)!=ids or set(gold)!=ids or set(traces)!=ids:
        raise ValueError('Every query requires a trace, gold and explicit source annotation')
    digest=sha256(args.traces);timestamp=now();rows=[]
    for q in queries:
        qid=q['id'];g=gold[qid];t=traces[qid];a=annotations[qid]
        if type(a.get('pass')) is not bool or not a.get('reason'):
            raise ValueError('Each annotation requires a boolean verdict and source-based reason')
        if not a['pass'] and not a.get('failure_type'):
            raise ValueError('A failed case requires a classified failure type')
        if set(a.get('citation_support',{}))!=set(t.get('citations',[])):
            raise ValueError('Annotate every actual citation alias: '+qid)
        registry=t.get('citation_registry',{})
        cited=[{'alias':alias,'supported':a['citation_support'][alias],
                'source':registry[alias],'reason':a.get('citation_reasons',{}).get(alias,a['reason'])}
               for alias in t.get('citations',[])]
        rows.append({'query_id':qid,'pass':a['pass'],'reason':a['reason'],
            'failure_type':a.get('failure_type'),'reviewer':'Codex (answer and original-source comparison; author source attestation recorded separately)',
            'reviewed_at':timestamp,'trace':args.traces.as_posix(),'trace_sha256':digest,
            'source_values':[ev['source_value'] for group in g.get('evidence_groups',[]) for ev in group],
            'source_locators':[ev for group in g.get('evidence_groups',[]) for ev in group],
            'source_absence_reason':g.get('absence_reason'),'calculation':g.get('calculation'),
            'absolute_tolerance':g.get('absolute_tolerance'),'citation_audit':cited,
            'source_verification':'artifacts/source-verification.json',
            'annotation_sha256':sha256(args.annotations)})
    write_jsonl(args.output,rows)
    print('Wrote explicit source reviews:',sum(r['pass'] for r in rows),'/',len(rows))


if __name__=='__main__':main()
