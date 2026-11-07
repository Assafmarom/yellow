import unittest, os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect
class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.old_config=dict(collect.SEARCH)
        collect.SEARCH=dict(collect.SEARCH)
        collect.SEARCH.update(min_price=350000,max_price=400000,min_bedrooms=4,min_bathrooms=2,areas=['Porto','Lisbon'],
                              must_have={'new_or_renovated':True,'private_garden':True,'garage':True},additional_requirements=[])
    def tearDown(self):
        collect.SEARCH=self.old_config
    def house(self):
        return {'id':'test123','url':'https://casa.sapo.pt/house-test123.html','title':'Moradia T4 Maia',
                'price':385000,'bedrooms':4,'bathrooms':2,'energyRating':'B','location':{'text':'Maia'},
                'description':'Totalmente renovada, jardim privado, garagem fechada, com piscina.'}
    def test_new_price_range_changes_results(self):
        self.assertIsNotNone(collect.normalize(self.house(),'Casa SAPO'))
        collect.SEARCH['max_price']=375000
        self.assertIsNone(collect.normalize(self.house(),'Casa SAPO'))
    def test_bedrooms_and_bathrooms_change(self):
        collect.SEARCH['min_bathrooms']=3
        self.assertIsNone(collect.normalize(self.house(),'Casa SAPO'))
        collect.SEARCH['min_bathrooms']=2
        collect.SEARCH['min_bedrooms']=5
        self.assertIsNone(collect.normalize(self.house(),'Casa SAPO'))
    def test_keyword_matched_or_missing_marked_unverified(self):
        collect.SEARCH['additional_requirements']=[{'kind':'keyword','label':'Swimming pool','query':'piscina','required':True},
                                                    {'kind':'keyword','label':'Solar panels','query':'painéis solares','required':True}]
        p=collect.normalize(self.house(),'Casa SAPO')
        self.assertEqual(p['custom_requirements'][0]['status'],'evidenced')
        self.assertEqual(p['custom_requirements'][1]['status'],'unverified')
        self.assertTrue(any('Solar panels' in i for i in p['issues']))
        self.assertEqual(p['category'],'possible')
    def test_arbitrary_manual_wish_unverified(self):
        collect.SEARCH['additional_requirements']=[{'kind':'manual','label':'Quiet street','query':'Quiet residential street','required':True}]
        self.assertEqual(collect.normalize(self.house(),'Casa SAPO')['custom_requirements'][0]['status'],'unverified')
    def test_places_without_key_does_not_invent_nearby(self):
        collect.SEARCH['additional_requirements']=[{'kind':'nearby','label':'Medical clinic','query':'medical clinic','max_distance_km':5,'required':True}]
        with patch.dict(os.environ,{'GOOGLE_MAPS_API_KEY':''}):
            p=collect.normalize(self.house(),'Casa SAPO')
        self.assertEqual(p['custom_requirements'][0]['status'],'unverified')
    def test_region_selection(self):
        collect.SEARCH['areas']=['Lisbon']
        self.assertIsNone(collect.normalize(self.house(),'Casa SAPO'))
if __name__=='__main__':unittest.main()
