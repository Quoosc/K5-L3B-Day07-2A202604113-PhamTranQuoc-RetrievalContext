import unittest

from src.day07.composite import finish


class FailingClient:
    model='local'
    def post(self,*args,**kwargs): raise TimeoutError('timed out')


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.elements={'crop':{'doc_id':'doc','source':'https://example.org','pdf_page':1,
                                'bbox':[0,0,100,100],'element_type':'image'}}
        self.ocr={'crop':{'status':'ok','lines':[{'text':'NODE-A','bbox':[10,10,30,20],'confidence':0.99},
                                                  {'text':'NODE-B','bbox':[50,10,70,20],'confidence':0.99}]}}
        self.vision={'query_id':'q','status':'answered','answer':'old [e1]','citations':['e1'],
                     'raw_answer':'{}','elapsed_ms':1,
                     'events':[{'event':'open_region','opened':[{'alias':'e1','evidence_id':'crop',
                               'extracted_text_sent':'nodes'}]}]}

    def test_unique_spatial_tool_keeps_source_registry(self):
        result=finish({'question':'In Figure 1-2, what is to the right of NODE-A?'},self.vision,
                      self.elements,self.ocr,FailingClient())
        self.assertEqual(result['answer'],'NODE-B [e1]')
        self.assertEqual(result['citation_registry']['e1']['id'],'crop')

    def test_vision_timeout_is_not_converted_into_an_answer(self):
        self.vision.update({'status':'error','error':'TimeoutError: timed out','answer':''})
        result=finish({'question':'In Figure 1-2, what is to the right of NODE-A?'},self.vision,
                      self.elements,self.ocr,FailingClient())
        self.assertEqual(result['status'],'error')

    def test_refiner_timeout_remains_an_error(self):
        result=finish({'question':'What does the document say?'},self.vision,
                      self.elements,self.ocr,FailingClient())
        self.assertEqual(result['status'],'error')
        self.assertIn('TimeoutError',result['error'])


if __name__=='__main__': unittest.main()
