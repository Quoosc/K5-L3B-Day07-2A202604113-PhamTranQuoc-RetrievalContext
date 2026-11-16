"""Finish a complete advanced vision run with local text and evidence tools."""
import argparse
import json
from pathlib import Path

from scripts.run_advanced import ROOT, external_hashes, fingerprint
from src.day07.__main__ import server_model_hash
from src.day07.agent import ModelClient
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.composite import finish
from src.day07.composite_lock import composite_hashes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--split',required=True,choices=('dev','test'))
    p.add_argument('--vision-run',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--day6-root',required=True,type=Path); p.add_argument('--model-path',required=True,type=Path)
    p.add_argument('--qdrant',required=True,type=Path); p.add_argument('--chunks',required=True,type=Path)
    p.add_argument('--ocr',required=True,type=Path); p.add_argument('--pdf',required=True,type=Path)
    p.add_argument('--projector',required=True,type=Path); p.add_argument('--vision-model',required=True,type=Path)
    p.add_argument('--benchmark',default=ROOT/'benchmarks/advanced',type=Path)
    p.add_argument('--config',default=ROOT/'configs/advanced.json',type=Path)
    p.add_argument('--server',default='http://127.0.0.1:8085'); p.add_argument('--model',default='qwen2.5-7b-local')
    p.add_argument('--timeout',default=120,type=int); p.add_argument('--lock',type=Path)
    args=p.parse_args()
    if args.split=='test' and not args.lock: raise ValueError('Test requires an advanced composite freeze')
    queries_path=args.benchmark/'queries'/f'{args.split}.jsonl'
    queries=read_jsonl(queries_path); vision_path=args.vision_run/'traces.jsonl'
    vision=read_jsonl(vision_path); vm=read_json(args.vision_run/'manifest.json')
    if vm['split']!=args.split or [v['query_id'] for v in vision] != [q['id'] for q in queries]:
        raise ValueError('Vision run is not exactly the complete requested split')
    if any(v.get('split')!=args.split for v in vision): raise ValueError('Trace split mismatch')
    checks={'model_sha256':sha256(args.vision_model),'projector_sha256':sha256(args.projector),
            'query_sha256':sha256(queries_path),'pdf_sha256':sha256(args.pdf),
            'search_chunks_sha256':sha256(args.chunks),'ocr_sha256':sha256(args.ocr),
            'qdrant_collection_sha256':sha256(args.qdrant/'collection/lab7_landsat_v5/storage.sqlite'),
            'day6_embeddings_sha256':sha256(args.day6_root/'src/embeddings.py'),
            'embedding_model_sha256':sha256(args.model_path/'model.safetensors')}
    if any(vm.get(k)!=v for k,v in checks.items()) or vm['config']!=read_json(args.config):
        raise ValueError('Vision stage inputs differ from the finalization inputs')
    if any(sha256(ROOT/name)!=digest for name,digest in vm['code_sha256'].items()):
        raise ValueError('Vision stage code differs from current code')
    hashes=fingerprint(args.pdf,args.chunks,args.benchmark,args.config,args.ocr)
    externals=external_hashes(args.day6_root,args.model_path,args.qdrant,args.projector)
    components=composite_hashes()
    text_hash=server_model_hash(args.server,args.model)
    if args.split=='test':
        lock=read_json(args.lock)
        if (lock.get('kind')!='advanced-composite' or lock['hashes']!=hashes or
                lock['external_hashes']!=externals or lock['composite_hashes']!=components or
                lock['text_model']!=args.model or lock['text_model_sha256']!=text_hash or
                lock['model_sha256']!=checks['model_sha256'] or vm.get('lock_sha256')!=sha256(args.lock)):
            raise ValueError('Composite code, models, index, benchmark or vision lock changed after freeze')
    elements={e['evidence_id']:e for e in read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')}
    ocr={r['evidence_id']:r for r in read_jsonl(args.ocr)}
    client=ModelClient(args.server,args.model,args.timeout)
    args.output.mkdir(parents=True,exist_ok=False)
    write_json(args.output/'manifest.json',{'started_at':now(),'split':args.split,
               'vision_run':str(args.vision_run),'vision_trace_sha256':sha256(vision_path),
               'vision_manifest_sha256':sha256(args.vision_run/'manifest.json'),
               'text_model':args.model,'text_model_sha256':text_hash,'input_checks':checks,
               'hashes':hashes,'external_hashes':externals,'composite_hashes':components,
               'lock_sha256':sha256(args.lock) if args.lock else None,
               'note':'Queries only; gold is not read. The vision and text stages may run sequentially on one machine.'})
    with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for n,(query,trace) in enumerate(zip(queries,vision),1):
            row=finish(query,trace,elements,ocr,client)
            row['split']=args.split; row['timestamp']=now()
            stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n'); stream.flush()
            print(f"{n}/{len(queries)} {query['id']} {row['policy_branch'] if 'policy_branch' in row else 'error'} {row['status']}",flush=True)


if __name__=='__main__': main()
