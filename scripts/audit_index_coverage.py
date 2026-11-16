"""Check structural source-region and page coverage of the advanced search export."""
import argparse
from collections import Counter
from pathlib import Path

from src.day07.common import now, read_json, read_jsonl, sha256, write_json


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--elements',required=True,type=Path); p.add_argument('--chunks',required=True,type=Path)
    p.add_argument('--pdf-manifest',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    elements=read_jsonl(args.elements); chunks=read_jsonl(args.chunks); manifest=read_json(args.pdf_manifest)
    ids={c['evidence_id'] for c in chunks}; pages={c['page'] for c in chunks}
    counts=Counter(e['element_type'] for e in elements)
    indexed=Counter(e['element_type'] for e in elements if e['evidence_id'] in ids)
    missing=[e['evidence_id'] for e in elements if e['evidence_id'] not in ids]
    expected_pages=set(range(1,manifest['pdf_pages']+1))
    write_json(args.output,{'created_at':now(),'elements_sha256':sha256(args.elements),'chunks_sha256':sha256(args.chunks),
               'indexed_pages':len(pages&expected_pages),'total_pages':manifest['pdf_pages'],
               'missing_pages':sorted(expected_pages-pages),'elements_by_type':dict(counts),
               'indexed_by_type':dict(indexed),'missing_evidence_ids':missing,
               'warning':'Structural presence of a region in search snippets is not proof that its visual meaning, labels or OCR are correct.'})
    print('Pages',len(pages&expected_pages),'/',manifest['pdf_pages'],'; missing source regions',len(missing))


if __name__=='__main__': main()
