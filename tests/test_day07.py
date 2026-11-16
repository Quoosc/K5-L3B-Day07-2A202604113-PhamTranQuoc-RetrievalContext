"""Offline tests of the new boundaries; these do not measure the real model."""
import unittest

from src.day07.agent import parse_answer, run_agent
from src.day07.context import pack
from src.day07.evaluation import retrieval_metrics, validate
from src.day07.retrieval import Lexical, rrf, validate_scope


def raw(chunk_id, text, source='doc', page=1):
    return {'chunk_id': chunk_id, 'document_id': source, 'source': 'https://example.org/doc',
            'page': page, 'text': text, 'metadata': {'version': '3.12'},
            'start_offset': 0, 'end_offset': len(text), 'token_count': 4}


def chunk(chunk_id, text, source='doc', page=1):
    return {'id': chunk_id, 'source_id': source, 'source': 'https://example.org/doc',
            'page': page, 'text': text, 'metadata': {'version': '3.12'},
            'start_offset': 0, 'end_offset': len(text), 'token_count': 4, 'rank': 1}


class Day07Tests(unittest.TestCase):
    def test_scope_is_whitelisted_and_applied(self):
        index = Lexical([chunk('a', 'json.loads decodes JSON'), chunk('b', 'other text')])
        self.assertEqual(index.search('json.loads', 3, {'version': '3.12'})[0]['id'], 'a')
        self.assertEqual(index.search('json.loads', 3, {'version': '9'}), [])
        with self.assertRaises(ValueError): validate_scope({'source_id': 'doc'})
        with self.assertRaises(ValueError): validate_scope([])

    def test_rrf_uses_ranks_and_stable_id_tiebreak(self):
        a, b = chunk('a', 'alpha'), chunk('b', 'beta')
        result = rrf([{**b, 'score': 0.9}, {**a, 'score': 0.1}],
                     [{**a, 'score': 1000}, {**b, 'score': 0.001}], 2)
        self.assertEqual([r['id'] for r in result], ['a', 'b'])
        self.assertEqual(result[0]['branch_ranks'], {'dense': 2, 'lexical': 1})

    def test_packer_keeps_whole_blocks_and_reports_dropped_candidates(self):
        a, b = chunk('a', 'alpha'), chunk('b', 'beta')
        one = pack([a], 'alpha', 1000, len)
        packed = pack([a, a, b], 'alpha', len(one['text']), len)
        self.assertEqual([c['id'] for c in packed['entries']], ['a'])
        self.assertEqual([d['decision'] for d in packed['decisions']],
                         ['keep', 'drop_duplicate', 'drop_budget'])
        self.assertLessEqual(packed['tokens'], packed['budget'])

    def test_citations_must_match_context_and_all_prose_markers(self):
        registry = {'e1': {'id': 'a'}, 'e2': {'id': 'b'}}
        valid = '{"status":"answered","answer":"A [e1, e2].","citations":["e1","e2"]}'
        self.assertEqual(parse_answer(valid, registry)['status'], 'answered')
        abstain = '{"status":"abstain","answer":"The supplied passages are insufficient [e1].","citations":["e1"]}'
        self.assertEqual(parse_answer(abstain, registry)['status'], 'abstain')
        self.assertEqual(parse_answer('{"status":"abstain","answer":"No evidence."}', {})['citations'], [])
        for invalid in (
            '{"status":"answered","answer":"A [e1] [unknown]","citations":["e1"]}',
            '{"status":"answered","answer":"A","citations":["e1"]}',
            '{"status":"answered","answer":"A [e2]","citations":["e2"]}',
        ):
            with self.assertRaises(ValueError): parse_answer(invalid, {'e1': {'id': 'a'}})

    def test_and_groups_and_missing_traces_count_in_denominator(self):
        qs = [{'id': 'q1'}, {'id': 'q2'}]
        evidence = lambda quote: {'source_id': 'doc', 'page': 1, 'quote': quote}
        gs = [{'id': 'q1', 'answerable': True, 'evidence_groups': [[evidence('alpha')], [evidence('beta')]]},
              {'id': 'q2', 'answerable': True, 'evidence_groups': [[evidence('alpha')]]}]
        traces = [{'query_id': 'q1', 'status': 'answered',
                   'original_ranking': {'results': [chunk('a', 'alpha'), chunk('b', 'beta')]},
                   'context': {'entries': [chunk('a', 'alpha')]}}]
        result = retrieval_metrics(qs, gs, traces)
        self.assertEqual(result['hit1'], {'n': 1, 'N': 2, 'rate': .5})
        self.assertEqual(result['all_groups_hit3']['n'], 1)
        self.assertEqual(result['context_evidence_rate']['n'], 0)
        self.assertEqual(result['errors_or_missing'], 1)

    def test_benchmark_validator_blocks_gold_leak_and_unresolvable_alternative(self):
        qs = [{'id': 'q', 'split': 'dev', 'question': 'Question?', 'scope': {}}]
        ev = {'source_id': 'doc', 'page': 1, 'quote': 'alpha'}
        gs = [{'id': 'q', 'split': 'dev', 'answerable': True, 'expected_answer': 'alpha',
               'evidence_groups': [[ev]]}]
        validate(qs, gs, [raw('a', 'alpha')], 'dev', enforce_minimum=False)
        with self.assertRaises(ValueError):
            validate([{**qs[0], 'answerable': True}], gs, [raw('a', 'alpha')], 'dev', False)
        with self.assertRaises(ValueError):
            validate(qs, [{**gs[0], 'evidence_groups': [[ev, {**ev, 'quote': 'missing'}]]}],
                     [raw('a', 'alpha')], 'dev', False)

    def test_tool_error_is_not_misreported_as_abstention(self):
        class Model:
            model = 'fake'
            def chat(self, messages, **kwargs):
                return {'choices': [{'message': {'role': 'assistant', 'tool_calls': [
                    {'id': 'call', 'function': {'name': 'search', 'arguments': '{"query":"q"}'}}]}}]}
        class Broken:
            def search(self, *args, **kwargs): raise ConnectionError('database unavailable')
        result = run_agent({'id': 'q', 'question': 'q'}, Broken(), Model(),
                           {'id': 'D0', 'method': 'dense', 'candidate_k': 3, 'context_budget': 100})
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['stop_reason'], 'system_or_protocol_error')


if __name__ == '__main__':
    unittest.main()
