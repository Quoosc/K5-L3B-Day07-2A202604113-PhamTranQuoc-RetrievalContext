import json
import unittest

from src.day07.advanced_formatting import normalize_refiner_reply


class AdvancedFormattingTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'e1': {'id': 'source-1'}}

    def test_empty_abstention_becomes_a_visible_refusal(self):
        raw = json.dumps({'status':'abstain','answer':'...','citations':['e1']})
        result, changes = normalize_refiner_reply(raw, self.registry)
        self.assertEqual(result['status'], 'abstain')
        self.assertIn('Insufficient evidence', result['answer'])
        self.assertEqual(result['citations'], [])
        self.assertEqual(len(changes), 2)

    def test_abstention_does_not_hide_an_unsupported_assertion(self):
        raw = json.dumps({'status':'abstain','answer':'The value is 7.','citations':[]})
        result, _ = normalize_refiner_reply(raw, self.registry)
        self.assertEqual(result['answer'], 'The value is 7.')

    def test_unknown_declared_citation_is_not_silently_removed(self):
        raw = json.dumps({'status':'abstain','answer':'','citations':['e2']})
        with self.assertRaises(ValueError):
            normalize_refiner_reply(raw, self.registry)

    def test_answer_only_renders_citation_already_declared(self):
        raw = json.dumps({'status':'answered','answer':'0.069','citations':['e1']})
        result, changes = normalize_refiner_reply(raw, self.registry)
        self.assertEqual(result['answer'], '0.069 [e1]')
        self.assertTrue(changes)


if __name__ == '__main__':
    unittest.main()
