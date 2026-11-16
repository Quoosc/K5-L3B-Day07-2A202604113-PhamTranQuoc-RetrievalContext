"""Structural benchmark checks combined with the separately recorded author audit."""
import argparse
import json
from pathlib import Path

from src.day07.advanced_eval import validate as advanced_validate
from src.day07.common import now, read_json, read_jsonl, write_json
from src.day07.evaluation import validate as base_validate

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    confirmation=read_json(ROOT/'artifacts/source-verification.json')
    if confirmation['status']!='AUTHOR_SOURCE_VERIFICATION_CONFIRMED':
        raise ValueError('Author source-verification record missing')
    result={'checked_at':now(),'source_verification':confirmation,'benchmarks':{}}
    for name in ('base','advanced','advanced-v2'):
        root=ROOT/'benchmarks'/name
        source=read_jsonl(ROOT/('artifacts/base/chunks.jsonl' if name=='base' else 'artifacts/advanced/elements.jsonl'))
        splits={}
        facts={}
        for split in ('dev','test'):
            qs=read_jsonl(root/'queries'/f'{split}.jsonl');gs=read_jsonl(root/'gold'/f'{split}.jsonl')
            if name!='base':
                answerable=sum(g['answerable'] for g in gs)
                missing=len(gs)-answerable
                required=(15,3) if split=='dev' else (24,6)
                if answerable<required[0] or missing<required[1]:
                    raise ValueError('Insufficient answerable/absence cases: '+name+'/'+split)
            checked=(base_validate if name=='base' else advanced_validate)(qs,gs,source,split)
            # Generic validator warnings describe what it cannot prove. Source
            # confirmation is an independent author record, never inferred from
            # a successful structural validator.
            splits[split]={'structural_validation':checked,
                'source_verification_status':confirmation['status'],
                'source_verification_record':'artifacts/source-verification.json'}
            facts[split]={key for g in gs for key in g.get('fact_keys',[])}
        if facts['dev'] & facts['test']:
            raise ValueError('Cross-split fact-key overlap: '+name)
        result['benchmarks'][name]={'splits':splits,'fact_overlap':[]}
    write_json(args.output,result)
    print('Validated all six benchmark splits; author source-verification record attached.')


if __name__=='__main__':main()
