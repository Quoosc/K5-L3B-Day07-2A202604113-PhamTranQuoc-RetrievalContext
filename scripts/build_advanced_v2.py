"""Source-first second holdout. Run before any model evaluation of this split.

The original 56 development/test cases are now development data. This builder
does not read model traces and never selects questions based on model outputs.
"""
from collections import Counter
from pathlib import Path

from src.day07.advanced_eval import validate
from src.day07.common import now, read_jsonl, sha256, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'benchmarks/advanced-v2'
    elements = read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')
    registry = {e['evidence_id']: e for e in elements}
    queries, gold = [], []

    def add(group, question, answer, facts, sources, calculation=None, tolerance=None):
        qid = f'adv2-test-{len(queries)+1:03d}'
        queries.append({'id': qid, 'split': 'test', 'question': question})
        evidence = []
        for eid, locator, value in sources:
            e = registry[eid]
            item = {'evidence_id': eid, 'pdf_page': e['pdf_page'],
                    'printed_label': e['printed_label'], 'bbox': e['bbox'],
                    'locator': locator, 'source_value': value}
            if tolerance is not None:
                item['absolute_tolerance'] = tolerance
            evidence.append([item])
        gold.append({'id': qid, 'split': 'test', 'answerable': True,
                     'primary_group': group, 'expected_answer': answer,
                     'evidence_groups': evidence, 'fact_keys': facts,
                     'calculation': calculation, 'absolute_tolerance': tolerance,
                     'review_reason': 'Original PDF region inspected before model evaluation; author has confirmed source verification.'})

    add('table', 'In Table 3-1, what purpose and calibration-parameter use are listed for integration time sweeps with blackbody and deep space?',
        'Monitor linearity of detectors and focal plane electronics; determine the need to update linearity coefficients.',
        ['cal_sweeps_purpose_and_use'], [('landsat-v5-p028-table_candidate-001',
        'TIRS on-orbit activities; integration-time-sweeps row; Purpose and calibration-parameter columns',
        'Monitor linearity of detectors and focal plane electronics; Determine calibration need to update linearity coefficients')])
    add('table', 'In Table 3-2, what assessment is used by Band Alignment Calibration, and which instrument parameters are adjusted?',
        'Band-to-band registration assessment; OLI line-of-sight (LOS) parameters.',
        ['band_alignment_assessment_parameters'], [('landsat-v5-p038-table_candidate-001',
        'Band Alignment Calibration row; Purpose column', 'Adjusts OLI LOS parameters based on band-to-band registration assessment')])
    add('table', 'In Table 3-3, what does the Cc field represent, and what is its starting value?',
        'Collection number; starts with 01.', ['cpf_collection_initial'],
        [('landsat-v5-p048-table_candidate-001', 'Cc row', 'Collection number (starts with 01)')])
    add('table', 'In Table 3-4, distinguish HH1 from MM1 in the effective starting timestamp.',
        'HH1 is the two-digit effective starting hours; MM1 is the two-digit effective starting minutes.',
        ['bpf_start_hour_minute'], [('landsat-v5-p050-table_candidate-001',
        'HH1 and MM1 rows (superscript 1 denotes effective start)', 'HH1: Two-digit effective starting hours; MM1: Two-digit effective starting minutes')])
    add('table', 'Decode the acquisition date and processing date of the example LC08_L1GT_029030_20151209_20160131_01_T1 in Table 4-1.',
        'Acquisition: December 9, 2015; processing: January 31, 2016.',
        ['filename_example_dates'], [('landsat-v5-p059-table_candidate-001',
        'YYYYMMDD/yyyymmdd definitions and Example row', 'YYYYMMDD acquisition; yyyymmdd processing; example 20151209 and 20160131')],
        calculation='Parse dates as YYYY-MM-DD, without swapping acquisition and processing dates.')
    add('table', 'Which bit numbers identify Cloud Shadow and Cirrus respectively in Table 5-4?',
        'Cloud Shadow: bit 4; Cirrus: bit 6.', ['look_shadow_cirrus_bits'],
        [('landsat-v5-p066-table_candidate-001', 'Cloud Shadow and Cirrus rows, Bit column', '4 Cloud Shadow; 6 Cirrus')])

    add('image', 'In Figure 2-2, name the two electronics assemblies labeled along the bottom base of the OLI instrument.',
        'Instrument Support Electronics and Focal Plane Electronics.', ['oli_bottom_electronics'],
        [('landsat-v5-p017-image-001', 'Two labels along lower left and lower right of base', 'Instrument Support Electronics; Focal Plane Electronics')])
    add('image', 'In the enlarged scene in Figure 4-2, what row number is shown and what are its labeled horizontal and vertical dimensions?',
        'Row 17; 190 km horizontally and 180 km vertically.', ['scene17_diagram_dimensions'],
        [('landsat-v5-p055-image-001', 'Enlarged right-hand scene rectangle and dimension arrows', 'Row 17; horizontal 190 km; vertical 180 km')])
    add('image', 'In Figure A-4, what do the dotted arc outside the right edge of the image and the small central highlighted point represent?',
        'Dotted arc: stray-light positions for this detector and frame; central point: direct line of sight for this detector and frame.',
        ['straylight_arc_vs_direct_marker'], [('landsat-v5-p077-image-001',
        'Arrow labels pointing to dotted arc and central orange point', 'Stray light positions for this detector & frame; Direct line-of-sight for this detector & frame')])
    add('image', 'In Figure B-6, which axis points upward, and which label identifies distance above the ellipsoid along the slanted line?',
        'The Z-axis points upward; Height labels the distance above the ellipsoid.', ['geodetic_up_and_height'],
        [('landsat-v5-p101-image-001', 'Upper vertical arrow and upper-right slanted extension', 'Z; Height')])
    add('image', 'In the Figure 6-1 interface screenshot, which two top tabs appear between Search Criteria and Results?',
        'Data Sets and Additional Criteria.', ['ee_middle_tabs'],
        [('landsat-v5-p069-image-001', 'Tabs along top of left sidebar', 'Search Criteria | Data Sets | Additional Criteria | Results')])

    add('chart', 'In Figure 2-3, approximately what SNR is shown by the blue OLI Requirement bar for the Pan band?',
        'About 80 SNR; absolute tolerance 10.', ['pan_required_snr_blue'],
        [('landsat-v5-p019-image-001', 'Pan group, blue OLI Requirement bar against SNR axis', 'Blue Pan bar about 80')], tolerance=10)
    add('chart', 'In Figure 4-3, approximately what wavelength in nm is at the center of OLI Band 9 in the top sensor row?',
        'About 1375 nm; absolute tolerance 50 nm.', ['cirrus_chart_center_nm'],
        [('landsat-v5-p058-image-001', 'Top row OLI Band 9 narrow rectangle just left of 1400 nm tick', 'Center approximately 1375 nm')], tolerance=50)
    add('chart', 'In the Band 11 panel of Figure A-2, what are the displayed horizontal and vertical angular-axis ranges, including units?',
        'Horizontal: -20 to +20 degrees; vertical: -50 to +50 degrees.', ['lunar_scan_axis_ranges'],
        [('landsat-v5-p075-image-001', 'Right scatter panel, horizontal and vertical Angle [Deg] axes', 'x ticks -20 to 20; y ticks -50 to 50; Angle [Deg]')])
    add('chart', 'Read the yellow annotation in the right panel of Figure A-3: what radiance amounts were removed for B10 and B11, with units?',
        'B10: 0.29 W/m²/μm/sr; B11: 0.51 W/m²/μm/sr.', ['calibration_radiance_annotation'],
        [('landsat-v5-p076-image-002', 'Yellow annotation in right scatter panel', 'B10 0.29 W/m2/um/sr removed; B11 0.51 W/m2/um/sr removed')], tolerance=0.01)
    add('chart', 'Approximately what encoder-current value does the green trace show at the leftmost March 1, 2013 date in Figure A-6? Use the plotted scale without assuming an unstated current unit.',
        'About 53 on the plotted encoder-current scale; absolute tolerance 2.', ['ssm_initial_current_trace'],
        [('landsat-v5-p079-image-001', 'Green series at leftmost 03/01/13 tick; Encoder Current axis', 'Green trace starts near 53; no current unit printed on axis')], tolerance=2)

    add('multi_hop', 'Combine the orbit duration in Section 2.1 with the Bias Parameter File generation interval in Section 3.3.2. Approximately how many BPF generation intervals fit in one orbit? Show the two source numbers.',
        '98.9 minutes / about 50 minutes = 1.978, approximately 2 intervals per orbit.',
        ['orbit_duration_and_bpf_interval_ratio'], [
        ('landsat-v5-p016-text-003', 'Section 2.1 orbit paragraph', 'Completely orbiting the Earth every 98.9 minutes'),
        ('landsat-v5-p050-text-002', 'Section 3.3.2 BPF paragraph', 'Generated automatically about every half orbit, or 50 minutes')],
        calculation='98.9 / 50 = 1.978; accept approximately 2 with both input numbers and both source citations.', tolerance=0.03)
    add('multi_hop', 'Compare the starting nn file-version numbers in Table 3-3 (CPF) and Table 3-5 (RLUT). What does each start at?',
        'CPF nn starts at 00; RLUT nn starts at 01.', ['cpf_vs_rlut_initial_version'], [
        ('landsat-v5-p048-table_candidate-001', 'nn row', 'Version number for this file (starts with 00)'),
        ('landsat-v5-p051-table_candidate-001', 'nn row', 'Version number for this file (starts with 01)')])
    add('multi_hop', 'Using Table 5-1 and Table 5-4, distinguish the bit positions for Snow/Ice Confidence in the Level 1 QA band from Snow/Ice in the LandsatLook quality image.',
        'Level 1 QA Snow/Ice Confidence occupies bits 9 and 10; LandsatLook Snow/Ice occupies bit 5.',
        ['qa_vs_look_snow_bit_positions'], [
        ('landsat-v5-p063-image-002', 'Snow/Ice Confidence merged column above bits 10 and 9', 'Snow/Ice Confidence spans bits 10 and 9'),
        ('landsat-v5-p066-table_candidate-001', 'Snow/Ice row', 'Bit 5 Snow/Ice')])
    add('multi_hop', 'Using the approximate Landsat 7 and Landsat 8 scenes/day in Table 1-1 and the approximately 950 MB Level 1 product size in Section 6, estimate the additional daily download volume for Landsat 8. Assume one 950 MB product per scene and decimal GB (1000 MB); show the calculation.',
        '(700 - 450) × 950 MB = 237500 MB = approximately 237.5 GB/day additional volume under the stated assumption.',
        ['scene_rate_product_volume_difference'], [
        ('landsat-v5-p013-table_candidate-001', 'Scenes / Day row, Landsat 7 and Landsat 8 columns', 'Landsat 7 ~450; Landsat 8 ~700'),
        ('landsat-v5-p068-text-003', 'Level 1 Data Product bullet', 'Approximate size 950 MB')],
        calculation='(700-450)*950/1000 = 237.5 decimal GB/day; estimate assumes fixed complete-product size, not onboard downlink rate.', tolerance=1)

    add('text', 'According to Section 6.1, what must a user complete before downloading data products through EarthExplorer, and what is required for some website functions?',
        'Complete user registration before downloading; some functions require a successful login.', ['ee_registration_login'],
        [('landsat-v5-p068-text-004', 'Section 6.1 EarthExplorer paragraph', 'Before downloading data products, users must complete the user registration; some functions work only after a successful login')])
    add('text', 'Which algorithm does the Landsat 8 Cloud Cover Assessment system use in Section 4.1.4.3, and name two bright-target types over which it may have difficulties?',
        'CFMask (C Function of Mask); any two of building tops, beaches, snow/ice, sand dunes and salt lakes.', ['cfmask_name_bright_target_limits'],
        [('landsat-v5-p056-text-003', 'Section 4.1.4.3 CCA', 'CFMask; bright targets such as building tops, beaches, snow/ice, sand dunes, and salt lakes')])
    add('text', 'What date-range condition must a Calibration Parameter File satisfy to process an ordered image, according to Section 3.3?',
        'Its effective date range must include the acquisition date of the ordered image.', ['cpf_effective_date_condition'],
        [('landsat-v5-p048-text-001', 'CPF time-stamp and effective date range paragraph', 'The parameter file used in processing an image requires an effective date range that includes the acquisition date of the ordered image')])
    add('text', 'According to Section B.8, where is the origin of the ECI J2000 coordinate system, and toward what does its Z-axis point?',
        'Origin: Earth’s center of mass; Z-axis: mean north celestial pole at epoch J2000.0.', ['eci_origin_z_direction'],
        [('landsat-v5-p098-text-003', 'Section B.8 ECI J2000 Coordinate System', 'Origin at Earth center of mass; Z-axis mean north celestial pole of epoch J2000.0')])

    negatives = [
        ('What manufacturer hardware serial number for the Landsat 8 OLI instrument is reported in this handbook?',
         'oli_hardware_serial', 'Instrument descriptions and appendices describe OLI hardware but do not give its manufacturer hardware serial number.', ['serial', 'serial number', 'OLI']),
        ('What exact numeric IP address for the EarthExplorer production web server is listed in this handbook?',
         'ee_server_numeric_ip', 'Access sections provide website URLs, not server IP addresses; a URL is not a numeric IP address.', ['IP address', 'EarthExplorer']),
        ('What was the USGS EROS Center annual electricity bill in US dollars for 2018, as reported in this handbook?',
         'eros_2018_electricity_bill', 'Operations and access descriptions contain no 2018 electricity invoice or annual electricity expenditure.', ['electricity', 'invoice', 'EROS']),
        ('Which engineer personally signed the Bias Parameter File approval on November 1, 2019, according to this handbook?',
         'bpf_2019_approval_signatory', 'BPF generation and naming are described; no named signatory or approval record for this date is given.', ['approval', 'signed', 'Bias Parameter']),
        ('What cryptographic SHA-256 checksum does this handbook give for the original July 2013 Calibration Parameter File?',
         'cpf_2013_sha256', 'CPF naming/content and archive access are documented, but no SHA-256 checksum is supplied for the requested file.', ['SHA', 'checksum', 'Calibration Parameter']),
        ('What annual subscription price in US dollars for Landsat 9 Level 2 products in 2025 is specified in this 2019 handbook?',
         'l9_2025_subscription_price', 'This version does not state a 2025 Landsat 9 Level 2 annual subscription price; Landsat 8 no-charge access is not that requested fact.', ['subscription', '2025', 'Landsat 9']),
    ]
    for question, fact, reason, terms in negatives:
        qid = f'adv2-test-{len(queries)+1:03d}'
        queries.append({'id': qid, 'split': 'test', 'question': question})
        gold.append({'id': qid, 'split': 'test', 'answerable': False,
                     'primary_group': 'unanswerable', 'expected_behavior': 'Clearly state insufficient evidence and do not invent the requested fact.',
                     'absence_reason': reason, 'absence_audit_terms': terms,
                     'absence_audit_scope': 'All 114 PDF pages, extracted text and 77 OCR regions, plus relevant original instrument/calibration/access pages.',
                     'fact_keys': [fact], 'evidence_groups': [],
                     'review_reason': 'Real entities with a missing requested attribute, not fictional entity-name matching.'})

    dev_q, dev_g = [], []
    for split in ('dev', 'test'):
        old_q = read_jsonl(ROOT / f'benchmarks/advanced/queries/{split}.jsonl')
        old_g = read_jsonl(ROOT / f'benchmarks/advanced/gold/{split}.jsonl')
        for q, g in zip(old_q, old_g):
            qid = 'adv2-dev-' + q['id'].replace('adv-', '')
            dev_q.append({**q, 'id': qid, 'split': 'dev'})
            dev_g.append({**g, 'id': qid, 'split': 'dev', 'original_id': g['id'],
                          'provenance': 'Former v1 dev/test is development data after its results were inspected.'})
    stats = {'dev': validate(dev_q, dev_g, elements, 'dev'),
             'test': validate(queries, gold, elements, 'test')}
    old_facts = {f for g in dev_g for f in g['fact_keys']}
    new_facts = {f for g in gold for f in g['fact_keys']}
    if old_facts & new_facts:
        raise ValueError('Cross-split fact collision')
    for split, qs, gs in [('dev', dev_q, dev_g), ('test', queries, gold)]:
        write_jsonl(output / 'queries' / f'{split}.jsonl', qs)
        write_jsonl(output / 'gold' / f'{split}.jsonl', gs)
    pages = sorted({a['pdf_page'] for g in gold for group in g['evidence_groups'] for a in group})
    write_json(output / 'manifest.json', {
        'created_at': now(), 'status': 'SOURCE_REVIEWED_BEFORE_MODEL_EVALUATION',
        'source_verification': 'artifacts/source-verification.json',
        'author': 'Phạm Trấn Quốc; benchmark preparation assisted by Codex',
        'stats': stats, 'test_evidence_pages': pages, 'test_evidence_page_count': len(pages),
        'fact_overlap': [],
        'semantic_overlap_review': 'New questions target new attributes, cells, chart series, relations or calculations; source pages may overlap. Original dev/test facts were checked manually as well as by fact-key intersection.',
        'multi_hop_source_pairs': [[group[0]['evidence_id'] for group in g['evidence_groups']] for g in gold if g['primary_group']=='multi_hop'],
        'negative_cases': 'All six ask missing attributes of real entities; none uses a fictional name.',
        'hashes': {f'{folder}/{split}.jsonl': sha256(output/folder/f'{split}.jsonl') for folder in ('queries','gold') for split in ('dev','test')},
        'selection_rule': 'All 30 declared cases will be evaluated. No replacement or selection based on model output.',
        'scoring': 'Binary full correctness plus supporting original-region citations; all errors retained; 27/30 required.',
    })
    print('Created dev/test:', len(dev_q), len(queries), '; test pages:', len(pages), '; groups:', dict(Counter(g['primary_group'] for g in gold)))


if __name__ == '__main__':
    main()
