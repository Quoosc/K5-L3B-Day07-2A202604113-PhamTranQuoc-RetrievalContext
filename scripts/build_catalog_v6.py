"""Build a source-derived document catalog, independently of any benchmark.

All 114 pages/852 regions are retained. Canonical table columns and visual
observations correct layout/OCR ambiguity. This module never opens questions,
gold answers or model-evaluation traces.
"""
from collections import defaultdict
from datetime import datetime
import argparse
import json
from pathlib import Path
import re
import statistics
import uuid

from src.day07.chart_geometry import fit_axis
from src.day07.common import now, read_jsonl, sha256, write_json, write_jsonl
from src.day07.day6 import load_module, MODEL, REVISION
from src.day07.advanced_retrieval import snippets

ROOT=Path(__file__).resolve().parents[1]

# Observations describe the whole source region, not a question or gold answer.
VISUAL={
 '001-001':'Cover illustration for the Landsat 8 Data Users Handbook, version 5.0. Decorative cover image; no scientific measurement is inferred.',
 '009-001':'Decorative Landsat illustration alongside introductory text. Original region retained; no quantitative instrument value is inferred from this illustration.',
 '012-001':'Figure 1-1: spectral-coverage comparison of Landsat instruments. Visible, VNIR, SWIR and TIR bars show mission continuity. Labels include L8 OLI 30 m and 15 m Pan; TIRS 100 m; Landsat 7 ETM+ 60 m TIR; Landsat 4/5 TM 120 m TIR. This is a spectral diagram, not a mission-date timeline.',
 '016-001':'Figure 2-1: Landsat 8 observatory. The upper-left sensor is TIRS; the upper-right sensor is OLI. The spacecraft bus is central. The long Solar Panel extends toward the lower right.',
 '017-001':'Figure 2-2: OLI instrument. At front/left is the Earth-View Baffle; the Solar-View Baffle is on the instrument side. Other labels are Solar Diffuser Assembly, Shutter Wheel Assembly and Tertiary Mirror. Along the bottom base are Instrument Support Electronics (left) and Focal Plane Electronics (right).',
 '018-001':'Table 2-1: side-by-side Landsat 7 ETM+ and Landsat 8 OLI/TIRS spectral bands. Wavelengths are micrometers, resolutions meters. Keep each sensor band and its own row; do not shift the Band 5 row to Band 6.',
 '019-001':'Figure 2-3: grouped SNR bars at Ltypical. Horizontal categories are Coastal/Aerosol, Blue, Green, Red, NIR, SWIR1, SWIR2, Pan, Cirrus. Vertical axis SNR, 0 to 400. Blue is OLI Requirement, red OLI Performance, green ETM+ Performance. Companion Table 2-2 on the same page supplies the plotted values.',
 '020-001':'Figure 2-4: OLI focal plane has 14 sensor chip assemblies (SCAs), staggered in two rows. Neighboring SCAs overlap at their ends. Bands are arranged across each SCA.',
 '020-002':'Figure 2-5: odd/even SCA band stacks. Odd stack top-to-bottom: 8 Panchromatic, 1 Coastal Aerosol, 2 Blue, 3 Green, 4 Red, 5 NIR, 6 SWIR1, 7 SWIR2, 9 Cirrus, 12–14 Blind. Even stack reverses the arrangement: 12–14 Blind at top, 9 Cirrus, 7 SWIR2, 6 SWIR1, 5 NIR, 4 Red, 3 Green, 2 Blue, 1 Coastal Aerosol, 8 Panchromatic at bottom.',
 '021-001':'Figure 2-6: TIRS with Earthshield Deployed. Labels: Blackbody Cal Radiator at upper right, Captive Earthshield Latch at left, Hinge/Hinge Dampers at lower left, Focal Plane Electronics at lower center-left, Interconnecting Harness Bracket below the center, External Alignment Cube at lower right.',
 '022-001':'Figure 2-7: TIRS focal plane. SCA-3 is upper left, SCA-1 upper right, SCA-2 below. Each shows a dark calibration band plus 10 µm and 12 µm bands; lower SCA has opposite vertical order. The focal plane has three SCAs. The upper stacks have dark, 10 µm, 12 µm from top down; the bottom stack has 12 µm, 10 µm, dark from top down.',
 '023-001':'Figure 2-8: TIRS Optical Sensor Unit. Left is the nadir-view baffle and right is the spaceview baffle. Labeled parts include Scene Mechanism, Scene Mirror, Spaceview Calibration, Nadir, Hot Calibration Target, Telescope Optics, QWIP FPA, Instrument Deck Interface. Do not confuse calibration-view labels with detector bands.',
 '044-001':'Figure 3-1: simulated OLI image of the Lake Pontchartrain Causeway. Parallel causeway features through water illustrate spatial response and geometry; no exact radiometric value is inferred from the scene image.',
 '053-001':'Figure 4-1: LPGS standard product processing flow. Radiometric Processing System (RPS) is followed directly by Geometric Processing System (GPS), then product/output packaging. The diagram contains branches and intermediate inputs; arrow direction matters.',
 '055-001':'Figure 4-2: left strip has WRS rows 15,16,17,18,19,20 from top to bottom. The right enlargement is Row 17. The horizontal scene dimension is 190 km and vertical dimension 180 km. Shaded strips indicate overlap with adjacent scenes.',
 '058-001':'Figure 4-3: spectral bars against Wavelength (nm) and Atmospheric Transmission (%). Visible-to-SWIR axis ticks run about 400–2400 nm, then a broken axis to 10000–13000 nm. OLI Band 9 is near 1375 nm. Thermal TIRS bands are numbered 10 and 11, not instrument labels TIRS-2/TIRS-3. ETM+ panchromatic Band 8 spans approximately 500–900 nm. The vertical atmospheric-transmission scale is 0–100%.',
 '061-001':'Figure 4-4: grayscale Landsat 8 quality-band scene. Light pixels are more likely to be affected by snow/cloud; dark pixels show other QA values. Brightness is a bit-mask display, not surface reflectance.',
 '062-001':'Section 5.2 solar-angle correction equation: true TOA reflectance rho = rho_prime / sin(solar elevation angle) = rho_prime / cos(solar zenith angle). The uncorrected rho_prime omits solar-angle correction.',
 '063-001':'Section 5.3 brightness-temperature equation: T = K2 / ln(K1/L_lambda + 1). Temperature is Kelvin, radiance is band-specific, K1 and K2 are metadata constants.',
 '063-002':'Table 5-1 Level 1 QA bit layout, read from right to left starting bit 0: bit0 Designated Fill; bit1 Terrain Occlusion; bits2–3 Radiometric Saturation; bit4 Cloud; bits5–6 Cloud Confidence; bits7–8 Cloud Shadow Confidence; bits9–10 Snow/Ice Confidence; bits11–12 Cirrus Confidence; bits13–15 unused. Confidence categories span TWO bits, not only their upper bit.',
 '067-001':'Figure 5-1: false-color LandsatLook Quality image. Color-coded regions distinguish quality conditions; use Table 5-4 color definitions, not natural-color interpretation.',
 '069-001':'Figure 6-1 EarthExplorer interface screenshot. Actual search tabs across the top of the left sidebar: Search Criteria, Data Sets, Additional Criteria, Results. The separate toolbar above has Home, Save Criteria, Load Favorite, Manage Criteria. Do not confuse toolbar items Home/Save Criteria with search tabs.',
 '069-002':'Figure 6-2 EarthExplorer Landsat datasets. Under Landsat Collection 1 Level-1, checkbox choices list Landsat 8 OLI/TIRS C1 Level-1, Landsat 7 ETM+ C1 Level-1, Landsat 4-5 TM C1 Level-1, and Landsat 1-5 MSS C1 Level-1.',
 '070-001':'Figure 6-3 EarthExplorer results/browse display: a selected Landsat browse scene is overlaid on a map beside a results list. Result actions include footprint, browse and download controls.',
 '070-002':'Figure 6-4 EarthExplorer Show Result Controls: controls above the results list allow showing footprints/browse for all results and adding all results to a bulk-download order.',
 '071-001':'Figure 6-5 GloVis interface: map viewer with a left selection/results panel and a highlighted Landsat scene footprint. This is a geographic search interface, not a sensor-performance chart.',
 '072-001':'Figure 6-6 LandsatLook viewer: web map with imagery and controls for searching/filtering Landsat scenes. The geographic image occupies the main map panel and search/filter controls surround it.',
 '074-001':'Figure A-1: paired TIRS images of Lake Superior illustrate apparent time-varying stray-light error. Differences across water can be instrument artifacts, not necessarily real temperature changes.',
 '075-001':'Figure A-2 lunar-scan scatter plots: Band 10 left, Band 11 right. Both horizontal axes Angle [Deg] range -20 to +20 and vertical axes -50 to +50. Blue dots mark lunar positions producing ghosts; gray dots did not. Band 11 blue positions form a denser, more continuous ring; Band 10 has sparser clusters.',
 '076-001':'Figure A-3 LEFT panel, before calibration adjustment. X: Vicarious Radiance (W/m²/µm/sr); Y: OBC Radiance in the same units. Band 10 uses blue dots and Band 11 red squares. Thin light-blue diagonal is the 1x1 reference line, equality of the two radiances.',
 '076-002':'Figure A-3 RIGHT panel, after calibration adjustment. Band 10 blue dots, Band 11 red squares, thin light-blue 1x1 equality line. Yellow annotation states B10 0.29 W/m²/µm/sr removed and B11 0.51 W/m²/µm/sr removed.',
 '077-001':'Figure A-4: TIRS path is labeled 185 km width. Central highlighted point is direct line of sight for this detector/frame; dotted arc outside the right edge marks stray-light positions. Vectors outside the interval use nearest latitude/longitude at the interval edge.',
 '078-001':'Figure A-5 TIRS SSM cutaway: Scene Select Mirror and actuator/encoder components above the optical path; Focal Plane Array (FPA) is labeled at the bottom.',
 '079-001':'Figure A-6: green encoder-current trace versus Date (Month/Day/Year), from March 2013 to January 2015. Red limit 85; yellow limit 80. The y-axis says Encoder Current without a printed current unit. It starts near 53, rises substantially late in 2014 and drops around the anomaly/test interval. Sampled dates/values below are approximate original-pixel measurements.',
 '083-001':'Figure A-7 compares OLI on the left and TIRS on the right during a mode-change anomaly. TIRS shows a small discontinuity absent from the corresponding OLI view.',
 '086-001':'Figure A-8: Landsat 8 oversaturation in lower-12-bit data. Bright areas have discontinuous/wrapped radiometric appearance; they must not be interpreted as genuine dark surface patches.',
 '088-001':'Figure A-9: single-pixel striping and multi-detector banding in Band 1, Coastal/Aerosol, over a homogeneous Greenland ice-sheet scene. No exact radiance is derived from this screenshot.',
 '089-001':'Figure A-10: striping/banding in Band 2 (Blue) over calm ocean water; relative nonuniformity is visible in an otherwise homogeneous region.',
 '090-001':'Figure A-11: striping/banding in TIRS Band 10 over calm ocean water, illustrating low-level detector nonuniformity.',
 '091-001':'Figure A-12: visible SCA overlap in OLI Band 9 (Cirrus), at a boundary between neighboring SCAs with high clouds.',
 '092-001':'Figure A-13: SCA overlap in TIRS Band 10. Adjacent SCA calibration differences are visible at the overlap boundary.',
 '093-001':'Figure A-14: oversaturation examples in OLI SWIR Bands 6 and 7; saturated bright targets produce anomalous digital response.',
 '094-001':'Figure A-15: OLI single-event upset (SEU) example, visible as a single-frame bright artifact affecting a few detectors along a line.',
 '095-001':'Figure B-1 OLI LOS coordinate plot: OLI Y is cross-track, positive toward the left; OLI X is along-track, positive downward on the plot. Even SCAs 02,04,06,08,10,12,14 are in the upper row; odd SCAs 01,03,05,07,09,11,13 in the lower row. Legend distinguishes nine bands.',
 '096-001':'Figure B-2 TIRS LOS layout: SCA-A/SCA01 upper left, SCA-B/SCA03 upper right, SCA-C/SCA02 below. Band 10 and Band 11 are bands within each SCA, not SCA names.',
 '098-001':'Figure B-3 orbital coordinate diagram: origin spacecraft center of mass; Z points toward Earth center, Y is normal to the orbital plane opposite angular momentum, X completes the right-handed system.',
 '099-001':'Figure B-4 Earth-centered inertial J2000 frame: origin Earth center of mass, Z toward mean north celestial pole, X toward mean vernal equinox at epoch J2000.0; axes are space-fixed.',
 '100-001':'Figure B-5 ECEF frame: origin Earth center, Z aligned with Earth axis of rotation, Greenwich Meridian is shown and Equator is labeled. X points through the prime-meridian/equator reference; Y lies in the equatorial plane.',
 '101-001':'Figure B-6 geodetic diagram: Z points upward, Y right, X lower left. Greenwich Meridian, Equator, Latitude, Longitude, Ellipsoid Normal and Height are labeled; height extends above the reference ellipsoid along its normal.'
}


