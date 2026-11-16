"""Conservative formatting of a model's declared answer, without deciding its truth."""
import json
import re

from .advanced_agent import parse_vision_answer
from .agent import parse_answer


def normalize_refiner_reply(raw, registry):
    """Render explicit abstention or declared single-claim citations; keep raw separately.

    Citation membership is checked before any formatting. An assertion inside an
    abstention is not removed or validated; semantic review must still reject it.
    """
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Invalid response')
    if data.get('status') != 'abstain':
        parsed, changed = parse_vision_answer(raw, registry)
        return parsed, ['rendered model-declared single-claim citation'] if changed else []
    prose, citations = data.get('answer'), data.get('citations')
    if not isinstance(prose, str) or not isinstance(citations, list):
        raise ValueError('Invalid abstention')
    if any(not isinstance(c, str) or c not in registry for c in citations):
        raise ValueError('Abstention declared an unavailable citation')
    changes = []
    if not prose.strip() or re.fullmatch(r'[.\s…]+', prose):
        data['answer'] = 'Insufficient evidence in the retrieved excerpts.'
        changes.append('rendered a standard refusal for an empty abstention')
    if not re.search(r'\[[^\[\]\n]{1,100}\]', data['answer']) and citations:
        data['citations'] = []
        changes.append('removed unreferenced citations from the abstention')
    return parse_answer(json.dumps(data, ensure_ascii=False), registry), changes
