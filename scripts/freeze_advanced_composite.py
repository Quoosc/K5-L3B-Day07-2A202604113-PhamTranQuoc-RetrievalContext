"""Freeze a source-reviewed advanced composite only after a complete qualifying dev run."""
import argparse
from pathlib import Path

from scripts.run_advanced import ROOT, external_hashes, fingerprint
from src.day07.advanced_eval import score
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.composite_lock import composite_hashes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dev-run',required=True,type=Path); p.add_argument('--reviews',required=True,type=Path)
    p.add_argument('--day6-root',required=True,type=Path); p.add_argument('--model-path',required=True,type=Path)
    p.add_argument('--qdrant',required=True,type=Path); p.add_argument('--chunks',required=True,type=Path)
    p.add_argument('--ocr',required=True,type=Path); p.add_argument('--pdf',required=True,type=Path)
    p.add_argument('--projector',required=True,type=Path); p.add_argument('--vision-model',required=True,type=Path)
    p.add_argument('--text-model',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--benchmark',default=ROOT/'benchmarks/advanced',type=Path)
    p.add_argument('--config',default=ROOT/'configs/advanced.json',type=Path)
    p.add_argument('--rationale',required=True)
    args=p.parse_args()
    manifest=read_json(args.dev_run/'manifest.json')
    if manifest['split']!='dev': raise ValueError('Freeze requires a development run')
    traces=read_jsonl(args.dev_run/'traces.jsonl'); reviews=read_jsonl(args.reviews)
    queries=read_jsonl(args.benchmark/'queries/dev.jsonl'); gold=read_jsonl(args.benchmark/'gold/dev.jsonl')
    metrics=score(queries,gold,traces,reviews)
    if not metrics['meets_90_percent'] or any(g['n']<1 for g in metrics['groups'].values()):
        raise ValueError('Complete source-reviewed dev must reach 90% and pass at least one case in every group')
    hashes=fingerprint(args.pdf,args.chunks,args.benchmark,args.config,args.ocr)
    externals=external_hashes(args.day6_root,args.model_path,args.qdrant,args.projector)
    components=composite_hashes()
    if (manifest['hashes']!=hashes or manifest['external_hashes']!=externals or
            manifest['composite_hashes']!=components or manifest['input_checks']['model_sha256']!=sha256(args.vision_model) or
            manifest['text_model_sha256']!=sha256(args.text_model)):
        raise ValueError('Code, data, index or model differs from the qualifying dev run')
    vision_run=Path(manifest['vision_run']); vm=read_json(vision_run/'manifest.json')
    if (sha256(vision_run/'traces.jsonl')!=manifest['vision_trace_sha256'] or
            sha256(vision_run/'manifest.json')!=manifest['vision_manifest_sha256']):
        raise ValueError('Qualifying vision trace or manifest changed')
    lock={'kind':'advanced-composite','frozen_at':now(),'model':vm['model'],
          'model_sha256':sha256(args.vision_model),'text_model':manifest['text_model'],
          'text_model_sha256':sha256(args.text_model),'hashes':hashes,'external_hashes':externals,
          'composite_hashes':components,'dev_trace_sha256':sha256(args.dev_run/'traces.jsonl'),
          'dev_review_sha256':sha256(args.reviews),'dev_summary':metrics,'rationale':args.rationale,
          'limitations':'A qualifying dev score is not an independent test or proof of source/index completeness.'}
    write_json(args.output,lock)
    print('Frozen advanced composite after reviewed development:',metrics['passed'],'/',metrics['total'])


if __name__=='__main__': main()
