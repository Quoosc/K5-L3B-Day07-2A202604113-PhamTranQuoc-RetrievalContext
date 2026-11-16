import unittest

from src.day07.spectral_join import spectral_join


class SpectralJoinTests(unittest.TestCase):
    def setUp(self):
        self.registry={'e1':{'id':'image'},'e2':{'id':'table'}}
        self.elements={'table':{'element_type':'table_candidate',
                       'rows':[['OLI','OLI'],['Band','Performance'],['1','238'],['2','364']]}}
        self.ocr={'image':{'status':'ok','lines':[
            {'text':'0.100 - 0.200','confidence':0.99,'bbox':[10,10,30,20]},
            {'text':'Band 1','confidence':0.99,'bbox':[35,10,55,20]}]}}
        self.question='Using two tables, which band spans 0.100–0.200 and what is its OLI performance?'

    def test_joins_only_the_two_referenced_sources(self):
        result=spectral_join(self.question,self.registry,self.elements,self.ocr)
        self.assertIn('OLI Band 1',result['answer'])
        self.assertIn('238 [e2]',result['answer'])
        self.assertEqual(result['citations'],['e1','e2'])

    def test_ambiguous_or_low_confidence_ocr_is_not_used(self):
        self.ocr['image']['lines'].append({'text':'Band 2','confidence':0.99,'bbox':[60,10,80,20]})
        self.assertIsNone(spectral_join(self.question,self.registry,self.elements,self.ocr))
        self.ocr['image']['lines'].pop()
        self.ocr['image']['lines'][0]['confidence']=0.4
        self.assertIsNone(spectral_join(self.question,self.registry,self.elements,self.ocr))


if __name__=='__main__': unittest.main()
