"""Aggregate a complete set of source-reviewed binary verdicts."""
import argparse
import json
from pathlib import Path

from src.day07.advanced_eval import score
from src.day07.common import read_jsonl, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--split', choices=('dev', 'test'), required=True)
    p.add_argument('--traces', type=Path, required=True); p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = Path('benchmarks/advanced')
    report = score(read_jsonl(root / 'queries' / f'{args.split}.jsonl'),
                   read_jsonl(root / 'gold' / f'{args.split}.jsonl'),
                   read_jsonl(args.traces), read_jsonl(args.reviews))
    report['split'] = args.split
    write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
