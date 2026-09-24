import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import tempfile
import unittest
from unittest.mock import patch
from club_chairman.persistence import SaveError
import pygame
from club_chairman.ui import App

class SetupInterfaceTests(unittest.TestCase):
    def test_wizard_controls_review_cancel_and_saved_start(self):
        with tempfile.TemporaryDirectory() as root:
            a=App(root)
            def click(label):
                a.render();found=[];original=a.button
                def capture(text,rect,callback,enabled=True):
                    original(text,rect,callback,enabled)
                    if text==label:found.append((callback,enabled))
                a.button=capture
                try:a.render()
                finally:a.button=original
                self.assertEqual(len(found),1,label);fn,enabled=found[0];self.assertTrue(enabled);fn()
            click('New career');self.assertEqual(a.screen,'Setup')
            a.setup_options['name']='Jordan';a.setup_seed=47
            click('Nationality: England')
            for ch in 'Japan':a.event(pygame.event.Event(pygame.KEYDOWN,key=ord(ch.lower()),unicode=ch,mod=0))
            click('Japan');self.assertEqual(a.setup_options['nationality'],'japan')
            click('Next step');click('• Compact development world');click('Next step')
            click('Division 1');click('Cedar Vale');click('Next step')
            click('Sandbox: Off');click('Extra club funding: £0');click('Next step')
            self.assertEqual(a.setup_step,4);self.assertIsNone(a.state)
            reviewed=a.setup_world
            with patch.object(a.store,'autosave',side_effect=SaveError('disk unavailable')):
                click('Start career');self.assertIsNone(a.state);self.assertEqual(a.screen,'Setup')
            click('Start career')
            self.assertIs(a.state,reviewed);self.assertEqual(a.screen,'Overview')
            self.assertTrue(a.store.entries());a.nav('Owner');a.render()
            a.nav('Home');click('New career');click('Cancel');self.assertIs(a.state,reviewed)
            pygame.quit()

if __name__=='__main__':unittest.main()
