"""Apply a narrow OCR/table join to saved dev traces without reading gold."""
import argparse
import json
from pathlib import Path

from scripts.refine_advanced_dev import ROOT, inputs
from src.day07.common import now, read_jsonl, sha256, write_json
from src.day07.spectral_join import spectral_join


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
               'kind':'offline-dev-spectral-tool-pilot','input_trace_sha256':sha256(args.trace),
               'ocr_sha256':sha256(args.ocr),'join_code_sha256':sha256(ROOT/'src/day07/spectral_join.py'),
               'script_sha256':sha256(Path(__file__)),'model_calls':0,
               'note':'No gold or new model calls. A unique OCR range/table-row lookup may replace an answer; '
                      'any original timeout remains an error. Both source regions require review.'})
    with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for q,trace in zip(queries,traces):
            result=dict(trace); _,registry=inputs(trace,elements)
            errors=' '.join(str(trace.get(k,'')) for k in ('error','original_error','pre_spatial_error'))
            decision=None if 'timeout' in errors.casefold() or 'timed out' in errors.casefold() else spectral_join(q['question'],registry,elements,ocr)
            if decision:
                result['pre_spectral_status']=result.get('status')
                result['pre_spectral_answer']=result.get('answer')
                result['pre_spectral_error']=result.get('error')
                result.update(decision); result.pop('error',None)
                result['policy_branch']='ocr_table_spectral_join'
            result['spectral_timestamp']=now()
            stream.write(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n'); stream.flush()
            if decision: print(q['id'],'ocr_table_spectral_join',flush=True)


if __name__=='__main__': main()
