import json
from copy import deepcopy
import os
import tempfile
import unittest
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career, view, start_match


class CupInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.a=App(self.temp.name)
        self.a.state=new_career(42);self.a.v=view(self.a.state)
        self.a.command('budget',value=4000000);self.a.command('hire',id='m0')

    def tearDown(self):
        pygame.quit();self.temp.cleanup()

    def click(self,label):
        original=self.a.button;found=[]
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled))
        self.a.button=capture
        try:self.a.render()
        finally:self.a.button=original
        self.assertTrue(found,label);rect,enabled=found[0];self.assertTrue(enabled,label)
        self.a.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(round(rect.centerx*self.a.scale+self.a.offset[0]),round(rect.centery*self.a.scale+self.a.offset[1]))))

    def test_cup_navigation_reports_and_keyboard_are_read_only(self):
        a=self.a;f=next(f for f in a.state['fixtures'] if f.get('knockout') and 'c0' in (f['home'],f['away']))
        a.state['day']=f['day'];a.state['match']=start_match(a.state,f);a.v=view(a.state)
        a.command('match_skip');a.command('match_close');a.nav('League')
        before=json.dumps(a.state,sort_keys=True)
        self.click('Northshire Cup');self.assertEqual(a.screen,'Cup')
        self.click('Next');self.click('Previous');self.click('Cup report')
        self.assertEqual(a.screen,'Matchday');self.assertTrue(a.match_report)
        a.render();a.nav('Cup');a.change_zoom(1.75)
        for _ in range(10):
            a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,unicode='\t',mod=0));a.render()
            rect=a.buttons[a.focus%len(a.buttons)][0]
            self.assertGreaterEqual(rect.left*a.scale+a.offset[0],0)
            self.assertLessEqual(rect.right*a.scale+a.offset[0],a.window.get_width())
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)

    def test_archived_cup_route_uses_saved_fixtures_without_replay(self):
        a=self.a
        # A public archive fixture exercises navigation independently of simulation.
        cup=deepcopy(a.v['competitions']['cup']);cup['winner']='c0'
        a.state['career']['history']=[dict(season=1,table=deepcopy(a.v['table']),
            fixtures=deepcopy(a.v['fixtures']),competitions={'cup':cup},cash=a.v['cash'],day=96)]
        a.v=view(a.state);before=json.dumps(a.state,sort_keys=True)
        a.open_season_history(1);self.click('Archived cup');self.assertEqual(a.screen,'CupHistory')
        a.render();self.assertEqual(json.dumps(a.state,sort_keys=True),before)

    def test_legacy_empty_state_and_fixture_labels_render(self):
        a=self.a;a.state['competitions']['cup']=None;a.v=view(a.state);a.nav('Cup')
        before=json.dumps(a.state,sort_keys=True);self.click('League table');self.assertEqual(a.screen,'League')
        a.nav('Fixtures');a.render();self.assertEqual(json.dumps(a.state,sort_keys=True),before)

    def test_division_switch_and_archived_tables_preserve_state_at_zoom(self):
        from test_leagues import completed_world
        a=self.a;a.state=completed_world();a.state['career']['history']=[dict(season=1,
            table=deepcopy(view(a.state)['table']),fixtures=deepcopy(a.state['fixtures']),
            leagues=deepcopy(view(a.state)['leagues']),competitions=deepcopy(a.state['competitions']),
            cash=a.state['cash'],day=96)]
        a.v=view(a.state);before=json.dumps(a.state,sort_keys=True);a.nav('League')
        a.render();self.assertEqual(a.league_id,'northshire-1')
        self.click('Switch division');self.assertEqual(a.league_id,'northshire-2')
        self.click('Your division');self.assertEqual(a.league_id,'northshire-1')
        self.click('Season review');a.open_season_history(1)
        self.click('Switch division');self.assertEqual(a.history_division,'northshire-2')
        a.change_zoom(1.75)
        for _ in range(12):
            a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,unicode='\t',mod=0));a.render()
            rect=a.buttons[a.focus%len(a.buttons)][0]
            self.assertGreaterEqual(rect.left*a.scale+a.offset[0],0)
            self.assertLessEqual(rect.right*a.scale+a.offset[0],a.window.get_width())
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)
