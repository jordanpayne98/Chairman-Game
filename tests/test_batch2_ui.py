import os
import tempfile
import unittest
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career,view
from club_chairman import pathways
import test_qol_ui


class Batch2InterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_brief_queue_results_and_cancel(self):
        a=self.app;a.command('planning',key='shortlist',value=['p144','p145']);self.click('Scouting desk');self.click('Save brief');self.assertIsNotNone(a.state['scouting_work']['brief'])
        cash=a.state['cash'];self.click('Scout saved targets');self.click('Cancel');self.assertEqual(a.state['cash'],cash)
        self.click('Scout saved targets');self.click('Confirm');self.assertEqual(len(a.state['scouting_work']['jobs']),2)
        self.click('Queue');self.click('Batch results');self.click('Outcomes');self.click('< Recruitment');self.assertEqual(a.tab,'Recruitment')

    def test_pathway_navigation_and_real_dossier(self):
        a=self.app;a.nav('Academy');self.click('Pathways');self.click('Development fixtures');self.assertEqual(a.screen,'Academy')
        self.click('Loans');self.click('Tables');self.click('Youth');self.assertEqual(a.development_group,'Reserves')
        self.click('Players');self.click('Development detail');pid=a.pathway_player;self.click('Player dossier');self.assertEqual(a.screen,'Squad');self.assertEqual(a.profile,pid)

    def test_advice_and_renewal_confirmations(self):
        a=self.app;p=next(p for p in a.state['players'] if p['club']=='c0' and p['youth']);pid=p['id'];p['contract_end']=20
        a.state['pathways']['reviews'][pid]=pathways.review(a.state,p);a.v=view(a.state);a.nav('Academy');self.click('Pathways');a.pathway_player=pid
        self.click('Apply advice');self.click('Cancel');self.assertEqual(a.state['players'][0]['development']['pathway_history'],[])
        self.click('Apply advice');self.click('Confirm');self.assertTrue(next(p for p in a.state['players'] if p['id']==pid)['development']['pathway_history'])
        self.click('Review renewal');self.click('Cancel');self.assertEqual(next(p for p in a.state['players'] if p['id']==pid)['contract_end'],20)
        self.click('Review renewal');self.click('Confirm');self.assertGreater(next(p for p in a.state['players'] if p['id']==pid)['contract_end'],20)