def compact(rows):
    return [[str(c).strip().replace('\n',' ') for c in row if c is not None and str(c).strip()] for row in rows]


def canonical_table(e):
    rows=[r for r in compact(e.get('rows',[])) if r]
    page=e['pdf_page']
    if page==13:
        return [{'Field':r[0],'Landsat 7':r[1],'Landsat 8':r[2]} for r in rows if len(r)==3 and r[0] not in ('Landsat 7','Landsat 8')]
    if page==19:
        return [dict(zip(['ETM+ Band','OLI Band','ETM+ Performance SNR','OLI Requirement SNR','OLI Performance SNR'],r))
                for r in rows if len(r)==5 and re.fullmatch(r'\d+',r[1])]
    if page==22:
        return [dict(zip(['Band','NEDT@240','NEDT@280','NEDT@320','NEDT@360'],r)) for r in rows if len(r)==5 and r[0].startswith('TIRS')]
    if page in (26,27,28,37,38):
        return [dict(zip(['Activity','Purpose','Use in calibration parameters'],r)) for r in rows if len(r)==3 and 'Purpose' not in r and 'Calibration Parameters' not in r]
    if page in (48,50,51,59):
        return [{'Symbol':re.sub(r'^_\s+(?=\w)','',r[0]),'Meaning':r[1]} for r in rows if len(r)==2]
    if page==66:
        desc=['Designated Fill','Terrain Occlusion','Radiometric Saturation','Cloud','Cloud Shadow','Snow/Ice','Cirrus','Unused']
        colors=['Black','Orange','Red','White','Blue','Cyan','Yellow','Unused']
        return [{'Bit':i,'Description':d,'Color':c} for i,(d,c) in enumerate(zip(desc,colors))]
    if page==76:
        return [{'TIRS Band':10,'Radiance Offset W/m²/sr/µm':'-0.29 ± 0.12','Temperature Offset K @300K':'-2.1 ± 0.8'},
                {'TIRS Band':11,'Radiance Offset W/m²/sr/µm':'-0.51 ± 0.2','Temperature Offset K @300K':'-4.4 ± 1.75'}]
    if page in (111,112,113,114):
        return [{'Acronym':r[0],'Expansion':r[1]} for r in rows if len(r)==2]
    return [{'unverified_raw_cells':r} for r in rows]


