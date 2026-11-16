"""Author a provisional Landsat dev/test benchmark from inspected source regions."""
from collections import Counter
from pathlib import Path

from src.day07.common import now, read_jsonl, sha256, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/advanced'
ELEMENTS = {e['evidence_id']: e for e in read_jsonl(ROOT / 'artifacts/advanced/elements.jsonl')}


def ev(page, kind, number, locator, value, tolerance=None):
    eid = f'landsat-v5-p{page:03d}-{kind}-{number:03d}'
    e = ELEMENTS[eid]
    result = {'evidence_id': eid, 'pdf_page': page, 'printed_label': e['printed_label'],
              'bbox': e['bbox'], 'element_type': e['element_type'], 'locator': locator,
              'source_value': value}
    if tolerance is not None: result['absolute_tolerance'] = tolerance
    return result


def main():
    cases = {'dev': [], 'test': []}
    def add(split, group, question, answer, evidence, facts):
        cases[split].append({'group': group, 'question': question, 'answer': answer,
                             'evidence': evidence, 'facts': facts})
    # Each table locator names the row and column; coordinates cover the complete table.
    add('dev','table','In Table 1-1, what SSR size and storage organization are given for Landsat 7?',
        '378 Gbits, block-based.', [ev(13,'table_candidate',1,'Table 1-1, SSR Size row, Landsat 7 column','378 Gbits, block-based')], ['l7_ssr'])
    add('dev','table','In Table 2-2, what is the OLI performance SNR for OLI Band 2 at Ltypical?',
        '364.', [ev(19,'table_candidate',1,'Table 2-2, OLI Band 2 row, OLI Performance column','364')], ['snr_band2'])
    add('dev','table','In Table 2-3, what NEΔT is listed for TIRS Band 10 at 240?',
        '0.069.', [ev(22,'table_candidate',1,'Table 2-3, TIRS 10 row, NEDT@240 column','0.069')], ['nedt_10_240'])
    add('dev','table','In Table A-1, what temperature offset is listed for TIRS Band 10 at 300 K?',
        '-2.1 ± 0.8 K at 300 K.', [ev(76,'table_candidate',1,'Table A-1, Band 10 row, Temperature Offset column','-2.1 +/- 0.8 K @ 300 K')], ['temp_offset_10'])
    add('test','table','In Table 1-1, what SSR size and storage organization are given for Landsat 8?',
        '3.14 Terabit, file-based.', [ev(13,'table_candidate',1,'Table 1-1, SSR Size row, Landsat 8 column','3.14 Terabit, file-based')], ['l8_ssr'])
    add('test','table','In Table 2-2, what is the OLI performance SNR for OLI Band 7 at Ltypical?',
        '334.', [ev(19,'table_candidate',1,'Table 2-2, OLI Band 7 row, OLI Performance column','334')], ['snr_band7'])
    add('test','table','In Table 2-3, what NEΔT is listed for TIRS Band 11 at 280?',
        '0.059.', [ev(22,'table_candidate',1,'Table 2-3, TIRS 11 row, NEDT@280 column','0.059')], ['nedt_11_280'])
    add('test','table','In Table A-1, what temperature offset is listed for TIRS Band 11 at 300 K?',
        '-4.4 ± 1.75 K at 300 K.', [ev(76,'table_candidate',1,'Table A-1, Band 11 row, Temperature Offset column','-4.4 +/- 1.75 K @ 300 K')], ['temp_offset_11'])
    add('test','table','In Table 2-1, what wavelength range is listed for Landsat 8 OLI Band 5?',
        '0.851–0.879 µm.', [ev(18,'image',1,'Table 2-1, Landsat 8 NIR Band 5 row','0.851–0.879 µm')], ['wavelength_band5'])
    add('test','table','What image downlink coverage is listed for Landsat 8 in Table 1-1?',
        'X-Band Earth Coverage.', [ev(13,'table_candidate',1,'Table 1-1, Image D/L row, Landsat 8 column','X-Band Earth Coverage')], ['l8_downlink'])

    add('dev','image','In Figure 2-1, which sensor is identified by the arrow at the upper left of the observatory?',
        'TIRS.', [ev(16,'image',1,'Figure 2-1, upper-left arrow and label','TIRS')], ['fig21_tirs'])
    add('dev','image','In Figure 2-5, which band appears at the top of the odd SCA band stack?',
        'Band 8, panchromatic.', [ev(20,'image',2,'Figure 2-5, left odd-SCA stack, top band','8 – Panchromatic')], ['fig25_odd_top'])
    add('dev','image','In Figure 2-7, which SCA is shown to the right of SCA-3?',
        'SCA-1.', [ev(22,'image',1,'Figure 2-7, upper right of focal-plane diagram','SCA-1')], ['fig27_right'])
    add('dev','image','In the Figure 4-1 flow diagram, which processing system follows Radiometric Processing System directly?',
        'Geometric Processing System (GPS).', [ev(53,'image',1,'Figure 4-1, downward arrow from RPS','Geometric Processing System (GPS)')], ['fig41_rps_next'])
    add('test','image','In Figure 2-1, what component is labeled at the lower right of the spacecraft bus?',
        'Solar Panel.', [ev(16,'image',1,'Figure 2-1, lower-right arrow and label','Solar Panel')], ['fig21_solar'])
    add('test','image','In Figure 2-5, what is at the top of the even SCA band stack?',
        'Bands 12–14, Blind.', [ev(20,'image',2,'Figure 2-5, right even-SCA stack, top band','12–14 Blind')], ['fig25_even_top'])
    add('test','image','In Figure 2-8, which baffle is shown on the left and which on the right?',
        'Nadir baffle on the left; spaceview baffle on the right.', [ev(23,'image',1,'Figure 2-8, left and right baffle arrows','Nadir / Spaceview')], ['fig28_baffles'])
    add('test','image','In Figure A-5, what component is labeled at the bottom of the TIRS cutaway?',
        'Focal Plane Array (FPA).', [ev(78,'image',1,'Figure A-5, bottom component label','Focal Plane Array (FPA)')], ['figa5_fpa'])
    add('test','image','In Figure B-2, which SCA is drawn below the upper SCA-A and SCA-B row?',
        'SCA-C / SCA02.', [ev(96,'image',1,'Figure B-2, lower row of the diagram','SCA-C / SCA02')], ['figb2_lower'])

    add('dev','chart','In Figure 2-3, approximately what OLI performance SNR does the red Coastal/Aerosol bar show at Ltypical?',
        'About 238, with absolute tolerance 20.', [ev(19,'image',1,'Figure 2-3, Coastal/Aerosol red bar and SNR axis','approximately 238',20)], ['snr_band1'])
    add('dev','chart','In Figure A-2, what do blue dots and gray dots indicate in the lunar-scan panels?',
        'Blue dots indicate scanned lunar positions that produced ghosts; gray dots indicate positions that did not.', [ev(75,'image',1,'Figure A-2, blue/gray legend','blue: ghosts; gray: no ghosts')], ['figa2_colors'])
    add('dev','chart','In Figure A-6, approximately what encoder-current value is marked by the yellow limit line?',
        'About 80, with absolute tolerance 1.', [ev(79,'image',1,'Figure A-6, yellow limit line and y-axis','80',1)], ['figa6_yellow'])
    add('dev','chart','What are the horizontal and vertical axis labels and units in Figure 4-3?',
        'Horizontal: wavelength in nm; vertical: atmospheric transmission in percent.', [ev(58,'image',1,'Figure 4-3, horizontal and vertical axes','Wavelength (nm); Atmospheric Transmission (%)')], ['fig43_axes'])
    add('test','chart','In Figure 2-3, approximately what OLI performance SNR does the red NIR bar show at Ltypical?',
        'About 204, with absolute tolerance 20.', [ev(19,'image',1,'Figure 2-3, NIR red bar and SNR axis','approximately 204',20)], ['snr_band5'])
    add('test','chart','In Figure 2-3, approximately what OLI performance SNR does the red Cirrus bar show?',
        'About 165, with absolute tolerance 20.', [ev(19,'image',1,'Figure 2-3, Cirrus red bar and SNR axis','approximately 165',20)], ['snr_band9'])
    add('test','chart','In Figure A-6, approximately what encoder-current value is marked by the red limit line?',
        'About 85, with absolute tolerance 1.', [ev(79,'image',1,'Figure A-6, red limit line and y-axis','85',1)], ['figa6_red'])
    add('test','chart','In Figure 4-3, which two TIRS bands are displayed at thermal wavelengths beyond 10,000 nm?',
        'Bands 10 and 11.', [ev(58,'image',1,'Figure 4-3, TIRS row to the right of the axis break','10 and 11')], ['fig43_thermal_bands'])
    add('test','chart','In the left panel of Figure A-3, what marker and color represent Band 11?',
        'Red squares.', [ev(76,'image',1,'Figure A-3 left panel, legend','Band 11: red squares')], ['figa3_band11_legend'])

    bands = {1:('0.435–0.451',238), 2:('0.452–0.512',364), 3:('0.533–0.590',302),
             4:('0.636–0.673',227), 5:('0.851–0.879',204), 6:('1.566–1.651',265),
             7:('2.107–2.294',334), 8:('0.503–0.676',149)}
    for band, (wavelength, snr) in bands.items():
        split = 'dev' if band <= 4 else 'test'
        add(split,'multi_hop',f'Using Table 2-1 to identify the Landsat 8 band spanning {wavelength} µm, then Table 2-2, what is that band and its OLI performance SNR at Ltypical?',
            f'OLI Band {band}; SNR {snr}.',
            [ev(18,'image',1,f'Table 2-1, Landsat 8 Band {band} wavelength row',f'{wavelength} µm, Band {band}'),
             ev(19,'table_candidate',1,f'Table 2-2, OLI Band {band}, OLI Performance column',str(snr))],
            [f'wavelength_band{band}',f'snr_band{band}'])

    add('dev','text','In the introduction, in what year was Landsat 8 launched?',
        '2013.', [ev(9,'text',3,'Foreword, launch sentence','Launched in 2013')], ['l8_launch_2013'])
    add('dev','text','According to the spacecraft overview, what were the specified design life and fuel-carrying requirement?',
        'A 5-year specified design life and sufficient fuel to maintain orbit for 10 years.', [ev(23,'text',2,'Section 2.4, design-life sentence','5 years; fuel for 10 years')], ['design_life_5_10'])
    add('dev','text','What bit depth and dimensions does the QA file have relative to the standard L1T scene?',
        'It is a 16-bit image with the same dimensions as the standard L1T scene.', [ev(60,'text',3,'Section 4.2.3, QA file description','16-bit; same dimensions as standard L1T scene')], ['qa_16bit'])
    add('dev','text','What does the TIRS SSM encoder convert into digital codes?',
        'Angular positions representing the orientation of the SSM.', [ev(78,'text',1,'Appendix A.2, encoder description','angular positions to digital codes')], ['ssm_encoder'])
    add('test','text','According to the Global Survey Mission description, how often does the world come within view of Landsat 8 sensors?',
        'Once every 16 days.', [ev(13,'text',14,'Section 1.3.3, repeat-coverage sentence','once every 16 days')], ['survey_16days'])
    add('test','text','How many potential gray levels does the document associate with 12-bit and previous 8-bit instruments?',
        '4,096 for 12-bit and 256 for 8-bit.', [ev(58,'text',2,'Section 4.2.1, dynamic-range paragraph','4096 versus 256')], ['gray_levels'])
    add('test','text','What effect does cloud contamination have on NDVI values according to the QA-band discussion?',
        'Cloud-contaminated pixels lower NDVI values and can distort phenology measurements.', [ev(60,'text',3,'Section 4.2.3, cloud contamination paragraph','cloud-contaminated pixels lower NDVI values')], ['qa_ndvi'])
    add('test','text','On what date was the first TIRS SSM anomaly discovered, according to Appendix A.2?',
        'December 19, 2014.', [ev(78,'text',3,'Appendix A.2, first discovery sentence','December 19, 2014')], ['ssm_discovery'])

    absent = {
        'dev': [('Aurora-Reef-2027','What was the Landsat 8 acquisition cost for the fictional Aurora-Reef-2027 campaign?'),
                ('Boreal-Station-X','What exact IP address did the fictional Boreal-Station-X use for Landsat 8 downlink?'),
                ('Cedar-Valley-2028','What was the cloud percentage of the fictional Cedar-Valley-2028 scene?'),
                ('Delta-Lab-42','Which engineer approved the fictional Delta-Lab-42 TIRS calibration in this handbook?'),
                ('Elm-Lake-Project','What was the fictional Elm-Lake-Project processing invoice in dollars?'),
                ('Fjord-Sensor-Z','What is the serial number of the fictional Fjord-Sensor-Z in this handbook?')],
        'test': [('Granite-Research-2029','What Landsat 8 acquisition date is reported for the fictional Granite-Research-2029 project?'),
                 ('Harbor-Node-Q','What was the telemetry password for the fictional Harbor-Node-Q ground station?'),
                 ('Indigo-Scene-88','What QA value is listed for the fictional Indigo-Scene-88 product?'),
                 ('Juniper-Team-7','Which operator led the fictional Juniper-Team-7 calibration in the handbook?'),
                 ('Kestrel-Archive-2030','What storage price is reported for the fictional Kestrel-Archive-2030 dataset?'),
                 ('Lumen-Station-9','What IP address is given for the fictional Lumen-Station-9 Landsat receiver?')],
    }
    all_text = '\n'.join(e['content'] for e in ELEMENTS.values() if e['element_type'] == 'text').casefold()
    for split, entries in absent.items():
        for entity, question in entries:
            if entity.casefold() in all_text: raise ValueError('Supposedly absent entity found in extracted text')
            cases[split].append({'group':'unanswerable','question':question,'entity':entity,'facts':[entity],
                                 'absence_reason':'Fictional entity absent from extracted text; relevant pages require visual/semantic absence audit.'})
    expected = {'dev': {'table':4,'image':4,'chart':4,'multi_hop':4,'text':4,'unanswerable':6},
                'test': {'table':6,'image':5,'chart':5,'multi_hop':4,'text':4,'unanswerable':6}}
    for split in cases:
        if dict(Counter(c['group'] for c in cases[split])) != expected[split]:
            raise ValueError('Unexpected advanced quota')
    fact_sets = {split: {f for c in rows for f in c['facts']} for split, rows in cases.items()}
    if fact_sets['dev'] & fact_sets['test']:
        raise ValueError(f"Cross-split fact reuse: {fact_sets['dev'] & fact_sets['test']}")
    all_questions = [c['question'].casefold() for rows in cases.values() for c in rows]
    if len(set(all_questions)) != len(all_questions): raise ValueError('Duplicate question')
    for split, rows in cases.items():
        queries, gold = [], []
        for n, c in enumerate(rows, 1):
            qid = f'adv-{split}-{n:03d}'
            queries.append({'id': qid, 'split': split, 'question': c['question']})
            item = {'id': qid, 'split': split, 'primary_group': c['group'],
                    'answerable': c['group'] != 'unanswerable', 'fact_keys': c['facts'],
                    'reviewer': 'Codex (AI-assisted; independent human review pending)'}
            if item['answerable']:
                item.update({'expected_answer': c['answer'], 'evidence_groups': [[e] for e in c['evidence']],
                             'review_reason': 'Source pages visually inspected; region and label require independent verification before claiming bonus.'})
            else:
                item.update({'expected_behavior':'search_and_abstain','absence_reason':c['absence_reason']})
            gold.append(item)
        write_jsonl(OUT / 'queries' / f'{split}.jsonl', queries)
        write_jsonl(OUT / 'gold' / f'{split}.jsonl', gold)
    paths = [OUT / kind / f'{split}.jsonl' for kind in ('queries','gold') for split in ('dev','test')]
    write_json(OUT / 'manifest.json', {'created_at': now(), 'source_sha256': 'baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756',
               'author_reviewer': 'Codex; independent human review pending', 'counts': expected,
               'cross_split_fact_keys_overlap': [], 'status': 'PROVISIONAL: needs full evidence/absence audit and dev experiments',
               'sha256': {str(p.relative_to(OUT)).replace('\\','/'): sha256(p) for p in paths}})
    print(expected)


if __name__ == '__main__': main()
