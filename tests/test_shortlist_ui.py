import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
from copy import deepcopy
import tempfile
import unittest
import pygame
from club_chairman.ui import App


class ShortlistInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=App(self.temp.name);self.app.start();self.app.nav('Recruitment')

    def tearDown(self):pygame.quit();self.temp.cleanup()

    def click(self,label):
        app=self.app;found=[];original=app.button
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled))
        app.button=capture
        try:app.render()
        finally:app.button=original
        self.assertEqual(len(found),1,label);rect,enabled=found[0];self.assertTrue(enabled,label)
        pos=(round(rect.centerx*app.scale+app.offset[0]),round(rect.centery*app.scale+app.offset[1]))
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos))

    def key(self,key,unicode='',mod=0):
        self.app.event(pygame.event.Event(pygame.KEYDOWN,key=key,unicode=unicode,mod=mod))

    def test_create_filter_profile_delete_undo_and_reload(self):
        app=self.app;before=deepcopy(app.state)
        self.click('Lists: Shortlist');app.list_typing=True
        for char in 'Summer targets':self.key(ord(char),char)
        self.key(pygame.K_RETURN,'\r')
        self.assertEqual(len(app.v['planning']['shortlists']['items']),1)
        self.click('Create list');self.assertEqual(app.shortlist_name(),'Summer targets')
        self.click('Close');self.click('Save visible page');self.click('Confirm')
        self.assertEqual(len(app.v['planning']['shortlist']),7)
        self.click('All players');self.assertEqual(len(app.filtered_players()),7)
        app.open_profile(app.filtered_players()[0]['id'])
        controls={};original=app.button
        def capture(label,rect,callback,enabled=True):
            controls[label]=pygame.Rect(rect);original(label,rect,callback,enabled)
        app.button=capture;app.render();app.button=original
        self.assertFalse(controls['List: Summer targets'].colliderect(controls['Private note']))
        self.click('List: Summer targets')
        app.list_name='Summer priorities';self.click('Rename')
        self.click('Delete selected');self.click('Confirm');self.assertEqual(app.shortlist_name(),'Shortlist')
        self.click('Undo');self.assertEqual(app.shortlist_name(),'Summer priorities')
        self.assertEqual(len(app.v['planning']['shortlist']),7)
        self.click('Close');app.manual_save();saved=deepcopy(app.state['planning'])
        entry=next(e for e in app.store.entries() if e['path'].name=='manual.sqlite3')
        app.load_entry(entry['path']);self.assertEqual(app.state['planning'],saved)
        for key in ('day','cash','players','fixtures','ledger','scouting'):self.assertEqual(app.state[key],before[key])

    def test_invalid_name_keeps_draft_and_escape_protects_it(self):
        app=self.app;self.click('Lists: Shortlist');app.list_name='SHORTLIST'
        self.click('Create list');self.assertEqual(app.list_name,'SHORTLIST')
        self.assertIn('unique',app.message)
        self.key(pygame.K_ESCAPE);self.assertIsNotNone(app.modal)
        self.click('Cancel');self.assertTrue(app.list_manager);self.assertEqual(app.list_name,'SHORTLIST')
        self.click('Close');self.click('Confirm');self.assertFalse(app.list_manager)

    def test_bulk_scope_is_frozen_and_undo_restores_previous_membership(self):
        app=self.app;app.role='GK'
        ids=[p['id'] for p in app.filtered_players()[:7]]
        self.click('Save visible page');self.click('Confirm')
        self.assertEqual(app.v['planning']['shortlist'],ids)
        self.click('Undo');self.assertEqual(app.v['planning']['shortlist'],[])
        self.click('Save visible page');app.command('planning',key='notes',value={'p144':'Changed during review'})
        self.click('Confirm');self.assertEqual(app.v['planning']['shortlist'],[])
        self.assertIn('career changed',app.message)

    def test_keyboard_focus_pagination_zoom_and_consequential_undo_block(self):
        app=self.app;self.click('Lists: Shortlist')
        for i in range(5):app.manage_shortlist('create',name=f'Targets {i}')
        self.assertEqual(app.list_page,1);self.click('< Lists');self.click('Shortlist')
        app.change_zoom(1.75);app.render()
        for _ in range(12):self.key(pygame.K_TAB);app.render()
        self.key(pygame.K_0,mod=pygame.KMOD_CTRL)
        self.assertEqual(app.ui_zoom,1)
        self.click('Close');app.command('hire',id='m0');self.assertIsNone(app.undo)
