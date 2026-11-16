"""A narrow, auditable two-source band/range lookup from OCR and extracted tables."""
from decimal import Decimal, InvalidOperation
import re

from .advanced_agent import normalize_table_rows

RANGE = re.compile(r'(?<!\d)(\d+\.\d+)\s*[-–—]\s*(\d+\.\d+)(?!\d)')
BAND = re.compile(r'^\s*(?:[A-Za-z]+\s+)?Band\s*(\d+)\s*$',re.I)


def _tokens(text):
    return set(re.findall(r'[a-z]+',text.casefold()))


def spectral_join(question, registry, elements, ocr):
    """Return a sourced answer only for a unique range→band→performance match.

    OCR and extracted table structure can be wrong. No benchmark gold is read;
    callers must log the selected cells and inspect both source regions.
    """
    qwords=_tokens(question)
    ranges=RANGE.findall(question)
    if len(ranges)!=1 or not {'band','performance'} <= qwords:
        return None
    try:
        target=tuple(Decimal(x) for x in ranges[0])
    except InvalidOperation:
        return None
    candidates=[]
    for alias,source in registry.items():
        record=ocr.get(source['id'],{})
        if record.get('status')!='ok': continue
        lines=record.get('lines',[])
        for line in lines:
            found=RANGE.search(line.get('text',''))
            if not found or line.get('confidence',0)<0.9: continue
            try: current=tuple(Decimal(x) for x in found.groups())
            except InvalidOperation: continue
            if current!=target: continue
            a=line['bbox']; y=(a[1]+a[3])/2
            nearby=[]
            for other in lines:
                match=BAND.match(other.get('text',''))
                if (match and other.get('confidence',0)>=0.9 and other['bbox'][0]>=a[2]
                        and other['bbox'][0]-a[2]<=100 and abs((other['bbox'][1]+other['bbox'][3])/2-y)<=4):
                    nearby.append((other,match.group(1)))
            if len(nearby)==1:
                candidates.append((alias,line,nearby[0][0],nearby[0][1]))
    if len(candidates)!=1: return None
    range_alias,range_line,band_line,number=candidates[0]
    matches=[]
    for alias,source in registry.items():
        element=elements.get(source['id'],{})
        if alias==range_alias or element.get('element_type')!='table_candidate': continue
        table=normalize_table_rows(element.get('rows',[]))
        bands=[h for h in table['headers'] if 'band' in _tokens(h)]
        values=[h for h in table['headers'] if 'band' not in _tokens(h)]
        def choose(headers):
            scored=[(len(_tokens(h)&qwords),h) for h in headers]
            best=max((n for n,_ in scored),default=0)
            winners=[h for n,h in scored if n==best and n>0]
            return winners[0] if len(winners)==1 else None
        band_header,value_header=choose(bands),choose(values)
        if not band_header or not value_header or 'performance' not in _tokens(value_header): continue
        rows=[row for row in table['rows'] if 'unaligned_row' not in row and str(row.get(band_header,'')).strip()==number]
        if len(rows)!=1: continue
        value=str(rows[0].get(value_header,'')).strip()
        if not re.fullmatch(r'-?\d+(?:\.\d+)?',value): continue
        matches.append((alias,band_header,value_header,value,rows[0]))
    if len(matches)!=1: return None
    table_alias,band_header,value_header,value,row=matches[0]
    instrument=re.sub(r'\bBand\b','',band_header,flags=re.I).strip()
    label=(instrument+' ' if instrument else '')+'Band '+number
    metric=value_header + (' SNR' if re.search(r'\bsnr\b',question,re.I) and 'snr' not in _tokens(value_header) else '')
    condition=' at Ltypical' if re.search(r'\bltypical\b',question,re.I) else ' at the requested condition'
    return {'status':'answered',
            'answer':f'{label} matches the requested range [{range_alias}]. {metric}{condition} is {value} [{table_alias}].',
            'citations':[range_alias,table_alias],
            'citation_registry':{range_alias:registry[range_alias],table_alias:registry[table_alias]},
            'tool_observation':{'method':'unique OCR range→band and parsed table row lookup; source review required',
                                'range_alias':range_alias,'range_line':range_line,'band_line':band_line,
                                'table_alias':table_alias,'band_header':band_header,'value_header':value_header,'row':row}}
