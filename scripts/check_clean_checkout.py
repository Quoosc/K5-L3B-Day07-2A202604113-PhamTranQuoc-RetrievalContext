"""Export the Git index to a clean source tree and verify the submitted commands.

Uses the existing pinned Python environment and explicitly supplied model/data
paths. This is a clean source checkout on the current machine, not a claim of
testing on an independent computer or in a newly installed environment.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

from src.day07.common import now, read_json, read_jsonl, sha256, write_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    for flag in ('python','day6-root','model-path','pdf','vision-model','projector','text-model','checkout','output'):
        p.add_argument('--'+flag,type=Path,required=True)
    args=p.parse_args();target=args.checkout.resolve()
    if not target.is_relative_to((ROOT/'.local').resolve()) or target.exists():
        raise ValueError('Clean export must be a new directory inside this workspace .local')
    target.mkdir(parents=True)
    subprocess.run(['git','checkout-index','--all','--prefix',target.as_posix()+'/'],cwd=ROOT,check=True,capture_output=True)
    result={'checked_at':now(),'checkout':target.as_posix(),'checks':[],
            'scope':'Clean export of Git index on same machine; existing pinned environment and external models. No claim of an independent clean machine.',
            'source_verification':'artifacts/source-verification.json'}
    def run(name,command):
        proc=subprocess.run([str(args.python.resolve()),'-X','utf8',*command],cwd=target,
                            env={**os.environ,'PYTHONUTF8':'1'},capture_output=True,text=True,encoding='utf-8')
        result['checks'].append({'name':name,'command':command,'exit_code':proc.returncode,
                                 'output':(proc.stdout+proc.stderr)[-14000:]})
        print(name,proc.returncode,flush=True)
        if proc.returncode:raise RuntimeError('Clean checkout check failed: '+name)
    try:
        for name,archive in [('base','artifacts/base/qdrant-snapshot.zip'),('advanced','artifacts/advanced/qdrant-v5-snapshot.zip')]:
            dest=target/'.local'/name;dest.mkdir(parents=True)
            with zipfile.ZipFile(target/archive) as z:
                if any(not (dest/n).resolve().is_relative_to(dest.resolve()) for n in z.namelist()):
                    raise ValueError('Unsafe archive member')
                z.extractall(dest)
        run('unit_tests',['-m','unittest','discover','-s','tests','-q'])
        for split in ('dev','test'):
            run('base_validate_'+split,['-m','src.day07','validate','--split',split])
        run('all_benchmark_structures_and_author_record',['-m','scripts.validate_submission_benchmarks','--output','.local/benchmark-check.json'])
        for config in ('D0','H0'):
            run('base_saved_trace_score_'+config,['-m','src.day07','score','--split','test',
                '--traces',f'artifacts/base/runs/base-test-20261115-v1/{config}.jsonl',
                '--output',f'.local/base-{config}-metrics.json'])
        source_check=("from pathlib import Path; from src.day07.__main__ import code_hashes; "
            "from src.day07.common import read_json; "
            "assert code_hashes(Path('configs/base.json'),Path('artifacts/base/chunks.jsonl'),Path('benchmarks/base'))==read_json('artifacts/base/freeze.json')['hashes']; "
            "print('Frozen base source, benchmark and corpus bytes preserved in checkout')")
        run('frozen_bytes_survive_git_checkout',['-c',source_check])
        if (target/'artifacts/advanced/freeze-v2.json').is_file():
            values={'day6_root':str(args.day6_root.resolve()),'model_path':str(args.model_path.resolve()),
                    'qdrant':str(target/'.local/advanced'),'pdf':str(args.pdf.resolve()),
                    'vision_model':str(args.vision_model.resolve()),'projector':str(args.projector.resolve()),
                    'text_model':str(args.text_model.resolve()),'config':'configs/advanced-v2.json',
                    'chunks':'artifacts/advanced/search_chunks-v5.jsonl','ocr':'artifacts/advanced/ocr-regions-v1.jsonl',
                    'benchmark':'benchmarks/advanced-v2'}
            expression=', '.join(k+'=Path('+repr(v)+')' for k,v in values.items())
            check=("from argparse import Namespace; from pathlib import Path; "
                   "from scripts.advanced_release import fingerprints; from src.day07.common import read_json; "
                   "inputs=Namespace("+expression+"); "
                   "assert fingerprints(inputs)==read_json('artifacts/advanced/freeze-v2.json')['hashes']; "
                   "print('All advanced code, benchmark, model, PDF and restored index hashes match the pre-test lock')")
            run('advanced_release_bytes_and_restored_index',['-c',check])
        # Use an explicitly short development probe. The full historical
        # benchmark still includes its malformed/overlong model answers; this
        # smoke checks the native tool/context/answer path without grading or
        # replacing those test results.
        smoke_benchmark=target/'.local/smoke-benchmark'
        for folder in ('queries','gold'):
            (smoke_benchmark/folder).mkdir(parents=True)
            for split in ('dev','test'):
                rows=[{'id':'clean-smoke-json-error','split':'dev',
                    'question':'What exception does json.loads raise when the input is not a valid JSON document? Answer in one short sentence.'}] if folder=='queries' and split=='dev' else []
                (smoke_benchmark/folder/f'{split}.jsonl').write_text(
                    ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8',newline='\n')
        run('base_real_model_dev_smoke',['-m','src.day07','run','--day6-root',str(args.day6_root.resolve()),
            '--qdrant',str(target/'.local/base'),'--model-path',str(args.model_path.resolve()),
            '--benchmark',str(smoke_benchmark),
            '--config','D0','--split','dev','--run-id','clean-source-smoke','--limit','1'])
        smoke=target/'artifacts/base/runs/clean-source-smoke/D0.jsonl'
        rows=read_jsonl(smoke)
        if len(rows)!=1 or rows[0]['status']=='error' or not rows[0].get('context',{}).get('entries'):
            raise ValueError('Clean checkout model smoke did not produce a valid sourced response')
        smoke_out=ROOT/'artifacts/clean-checkout-smoke';smoke_out.mkdir(exist_ok=False)
        shutil.copy2(smoke,smoke_out/'D0.jsonl')
        shutil.copy2(smoke.parent/'manifest.json',smoke_out/'manifest.json')
        result['model_smoke']={'status':rows[0]['status'],'query_id':rows[0]['query_id'],
            'trace':'artifacts/clean-checkout-smoke/D0.jsonl','trace_sha256':sha256(smoke),
            'note':'Development smoke only; original test results are not replaced.'}
        result['all_checks_pass']=all(c['exit_code']==0 for c in result['checks'])
    except Exception as exc:
        result['all_checks_pass']=False;result['error']=f'{type(exc).__name__}: {exc}'
        write_json(args.output,result)
        raise
    write_json(args.output,result)
    print('Clean source checkout checks passed:',len(result['checks']))


if __name__=='__main__':main()
