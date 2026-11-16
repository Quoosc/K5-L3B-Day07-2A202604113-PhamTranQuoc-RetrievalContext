"""Declare a fresh 30-case holdout after source-only catalog curation.

No evaluation outputs are read. The former 86 cases are development data.
"""
from collections import Counter
from pathlib import Path
from src.day07.common import now,read_jsonl,sha256,write_json,write_jsonl
from src.day07.advanced_eval import validate

ROOT=Path(__file__).resolve().parents[1]


def main():
    target=ROOT/'benchmarks/advanced-v3'
    elements=read_jsonl(ROOT/'artifacts/advanced/elements.jsonl');es={e['evidence_id']:e for e in elements}
    qs=[];gs=[]
    def add(group,question,answer,fact,sources,tolerance=None,calculation=None):
        qid=f'adv3-test-{len(qs)+1:03d}';qs.append({'id':qid,'split':'test','question':question})
        evidence=[]
        for eid,locator,value in sources:
            e=es[eid];ev={'evidence_id':eid,'pdf_page':e['pdf_page'],'printed_label':e['printed_label'],
                         'bbox':e['bbox'],'locator':locator,'source_value':value}
            if tolerance is not None:ev['absolute_tolerance']=tolerance
            evidence.append([ev])
        gs.append({'id':qid,'split':'test','answerable':True,'primary_group':group,'expected_answer':answer,
                   'fact_keys':[fact],'evidence_groups':evidence,'absolute_tolerance':tolerance,
                   'calculation':calculation,'review_reason':'Original source checked; new attribute/cell/relation relative to both prior benchmark versions.'})
    add('table','Compare the compression entries for Landsat 7 and Landsat 8 in Table 1-1.',
        'Landsat 7: No compression; Landsat 8: approximately 2:1 Variable Rice Compression.','compression_l7_l8',
        [('landsat-v5-p013-table_candidate-001','Compression row, both satellite columns','No; ~2:1 Variable Rice Compression')])
    add('table','For the OLI Band 4 row of Table 2-2, what ETM+ band and ETM+ performance SNR are listed?',
        'ETM+ Band 3; ETM+ performance SNR 28.','oli4_etm_band_and_performance',
        [('landsat-v5-p019-table_candidate-001','OLI Band 4 row, ETM+ Band and ETM+ Performance columns','3; 28')])
    add('table','What NEDT value is listed for TIRS Band 10 at 320 in Table 2-3?',
        '0.046.','nedt_10_320',[('landsat-v5-p022-table_candidate-001','TIRS 10 row, NEDT@320 column','0.046')])
    add('table','In Table 3-4, what does the SS2 field mean in the effective ending timestamp?',
        'Two-digit effective ending seconds.','bpf_end_seconds',
        [('landsat-v5-p050-table_candidate-001','SS2 row','Two-digit effective ending seconds')])
    add('table','According to Table 4-1, expand the RT, T1 and T2 codes in the TX collection-category field.',
        'RT = Real-Time; T1 = Tier 1; T2 = Tier 2.','collection_category_codes',
        [('landsat-v5-p059-table_candidate-001','TX row','RT = Real-Time; T1 = Tier 1; T2 = Tier 2')])
    add('table','Read the color cells in Table 5-4: which colors denote Cloud Shadow and Snow/Ice respectively?',
        'Cloud Shadow: blue (blue-violet acceptable); Snow/Ice: cyan (light blue acceptable).','look_shadow_snow_colors',
        [('landsat-v5-p066-table_candidate-001','Cloud Shadow and Snow/Ice rows, Color column','Cloud Shadow blue; Snow/Ice cyan')])
    add('image','In Figure 2-2, which baffle is at the front-left viewing opening, and which is labeled on the side of the OLI instrument?',
        'Earth-View Baffle at the front-left opening; Solar-View Baffle on the side.','oli_baffle_view_labels',
        [('landsat-v5-p017-image-001','Earth-View Baffle and Solar-View Baffle arrow labels','Earth-View Baffle; Solar-View Baffle')])
    add('image','In Figure 2-6, what bracket is labeled below the center of the TIRS instrument?',
        'Interconnecting Harness Bracket.','tirs_lower_bracket',
        [('landsat-v5-p021-image-001','Lower-center arrow label','Interconnecting Harness Bracket')])
    add('image','In the Figure 6-2 dataset screenshot, which sensor families are listed for Landsat 4-5 and Landsat 1-5 respectively?',
        'Landsat 4-5: TM; Landsat 1-5: MSS.','dataset_screenshot_tm_mss',
        [('landsat-v5-p069-image-002','Third and fourth dataset checkbox entries','Landsat 4-5 TM C1 Level-1; Landsat 1-5 MSS C1 Level-1')])
    add('image','What width in km is printed alongside the TIRS path in Figure A-4?',
        '185 km.','tirs_path_width_annotation',
        [('landsat-v5-p077-image-001','Left path-width arrow label','TIRS path (185 km width)')])
    add('image','In Figure B-5, name the meridian shown and the axis aligned with the Earth axis of rotation.',
        'Greenwich Meridian; Z-axis.','ecef_meridian_rotation_axis',
        [('landsat-v5-p100-image-001','Meridian label and vertical rotation-axis arrow','Greenwich Meridian; Z')])
    add('chart','In Figure 2-3, approximately what ETM+ performance SNR does the green NIR bar show?',
        'About 35 SNR, absolute tolerance 5.','etm_nir_green_snr',
        [('landsat-v5-p019-image-001','NIR group, green ETM+ Performance bar','About 35 SNR')],5)
    add('chart','In Figure 2-3, approximately what OLI requirement SNR does the blue Coastal/Aerosol bar show?',
        'About 130 SNR, absolute tolerance 10.','coastal_requirement_blue_snr',
        [('landsat-v5-p019-image-001','Coastal/Aerosol group, blue OLI Requirement bar','About 130 SNR')],10)
    add('chart','Approximately what encoder-current value is shown by the green trace at November 1, 2014 in Figure A-6? Do not assume a current unit that is not printed.',
        'About 70 on the plotted encoder-current scale; absolute tolerance 2.','ssm_current_nov2014',
        [('landsat-v5-p079-image-001','Green series at 11/01/14 tick','Approximately 70; axis has no printed current unit')],2)
    add('chart','In the left panel of Figure A-3, what does the thin light-blue diagonal reference line represent?',
        'The 1x1 line, equality of OBC radiance and vicarious radiance.','radiance_diagonal_equality_line',
        [('landsat-v5-p076-image-001','Left-panel legend and diagonal line','1x1 line: equal OBC and vicarious radiance')])
    add('chart','From the spectral bars in Figure 4-3, give the approximate lower and upper wavelengths in nm of the ETM+ panchromatic Band 8.',
        'Approximately 500–900 nm; absolute tolerance 70 nm on each endpoint.','etm_pan_chart_endpoints',
        [('landsat-v5-p058-image-001','ETM+ panchromatic Band 8 bar against wavelength axis','Approximately 500–900 nm')],70)
    add('multi_hop','Using Table 3-3 and Table 3-4, compare how the CPF and BPF naming conventions encode the sensor: what does CPF C mean, and which O/T values can BPF S take?',
        'CPF C means combined OLI and TIRS; BPF S is O for OLI or T for TIRS.','cpf_bpf_sensor_encoding',[
        ('landsat-v5-p048-table_candidate-001','C row','C = combined for OLI and TIRS'),
        ('landsat-v5-p050-table_candidate-001','S row','O for OLI or T for TIRS')])
    add('multi_hop','Compare the satellite-field symbols in Table 3-5 and Table 4-1. What are the field letters in each, and which satellite does 08 denote in both?',
        'RLUT uses NN; Level 1 product naming uses SS; 08 denotes Landsat 8 in both.','rlut_l1_satellite_field_symbols',[
        ('landsat-v5-p051-table_candidate-001','NN row','NN; 08 = Landsat 8, 09 = Landsat 09'),
        ('landsat-v5-p059-table_candidate-001','SS row','SS; 08 = Landsat 8')])
    add('multi_hop','Using Section 3.3.3 and Section 4.1.4.2, contrast the storage format for the large RLUT parameters with the delivered Level 1 band images.',
        'RLUT parameters are stored in Hierarchical Data Format (HDF); Level 1 band images use GeoTIFF.','rlut_vs_l1_storage_formats',[
        ('landsat-v5-p051-text-001','RLUT parameter organization paragraph','Hierarchical Data Format (HDF)'),
        ('landsat-v5-p056-text-002','Product Format paragraph','Georeferenced Tagged Image File Format (GeoTIFF)')])
    add('multi_hop','Using the instrument descriptions in Section 2.2 and Section 2.3, how many SCAs do OLI and TIRS have, and how many more does OLI have?',
        'OLI has 14; TIRS has 3; OLI has 11 more SCAs.','oli_tirs_sca_count_difference',[
        ('landsat-v5-p019-text-009','OLI focal-plane description','14 identical Sensor Chip Assemblies'),
        ('landsat-v5-p022-text-005','TIRS focal-plane description','three identical SCAs')],calculation='14 - 3 = 11')
    add('text','According to Section 1.4, which two project science offices prepared the handbook, and in which cities are they located?',
        'USGS Landsat Project Science Office at EROS Center in Sioux Falls, South Dakota; NASA Landsat Project Science Office at GSFC in Greenbelt, Maryland.','handbook_preparing_offices_cities',
        [('landsat-v5-p014-text-004','Document Purpose paragraph','USGS EROS Sioux Falls, SD; NASA GSFC Greenbelt, Maryland')])
    add('text','In what format is the human-readable Level 1 metadata (MTL) file described in Section 4.1.4?',
        'ODL format.','mtl_odl_format',
        [('landsat-v5-p056-text-001','MTL file paragraph','human-readable text file in ODL format')])
    add('text','According to Section 1.3.4, within how many hours of acquisition are Landsat 8 data downlinked and processed into standard products?',
        'Within 24 hours.','rapid_data_24hours',
        [('landsat-v5-p013-text-015','Rapid Data Availability paragraph','within 24 hours of acquisition')])
    add('text','In Section 4.1.5, what do Image_Quality_OLI values 9, 0 and -1 mean?',
        '9 = Best; 0 = Worst; -1 = quality not calculated or assessed.','image_quality_score_meanings',
        [('landsat-v5-p057-text-005','Image_Quality_OLI values block','9 Best; 0 Worst; -1 quality not calculated or assessed')])
    negatives=[
        ('What is the onboard TIRS processor clock frequency in MHz specified in this handbook?','tirs_cpu_clock','The handbook describes TIRS sensing and electronics, but supplies no processor clock frequency in MHz.'),
        ('What exact EarthExplorer API rate limit in requests per second is specified here?','ee_api_rate_limit','The access chapter describes interactive search/download interfaces, not a numeric API request rate limit.'),
        ('How many employees worked at the USGS EROS Center on November 1, 2019, according to this handbook?','eros_2019_staff_headcount','EROS responsibilities and location are described; a dated employee headcount is not supplied.'),
        ('What monthly uptime percentage for GloVis during August 2018 is reported in the handbook?','glovis_aug2018_uptime','The GloVis interface is described, without monthly service-availability statistics.'),
        ('How many training images were used to train CFMask, as specified in this handbook?','cfmask_training_image_count','The CFMask description explains masking and validation limits, not a training-image count.'),
        ('What is the minimum Android operating-system version required by the LandsatLook Viewer according to this handbook?','landsatlook_android_requirement','The handbook describes a web viewer and does not specify an Android minimum-version requirement.')]
    for question,fact,reason in negatives:
        qid=f'adv3-test-{len(qs)+1:03d}';qs.append({'id':qid,'split':'test','question':question})
        gs.append({'id':qid,'split':'test','answerable':False,'primary_group':'unanswerable',
            'expected_behavior':'Clearly decline the unsupported requested attribute without inventing it.',
            'absence_reason':reason,'fact_keys':[fact],'evidence_groups':[],
            'absence_audit_scope':'All 114 original pages and OCR regions; relevant instrument, access, office and CFMask sections.'})
    dq=[];dg=[]
    for root,split in [('advanced-v2','dev'),('advanced-v2','test')]:
        oq=read_jsonl(ROOT/f'benchmarks/{root}/queries/{split}.jsonl');og=read_jsonl(ROOT/f'benchmarks/{root}/gold/{split}.jsonl')
        for q,g in zip(oq,og):
            qid='adv3-dev-'+q['id'];dq.append({**q,'id':qid,'split':'dev'})
            dg.append({**g,'id':qid,'split':'dev','original_id':g['id'],
                       'provenance':'Former v1/v2 cases are development data after their outputs were inspected.'})
    stats={'dev':validate(dq,dg,elements,'dev'),'test':validate(qs,gs,elements,'test')}
    if {f for g in dg for f in g['fact_keys']} & {f for g in gs for f in g['fact_keys']}:raise ValueError('Fact-key collision')
    for split,q,g in [('dev',dq,dg),('test',qs,gs)]:
        write_jsonl(target/'queries'/f'{split}.jsonl',q);write_jsonl(target/'gold'/f'{split}.jsonl',g)
    write_json(target/'manifest.json',{'created_at':now(),'status':'SOURCE_REVIEWED_BEFORE_ANY_V3_MODEL_RUN',
        'stats':stats,'test_pages':sorted({e['pdf_page'] for g in gs for group in g['evidence_groups'] for e in group}),
        'groups':dict(Counter(g['primary_group'] for g in gs)),
        'source_catalog_precedes_benchmark':'artifacts/advanced/catalog-v7/manifest.json',
        'source_verification':'artifacts/source-verification.json','fact_key_overlap':[],
        'semantic_overlap_review':'New source attributes/columns/series/relations relative to both former benchmark versions. Source pages may overlap; same underlying answer was not merely reworded.',
        'test_policy':'All 30 cases, frozen before running; no replacements based on output; 27/30 minimum.',
        'hashes':{f'{folder}/{split}.jsonl':sha256(target/folder/f'{split}.jsonl') for folder in ('queries','gold') for split in ('dev','test')}})
    print('Created',len(dq),'dev and',len(qs),'fresh test cases')


if __name__=='__main__':main()
