"""Conservative AI-assisted dev review. Never reads the held-out test split."""
from collections import Counter
from pathlib import Path
import json

from src.day07.common import now, read_jsonl, read_json, write_json
from src.day07.evaluation import group_hits

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ('D0', 'L0', 'H0', 'H1', 'H2', 'H3')

# Overrides reflect direct reading of answers and cited source text, not just ID matches.
OVERRIDES = {
    ('L0', 'b-dev-q01'): (1, 'The extra example is not established for the unspecified s.'),
    ('H0', 'b-dev-q01'): (1, 'The extra example is not established for the unspecified s.'),
    ('H2', 'b-dev-q01'): (1, 'The extra example is not established for the unspecified s.'),
    ('H3', 'b-dev-q01'): (1, 'The extra example is not established for the unspecified s.'),
    **{(c, 'b-dev-q03'): (0, 'The answer omits the tell() condition and/or asserts unsupported offsets.') for c in ('D0', 'L0', 'H0', 'H1', 'H3')},
    ('H2', 'b-dev-q03'): (1, 'Mentions tell() or zero but omits the seek(0, 2) exception.'),
    **{(c, 'b-dev-q04'): (0, 'The answer reverses the derived-class/base-class relationship despite the evidence.') for c in CONFIGS},
    ('D0', 'b-dev-q06'): (1, 'Identifies deque and slow front operations but does not explain the required element shifts.'),
    ('H2', 'b-dev-q06'): (1, 'Identifies deque and slow front operations but does not explain the required element shifts.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/base/queries/dev.jsonl')
    gold = {g['id']: g for g in read_jsonl(ROOT / 'benchmarks/base/gold/dev.jsonl')}
    result = {'created_at': now(), 'reviewer': 'Codex (AI-assisted review; not human-verified)',
              'method': 'Read answers and obvious failure cases; require exact gold passage in cited context for grade 2, with conservative overrides. A quote match alone is not a semantic citation audit.',
              'per_config': {}}
    for config in CONFIGS:
        run = 'base-dev-20261115-h3' if config == 'H3' else 'base-dev-20261115-v1'
        trace_path = ROOT / f'artifacts/base/runs/{run}/{config}-parser-v3.jsonl'
        traces = {t['query_id']: t for t in read_jsonl(trace_path)}
        metrics = read_json(ROOT / f'artifacts/base/dev-metrics-{config}-v3.json')
        rows = []
        for query in queries:
            qid = query['id']; g = gold[qid]; t = traces[qid]
            row = {'query_id': qid, 'status': t['status'], 'trace': str(trace_path.relative_to(ROOT)).replace('\\', '/')}
            if not g['answerable']:
                correct = t['status'] == 'abstain' and not any(term in t.get('answer', '').casefold()
                            for term in ('probably', 'likely', 'i guess', 'might be'))
                row.update({'abstention_correct': correct,
                            'reason': 'Explicitly declined the fictional entity; corpus name/variant scan is recorded in gold.' if correct else 'Error or no valid abstention.'})
            else:
                entries = t.get('context', {}).get('entries', [])
                cited = [e for e in entries if e['alias'] in t.get('citations', [])]
                in_context = group_hits(entries, g['evidence_groups'])
                in_cited = group_hits(cited, g['evidence_groups'])
                row['context_grade'] = 2 if all(in_context) else 1 if any(in_context) else 0
                if t['status'] != 'answered':
                    grade, reason = 0, 'Model abstained or returned a protocol/system error.'
                elif (config, qid) in OVERRIDES:
                    grade, reason = OVERRIDES[(config, qid)]
                elif not all(in_cited):
                    grade, reason = 0, 'Cited passages do not contain a complete validated gold alternative; conservative no-credit decision.'
                else:
                    grade, reason = 2, 'The answer matches the expected fact and a cited passage contains a complete gold alternative; semantic citation audit remains provisional.'
                row.update({'answer_grade': grade, 'reason': reason, 'all_gold_groups_in_cited': all(in_cited)})
            rows.append(row)
        grade_counts = Counter(str(row['answer_grade']) for row in rows if 'answer_grade' in row)
        abstain = sum(row.get('abstention_correct', False) for row in rows)
        primary = grade_counts['2'] + abstain
        result['per_config'][config] = {'selection_score': primary, 'grounded_0_1_2': dict(grade_counts),
            'correct_abstentions': abstain, 'context_rate': metrics['context_evidence_rate']['rate'],
            'hit3': metrics['evidence_hit3']['rate'], 'hit1': metrics['hit1']['rate'],
            'p95_ms': metrics['runtime']['p95_ms_nearest_rank'], 'api_cost_usd': metrics['runtime']['api_cost_usd'],
            'labels': rows}
    def key(item):
        name, d = item
        return (-d['selection_score'], -d['context_rate'], -d['hit3'], -d['hit1'], d['p95_ms'], d['api_cost_usd'], name)
    ranked = sorted(result['per_config'].items(), key=key)
    result['chosen'] = ranked[0][0]
    result['ranking'] = [name for name, _ in ranked]
    result['selection_rationale'] = 'Apply the predeclared ordering to the conservative AI-reviewed dev labels; this is not a substitute for independent human review.'
    write_json(ROOT / 'artifacts/base/dev_review.json', result)
    print(json.dumps({'chosen': result['chosen'], 'ranking': result['ranking'],
                      'scores': {c: result['per_config'][c]['selection_score'] for c in CONFIGS}}, indent=2))


if __name__ == '__main__': main()
