"""Apply a conservative OCR geometry tool to a complete saved dev pipeline trace."""
import argparse
import json
from pathlib import Path

from scripts.refine_advanced_dev import ROOT, inputs
from src.day07.common import now, read_jsonl, sha256, write_json
from src.day07.spatial_ocr import spatial_lookup


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trace',required=True,type=Path); p.add_argument('--ocr',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    queries=read_jsonl(ROOT/'benchmarks/advanced/queries/dev.jsonl')
    traces=read_jsonl(args.trace)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries] or any(t.get('split')!='dev' for t in traces):
        raise ValueError('Only the full ordered dev split is accepted')
    elements={e['evidence_id']:e for e in read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')}
    ocr={r['evidence_id']:r for r in read_jsonl(args.ocr)}
    args.output.mkdir(parents=True,exist_ok=False)
    write_json(args.output/'manifest.json',{'created_at':now(),'split':'dev',
               'kind':'offline-dev-spatial-tool-pilot','input_trace_sha256':sha256(args.trace),
               'ocr_sha256':sha256(args.ocr),'spatial_code_sha256':sha256(ROOT/'src/day07/spatial_ocr.py'),
               'script_sha256':sha256(Path(__file__)),'model_calls':0,
               'note':'No gold or new model calls. A unique OCR geometry lookup may replace an answer; '
                      'each change requires source review and this is not a test run.'})
    with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for q,trace in zip(queries,traces):
            result=dict(trace); _,registry=inputs(trace,elements)
            choices=[]
            for alias,source in registry.items():
                item=ocr.get(source['id'],{})
                if item.get('status')=='ok':
                    decision=spatial_lookup(q['question'],alias,registry,item.get('lines',[]))
                    if decision: choices.append(decision)
            if len(choices)==1:
                result['pre_spatial_status']=result.get('status')
                result['pre_spatial_answer']=result.get('answer')
                result['pre_spatial_error']=result.get('error')
                result.update(choices[0]); result.pop('error',None)
                result['policy_branch']='ocr_spatial_lookup'
            result['spatial_timestamp']=now()
            stream.write(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n'); stream.flush()
            if len(choices)==1: print(q['id'],'ocr_spatial_lookup',flush=True)


if __name__=='__main__': main()
