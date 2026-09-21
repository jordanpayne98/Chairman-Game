import json
import os
import tempfile
import unittest
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career,view
from club_chairman.navigation import search
import test_qol_ui


class DepthInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click
    key=test_qol_ui.QolInterfaceTests.key

    def test_exact_full_and_stale_profile_labels_and_comparison(self):
        from club_chairman import people
        from club_chairman.football_ui import interval
        a=self.app;seen=[];original=a.text
        def capture(text,*args,**kwargs):
            seen.append(text);return original(text,*args,**kwargs)
        a.text=capture
        p=a.state['players'][144]
        for day,expected in ((0,'FULLY SCOUTED'),(28,'STALE')):
            if day==0:a.state['reports'][p['id']]=people.report(a.state,p,'Analyst',9,complete=True)
            a.state['day']=day;a.v=view(a.state);a.nav('Recruitment');a.open_profile(p['id'])
            before=json.dumps(a.state,sort_keys=True);seen.clear();a.render()
            self.assertIn(expected,seen)
            self.assertIn('CURRENT ABILITY' if day==0 else 'EST. ABILITY',seen)
            self.assertIn('EST. POTENTIAL',seen)
            self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        a.restore_position({'sort':'Goalkeeping'});self.assertEqual(a.sort,'Reflexes')
        a.state['reports']['p145']=dict(day=0,source='Legacy',confidence='Low',ranges={'goalkeeping':[40,60]})
        a.state['planning']['comparison']=['p2',p['id'],'p145','p146']
        a.v=view(a.state);a.nav('Comparison');before=json.dumps(a.state,sort_keys=True);a.render()
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        self.assertEqual(interval([61,61]),'61');self.assertEqual(interval([55,65]),'55–65')

    def test_profile_groups_plans_and_registration_confirmation(self):
        a=self.app;a.nav('Squad');a.open_profile('p2')
        self.click('Goalkeeping');self.assertEqual(a.profile_tab,'Goalkeeping')
        self.click('Development');self.click('Focus: Balanced');self.click('Load: Normal')
        p=next(p for p in a.state['players'] if p['id']=='p2')
        self.assertEqual((p['development']['focus'],p['development']['load']),('Technical','Intense'))
        self.click('< Back to list');self.click('Registration')
        before=json.dumps(a.state,sort_keys=True);self.click('Remove',2)
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        self.click('Review registration');self.click('Confirm')
        self.assertNotIn('p2',a.state['registration']['c0']);self.assertEqual(p['club'],'c0')

    def test_search_is_public_navigation_and_cannot_spend(self):
        a=self.app;before=json.dumps(a.state,sort_keys=True)
        self.key(pygame.K_k,mod=pygame.KMOD_CTRL)
        for c in 'registration':self.key(ord(c),c)
        self.assertEqual(a.palette,'registration')
        self.click('Squad / department');self.assertEqual(a.screen,'Squad')
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        result=search(a.v,'Daniel')
        for p in a.state['players']:p['potential']=100;p['attrs']['passing']=99
        self.assertEqual(result,search(view(a.state),'Daniel'))

    def test_keyboard_controls_and_confirmation_are_reachable_at_175_percent(self):
        a=self.app;a.nav('Squad');a.open_profile('p2');a.change_zoom(1.75)
        before=json.dumps(a.state,sort_keys=True)
        for _ in range(50):
            self.key(pygame.K_TAB);a.render()
            rect=a.buttons[a.focus%len(a.buttons)][0]
            center=(rect.centerx*a.scale+a.offset[0],rect.centery*a.scale+a.offset[1])
            self.assertTrue(0<=center[0]<=a.window.get_width() and 0<=center[1]<=a.window.get_height(),(rect,center))
        a.confirm('Review','The full contract review is accessible.',lambda:None);a.render()
        self.key(pygame.K_TAB);self.key(pygame.K_RETURN,'\r');self.assertIsNone(a.modal)
        self.key(pygame.K_0,mod=pygame.KMOD_CTRL);self.assertEqual(a.ui_zoom,1)
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))

    def test_finished_match_review_and_all_stat_tabs_do_not_mutate(self):
        a=self.app;a.command('hire',id='m0')
        while not a.state['match']:
            if a.state['decision']:a.command('decision',choice='decline')
            a.command('continue')
        a.nav('Matchday');self.click('Skip to full time')
        self.assertTrue(a.state['match']['finished'])
        before=json.dumps(a.state,sort_keys=True)
        self.click('Statistics');self.click('Lineups');self.click('Show commentary');self.click('Key events')
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        self.click('Finish review');self.assertEqual(a.screen,'Overview')


if __name__=='__main__':unittest.main()
