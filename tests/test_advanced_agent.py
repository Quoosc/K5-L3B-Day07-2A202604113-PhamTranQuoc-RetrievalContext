import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.day07.advanced_agent import format_ocr_rows, normalize_table_rows, parse_vision_answer, run_advanced, table_query_hints
from src.day07.common import sha256


class AdvancedAgentTests(unittest.TestCase):
    def test_ocr_lines_keep_row_and_column_order(self):
        lines = [{'text':'right','bbox':[50,10,60,20]}, {'text':'left','bbox':[2,11,12,21]},
                 {'text':'next','bbox':[2,30,12,40]}]
        self.assertEqual(format_ocr_rows(lines), 'left (x=2.0) | right (x=50.0)\nnext (x=2.0)')

    def test_multilevel_headers_are_kept_and_incomplete_rows_are_not_shifted(self):
        rows = [['SNR'], ['ETM+', 'OLI', 'ETM+', 'OLI', 'OLI'],
                ['Band', 'Band', 'Performance', 'Requirement', 'Performance'],
                ['1', '2', '40', '130', '364'], ['missing', '20']]
        result = normalize_table_rows(rows)
        self.assertEqual(result['headers'], ['ETM+ Band', 'OLI Band', 'ETM+ Performance', 'OLI Requirement', 'OLI Performance'])
        self.assertEqual(result['rows'][0]['OLI Performance'], '364')
        self.assertEqual(result['rows'][1], {'unaligned_row':['missing','20']})
        hint = table_query_hints(result, 'What is OLI performance for OLI Band 2?')
        self.assertEqual(hint['candidate_rows'][0]['OLI Performance'], '364')
        self.assertEqual(hint['candidate_columns'], ['OLI Performance'])

    def test_single_claim_citation_can_be_rendered_without_inventing_a_source(self):
        registry = {'e1': {'id': 'evidence'}}
        raw = json.dumps({'status': 'answered', 'answer': 'A fact.', 'citations': ['e1']})
        parsed, normalized = parse_vision_answer(raw, registry)
        self.assertTrue(normalized)
        self.assertEqual(parsed['answer'], 'A fact [e1].')
        parsed, normalized = parse_vision_answer(json.dumps({'status':'answered','answer':'A fact [e1].',
            'citations':['e1','e2']}), {'e1': {'id':'one'}, 'e2': {'id':'two'}})
        self.assertEqual(parsed['answer'], 'A fact [e1] [e2].')
        with self.assertRaises(ValueError):
            parse_vision_answer(json.dumps({'status': 'answered', 'answer': 'First. Second.', 'citations': ['e1']}), registry)
        with self.assertRaises(ValueError):
            parse_vision_answer(json.dumps({'status': 'answered', 'answer': 'A fact.', 'citations': ['unknown']}), registry)

    def test_open_region_cannot_use_an_id_outside_search_results(self):
        class Client:
            model = 'fake'
            def __init__(self): self.calls = []
            def post(self, path, data):
                self.calls.append(data)
                if len(self.calls) == 1:
                    data = {'action': 'search', 'query': 'q'}
                else:
                    data = {'action': 'open_region', 'handles': ['not-retrieved']}
                return {'choices': [{'message': {'role': 'assistant', 'content': json.dumps(data)}}]}
        class Retriever:
            def search(self, *args, **kwargs):
                return {'results': [{'id': 'part', 'evidence_id': 'retrieved', 'page': 1,
                                     'bbox': [0, 0, 1, 1], 'metadata': {'element_type': 'text'},
                                     'text': 'public evidence', 'score': 1.0, 'rank': 1}],
                        'reference_routing': [], 'raw_ranking': []}
        temp_parent = (Path(__file__).resolve().parents[1] / '.local').resolve()
        temp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_parent) as tmp:
            root = Path(tmp).resolve()
            self.assertTrue(root.is_relative_to(temp_parent))
            pdf = root / 'doc.pdf'; pdf.write_bytes(b'fake pdf')
            elements = root / 'elements.jsonl'; elements.write_text('{}\n', encoding='utf-8')
            # A syntactically valid registry is enough to reach the authorization boundary.
            elements.write_text(json.dumps({'evidence_id': 'retrieved'}) + '\n', encoding='utf-8')
            client = Client()
            with patch.dict(sys.modules, {'fitz': types.ModuleType('fitz')}):
                result = run_advanced({'id': 'q', 'question': 'q'}, Retriever(), client, pdf, elements, sha256(pdf))
            self.assertEqual(result['status'], 'error')
            self.assertIn('search results', result['error'])
            self.assertEqual(len(client.calls), 2)


if __name__ == '__main__': unittest.main()
