import unittest

from src.day07.spatial_ocr import spatial_hints, spatial_lookup


class SpatialOcrTests(unittest.TestCase):
    def test_right_candidate_stays_on_same_ocr_row(self):
        lines = [{'text':'NODE-A','bbox':[10,10,30,20]}, {'text':'NODE-B','bbox':[50,10,70,20]},
                 {'text':'NODE-C','bbox':[35,50,55,60]}]
        result = spatial_hints('What is to the right of NODE-A?',lines)
        self.assertEqual(result['hints'][0]['candidates'][0]['text'],'NODE-B')

    def test_top_numbered_entries_use_the_referenced_column(self):
        lines = [{'text':'2 - Blue','bbox':[10,20,30,25]}, {'text':'7 - Green','bbox':[10,30,30,35]},
                 {'text':'Odd Sensors','bbox':[10,50,40,55]}, {'text':'9 - Red','bbox':[100,10,120,15]}]
        result = spatial_hints('What is at the top of the odd sensor stack?',lines)
        self.assertEqual(result['hints'][0]['candidates'][0]['text'],'2 - Blue')

    def test_tool_resolves_unique_geometry_without_inventing_a_citation(self):
        lines = [{'text':'NODE-A','bbox':[10,10,30,20],'confidence':0.99}, {'text':'NODE-B','bbox':[50,10,70,20],'confidence':0.99}]
        result = spatial_lookup('In Figure 1-2, what is to the right of NODE-A?', 'e1', {'e1':{'id':'crop'}}, lines)
        self.assertEqual(result['answer'],'NODE-B [e1]')
        self.assertEqual(result['citation_registry']['e1']['id'],'crop')

    def test_tool_refuses_ambiguous_or_missing_regions(self):
        lines = [{'text':'NODE-A','bbox':[10,10,30,20],'confidence':0.99}, {'text':'NODE-B','bbox':[50,10,70,20],'confidence':0.99},
                 {'text':'NODE-C','bbox':[90,10,110,20],'confidence':0.99}]
        self.assertIsNone(spatial_lookup('In Figure 1-2, what is to the right of NODE-A?', 'e1', {'e1':{'id':'crop'}}, lines))
        self.assertIsNone(spatial_lookup('In Figure 1-2, what is to the right of NODE-A?', 'e2', {'e1':{'id':'crop'}}, lines))


if __name__ == '__main__': unittest.main()
