"""Reparse saved dev refiner outputs, preserving original model responses and errors."""
import argparse
import json
from pathlib import Path

from scripts.refine_advanced_dev import ROOT, inputs
from src.day07.advanced_formatting import normalize_refiner_reply
from src.day07.common import now, read_jsonl, sha256, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trace', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    traces = read_jsonl(args.trace)
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    if [t['query_id'] for t in traces] != [q['id'] for q in queries] or any(t.get('split') != 'dev' for t in traces):
        raise ValueError('Only a complete, ordered dev trace may be reparsed')
    elements = {e['evidence_id']: e for e in read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')}
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / 'manifest.json', {'created_at': now(), 'split': 'dev',
               'source_trace_sha256': sha256(args.trace), 'formatting_code_sha256': sha256(ROOT / 'src/day07/advanced_formatting.py'),
               'revalidation_code_sha256': sha256(Path(__file__)), 'model_calls': 0,
               'note': 'Reparses saved raw outputs; original missing drafts/errors remain and semantic support still requires review.'})
    with (args.output / 'traces.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for original in traces:
            result = dict(original)
            result['pre_normalization_status'] = original['status']
            result['pre_normalization_error'] = original.get('error')
            raw = original.get('raw_refiner_answer')
            if raw:
                try:
                    _, registry = inputs(original, elements)
                    parsed, changes = normalize_refiner_reply(raw, registry)
                    result.update(parsed); result.pop('error', None)
                    result['format_normalization'] = changes
                except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    result.update({'status':'error','answer':'','citations':[],
                                   'error':f'{type(exc).__name__}: {exc}'})
            stream.write(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
