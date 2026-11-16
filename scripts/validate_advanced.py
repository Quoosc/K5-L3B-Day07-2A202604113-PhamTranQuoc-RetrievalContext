import argparse
import json
from pathlib import Path

from src.day07.advanced_eval import validate
from src.day07.common import read_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', required=True, choices=('dev', 'test'))
    args = parser.parse_args()
    root = Path('benchmarks/advanced')
    print(json.dumps(validate(read_jsonl(root / 'queries' / f'{args.split}.jsonl'),
                              read_jsonl(root / 'gold' / f'{args.split}.jsonl'),
                              read_jsonl('artifacts/advanced/elements.jsonl'), args.split),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
