import unittest
from src.day07.catalog_agent import decode, source_reference,reference_evidence,row_matches,run
import json


class CatalogProtocolTests(unittest.TestCase):
    def test_answer_first_protocol_has_no_conflicting_status_field(self):
        result=decode('{"answer":"The value is 7.","citations":["e1"]}',{'e1':{'id':'source'}})
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['answer'],'The value is 7 [e1].')

    def test_only_an_explicit_pure_refusal_sentinel_becomes_abstain(self):
        result=decode('{"answer":"INSUFFICIENT_EVIDENCE","citations":[]}',{'e1':{'id':'source'}})
        self.assertEqual(result['status'],'abstain')
        with self.assertRaises(ValueError):
            decode('{"answer":"INSUFFICIENT_EVIDENCE but a price is $10","citations":[]}',{'e1':{'id':'source'}})

    def test_unknown_or_undeclared_sources_are_not_repaired(self):
        with self.assertRaises(ValueError):decode('{"answer":"A fact","citations":["e2"]}',{'e1':{'id':'source'}})
        with self.assertRaises(ValueError):decode('{"answer":"A fact [e2]","citations":["e1"]}',{'e1':{'id':'source'}})

    def test_original_image_caption_prefix_distinguishes_same_page_figures(self):
        self.assertEqual(source_reference({'metadata':{'element_type':'image'},'page':69,
            'text':'Figure 6-2: dataset checkbox screenshot.'}),'figure 6-2')

    def test_caption_only_text_is_not_a_source_for_table_values(self):
        self.assertIsNone(reference_evidence({'metadata':{'element_type':'text','source_reference':'table 3-3'},
            'page':48,'text':'Table 3-3. Naming convention.'}))

    def test_exact_activity_phrase_selects_the_source_row(self):
        region={'metadata':{'element_type':'table_candidate'},'curated_data':[
            {'Activity':'Band Alignment Characterization','Purpose':'Measure registration'},
            {'Activity':'Band Alignment Calibration','Purpose':'Adjust OLI LOS'}]}
        self.assertEqual(row_matches(region,'What does Band Alignment Calibration adjust?')[0]['Purpose'],'Adjust OLI LOS')

    def test_grouped_undeclared_inline_sources_are_rejected(self):
        with self.assertRaises(ValueError):decode('{"answer":"A fact [e1, e2]","citations":["e1"]}',{'e1':{'id':'one'},'e2':{'id':'two'}})

    def exercise(self,proposals=None,timeout=False):
        class Client:
            model='unit-fixture'
            def __init__(self):self.requests=[]
            def count_tokens(self,text):return len(text.split())
            def post(self,path,data):
                self.requests.append(data)
                if len(self.requests)==1:
                    if timeout:raise TimeoutError('fixture timeout')
                    return {'choices':[{'message':{'role':'assistant','content':'INSUFFICIENT_EVIDENCE','tool_calls':proposals or []}}]}
                return {'choices':[{'message':{'role':'assistant','content':'{"answer":"The value is 7","citations":["e1"]}'}}]}
        class Retriever:
            def __init__(self):self.calls=[]
            def retrieve(self,*args):
                self.calls.append(args)
                return {'results':[{'evidence_id':'source','source_id':'doc','source':'https://example.test/source',
                    'page':1,'bbox':[0,0,10,10],'text':'The value is 7.','reference':None,
                    'metadata':{'element_type':'text'}}]}
        c=Client();r=Retriever()
        result=run({'id':'fixture','question':'What is the value?'},r,c,{'branch_pool':3,'max_regions':2,
            'region_text_chars':1000,'context_budget_tokens':1000,'max_output_tokens':100})
        return result,c,r

    def test_missing_native_proposal_uses_logged_original_query_fallback(self):
        result,c,r=self.exercise()
        self.assertEqual(result['status'],'answered')
        self.assertEqual(r.calls[0][1],'What is the value?')
        self.assertEqual(result['events'][0]['event'],'controller_protocol_recovery')
        self.assertFalse(result['events'][1]['native_call_executed'])

    def test_extra_native_proposals_are_acknowledged_but_only_one_is_executed(self):
        proposals=[{'id':name,'type':'function','function':{'name':'search','arguments':json.dumps({'query':q})}}
                   for name,q in [('c1','first query'),('c2','second query')]]
        result,c,r=self.exercise(proposals)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(len(r.calls),1)
        messages=c.requests[-1]['messages']
        self.assertEqual(len([m for m in messages if m['role']=='tool']),2)
        self.assertTrue(any('Not executed' in m.get('content','') for m in messages))

    def test_model_timeout_remains_an_error_and_does_not_become_a_refusal(self):
        result,c,r=self.exercise(timeout=True)
        self.assertEqual(result['status'],'error')
        self.assertEqual(r.calls,[])


if __name__=='__main__':unittest.main()
