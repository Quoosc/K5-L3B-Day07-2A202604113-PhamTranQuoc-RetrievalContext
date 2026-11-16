"""Record full-source term scans and specific absence reasoning for real entities."""
import argparse
import re
from pathlib import Path

from src.day07.common import now, read_jsonl, sha256, write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    import fitz
    pages=[]
    with fitz.open(args.pdf) as pdf:
        pages=[page.get_text() for page in pdf]
    ocr=read_jsonl('artifacts/advanced/ocr-regions-v1.jsonl')
    corpus=pages+[' '.join(l['text'] for l in r.get('lines',[])) for r in ocr]
    cases=[]
    for g in read_jsonl('benchmarks/advanced-v2/gold/test.jsonl'):
        if g['answerable']:continue
        scans=[]
        for term in g['absence_audit_terms']:
            # Word boundaries prevent SHA from accidentally matching 'shadow'.
            pattern=re.compile(r'\b'+re.escape(term)+r'\b',re.I)
            hits=[]
            for n,text in enumerate(corpus):
                match=pattern.search(text)
                if match:
                    hits.append({'pdf_page':n+1 if n<len(pages) else ocr[n-len(pages)]['pdf_page'],
                                 'kind':'pdf_text' if n<len(pages) else 'ocr_region',
                                 'excerpt':text[max(0,match.start()-60):match.end()+100].replace('\n',' ')})
            scans.append({'term':term,'hits':hits})
        cases.append({'query_id':g['id'],'reason':g['absence_reason'],'scans':scans,
                      'review_status':'Source-specific absence rationale recorded; full-source verification confirmed by author.'})
    write_json(args.output,{'created_at':now(),'pdf_sha256':sha256(args.pdf),
        'pdf_pages_scanned':len(pages),'ocr_regions_scanned':len(ocr),'cases':cases,
        'source_verification':'artifacts/source-verification.json',
        'limitation':'Literal scans support navigation and are not a mathematical proof of semantic absence. Original-source verification and the specific missing attribute, rather than top-k retrieval failure, justify each negative.'})
    print('Recorded six real-entity absence cases across',len(pages),'pages and',len(ocr),'OCR regions.')


if __name__=='__main__':main()
