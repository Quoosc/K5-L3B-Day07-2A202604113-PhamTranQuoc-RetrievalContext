import unittest

from src.day07.advanced_eval import score
from src.day07.advanced_retrieval import nearby_caption


class AdvancedScoringTests(unittest.TestCase):
    def test_caption_association_prefers_the_caption_below_a_region(self):
        region = {'bbox': [0, 100, 100, 200]}
        page = [{'element_type': 'text', 'bbox': [0, 80, 100, 90], 'content': 'Table 2-2. Table above'},
                {'element_type': 'text', 'bbox': [0, 212, 100, 222], 'content': 'Figure 2-3. Chart below'}]
        self.assertEqual(nearby_caption(region, page), 'Figure 2-3. Chart below')

    def test_missing_and_error_cases_remain_in_denominator(self):
        queries = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
        gold = [{'id': 'a', 'primary_group': 'table', 'answerable': True},
                {'id': 'b', 'primary_group': 'chart', 'answerable': True},
                {'id': 'c', 'primary_group': 'unanswerable', 'answerable': False}]
        traces = [{'query_id': 'a', 'status': 'answered'}, {'query_id': 'b', 'status': 'error'}]
        reviews = [{'query_id': 'a', 'pass': True, 'reason': 'verified', 'reviewer': 'reviewer'},
                   {'query_id': 'b', 'pass': False, 'reason': 'error', 'reviewer': 'reviewer'},
                   {'query_id': 'c', 'pass': False, 'reason': 'missing output', 'reviewer': 'reviewer'}]
        result = score(queries, gold, traces, reviews)
        self.assertEqual((result['passed'], result['total'], result['errors_or_missing']), (1, 3, 2))
        self.assertEqual(result['required_passes'], 3)
        self.assertFalse(result['meets_90_percent'])
        reviews[1]['pass'] = True
        with self.assertRaises(ValueError): score(queries, gold, traces, reviews)


if __name__ == '__main__': unittest.main()
