"""Input and persistence checks for the Figma runtime routes."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career, view


class ExecutiveInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=App(self.temp.name)

    def tearDown(self):
        pygame.quit();self.temp.cleanup()

    def career(self):
        self.app.state=new_career(42);self.app.v=view(self.app.state);self.app.nav('Overview')

    def click(self,label,index=0):
        a=self.app;found=[];original=a.button
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled))
        a.button=capture
        try:a.render()
        finally:a.button=original
        self.assertGreater(len(found),index,label)
        rect,enabled=found[index];self.assertTrue(enabled,label)
        a.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(round(rect.centerx*a.scale+a.offset[0]),round(rect.centery*a.scale+a.offset[1]))))

    def test_home_settings_and_continue_preserve_original_save(self):
        a=self.app;self.click('Settings');self.click('Reduced motion: Off');self.click('Back')
        self.assertIsNone(a.state);self.assertTrue(a.reduced_motion)
        self.career();a.manual_save();path=next(e['path'] for e in a.store.entries() if e['path'].name=='manual.sqlite3')
        original=path.read_bytes();expected=a.state.copy()
        self.app=App(self.temp.name);self.assertTrue(self.app.reduced_motion)
        self.click('Continue career')
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(self.app.state['cash'],expected['cash'])
        self.assertNotEqual(self.app.state['career_id'],expected['career_id'])
        self.assertEqual(self.app.screen,'Overview')

    def test_inbox_long_reading_and_cancel_do_not_resolve_decision(self):
        self.career();a=self.app;a.command('hire',id='m0')
        for _ in range(3):a.command('continue')
        a.state['inbox'].append(dict(day=a.state['day'],title='Long monthly report',body='Evidence and recorded financial commitments. '*90))
        a.v=view(a.state);before=json.dumps(a.state,sort_keys=True)
        self.click('Inbox');self.click('Long monthly report');self.click('More text')
        self.assertEqual(a.inbox_reader_page,1);self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        self.click('Mark all read');self.assertIsNotNone(a.state['decision'])
        self.click('Review required decision');self.click('Cancel');self.assertIsNotNone(a.state['decision'])
        self.click('Decline');self.click('Cancel');self.assertIsNotNone(a.state['decision'])
        self.click('Review required decision');self.click('Confirm');self.assertIsNone(a.state['decision'])

    def test_fixture_report_is_read_only_and_sidebar_preserves_authority_draft(self):
        self.career();a=self.app;a.command('hire',id='m0')
        while not a.state['match']:
            if a.state['decision']:a.command('decision',choice='decline')
            a.command('continue')
        a.command('match_skip');a.command('match_close');before=json.dumps(a.state,sort_keys=True)
        self.click('Fixtures');self.click('Match report')
        self.assertEqual(a.match_report,'f0-0');self.assertEqual(json.dumps(a.state,sort_keys=True),before)
        self.click('Responsibilities');a.authority_draft={'mode':'Approval required','limit':100000,'duration':1}
        draft=a.authority_draft.copy();self.click('Finances');self.click('Responsibilities')
        self.assertEqual(a.staff_tab,'Responsibilities');self.assertEqual(a.authority_draft,draft)

    def test_long_review_pages_and_keyboard_zoom_keep_controls_reachable(self):
        self.career();a=self.app;before=json.dumps(a.state,sort_keys=True)
        a.confirm('Detailed review','All current obligations remain binding. '*100,None)
        self.click('Next text');self.assertEqual(a.modal_page,1)
        a.change_zoom(1.75)
        for _ in range(8):
            a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,unicode='\t',mod=0));a.render()
            rect=a.buttons[a.focus%len(a.buttons)][0]
            self.assertGreaterEqual(rect.left*a.scale+a.offset[0],0)
            self.assertLessEqual(rect.right*a.scale+a.offset[0],a.window.get_width())
        a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,unicode='',mod=0));a.render()
        self.assertIsNone(a.modal);self.assertEqual(json.dumps(a.state,sort_keys=True),before)


if __name__=='__main__':unittest.main()
