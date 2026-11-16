"""Best-effort OCR geometry hints. Relations are candidates, not visual proof."""
import re


def _words(text):
    words = re.findall(r'[a-z0-9]+', text.casefold())
    return {w[:-1] if w.endswith('s') and len(w) > 3 and not w.isdigit() else w for w in words}


def spatial_hints(question, lines):
    """Find referenced labels and nearby OCR text by position, without any gold."""
    valid = [line for line in lines if len(line.get('bbox', [])) == 4 and line.get('text')]
    words = _words(question)
    anchors = []
    for line in valid:
        tokens = _words(line['text'])
        if len(tokens) >= 2 and tokens <= words:
            anchors.append(line)
    hints = []
    for anchor in anchors:
        ax0, ay0, ax1, ay1 = anchor['bbox']
        ay = (ay0 + ay1) / 2
        if re.search(r'\b(right|left)\b', question, re.I):
            direction = 'right' if re.search(r'\bright\b', question, re.I) else 'left'
            same_row = [l for l in valid if l is not anchor and
                        abs((l['bbox'][1] + l['bbox'][3]) / 2 - ay) <= 4 and
                        ((l['bbox'][0] > ax1) if direction == 'right' else (l['bbox'][2] < ax0))]
            same_row.sort(key=lambda l: abs(l['bbox'][0] - ax0))
            if same_row:
                hints.append({'anchor':anchor['text'], 'kind':f'ocr_same_row_{direction}_candidates',
                              'candidates':[{'text':l['text'],'bbox':l['bbox']} for l in same_row[:5]]})
        if re.search(r'\btop\b', question, re.I):
            column = [l for l in valid if l['bbox'][3] < ay0 and abs(l['bbox'][0] - ax0) <= 35
                      and re.match(r'^\s*\d[\d\s–-]*[-–]\s*\S',l['text'])]
            column.sort(key=lambda l:l['bbox'][1])
            if column:
                hints.append({'anchor':anchor['text'], 'kind':'ocr_numbered_column_above_label_top_to_bottom',
                              'candidates':[{'text':l['text'],'bbox':l['bbox']} for l in column]})
    return {'hints':hints, 'warning':'OCR geometry can be wrong and does not prove arrow connections or meaning.'}


def spatial_lookup(question, alias, registry, lines):
    """Resolve only an unambiguous same-row or top-of-numbered-column lookup.

    This deterministic tool does not infer arrows, causal relationships or visual
    semantics. The caller must log the result and still review the original crop.
    """
    if alias not in registry or not re.search(r'\bFigure\s+[A-Za-z0-9]+[-.]\d+',question,re.I):
        return None
    observations = spatial_hints(question, lines)
    eligible = []
    for hint in observations['hints']:
        candidates = hint['candidates']
        if hint['kind'] in ('ocr_same_row_right_candidates','ocr_same_row_left_candidates') and len(candidates)==1:
            eligible.append((hint,candidates[0]))
        elif hint['kind']=='ocr_numbered_column_above_label_top_to_bottom' and candidates:
            eligible.append((hint,candidates[0]))
    if len(eligible)!=1:
        return None
    hint, selected = eligible[0]
    return {'status':'answered','answer':f"{selected['text']} [{alias}]",'citations':[alias],
            'citation_registry':{alias:registry[alias]},
            'tool_observation':{'method':'deterministic OCR geometry; original crop must be reviewed',
                                'anchor':hint['anchor'],'kind':hint['kind'],'selected':selected,
                                'all_candidates':hint['candidates']}}
