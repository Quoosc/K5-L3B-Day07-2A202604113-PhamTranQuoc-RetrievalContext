"""One off-benchmark probe for retrieval, region opening and local vision."""
import argparse
from pathlib import Path

from src.day07.advanced_agent import run_advanced
from src.day07.advanced_retrieval import AdvancedRetriever
from src.day07.agent import ModelClient
from src.day07.common import read_json, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--day6-root', type=Path, required=True); p.add_argument('--model-path', type=Path, required=True)
    p.add_argument('--qdrant', type=Path, required=True); p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--chunks', type=Path, default=Path('artifacts/advanced/search_chunks.jsonl'))
    p.add_argument('--server', default='http://127.0.0.1:8086'); p.add_argument('--model', default='qwen2.5-vl-3b-local')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    retriever = AdvancedRetriever(args.day6_root, args.model_path, args.qdrant, args.chunks)
    try:
        query = {'id': 'advanced-smoke-outside-benchmark',
                 'question': 'In Figure 2-1 of the handbook, what label points to the central blue body of the spacecraft?'}
        result = run_advanced(query, retriever, ModelClient(args.server, args.model, timeout=180), args.pdf,
                              Path('artifacts/advanced/elements.jsonl'),
                              read_json('artifacts/advanced/pdf_manifest.json')['pdf_sha256'])
        result['synthetic_not_benchmark'] = True
        write_json(args.output, result)
        print(result['status'], result.get('answer') or result.get('error'))
    finally:
        retriever.close()


if __name__ == '__main__': main()
