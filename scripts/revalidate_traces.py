"""Re-evaluate stored model output after a parser change without another model call."""
import argparse
from pathlib import Path

from src.day07.agent import parse_answer
from src.day07.common import now, read_jsonl, write_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    traces = read_jsonl(args.input)
    for trace in traces:
        if trace.get('status') != 'error' or not trace.get('raw_answer') or not trace.get('context'):
            continue
        registry = {entry['alias']: {key: entry[key] for key in ('id', 'source_id', 'source', 'page',
                                                                  'start_offset', 'end_offset')}
                    for entry in trace['context']['entries']}
        try:
            parsed = parse_answer(trace['raw_answer'], registry)
        except ValueError:
            continue
        trace['parser_revalidation'] = {'at': now(), 'previous_status': trace['status'],
                                        'previous_error': trace.get('error'),
                                        'reason': 'Parser accepts citations on abstentions and repeated references to the same ID; citation support still requires review.',
                                        'model_called_again': False}
        trace.update(parsed)
        trace['stop_reason'] = 'model_answer' if trace['status'] == 'answered' else 'model_abstain'
        trace.pop('error', None)
    write_jsonl(args.output, traces)
    print(f'Revalidated {len(traces)} stored traces; no model calls.')


if __name__ == '__main__': main()
