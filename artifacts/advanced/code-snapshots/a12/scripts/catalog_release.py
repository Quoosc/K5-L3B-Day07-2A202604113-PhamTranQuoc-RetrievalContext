"""Freeze and evaluate native-tool RAG over a complete source-derived catalog."""
import argparse
import json
from pathlib import Path

from scripts.advanced_release import runtime_attestation,runtime_signature,reviewed_score
from src.day07.agent import ModelClient
from src.day07.catalog_agent import CatalogRetriever,run
from src.day07.common import now,read_json,read_jsonl,sha256,write_json

ROOT=Path(__file__).resolve().parents[1]
DEPENDENCIES=('src/day07/catalog_agent.py','src/day07/advanced_retrieval.py','src/day07/agent.py',
              'src/day07/retrieval.py','src/day07/common.py','src/day07/day6.py','src/day07/context.py',
              'src/day07/advanced_eval.py','src/day07/__main__.py','scripts/advanced_release.py',
              'scripts/catalog_release.py','scripts/build_catalog_v6.py','scripts/enrich_catalog_v7.py',
              'scripts/build_advanced_v3.py','scripts/start_model_server.ps1','requirements-lock.txt')


def fingerprints(args):
    paths=[ROOT/p for p in DEPENDENCIES]+[args.config,args.chunks,args.regions,
             ROOT/'artifacts/advanced/catalog-v7/manifest.json',ROOT/'artifacts/advanced/catalog-v6/manifest.json',
             ROOT/'artifacts/advanced/elements.jsonl']
    paths += [args.benchmark/folder/f'{split}.jsonl' for folder in ('queries','gold') for split in ('dev','test')]
    repo={p.resolve().relative_to(ROOT).as_posix():sha256(p) for p in paths}
    external={'pdf':sha256(args.pdf),'text_model':sha256(args.text_model),
              'day6_embeddings':sha256(args.day6_root/'src/embeddings.py'),
              'qdrant_meta':sha256(args.qdrant/'meta.json'),
              'qdrant_collection':sha256(args.qdrant/'collection/lab7_landsat_v5/storage.sqlite')}
    external.update({'embedding/'+p.relative_to(args.model_path).as_posix():sha256(p) for p in args.model_path.rglob('*') if p.is_file()})
    return {'repository':repo,'external':external}


def execute(args):
    if args.split=='test' and (args.dev_ids or not args.lock):
        raise ValueError('Test requires a pre-test lock and the full declared split')
    config=read_json(args.config);hashes=fingerprints(args)
    attestation=runtime_attestation(args,'text',config)
    if args.split=='test':
        lock=read_json(args.lock)
        if lock['kind']!='catalog-v3' or lock['hashes']!=hashes or lock['runtime']!=runtime_signature(attestation):
            raise ValueError('Code, source catalog, benchmark, model or actual runtime changed after freeze')
    queries=read_jsonl(args.benchmark/'queries'/f'{args.split}.jsonl')
    if args.dev_ids:
        ids=set(args.dev_ids.split(','));queries=[q for q in queries if q['id'] in ids]
        if len(queries)!=len(ids):raise ValueError('Unknown development probe IDs')
    args.output.mkdir(parents=True,exist_ok=False)
    write_json(args.output/'manifest.json',{'started_at':now(),'kind':'catalog-v3','split':args.split,
        'query_count':len(queries),'hashes':hashes,'runtime':attestation,'config':config,
        'lock_sha256':sha256(args.lock) if args.lock else None,
        'note':'Real native-tool text model uses original text, source-derived table columns and visual observations. Gold bytes are hashed, never supplied as model context.'})
    retriever=CatalogRetriever(args.day6_root,args.model_path,args.qdrant,args.chunks,args.regions)
    client=ModelClient('http://127.0.0.1:'+str(config['runtime']['text']['port']),config['runtime']['text']['alias'],config['timeout_seconds'])
    try:
        with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for i,q in enumerate(queries,1):
                trace=run(q,retriever,client,config);trace.update(split=args.split,timestamp=now(),release_config=config['id'])
                stream.write(json.dumps(trace,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
                print(f"{i}/{len(queries)} {q['id']} {trace['status']}",flush=True)
    finally:retriever.close()
    write_json(args.output/'completion.json',{'completed_at':now(),'cases':len(queries),'trace_sha256':sha256(args.output/'traces.jsonl')})


def freeze(args):
    manifest=read_json(args.dev_run/'manifest.json')
    if manifest['split']!='dev':raise ValueError('Freeze requires dev')
    metrics=reviewed_score(args.benchmark,'dev',args.dev_run/'traces.jsonl',args.reviews)
    if not metrics['meets_90_percent'] or any(g['n']==0 for g in metrics['groups'].values()):
        raise ValueError('Complete reviewed dev is below the readiness target')
    hashes=fingerprints(args)
    if hashes!=manifest['hashes']:raise ValueError('Release differs from qualifying development run')
    write_json(args.output,{'kind':'catalog-v3','frozen_at':now(),'hashes':hashes,
        'runtime':runtime_signature(manifest['runtime']),'dev_trace_sha256':sha256(args.dev_run/'traces.jsonl'),
        'dev_review_sha256':sha256(args.reviews),'dev_score':{k:v for k,v in metrics.items() if k!='cases'},
        'test_policy':'All 30 fresh cases, >=27 required; no replacements or tuning based on test outputs.',
        'source_policy':'Catalog covers all 114 pages/852 regions and was built without reading any benchmark.'})
    print('Frozen catalog release after dev',metrics['passed'],'/',metrics['total'])


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for command in ('run','freeze','score'):
        s=sub.add_parser(command);s.add_argument('--output',required=True,type=Path)
        s.add_argument('--benchmark',default=ROOT/'benchmarks/advanced-v3',type=Path)
        if command=='score':
            s.add_argument('--split',choices=('dev','test'),required=True)
            s.add_argument('--traces',required=True,type=Path);s.add_argument('--reviews',required=True,type=Path)
            continue
        for flag in ('day6-root','model-path','qdrant','pdf','text-model'):s.add_argument('--'+flag,required=True,type=Path)
        s.add_argument('--config',default=ROOT/'configs/catalog-v3.json',type=Path)
        s.add_argument('--regions',default=ROOT/'artifacts/advanced/catalog-v7/regions.jsonl',type=Path)
        s.add_argument('--chunks',default=ROOT/'artifacts/advanced/catalog-v7/chunks.jsonl',type=Path)
        if command=='run':
            s.add_argument('--split',choices=('dev','test'),required=True);s.add_argument('--lock',type=Path)
            s.add_argument('--dev-ids')
        else:
            s.add_argument('--dev-run',required=True,type=Path);s.add_argument('--reviews',required=True,type=Path)
    args=p.parse_args()
    if args.command=='run':execute(args)
    elif args.command=='freeze':freeze(args)
    else:
        result=reviewed_score(args.benchmark,args.split,args.traces,args.reviews);write_json(args.output,result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('cases','operations_by_group')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
