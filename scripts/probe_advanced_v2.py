"""Dev-only visual regression probe; cannot load the new holdout queries."""
import argparse
import json
from pathlib import Path

from src.day07.agent import ModelClient
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.multimodal_v2 import RetrieverV2, vision

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    for flag in ('day6-root','model-path','qdrant','pdf','output'):
        p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--ids',required=True)
    args=p.parse_args()
    requested=set(args.ids.split(','))
    queries=[q for q in read_jsonl(ROOT/'benchmarks/advanced-v2/queries/dev.jsonl') if q['id'] in requested]
    if len(queries)!=len(requested): raise ValueError('Only existing development IDs are allowed')
    args.output.mkdir(parents=True,exist_ok=False)
    elements=read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')
    ocr={r['evidence_id']:r for r in read_jsonl(ROOT/'artifacts/advanced/ocr-regions-v1.jsonl')}
    config=read_json(ROOT/'configs/advanced-v2.json')
    write_json(args.output/'manifest.json',{'started_at':now(),'split':'dev','kind':'visual-regression-probe',
        'query_ids':[q['id'] for q in queries],'config':config,
        'code_sha256':sha256(ROOT/'src/day07/multimodal_v2.py'),
        'note':'A partial development probe; cannot qualify a freeze or a test score.'})
    r=RetrieverV2(args.day6_root,args.model_path,args.qdrant,ROOT/'artifacts/advanced/search_chunks-v5.jsonl',elements)
    client=ModelClient('http://127.0.0.1:8086','qwen2.5-vl-3b-local',config['timeout_seconds'])
    try:
        with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for q in queries:
                t=vision(q,r,client,args.pdf,{e['evidence_id']:e for e in elements},ocr,config)
                t['split']='dev';stream.write(json.dumps(t,ensure_ascii=False)+'\n');stream.flush()
                print(q['id'],t['status'],t.get('answer'),flush=True)
    finally:r.close()


if __name__=='__main__':main()
