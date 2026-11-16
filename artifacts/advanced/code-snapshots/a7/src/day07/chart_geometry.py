"""Conservative source-pixel measurement for explicit colored bar lookups.

Uses OCR axis ticks/category labels and original PDF pixels. Returns no result
unless the tick scale is linear and one unambiguous bar component is found.
There are no document-specific labels, values, page numbers or gold inputs.
"""
import math
import re
import statistics


def fit_axis(ticks):
    if len(ticks)<3: return None
    ys=[t[0] for t in ticks]; values=[t[1] for t in ticks]
    ym=statistics.mean(ys); vm=statistics.mean(values)
    denominator=sum((y-ym)**2 for y in ys)
    if denominator==0 or max(values)==min(values): return None
    slope=sum((y-ym)*(v-vm) for y,v in ticks)/denominator
    intercept=vm-slope*ym
    residual=max(abs(slope*y+intercept-v) for y,v in ticks)
    if slope>=0 or residual>max(.5,(max(values)-min(values))*.015): return None
    return {'slope':slope,'intercept':intercept,'max_residual':residual,
            'ticks':ticks,'baseline_y':-intercept/slope,'top_y':min(ys)}


def _words(text):
    return set(re.findall(r'[a-z0-9]+',text.casefold()))


def _colored(pixel,color):
    r,g,b=pixel[:3]
    if max(r,g,b)-min(r,g,b)<50: return False
    return {'red':r>100 and r>g*1.3 and r>b*1.3,
            'blue':b>100 and b>r*1.2 and b>g*1.1,
            'green':g>80 and g>r*1.08 and g>b*1.1}[color]


def bar_lookup(question,alias,source,lines,pdf_path,dpi=200):
    if not re.search(r'\bbar\b',question,re.I): return None
    colors=set(re.findall(r'\b(red|blue|green)\b',question.casefold()))
    if len(colors)!=1: return None
    color=next(iter(colors))
    numeric=[]
    for line in lines:
        text=line.get('text','').strip()
        if line.get('confidence',0)>=.95 and re.fullmatch(r'-?\d+(?:\.\d+)?',text):
            x0,y0,x1,y1=line['bbox'];numeric.append(((x0+x1)/2,(y0+y1)/2,float(text)))
    clusters=[]
    for item in sorted(numeric):
        group=next((g for g in clusters if abs(g[0][0]-item[0])<=8),None)
        if group is None:group=[];clusters.append(group)
        group.append(item)
    fits=[fit_axis([(y,v) for _,y,v in group]) for group in clusters if len(group)>=3]
    fits=[f for f in fits if f and f['baseline_y']>f['top_y']+30]
    if len(fits)!=1:return None
    axis=fits[0];words=_words(question)
    categories=[line for line in lines if line.get('confidence',0)>=.9 and
                axis['baseline_y']+2<statistics.mean([line['bbox'][1],line['bbox'][3]])<axis['baseline_y']+22 and
                not re.fullmatch(r'[\d.\s-]+',line['text']) and _words(line['text'])!={'band'}]
    matching=[line for line in categories if _words(line['text']) and _words(line['text'])<=words]
    # A category can itself be named Red/Blue/Green. A question about a red
    # NIR bar matches both 'Red' and 'NIR'; the non-color category is intended.
    if len(matching)>1:
        non_color=[line for line in matching if _words(line['text'])!={color}]
        if non_color:matching=non_color
    if len(matching)!=1 or len(categories)<2:return None
    category=matching[0];cx=(category['bbox'][0]+category['bbox'][2])/2
    centers=sorted((l['bbox'][0]+l['bbox'][2])/2 for l in categories)
    gaps=[abs(x-cx) for x in centers if abs(x-cx)>1]
    if not gaps:return None
    half_width=min(gaps)*.43
    import fitz
    with fitz.open(pdf_path) as pdf:
        pix=pdf[source['page']-1].get_pixmap(dpi=dpi,clip=fitz.Rect(source['bbox']),alpha=False)
        pixels=memoryview(pix.samples)
    scale=dpi/72
    x0=max(0,math.floor((cx-half_width)*scale-pix.x));x1=min(pix.width,math.ceil((cx+half_width)*scale-pix.x))
    y0=max(0,math.floor(axis['top_y']*scale-pix.y));y1=min(pix.height,math.ceil(axis['baseline_y']*scale-pix.y))
    columns=[]
    for x in range(x0,x1):
        ys=[y for y in range(y0,y1) if _colored(pixels[y*pix.stride+x*pix.n:y*pix.stride+x*pix.n+3],color)]
        if len(ys)>=5 and max(ys)>=y1-5:
            columns.append((x,min(ys)))
    components=[]
    for point in columns:
        if not components or point[0]>components[-1][-1][0]+1:components.append([])
        components[-1].append(point)
    components=[c for c in components if len(c)>=4]
    if len(components)!=1:return None
    component=components[0]
    y=statistics.median(p[1] for p in component)
    pdf_y=(y+pix.y)/scale;value=axis['slope']*pdf_y+axis['intercept']
    if value<0 or value>max(v for _,v in axis['ticks'])*1.02:return None
    unit=' SNR' if any(line.get('text','').strip().casefold()=='snr' for line in lines) else ' on the plotted scale'
    return {'status':'answered','answer':f'Approximately {value:.0f}{unit} [{alias}].',
            'citations':[alias],'citation_registry':{alias:source},
            'tool_observation':{'method':'linear OCR tick calibration plus original PDF colored-bar pixels',
                'category':category,'color':color,'axis_fit':axis,'bar_top_pdf_y':pdf_y,
                'measured_value':value,'dpi':dpi,'component_columns':len(component),
                'source_page':source['page'],'source_bbox':source['bbox']}}
