import os,tempfile,unittest
from copy import deepcopy
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from club_chairman.ui import App
from club_chairman.simulation import new_career,view
from test_feeders import place_owner,finish


class FeederInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory();self.a=App(self.root.name)
        self.a.state=new_career(19,'wales');self.a.v=view(self.a.state);self.a.nav('League')

    def tearDown(self):pygame.quit();self.root.cleanup()

    def click(self,label):
        a=self.a;original=a.button;found=[]
        def capture(text,rect,callback,enabled=True):
            original(text,rect,callback,enabled)
            if text==label:found.append((pygame.Rect(rect),enabled))
        a.button=capture
        try:a.render()
        finally:a.button=original
        self.assertEqual(len(found),1,label);r,enabled=found[0];self.assertTrue(enabled,label)
        a.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(round(r.centerx*a.scale+a.offset[0]),round(r.centery*a.scale+a.offset[1]))))

    def test_pool_navigation_is_read_only_and_archives_keep_pool_tables(self):
        a=self.a;before=deepcopy(a.state)
        self.click('Regional pool');self.assertEqual(a.league_id,'wales-regional')
        controls={};original=a.button
        def capture(label,rect,callback,enabled=True):
            controls[label]=pygame.Rect(rect);original(label,rect,callback,enabled)
        a.button=capture;a.render();a.button=original
        for label,rect in controls.items():
            if label!='Regional pool':self.assertFalse(controls['Regional pool'].colliderect(rect),label)
        self.click('Your division');self.assertEqual(a.league_id,'wales-1');self.assertEqual(a.state,before)
        a.state=finish(place_owner(a.state,'wales-2'));a.v=view(a.state);a.nav('Career')
        self.click('Prepare next season');self.click('Confirm')
        self.assertEqual(a.v['leagues']['own_division'],'wales-regional');self.assertNotIn('c0',a.v['competitions']['cup']['entrants'])
        a.nav('League');a.render();self.assertEqual(a.league_id,'wales-regional')
        a.open_season_history(1);self.click('Switch division')
        self.assertEqual(a.history_division,'wales-regional')
        before=deepcopy(a.state);a.render();self.assertEqual(a.state,before)

    def test_relegated_career_explains_cup_exclusion_and_controls_at_zoom(self):
        a=self.a;a.state=place_owner(a.state,'wales-regional');a.v=view(a.state);a.nav('Career')
        texts=[];original=a.wrap
        def capture(text,*args,**kwargs):texts.append(text);return original(text,*args,**kwargs)
        a.wrap=capture;a.render();a.wrap=original
        self.assertTrue(any('do not enter the primary cup' in text for text in texts))
        a.nav('League');a.change_zoom(1.75)
        for _ in range(10):
            a.render();a.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB,unicode='\t',mod=0));a.render()
            r=a.buttons[a.focus%len(a.buttons)][0]
            self.assertGreaterEqual(r.left*a.scale+a.offset[0],0)
            self.assertLessEqual(r.right*a.scale+a.offset[0],a.window.get_width())
