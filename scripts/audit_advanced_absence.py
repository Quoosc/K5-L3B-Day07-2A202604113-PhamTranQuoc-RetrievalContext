"""Search full extracted PDF text and unverified OCR for absent benchmark entities."""
import argparse
import json
from pathlib import Path
import re
import unicodedata

from src.day07.common import now, read_json, read_jsonl, sha256, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


def normalize(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def main():
    import fitz
    p = argparse.ArgumentParser()
    p.add_argument('--pdf', required=True, type=Path)
    p.add_argument('--ocr', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    manifest = read_json(ROOT / 'artifacts/advanced/pdf_manifest.json')
    if sha256(args.pdf) != manifest['pdf_sha256']:
        raise ValueError('PDF hash differs from the indexed document')
    ocr = read_jsonl(args.ocr)
    required = {e['evidence_id'] for e in read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')
                if e['element_type'] in ('image','vector_page')}
    if {r['evidence_id'] for r in ocr} != required:
        raise ValueError('OCR records do not match the indexed image/vector candidates')
    doc = fitz.open(args.pdf)
    pages = [normalize(page.get_text('text')) for page in doc]
    doc.close()
    ocr_text = {r['evidence_id']:normalize(' '.join(line['text'] for line in r.get('lines', []))) for r in ocr}
    records = []
    for split in ('dev','test'):
        for g in read_jsonl(ROOT / 'benchmarks/advanced/gold' / f'{split}.jsonl'):
            if g['answerable']: continue
            for entity in g['fact_keys']:
                term = normalize(entity)
                records.append({'query_id':g['id'], 'split':split, 'entity':entity,
                                'pdf_text_pages':[i+1 for i, text in enumerate(pages) if term in text],
                                'ocr_regions':[eid for eid, text in ocr_text.items() if term in text],
                                'scope':'Exact normalized entity phrase in extracted text and unverified OCR only',
                                'limitation':'A missing OCR match does not prove the image or PDF lacks the concept.'})
    if args.output.exists(): raise FileExistsError(args.output)
    write_jsonl(args.output, records)
    write_json(args.output.with_suffix('.summary.json'), {'created_at':now(), 'pdf_sha256':sha256(args.pdf),
               'ocr_sha256':sha256(args.ocr), 'pages_scanned':len(pages), 'ocr_regions_scanned':len(ocr),
               'ocr_empty_regions':sum(not r.get('lines') for r in ocr), 'entities':len(records),
               'entities_found_in_text_or_ocr':sum(bool(r['pdf_text_pages'] or r['ocr_regions']) for r in records),
               'warning':'Literal matching and imperfect OCR do not replace visual or semantic absence review.'})
    print(json.dumps({'pages':len(pages),'ocr_regions':len(ocr),'entities':len(records),
                      'found':sum(bool(r['pdf_text_pages'] or r['ocr_regions']) for r in records)}))


if __name__ == '__main__': main()
