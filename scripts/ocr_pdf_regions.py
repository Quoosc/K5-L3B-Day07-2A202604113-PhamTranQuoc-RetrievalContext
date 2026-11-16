"""OCR every indexed image/vector candidate locally; output coordinates and uncertainty."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from src.day07.common import now, read_jsonl, sha256, write_json


def main():
    import fitz
    import numpy as np
    from rapidocr import RapidOCR
    p = argparse.ArgumentParser()
    p.add_argument('--pdf', type=Path, required=True); p.add_argument('--elements', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--dpi', type=int, default=200)
    p.add_argument('--pages', help='Optional comma-separated PDF pages for a non-benchmark probe')
    args = p.parse_args()
    if args.dpi < 72 or args.dpi > 400: raise ValueError('DPI must be between 72 and 400')
    pages = set(map(int, args.pages.split(','))) if args.pages else None
    elements = [e for e in read_jsonl(args.elements) if e['element_type'] in ('image', 'vector_page')
                and (pages is None or e['pdf_page'] in pages)]
    if args.output.exists(): raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open(args.pdf); engine = RapidOCR(); started = time.perf_counter()
    pdf_hash = sha256(args.pdf); failures = 0
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        for n, e in enumerate(elements, 1):
            item = {'evidence_id': e['evidence_id'], 'pdf_page': e['pdf_page'], 'region_bbox': e['bbox'],
                    'dpi': args.dpi, 'pdf_sha256': pdf_hash, 'extractor': 'RapidOCR ' + importlib.metadata.version('rapidocr'),
                    'note': 'Unverified OCR; use original PDF and confidence/coordinates for review.'}
            try:
                page = pdf[e['pdf_page'] - 1]; rect = fitz.Rect(e['bbox']) & page.rect
                pix = page.get_pixmap(dpi=args.dpi, clip=rect, alpha=False)
                pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                image = pixels[:, :, :3][:, :, ::-1].copy()
                result = engine(image)
                boxes = result.boxes if result.boxes is not None else []
                texts = result.txts if result.txts is not None else []
                scores = result.scores if result.scores is not None else []
                lines = []
                for box, text, conf in zip(boxes, texts, scores):
                    x = [float(pt[0]) * 72 / args.dpi + rect.x0 for pt in box]
                    y = [float(pt[1]) * 72 / args.dpi + rect.y0 for pt in box]
                    lines.append({'text': str(text), 'confidence': round(float(conf), 4),
                                  'bbox': [round(min(x),2), round(min(y),2), round(max(x),2), round(max(y),2)]})
                item.update({'status':'ok', 'lines':lines,
                             'crop_sha256':hashlib.sha256(pix.tobytes('png')).hexdigest()})
            except Exception as exc:
                failures += 1; item.update({'status':'error', 'lines':[], 'error':f'{type(exc).__name__}: {exc}'})
            stream.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + '\n'); stream.flush()
            print(f"OCR {n}/{len(elements)} {e['evidence_id']} {item['status']} lines={len(item['lines'])}", flush=True)
    write_json(args.output.with_suffix('.summary.json'), {'created_at': now(), 'regions':len(elements),
               'errors':failures, 'pdf_sha256':pdf_hash, 'dpi':args.dpi,
               'elapsed_seconds':time.perf_counter()-started, 'ocr_sha256':sha256(args.output),
               'scope': 'All indexed image/vector candidates' if pages is None else f'Probe pages {sorted(pages)}',
               'warning':'OCR is not independently verified and may miss or distort labels, numbers and table structure.'})


if __name__ == '__main__': main()
