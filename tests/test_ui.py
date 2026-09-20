import os
os.environ['SDL_VIDEODRIVER']='dummy'
import tempfile
import unittest
import pygame
from club_chairman.ui import App

class InterfaceTests(unittest.TestCase):
    def test_connected_management_flow(self):
        with tempfile.TemporaryDirectory() as temp:
            app=App(temp)
            def click(label):
                app.render()
                # Click the rendered button by its displayed text order through a capture wrapper.
                found=[];original=app.button
                def capture(text,rect,callback,enabled=True):
                    original(text,rect,callback,enabled)
                    if text==label:found.append((pygame.Rect(rect),enabled))
                app.button=capture;app.render();app.button=original
                self.assertEqual(len(found),1,label);rect,enabled=found[0];self.assertTrue(enabled,label)
                point=(round(rect.centerx*app.scale+app.offset[0]),round(rect.centery*app.scale+app.offset[1]))
                app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
            click('New career');click('Confirm');click('Staff');click('Review Alex Rowan');click('Confirm')
            self.assertIsNotNone(app.state['manager'])
            click('Recruitment');app.profile='p144';click('Request scouting');click('Confirm')
            click('Overview')
            for _ in range(3):click('Continue  >')
            self.assertIsNotNone(app.state['decision']);click('Review decision');click('Confirm')
            click('Finances');click('Budget +£2k');click('Recruitment');app.profile='p144';click('Negotiate contract');click('Send proposal');click('Review conditional acceptance');click('Confirm')
            self.assertIsNone(next(p for p in app.state['players'] if p['id']=='p144')['club'])
            click('Next fixture')
            while app.batch:app.continue_day()
            self.assertEqual(app.screen,'Matchday')
            click('Back the manager');click('Confirm');click('Skip to full time');click('Finish review');click('Contracts');click('Review completion');click('Confirm');click('Save')
            self.assertEqual(next(p for p in app.state['players'] if p['id']=='p144')['club'],'c0')
            self.assertEqual(app.state['clubs'][0]['played'],1)
            before=app.state['cash'];entry=next(e for e in app.store.entries() if e['path'].name=='manual.sqlite3')
            app.load_entry(entry['path']);self.assertEqual(app.state['cash'],before)
            for screen in ('Overview','Inbox','Squad','Staff','Recruitment','Finances','League','Matchday','Help'):
                app.nav(screen);app.render()
            pygame.quit()
