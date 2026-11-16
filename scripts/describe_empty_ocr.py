"""Attach manually inspected, limited visual descriptions to the ten empty-OCR regions."""
import argparse
from pathlib import Path

from src.day07.common import now, read_jsonl, sha256, write_json, write_jsonl

DESCRIPTIONS = {
    'landsat-v5-p009-image-001':'Photograph of a rocket launching beside a launch tower.',
    'landsat-v5-p044-image-001':'Dark grayscale image with one narrow, nearly vertical bright streak.',
    'landsat-v5-p061-image-001':'Tilted grayscale rectangular image on a black background with light and dark areas.',
    'landsat-v5-p083-image-001':'Two side-by-side images, one colored and one pale grayscale, each with a red rectangle.',
    'landsat-v5-p088-image-001':'Grayscale image with several narrow dark diagonal streaks.',
    'landsat-v5-p089-image-001':'Grayscale image with nearly vertical light and dark bands.',
    'landsat-v5-p090-image-001':'Grayscale image with irregular light and dark areas and faint bands.',
    'landsat-v5-p091-image-001':'High-contrast grayscale image with a red rectangle and a red arrow.',
    'landsat-v5-p092-image-001':'Grayscale textured image crossed by bright curved and diagonal lines.',
    'landsat-v5-p094-image-001':'Dark grayscale image with two small groups of bright dots.',
}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--elements',required=True,type=Path); p.add_argument('--ocr',required=True,type=Path)
    p.add_argument('--descriptions',required=True,type=Path); p.add_argument('--elements-output',required=True,type=Path)
    args=p.parse_args()
    if args.descriptions.exists() or args.elements_output.exists():
        raise FileExistsError('Refusing to overwrite descriptions or elements')
    elements=read_jsonl(args.elements); ocr=read_jsonl(args.ocr)
    empty={r['evidence_id'] for r in ocr if r.get('status')=='ok' and not r.get('lines')}
    if empty != set(DESCRIPTIONS): raise ValueError('The empty-OCR region inventory changed')
    records=[]; output=[]
    for e in elements:
        row=dict(e); eid=e['evidence_id']
        if eid in DESCRIPTIONS:
            desc=DESCRIPTIONS[eid]
            records.append({'evidence_id':eid,'pdf_page':e['pdf_page'],'bbox':e['bbox'],'description':desc,
                            'method':'Codex visual inspection of original PDF crop at 110 DPI',
                            'status':'AI-observed; independent human review pending',
                            'warning':'Qualitative observation, not a scientific interpretation or source evidence.'})
            row['content'] += '\nAI-observed visual description, not independently verified: ' + desc
            row['warning']='Contains an AI-observed visual description; inspect the original PDF crop.'
        output.append(row)
    if len(records)!=len(DESCRIPTIONS): raise ValueError('A reviewed region was not found in the inventory')
    write_jsonl(args.descriptions,records); write_jsonl(args.elements_output,output)
    write_json(args.descriptions.with_suffix('.summary.json'), {'created_at':now(),
               'source_elements_sha256':sha256(args.elements),'ocr_sha256':sha256(args.ocr),
               'description_count':len(records),'descriptions_sha256':sha256(args.descriptions),
               'augmented_elements_sha256':sha256(args.elements_output),
               'warning':'Only the ten OCR-empty candidates are described; the remaining visuals need further semantic audit.'})
    print(f'Described {len(records)} of {len(ocr)} OCR candidates')


if __name__=='__main__': main()
