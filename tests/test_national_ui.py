import json,os,tempfile,unittest
from copy import deepcopy
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career,view
from test_nations import finish_country


class NationalInterfaceTests(unittest.TestCase):
    def setUp(self):self.root=tempfile.TemporaryDirectory();self.a=App(self.root.name)
    def tearDown(self):pygame.quit();self.root.cleanup()
    def click(self,label):
        original=self.a.button;found=[]
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled))
        self.a.button=capture
        try:self.a.render()
        finally:self.a.button=original
        self.assertTrue(found,label);r,enabled=found[0];self.assertTrue(enabled,label)
        self.a.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(round(r.centerx*self.a.scale+self.a.offset[0]),round(r.centery*self.a.scale+self.a.offset[1]))))

    def test_scenario_selection_review_and_creation(self):
        a=self.a;self.click('Scenario: Compact');self.click('Scenario: England');self.click('Scenario: Wales')
        self.assertEqual(a.new_scenario,'brazil');self.assertIsNone(a.state)
        self.click('New career');self.assertIsNone(a.state);self.click('Confirm')
        self.assertEqual(a.state['calendar']['nation'],'brazil');self.assertEqual(len(a.state['clubs']),62)
        self.assertEqual(a.state['config']['start_date'],'2026-02-01')
        self.assertTrue(a.store.entries())

    def test_twenty_club_table_pages_and_history_navigation_are_read_only(self):
        a=self.a;a.state=new_career(42,'england');a.v=view(a.state);a.nav('League')
        before=json.dumps(a.state,sort_keys=True)
        self.click('Next');self.assertEqual(a.page,1);self.click('Next');self.assertEqual(a.page,2)
        self.click('Switch division');self.assertEqual(a.page,0);self.assertEqual(a.league_id,'england-2')
        self.click('Your division');self.assertEqual(a.league_id,'england-1')
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        # Archive a complete table without requiring a second football-engine run.
        a.state=finish_country(a.state);a.v=view(a.state);a.command('next_season');a.open_season_history(1)
        before=json.dumps(a.state,sort_keys=True)
        self.click('Next clubs');self.click('Next clubs');self.assertEqual(a.history_table_page,2)
        self.click('Switch division');self.assertEqual(a.history_table_page,0)
        a.change_zoom(1.75)
        for _ in range(12):
            a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,unicode='\t',mod=0));a.render()
            r=a.buttons[a.focus%len(a.buttons)][0]
            self.assertGreaterEqual(r.left*a.scale+a.offset[0],0)
            self.assertLessEqual(r.right*a.scale+a.offset[0],a.window.get_width())
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)

    def test_calendar_conflict_preserves_current_career_and_explains_failure(self):
        from unittest.mock import patch
        from club_chairman import nations
        a=self.a;a.state=new_career(42);a.v=view(a.state);before=deepcopy(a.state)
        n=nations.scenario('england');n['blackout_ranges']=[[0,303]]
        with patch('club_chairman.nations.scenario',return_value=n):self.assertFalse(a.start('england'))
        self.assertEqual(a.state,before);self.assertIn('Calendar conflict',a.message)
