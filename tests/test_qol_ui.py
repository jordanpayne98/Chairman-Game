import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ['SDL_VIDEODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career,view


class QolInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=App(self.temp.name)
        self.app.state=new_career(42);self.app.v=view(self.app.state);self.app.nav('Recruitment')

    def tearDown(self):
        pygame.quit();self.temp.cleanup()

    def click(self,label,index=0):
        app=self.app;found=[];original=app.button
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled,callback))
        app.button=capture
        try:app.render()
        finally:app.button=original
        self.assertGreater(len(found),index,label)
        rect,enabled,callback=found[index];self.assertTrue(enabled,label)
        point=(round(rect.centerx*app.scale+app.offset[0]),round(rect.centery*app.scale+app.offset[1]))
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
        return callback

    def key(self,key,unicode='',mod=0):
        self.app.render();self.app.event(pygame.event.Event(pygame.KEYDOWN,key=key,unicode=unicode,mod=mod))

    def test_navigation_filters_comparison_undo_and_career_memory(self):
        a=self.app;a.filter_change('sort','Wage');a.filter_change('descending',True);a.page=1
        ids=[p['id'] for p in a.filtered_players()];self.click('Profile',0)
        self.assertEqual(a.profile,ids[7]);self.click('Next player');self.click('Next player')
        self.click('< Back to list');self.assertEqual(a.page,1);self.assertEqual(a.sort,'Wage')
        self.click('+ List',0);self.assertEqual(len(a.v['planning']['shortlist']),1)
        self.click('Undo');self.assertEqual(a.v['planning']['shortlist'],[])
        self.click('+ Pin',0);self.click('Compare (1/4)');self.assertEqual(a.screen,'Comparison')
        self.click('Forecast this plan');self.assertEqual(a.tab,'Plan')
        self.key(pygame.K_LEFT,mod=pygame.KMOD_ALT);self.assertEqual(a.screen,'Comparison')
        self.key(pygame.K_RIGHT,mod=pygame.KMOD_ALT);self.assertEqual(a.screen,'Finances')
        self.click('Recruitment');self.assertEqual(a.page,1);self.assertEqual(a.sort,'Wage');self.assertTrue(a.descending)
        a.manual_save();path=next(e['path'] for e in a.store.entries() if e['path'].name=='manual.sqlite3')
        a.load_entry(path);a.nav('Recruitment');self.assertEqual(a.page,1);self.assertEqual(a.sort,'Wage')
        self.assertEqual(len(a.v['planning']['comparison']),1)

    def test_notes_keyboard_and_stale_confirmation(self):
        a=self.app;a.open_profile('p144');self.click('Private note')
        self.key(pygame.K_h,'H');self.key(pygame.K_i,'i');self.key(pygame.K_RETURN,'\r')
        self.assertEqual(a.note_draft,'Hi');self.assertIsNotNone(a.editor)
        self.key(pygame.K_TAB);self.key(pygame.K_TAB);self.key(pygame.K_RETURN,'\r')
        self.assertIsNone(a.editor);self.assertEqual(a.v['planning']['notes']['p144'],'Hi')
        self.click('Request scouting');a.command('tickets',value=2000);self.click('Confirm')
        self.assertNotIn('p144',a.state['scouting']);self.assertIn('career changed',a.message)
        self.click('Request scouting');callback=self.click('Confirm');cash=a.state['cash'];callback()
        self.assertEqual(cash,a.state['cash']);self.assertIn('p144',a.state['scouting'])

    def test_reading_inbox_does_not_resolve_approval_and_archive_is_read_only(self):
        a=self.app;a.command('hire',id='m0')
        for _ in range(3):a.command('continue')
        self.click('Inbox');self.click('Mark all read')
        self.assertIsNotNone(a.state['decision']);self.assertFalse(a.command('continue'))
        a.command('decision',choice='decline')
        while not a.state['match']:a.command('continue')
        a.command('match_step',minutes=90);a.command('match_close')
        self.click('League');before=json.dumps(a.state,sort_keys=True)
        self.click('Open match report');self.click('Lineups');self.click('Show commentary');self.click('Key events')
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        self.assertEqual(a.match_report,'f0-0')
        a.collapsed=True;a.render();self.click('Back to fixtures')
        self.assertEqual(a.screen,'League')

    def test_career_contracts_projects_and_keyboard_explanations(self):
        a=self.app;a.command('budget',value=4000000)
        self.click('Staff');self.click('Review Alex Rowan');self.click('Confirm')
        self.click('Recruitment');a.open_profile('p144');self.click('Negotiate contract')
        self.assertEqual(a.screen,'Contracts');self.click('+',0)
        draft=dict(a.offer_draft);self.click('Finances');self.click('Contracts')
        self.assertEqual(a.offer_draft,draft)
        self.click('Send proposal');self.click('Review conditional acceptance');self.click('Confirm')
        self.assertEqual(a.v['career']['offers']['p144']['status'],'medical')
        self.click('Continue  >');self.click('Continue  >')
        self.click('Review completion');self.click('Confirm')
        self.assertEqual(next(p for p in a.v['players'] if p['id']=='p144')['club'],'c0')
        self.click('Staff');self.click('Review Morgan Vale');self.click('Confirm')
        self.assertEqual(a.v['manager']['id'],'m1')
        self.click('Academy');self.click('Arrange annual trials');self.click('Confirm')
        self.click('Review admission',0);self.click('Confirm')
        self.assertEqual(sum(p['club']=='c0' and p['youth'] for p in a.v['players']),1)
        self.click('Facilities');self.click('Commission proposal',0);self.click('Confirm')
        self.click('Cancel proposal');self.click('Confirm')
        self.assertEqual(a.v['career']['projects'][0]['status'],'cancelled')
        a.render();before=json.dumps(a.state,sort_keys=True)
        self.key(pygame.K_F2);a.render();self.assertTrue(a.explain_focus)
        self.key(pygame.K_ESCAPE);self.assertFalse(a.explain_focus)
        self.click('Settings');self.click('Reduced motion: Off')
        self.assertTrue(a.reduced_motion);self.assertEqual(before,json.dumps(a.state,sort_keys=True))

    def test_goal_feedback_uses_current_match_score(self):
        a=self.app;a.command('hire',id='m0')
        while not a.state['match']:
            if a.state['decision']:a.command('decision',choice='decline')
            a.command('continue')
        a.last_score=(9,9)  # A previous match or restored UI must not trigger a cue.
        a.state['config']['shot_rate']=0
        with patch.object(a.sound,'play') as sound:
            a.command('match_step',minutes=1);sound.assert_not_called()
            a.state['config']['shot_rate']=10
            a.command('match_step',minutes=90)
            self.assertGreater(sum(a.v['match']['score']),0);sound.assert_called_once_with('goal')

    def test_fast_forward_stops_for_medical_and_preserves_explicit_control(self):
        a=self.app;a.command('budget',value=4000000);a.command('hire',id='m0')
        a.open_profile('p144');self.click('Negotiate contract');self.click('Send proposal')
        self.click('Review conditional acceptance');self.click('Confirm')
        self.click('Next fixture')
        while a.batch:a.continue_day()
        self.assertEqual(a.v['day'],2);self.assertEqual(a.screen,'Contracts')
        self.assertEqual(a.offer_id,'p144');self.assertEqual(a.v['career']['offers']['p144']['status'],'ready')
        self.assertIsNone(next(p for p in a.v['players'] if p['id']=='p144')['club'])
        self.click('Next fixture');self.assertIsNotNone(a.modal);self.assertFalse(a.batch)
        self.click('Cancel');self.click('Cash review');self.click('Conversation');self.click('Terms')
        self.click('Review completion');self.click('Confirm')
        self.assertEqual(next(p for p in a.v['players'] if p['id']=='p144')['club'],'c0')

    def test_contract_history_is_read_only_and_draft_costs_do_not_submit(self):
        a=self.app;a.command('budget',value=4000000);a.command('hire',id='m0')
        a.open_profile('p144');self.click('Negotiate contract');self.click('+',0)
        before=json.dumps(a.state,sort_keys=True)
        self.click('Cash review');self.click('Conversation');self.click('Terms')
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        self.click('Withdraw');self.click('Confirm');a.contract_open('p144')
        self.click('< Discussions');self.click('History');self.click('Open discussion')
        self.assertIsNotNone(a.offer_archive)
        before=json.dumps(a.state,sort_keys=True)
        self.click('Conversation');self.click('Cash review');self.click('Terms')
        self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        self.assertEqual(len(a.state['career']['offer_history']),1)
        self.assertEqual(a.state['career']['offers']['p144']['status'],'draft')