def line_samples(pdf_path,e,ocr):
    """Digitize every readable date tick of the green trace, with no query."""
    import fitz
    ticks=[]; dates=[]
    for line in ocr.get('lines',[]):
        text=line['text'].strip();x0,y0,x1,y1=line['bbox']
        if re.fullmatch(r'\d{2}',text) and x1<100:
            ticks.append(((y0+y1)/2,float(text)))
        for m in re.finditer(r'\d{2}/\d{2}/\d{2}',text):
            date=datetime.strptime(m.group(),'%m/%d/%y')
            x=x0+(m.start()+len(m.group())/2)/len(text)*(x1-x0)
            dates.append((x,date))
    axis=fit_axis(ticks)
    if not axis or len(dates)<3:return []
    xs=[x for x,_ in dates]; ds=[d.toordinal() for _,d in dates]
    xm=statistics.mean(xs);dm=statistics.mean(ds)
    slope=sum((d-dm)*(x-xm) for x,d in zip(xs,ds))/sum((d-dm)**2 for d in ds)
    offset=xm-slope*dm
    with fitz.open(pdf_path) as pdf:
        pix=pdf[e['pdf_page']-1].get_pixmap(dpi=200,clip=fitz.Rect(e['bbox']),alpha=False)
        pixels=memoryview(pix.samples); scale=200/72; result=[]
        for _,d in dates:
            x=round((slope*d.toordinal()+offset)*scale-pix.x);ys=[]
            for px in range(max(0,x-2),min(pix.width,x+3)):
                for y in range(pix.height):
                    r,g,b=pixels[y*pix.stride+px*pix.n:y*pix.stride+px*pix.n+3]
                    if g>r*1.3 and g>b*1.08 and g>70:
                        value=axis['slope']*((y+pix.y)/scale)+axis['intercept']
                        if 48<=value<=90:ys.append(value)
            if ys:result.append({'date':d.strftime('%Y-%m-%d'),'encoder_current_approx':round(statistics.median(ys),1),
                                'unit':'not printed on original axis','reading_uncertainty':2})
        return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--pdf',required=True,type=Path)
    p.add_argument('--day6-root',required=True,type=Path);p.add_argument('--model-path',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--qdrant',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.qdrant.exists():raise FileExistsError('Catalog/index outputs must be new')
    args.output.mkdir(parents=True)
    elements=read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')
    ocr={r['evidence_id']:r for r in read_jsonl(ROOT/'artifacts/advanced/ocr-regions-v1.jsonl')}
    tables={e['evidence_id']:canonical_table(e) for e in elements if e['element_type']=='table_candidate'}
    # Explicit source transcription of Table 2-1, including BOTH sensor columns.
    l8=[(1,'Coastal/Aerosol',30,.435,.451),(2,'Blue',30,.452,.512),(3,'Green',30,.533,.590),
        (4,'Red',30,.636,.673),(5,'NIR',30,.851,.879),(6,'SWIR-1',30,1.566,1.651),
        (7,'SWIR-2',30,2.107,2.294),(8,'Pan',15,.503,.676),(9,'Cirrus',30,1.363,1.384),
        (10,'TIR-1',100,10.60,11.19),(11,'TIR-2',100,11.50,12.51)]
    l7=[(1,'Blue',30,.441,.514),(2,'Green',30,.519,.601),(3,'Red',30,.631,.692),(4,'NIR',30,.772,.898),
        (5,'SWIR-1',30,1.547,1.749),(6,'TIR',60,10.31,12.36),(7,'SWIR-2',30,2.064,2.345),(8,'Pan',15,.515,.896)]
    spectral=[{'Sensor':sensor,'Band':b,'Name':name,'Resolution m':resolution,'Wavelength min µm':low,'Wavelength max µm':high}
              for sensor,data in [('Landsat 8 OLI/TIRS',l8),('Landsat 7 ETM+',l7)] for b,name,resolution,low,high in data]
    chart_snr=tables['landsat-v5-p019-table_candidate-001']
    regions=[]
    for e in elements:
        eid=e['evidence_id'];kind=e['element_type'];content=e['content'].strip()
        curated=None
        if kind=='table_candidate':
            curated=tables[eid]
            content='Source table, canonical columns. Original merged cells remain authoritative.\n'+json.dumps(curated,ensure_ascii=False)
        if kind=='image':
            key=f"{e['pdf_page']:03d}-{eid.rsplit('-',1)[1]}"
            observation=VISUAL.get(key)
            if not observation:raise ValueError('Missing image observation: '+eid)
            content=observation
            if e['pdf_page']==18:curated=spectral
            if e['pdf_page']==19:curated=chart_snr
            if e['pdf_page']==79:curated=line_samples(args.pdf,e,ocr.get(eid,{}))
            if curated is not None:content+='\nSource-derived structured observations:\n'+json.dumps(curated,ensure_ascii=False)
        if kind=='vector_page':
            on_page=[other for other in elements if other['pdf_page']==e['pdf_page'] and other['element_type'] in ('text','table_candidate')]
            content+='\nPage text and registered table regions are indexed separately; inspect their tight source regions for individual claims.'
        if eid in ocr and ocr[eid].get('status')=='ok':
            content+='\nOCR labels (secondary, may contain recognition errors): '+ ' | '.join(l['text'] for l in ocr[eid].get('lines',[]))
        regions.append({'evidence_id':eid,'source_id':e['doc_id'],'source':e['source'],'page':e['pdf_page'],
            'printed_label':e['printed_label'],'bbox':e['bbox'],'text':content,
            'metadata':{'element_type':kind,'section':e['section'],'source_catalog':'v6','curated':curated is not None or kind=='image'},
            'curated_data':curated,'automatic_table_cells':e.get('rows'),
            'curation_method':'Source-only layout transcription, caption/OCR descriptions and Codex visual checks; no benchmark inputs',
            'source_verification':'artifacts/source-verification.json'})
    module=load_module(args.day6_root/'src/embeddings.py','catalog_v6_embed')
    embedder=module.LocalEmbedder(model_name=MODEL,revision=REVISION,model_path=str(args.model_path),device='cpu',batch_size=16)
    chunks=[]
    for r in regions:
        for i,part in enumerate(snippets(r['text'],embedder.tokenizer,size=500,overlap=48),1):
            chunks.append({k:v for k,v in r.items() if k not in ('curated_data',)}|{'id':r['evidence_id']+f'#catalog-{i:03d}','text':part})
    from qdrant_client import QdrantClient,models
    client=QdrantClient(path=str(args.qdrant))
    try:
        client.create_collection('lab7_landsat_v5',vectors_config=models.VectorParams(size=384,distance=models.Distance.COSINE))
        for start in range(0,len(chunks),64):
            batch=chunks[start:start+64];vectors=embedder.embed_documents([r['text'] for r in batch])
            client.upsert('lab7_landsat_v5',points=[models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL,r['id'])),vector=v,payload=r) for r,v in zip(batch,vectors)],wait=True)
            print('Indexed',min(start+64,len(chunks)),'/',len(chunks),flush=True)
    finally:client.close()
    write_jsonl(args.output/'regions.jsonl',regions);write_jsonl(args.output/'chunks.jsonl',chunks)
    write_json(args.output/'manifest.json',{'created_at':now(),'pdf_sha256':sha256(args.pdf),
        'source_elements_sha256':sha256(ROOT/'artifacts/advanced/elements.jsonl'),'regions':len(regions),
        'pages':len({r['page'] for r in regions}),'chunks':len(chunks),'image_observations':len(VISUAL),
        'table_candidates':len(tables),'benchmark_inputs_read':False,'builder_sha256':sha256(Path(__file__)),
        'limits':['Some automatic table candidates are reference paragraphs, not actual tables.',
            'Complex unverified table cells are retained explicitly as raw cells; original region remains available.',
            'Visual descriptions and numeric digitization have documented approximation; original PDF is authoritative.'],
        'source_verification':'artifacts/source-verification.json'})
    print('Catalog complete:',len(regions),'regions on',len({r['page'] for r in regions}),'pages')


if __name__=='__main__':main()
