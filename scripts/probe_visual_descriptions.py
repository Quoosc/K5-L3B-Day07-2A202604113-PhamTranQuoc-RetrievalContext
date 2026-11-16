"""Smoke-check non-benchmark visual-description retrieval against three reviewed crops."""
import argparse
from pathlib import Path

from src.day07.advanced_retrieval import AdvancedRetriever
from src.day07.common import now, sha256, write_json

CASES = [
    ('rocket taking off near a launch tower', 'landsat-v5-p009-image-001'),
    ('grayscale image with a red rectangle and red arrow', 'landsat-v5-p091-image-001'),
    ('two side by side color and grayscale images marked with red boxes', 'landsat-v5-p083-image-001'),
]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--day6-root',required=True,type=Path); p.add_argument('--model-path',required=True,type=Path)
    p.add_argument('--qdrant',required=True,type=Path); p.add_argument('--chunks',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    retriever=AdvancedRetriever(args.day6_root,args.model_path,args.qdrant,args.chunks)
    cases=[]
    try:
        for query,expected in CASES:
            result=retriever.search(query,method='hybrid',top_k=5,pool=10)
            ids=[r['evidence_id'] for r in result['results']]
            cases.append({'query':query,'expected':expected,'rank':ids.index(expected)+1 if expected in ids else None,
                          'top5':ids,'result':result})
            print(query, cases[-1]['rank'], flush=True)
    finally:
        retriever.close()
    write_json(args.output,{'created_at':now(),'kind':'three non-benchmark retrieval smoke cases, not answer quality',
               'chunks_sha256':sha256(args.chunks),'cases':cases})


if __name__=='__main__': main()
