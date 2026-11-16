"""Inventory a PDF and extract auditable candidate regions; not a vision review."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .common import now, read_jsonl, sha256, write_json, write_jsonl

SOURCE = 'https://www.usgs.gov/media/files/landsat-8-data-users-handbook'


def bbox(values):
    return [round(float(value), 2) for value in values]


def content_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def footer_label(page, blocks):
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        if y0 > page.rect.height * .85:
            match = re.search(r'-\s*([ivxlcdm]+|\d+)\s*-', text, re.IGNORECASE)
            if match:
                return match.group(1)
    return None


def build(pdf_path: Path, out: Path):
    import fitz
    pdf = fitz.open(pdf_path)
    if len(pdf) < 100:
        raise ValueError('The challenge requires at least 100 PDF pages')
    out.mkdir(parents=True, exist_ok=True)
    for name in ('elements.jsonl', 'page_inventory.jsonl', 'pdf_manifest.json'):
        if (out / name).exists():
            raise FileExistsError(f'Refusing to overwrite {out / name}')
    pdf_hash = sha256(pdf_path)
    elements, inventory = [], []
    section = None
    for number, page in enumerate(pdf, 1):
        blocks = page.get_text('blocks', sort=True)
        label = footer_label(page, blocks)
        before = len(elements)
        counts = Counter()

        def add(kind, box, content, **extra):
            counts[kind] += 1
            eid = f'landsat-v5-p{number:03d}-{kind}-{counts[kind]:03d}'
            elements.append({'evidence_id': eid, 'doc_id': 'LSDS-1574-v5.0',
                             'pdf_page': number, 'printed_label': label, 'bbox': bbox(box),
                             'page_size_points': bbox((0, 0, page.rect.width, page.rect.height))[2:],
                             'element_type': kind, 'section': section, 'content': content,
                             'content_sha256': content_hash(content), 'source': SOURCE,
                             'crop_ref': f'{eid}.png', 'extraction': 'PyMuPDF ' + fitz.VersionBind,
                             **extra})

        for block in blocks:
            x0, y0, x1, y1, text, _, kind = block
            if kind != 0 or not text.strip():
                continue
            text = text.strip()
            first = text.splitlines()[0].strip()
            if re.match(r'^(Section\s+\d+\b|\d+(?:\.\d+){1,3}\s+\S)', first):
                section = first[:160]
            add('text', (x0, y0, x1, y1), text, reading_order='PyMuPDF sort=True; verify columns manually')
        captions = [b[4].strip() for b in blocks if b[6] == 0 and
                    re.search(r'\b(?:Figure|Table)\s+[A-Z\d]+[-.]\d+', b[4])]
        for img in page.get_image_info(xrefs=True):
            add('image', img['bbox'], '\n'.join(captions), xref=img.get('xref'),
                warning='Image region is indexed by nearby page captions only; its visual content is not transcribed or verified.')
        drawings = page.get_drawings()
        if len(drawings) >= 10:
            add('vector_page', page.rect, '\n'.join(captions), drawing_count=len(drawings),
                warning='Page-level candidate for vector graphics; not a verified figure or chart boundary.')
        try:
            tables = page.find_tables().tables
            for table in tables:
                values = table.extract()
                cells = [[bbox(cell) if cell is not None else None for cell in row.cells] for row in table.rows]
                add('table_candidate', table.bbox, json.dumps(values, ensure_ascii=False),
                    rows=values, cell_bboxes=cells,
                    warning='Automatic table candidate; merged headers, units and cells require visual review.')
            table_error = None
        except Exception as exc:
            table_error = f'{type(exc).__name__}: {exc}'
        inventory.append({'pdf_page': number, 'printed_label': label, 'section': section,
                          'counts': dict(counts), 'indexed_elements': len(elements) - before,
                          'drawings': len(drawings), 'table_extraction_error': table_error,
                          'status': 'candidate_regions_extracted' if len(elements) > before else 'no_extractable_elements',
                          'limitations': ['visual contents and table structure not yet verified',
                                          'OCR not performed for any image-only text']})
    write_jsonl(out / 'elements.jsonl', elements)
    write_jsonl(out / 'page_inventory.jsonl', inventory)
    counts = Counter(e['element_type'] for e in elements)
    manifest = {'created_at': now(), 'source': SOURCE,
                'pdf_url': 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-1574_L8_Data_Users_Handbook-v5.0.pdf',
                'document': 'Landsat 8 Data Users Handbook LSDS-1574 v5.0 (November 2019)',
                'pdf_sha256': pdf_hash, 'pdf_pages': len(pdf), 'indexed_pages': sum(x['indexed_elements'] > 0 for x in inventory),
                'element_counts': dict(counts), 'coordinate_system': 'PDF points, top-left origin, 1-based PDF pages',
                'extractor': 'PyMuPDF ' + fitz.VersionBind, 'rights': 'USGS source page: Public Domain; individual third-party images must be checked.',
                'status': 'PARTIAL: candidates only, not an audited multimodal index',
                'limitations': ['No OCR or vision description; text embedded in pictures is not searchable.',
                                'Table candidates and vector page boxes require manual source comparison.',
                                'No claim that all useful visual content has been interpreted.',
                                'No benchmark, independent test, or 90 percent result is implied by this inventory.'],
                'hashes': {'elements.jsonl': sha256(out / 'elements.jsonl'),
                           'page_inventory.jsonl': sha256(out / 'page_inventory.jsonl')}}
    write_json(out / 'pdf_manifest.json', manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def render(pdf_path: Path, index: Path, evidence_id: str, output: Path, dpi: int):
    import fitz
    entries = [e for e in read_jsonl(index) if e['evidence_id'] == evidence_id]
    if len(entries) != 1:
        raise ValueError('Evidence ID must resolve to exactly one indexed region')
    entry = entries[0]
    pdf = fitz.open(pdf_path)
    page = pdf[entry['pdf_page'] - 1]
    region = fitz.Rect(entry['bbox']) & page.rect
    if region.is_empty:
        raise ValueError('Evidence region is outside the page')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing crop')
    page.get_pixmap(dpi=dpi, clip=region, alpha=False).save(output)
    print(json.dumps({'evidence_id': evidence_id, 'pdf_page': entry['pdf_page'],
                      'bbox': entry['bbox'], 'dpi': dpi, 'output': str(output)}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--pdf', type=Path, required=True); b.add_argument('--output', type=Path, required=True)
    r = sub.add_parser('render-region'); r.add_argument('--pdf', type=Path, required=True); r.add_argument('--index', type=Path, required=True)
    r.add_argument('--evidence-id', required=True); r.add_argument('--output', type=Path, required=True); r.add_argument('--dpi', type=int, default=150)
    args = p.parse_args()
    if args.command == 'build': build(args.pdf, args.output)
    else: render(args.pdf, args.index, args.evidence_id, args.output, args.dpi)


if __name__ == '__main__':
    main()
