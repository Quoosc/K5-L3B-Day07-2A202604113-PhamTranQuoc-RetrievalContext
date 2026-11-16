"""Validate, execute, freeze and score the second advanced release.

Every test run checks the complete query split, code/data/model hashes AND
the actual local llama-server executable and command line. No gold values
are parsed by a runtime stage; gold file bytes are hashed for freeze checks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import statistics
import subprocess
import urllib.request

from src.day07.advanced_eval import score, validate
from src.day07.agent import ModelClient
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.multimodal_v2 import RetrieverV2, finish, vision

ROOT = Path(__file__).resolve().parents[1]


def runtime_signature(attestation):
    return {k: attestation[k] for k in ('binary_sha256','model_sha256','projector_sha256','normalized_arguments','contract')}


def runtime_attestation(args, stage, config):
    contract = config['runtime'][stage]
    server = f"http://127.0.0.1:{contract['port']}"
    with urllib.request.urlopen(server+'/props',timeout=10) as response:
        props = json.load(response)
    model = args.vision_model if stage=='vision' else args.text_model
    if props.get('model_alias')!=contract['alias'] or sha256(Path(props['model_path']))!=sha256(model):
        raise ValueError('Server alias or loaded model differs from configured model')
    ps = ("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
          "Get-CimInstance Win32_Process -Filter \"Name = 'llama-server.exe'\" | "
          "Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress")
    raw = subprocess.check_output(['powershell','-NoProfile','-Command',ps],encoding='utf-8').strip()
    records = json.loads(raw) if raw else []
    if isinstance(records,dict): records=[records]
    found=[]
    for process in records:
        argv=[part.strip('"') for part in shlex.split(process['CommandLine'],posix=False)]
        def option(flag):
            return argv[argv.index(flag)+1] if flag in argv and argv.index(flag)+1<len(argv) else None
        if option('--port')!=str(contract['port']): continue
        checks={'--host':'127.0.0.1','--port':str(contract['port']),
                '--alias':contract['alias'],'--ctx-size':str(contract['ctx_size']),
                '--threads':str(contract['threads']),'--parallel':str(contract['parallel']),
                '--device':contract['device'],'--n-gpu-layers':str(contract['n_gpu_layers'])}
        if stage=='vision':
            checks['--image-max-tokens']=str(contract['image_max_tokens'])
            checks['--image-min-tokens']=str(contract['image_min_tokens'])
        if any(option(k)!=v for k,v in checks.items()):
            raise ValueError('Actual llama-server flags differ from configured runtime contract')
        if not option('-m') or Path(option('-m')).resolve()!=model.resolve():
            raise ValueError('Actual model command line differs from supplied model')
        if stage=='vision' and (not option('--mmproj') or Path(option('--mmproj')).resolve()!=args.projector.resolve()):
            raise ValueError('Actual projector command line differs from supplied projector')
        if stage=='text' and '--jinja' not in argv:
            raise ValueError('Text stage requires the declared Jinja chat template')
        normalized=argv[1:]
        for flag,digest in [('-m',sha256(model)),('--mmproj',sha256(args.projector) if stage=='vision' else None)]:
            if flag in normalized:
                normalized[normalized.index(flag)+1]='sha256:'+digest
        found.append({'checked_at':now(),'process_id':process['ProcessId'],
            'executable':process['ExecutablePath'],'command_line':process['CommandLine'],
            'binary_sha256':sha256(process['ExecutablePath']),'model_sha256':sha256(model),
            'projector_sha256':sha256(args.projector) if stage=='vision' else None,
            'normalized_arguments':normalized,'contract':contract,
            'server_context':props.get('default_generation_settings',{}).get('n_ctx')})
    if len(found)!=1: raise ValueError('Expected exactly one local process matching the runtime contract')
    return found[0]


def fingerprints(args):
    paths=list((ROOT/'src/day07').glob('*.py'))
    paths += [Path(__file__),ROOT/'scripts/build_advanced_v2.py',ROOT/'scripts/start_model_server.ps1',args.config,args.chunks,args.ocr,
              ROOT/'requirements-lock.txt',ROOT/'requirements-ocr-lock.txt',
              ROOT/'artifacts/advanced/elements.jsonl',ROOT/'artifacts/advanced/page_inventory.jsonl']
    paths += [args.benchmark/folder/f'{split}.jsonl' for folder in ('queries','gold') for split in ('dev','test')]
    repository={p.resolve().relative_to(ROOT).as_posix():sha256(p) for p in paths}
    external={'pdf':sha256(args.pdf),'vision_model':sha256(args.vision_model),
              'projector':sha256(args.projector),'text_model':sha256(args.text_model),
              'day6_embeddings':sha256(args.day6_root/'src/embeddings.py'),
              'qdrant_meta':sha256(args.qdrant/'meta.json'),
              'qdrant_collection':sha256(args.qdrant/'collection/lab7_landsat_v5/storage.sqlite')}
    external.update({'embedding/'+p.relative_to(args.model_path).as_posix():sha256(p)
                     for p in args.model_path.rglob('*') if p.is_file()})
    return {'repository':repository,'external':external}


def check_test_lock(args, stage, hashes, attestation):
    if not args.lock: raise ValueError('An independent test requires a pre-test release lock')
    lock=read_json(args.lock)
    if lock['kind']!='advanced-v2' or lock['hashes']!=hashes:
        raise ValueError('Release code, inputs or models differ from pre-test freeze')
    if lock['runtime'][stage]!=runtime_signature(attestation):
        raise ValueError('Runtime executable or arguments differ from qualifying dev')


def execute(args):
    config=read_json(args.config)
    if config['temperature']!=0 or config['retry_count']!=0:
        raise ValueError('Unsupported generation policy')
    hashes=fingerprints(args)
    attestation=runtime_attestation(args,args.stage,config)
    if args.split=='test': check_test_lock(args,args.stage,hashes,attestation)
    queries=read_jsonl(args.benchmark/'queries'/f'{args.split}.jsonl')
    if any(q['split']!=args.split for q in queries) or len({q['id'] for q in queries})!=len(queries):
        raise ValueError('Query split or identity mismatch')
    args.output.mkdir(parents=True,exist_ok=False)
    manifest={'started_at':now(),'kind':'advanced-v2-'+args.stage,'split':args.split,
              'query_count':len(queries),'hashes':hashes,'runtime':attestation,
              'config':config,'lock_sha256':sha256(args.lock) if args.lock else None,
              'note':'Gold bytes are hashed for change detection; no gold values, labels or gold regions enter model inputs.'}
    elements={e['evidence_id']:e for e in read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')}
    ocr={e['evidence_id']:e for e in read_jsonl(args.ocr)}
    client=ModelClient(f"http://127.0.0.1:{config['runtime'][args.stage]['port']}",config['runtime'][args.stage]['alias'],config['timeout_seconds'])
    retriever=None
    if args.stage=='vision':
        retriever=RetrieverV2(args.day6_root,args.model_path,args.qdrant,args.chunks,list(elements.values()))
        source_traces=[None]*len(queries)
    else:
        if not args.vision_run: raise ValueError('Text stage requires a complete vision run')
        source_traces=read_jsonl(args.vision_run/'traces.jsonl')
        vm=read_json(args.vision_run/'manifest.json')
        if vm['split']!=args.split or vm['hashes']!=hashes or [t['query_id'] for t in source_traces]!=[q['id'] for q in queries]:
            raise ValueError('Vision run is incomplete or has different release inputs')
        if vm['lock_sha256']!=manifest['lock_sha256']:
            raise ValueError('Vision and text stages have different locks')
        manifest.update(vision_run=args.vision_run.as_posix(),vision_trace_sha256=sha256(args.vision_run/'traces.jsonl'),
                        vision_manifest_sha256=sha256(args.vision_run/'manifest.json'),vision_runtime=vm['runtime'])
    write_json(args.output/'manifest.json',manifest)
    try:
        with (args.output/'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for n,(q,source) in enumerate(zip(queries,source_traces),1):
                trace=vision(q,retriever,client,args.pdf,elements,ocr,config) if args.stage=='vision' else finish(q,source,elements,ocr,client,config)
                trace.update(split=args.split,timestamp=now(),release_config=config['id'])
                stream.write(json.dumps(trace,ensure_ascii=False,allow_nan=False)+'\n'); stream.flush()
                print(f"{n}/{len(queries)} {q['id']} {trace['status']}",flush=True)
    finally:
        if retriever: retriever.close()
    write_json(args.output/'completion.json',{'completed_at':now(),'cases':len(queries),'trace_sha256':sha256(args.output/'traces.jsonl')})


def reviewed_score(benchmark,split,traces_path,reviews_path):
    queries=read_jsonl(benchmark/'queries'/f'{split}.jsonl'); gold=read_jsonl(benchmark/'gold'/f'{split}.jsonl')
    traces=read_jsonl(traces_path); reviews=read_jsonl(reviews_path)
    digest=sha256(traces_path)
    if any(r.get('trace_sha256')!=digest or 'failure_type' not in r or 'source_values' not in r for r in reviews):
        raise ValueError('Reviews must name the exact trace hash and include error type and checked source values')
    result=score(queries,gold,traces,reviews)
    gs={g['id']:g for g in gold}; rs={r['query_id']:r for r in reviews}
    cases=[]
    for t in traces:
        qid=t['query_id']; r=rs[qid]
        if r['pass'] and gs[qid]['answerable']:
            registry=t.get('citation_registry',{})
            if not t.get('citations') or any(c not in registry for c in t['citations']):
                raise ValueError('A passing answer requires resolved source citations')
            if any(c.get('supported') is not True for c in r.get('citation_audit',[])) or not r.get('citation_audit'):
                raise ValueError('A passing answer requires source-based citation annotations')
        usage=[t.get('usage',{}),t.get('refiner_usage',{})]
        cases.append({'query_id':qid,'group':gs[qid]['primary_group'],'pass':r['pass'],
                      'status':t['status'],'failure_type':r['failure_type'],
                      'latency_seconds':t.get('combined_elapsed_ms',t['elapsed_ms'])/1000,
                      'prompt_tokens':sum(u.get('prompt_tokens',0) for u in usage),
                      'completion_tokens':sum(u.get('completion_tokens',0) for u in usage),
                      'api_cost_usd':t.get('api_cost_usd',0),
                      'vision_protocol_error':t.get('vision_stage_status')=='error'})
    def operations(rows):
        latencies=sorted(r['latency_seconds'] for r in rows)
        import math
        return {'cases':len(rows),'errors':sum(r['status']=='error' for r in rows),
                'vision_protocol_errors':sum(r['vision_protocol_error'] for r in rows),
                'latency_seconds':{'median':statistics.median(latencies),'p95':latencies[math.ceil(.95*len(latencies))-1]},
                'prompt_tokens':sum(r['prompt_tokens'] for r in rows),
                'completion_tokens':sum(r['completion_tokens'] for r in rows),
                'api_cost_usd':sum(r['api_cost_usd'] for r in rows)}
    result.update(split=split,trace_sha256=digest,review_sha256=sha256(reviews_path),
                  operations=operations(cases),operations_by_group={group:operations([r for r in cases if r['group']==group]) for group in result['groups']},
                  cases=cases,source_verification='artifacts/source-verification.json',
                  latency_note='Sum of model-stage per-case times, excluding server startup and inter-stage waiting. Local hardware/electricity cost is not measured.')
    return result


def freeze(args):
    if args.output.exists(): raise FileExistsError('Refusing to overwrite a release lock')
    manifest=read_json(args.dev_run/'manifest.json')
    if manifest['split']!='dev' or manifest['kind']!='advanced-v2-text':
        raise ValueError('Freeze requires a complete finalized development run')
    metrics=reviewed_score(args.benchmark,'dev',args.dev_run/'traces.jsonl',args.reviews)
    if not metrics['meets_90_percent'] or any(g['n']==0 for g in metrics['groups'].values()):
        raise ValueError('Development readiness target has not been met')
    hashes=fingerprints(args)
    if manifest['hashes']!=hashes: raise ValueError('Release changed after qualifying development run')
    write_json(args.output,{'kind':'advanced-v2','frozen_at':now(),'hashes':hashes,
               'runtime':{'vision':runtime_signature(manifest['vision_runtime']),'text':runtime_signature(manifest['runtime'])},
               'dev_trace_sha256':sha256(args.dev_run/'traces.jsonl'),'dev_review_sha256':sha256(args.reviews),
               'dev_score':{k:v for k,v in metrics.items() if k!='cases'},
               'selection':'All 56 former cases treated as dev; readiness >=90%; no v2 test outputs consulted.',
               'test_policy':'All 30 predeclared cases, no replacements, all failures remain in denominator.'})
    print('Frozen after qualifying dev:',metrics['passed'],'/',metrics['total'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('validate','run','freeze','score'):
        p=sub.add_parser(command)
        p.add_argument('--benchmark',type=Path,default=ROOT/'benchmarks/advanced-v2')
        if command in ('validate','run','score'): p.add_argument('--split',choices=('dev','test'),required=True)
        if command=='validate': continue
        p.add_argument('--output',type=Path,required=True)
        if command=='score':
            p.add_argument('--traces',type=Path,required=True); p.add_argument('--reviews',type=Path,required=True)
            continue
        for flag in ('day6-root','model-path','qdrant','pdf','vision-model','projector','text-model'):
            p.add_argument('--'+flag,type=Path,required=True)
        p.add_argument('--config',type=Path,default=ROOT/'configs/advanced-v2.json')
        p.add_argument('--chunks',type=Path,default=ROOT/'artifacts/advanced/search_chunks-v5.jsonl')
        p.add_argument('--ocr',type=Path,default=ROOT/'artifacts/advanced/ocr-regions-v1.jsonl')
        if command=='run':
            p.add_argument('--stage',choices=('vision','text'),required=True)
            p.add_argument('--vision-run',type=Path); p.add_argument('--lock',type=Path)
        else:
            p.add_argument('--dev-run',type=Path,required=True); p.add_argument('--reviews',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='validate':
        print(json.dumps(validate(read_jsonl(args.benchmark/'queries'/f'{args.split}.jsonl'),
              read_jsonl(args.benchmark/'gold'/f'{args.split}.jsonl'),
              read_jsonl(ROOT/'artifacts/advanced/elements.jsonl'),args.split),ensure_ascii=False,indent=2))
    elif args.command=='run': execute(args)
    elif args.command=='freeze': freeze(args)
    else:
        result=reviewed_score(args.benchmark,args.split,args.traces,args.reviews)
        write_json(args.output,result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('cases','operations_by_group')},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
