import unittest
from unittest.mock import patch

from src.day07.multimodal_v2 import RetrieverV2, caption_map


def element(eid, kind, bbox, content='', page=1):
    return {'evidence_id':eid,'element_type':kind,'bbox':bbox,'content':content,'pdf_page':page}


class RoutingTests(unittest.TestCase):
    def test_two_figures_on_one_page_use_their_own_nearest_caption(self):
        rows=[element('first','image',[0,0,100,100]),
              element('cap1','text',[0,105,100,115],'Figure 6-1. First interface'),
              element('second','image',[0,180,100,250]),
              element('cap2','text',[0,255,100,265],'Figure 6-2. Second interface')]
        mapping=caption_map(rows)
        self.assertEqual(mapping[('figure','6','1')],['first'])
        self.assertEqual(mapping[('figure','6','2')],['second'])

    def test_adjacent_panels_share_a_caption_and_image_only_table_is_available(self):
        rows=[element('left','image',[0,0,50,100]),element('right','image',[50,0,100,100]),
              element('cap','text',[0,105,100,115],'Figure A-3. Plot'),
              element('table','image',[0,200,100,250]),
              element('tcap','text',[0,255,100,265],'Table 5-1. QA bits')]
        mapping=caption_map(rows)
        self.assertEqual(mapping[('figure','a','3')],['left','right'])
        self.assertEqual(mapping[('table','5','1')],['table'])

    def test_toc_entry_does_not_route_a_region(self):
        self.assertEqual(caption_map([element('toc','text',[0,10,100,20],
            'Figure 2-1. Observatory ........ 8'),element('im','image',[0,30,100,100])]),{})

    def test_original_query_is_kept_when_model_rewrite_loses_the_subject(self):
        r=RetrieverV2.__new__(RetrieverV2)
        r.elements={'source':element('source','text',[0,0,100,100],'Original subject evidence '*10)}
        row={'evidence_id':'source','id':'part','text':'Original subject evidence',
             'metadata':{'element_type':'text'},'score':1,'page':1,'bbox':[0,0,100,100]}
        r.first={'source':row}; r.references={}
        calls=[]
        def search(instance,q,*args,**kwargs):
            calls.append(q)
            return {'raw_ranking':[row] if q=='original subject' else []}
        with patch('src.day07.multimodal_v2.AdvancedRetriever.search',search):
            result=r.candidates('original subject','unrelated rewrite')
        self.assertEqual(calls,['original subject','unrelated rewrite'])
        self.assertEqual(result['results'][0]['evidence_id'],'source')


if __name__=='__main__': unittest.main()
