"""Audit submitted source coverage without modifying or querying the agent index."""
import argparse
from collections import Counter
from pathlib import Path

from src.day07.common import now, read_json, read_jsonl, sha256, write_json

ROOT=Path(__file__).resolve().parents[1]


def main():
    import fitz
    p=argparse.ArgumentParser()
    p.add_argument('--pdf',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    original=read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')
    regions=read_jsonl(ROOT/'artifacts/advanced/catalog-v7/regions.jsonl')
    chunks=read_jsonl(ROOT/'artifacts/advanced/catalog-v7/chunks.jsonl')
    source={r['evidence_id']:r for r in original}
    mapped={r['evidence_id']:r for r in regions}
    v6=read_json(ROOT/'artifacts/advanced/catalog-v6/manifest.json')
    v7=read_json(ROOT/'artifacts/advanced/catalog-v7/manifest.json')
    benchmark=read_json(ROOT/'benchmarks/advanced-v3/manifest.json')
    with fitz.open(args.pdf) as doc:
        page_text=[page.get_text() for page in doc]
        valid_bounds=all(0<=r['bbox'][0]<r['bbox'][2]<=doc[r['page']-1].rect.width+1 and
                         0<=r['bbox'][1]<r['bbox'][3]<=doc[r['page']-1].rect.height+1 for r in regions)
    checks={
        'original_pdf_digest':sha256(args.pdf)==v6['pdf_sha256'],
        'all_114_pages':len(page_text)==114 and {r['page'] for r in regions}==set(range(1,115)),
        'all_852_original_regions':len(regions)==len(mapped)==len(source)==852 and set(mapped)==set(source),
        'original_locators_preserved':all(r['page']==source[eid]['pdf_page'] and r['bbox']==source[eid]['bbox'] and
                                        r['printed_label']==source[eid]['printed_label'] for eid,r in mapped.items()),
        'locators_inside_original_page':valid_bounds,
        'every_region_has_search_chunk':{r['evidence_id'] for r in chunks}==set(source),
        '941_unique_chunks':len(chunks)==len({r['id'] for r in chunks})==941,
        'all_49_images_described':sum(r['metadata']['element_type']=='image' and len(r['text'])>40 for r in regions)==49,
        'all_31_table_candidates_retained':sum(r['metadata']['element_type']=='table_candidate' and 'automatic_table_cells' in r for r in regions)==31,
        'source_precedes_benchmark':v6['created_at']<v7['created_at']<benchmark['created_at'],
        'builder_digests_match':sha256(ROOT/'scripts/build_catalog_v6.py')==v6['builder_sha256'] and
                                sha256(ROOT/'scripts/enrich_catalog_v7.py')==v7['builder_sha256'],
        'source_only_builder_declaration':v6['benchmark_inputs_read'] is False and v7['benchmark_inputs_read'] is False,
        'author_source_confirmation':read_json(ROOT/'artifacts/source-verification.json')['status']=='AUTHOR_SOURCE_VERIFICATION_CONFIRMED',
    }
    # Term hits locate relevant chapters. They are supplementary absence checks,
    # not a proof that no semantic answer exists anywhere in a figure.
    terms={
        'adv3-test-025':['TIRS','MHz','processor','clock'],
        'adv3-test-026':['EarthExplorer','API','rate limit','requests per second'],
        'adv3-test-027':['EROS','employees','headcount'],
        'adv3-test-028':['GloVis','uptime','availability'],
        'adv3-test-029':['CFMask','training','decision trees'],
        'adv3-test-030':['LandsatLook','Android','operating system'],
    }
    negatives={g['id']:g for g in read_jsonl(ROOT/'benchmarks/advanced-v3/gold/test.jsonl') if not g['answerable']}
    absence=[{'query_id':qid,'reason':negatives[qid]['absence_reason'],
              'original_text_hits':{term:[i for i,text in enumerate(page_text,1) if term.casefold() in text.casefold()] for term in words},
              'review_scope':negatives[qid]['absence_audit_scope'],
              'source_verification':'artifacts/source-verification.json',
              'limit':'Literal term hits only assist locating source sections; author source verification and original-source review are recorded separately.'}
             for qid,words in terms.items()]
    result={'checked_at':now(),'checks':checks,'all_checks_pass':all(checks.values()),
        'source_counts':dict(Counter(r['metadata']['element_type'] for r in regions)),
        'pdf_sha256':sha256(args.pdf),'catalog_regions_sha256':sha256(ROOT/'artifacts/advanced/catalog-v7/regions.jsonl'),
        'catalog_chunks_sha256':sha256(ROOT/'artifacts/advanced/catalog-v7/chunks.jsonl'),
        'index_policy':'All source regions retained; source-only descriptions/transcriptions, not benchmark answer injection. This script reads gold solely for a separate audit and does not write the retrieval corpus or index.',
        'limits':v6['limits'],'absence_audits':absence}
    write_json(args.output,result)
    print('Source catalog checks:',sum(checks.values()),'/',len(checks))
    if not result['all_checks_pass']:raise SystemExit(1)


if __name__=='__main__':main()
