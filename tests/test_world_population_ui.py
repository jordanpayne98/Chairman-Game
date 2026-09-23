import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
import test_qol_ui
from club_chairman.simulation import view


class WorldPopulationInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_browsed_ages_refresh_when_the_career_clock_changes(self):
        a=self.app;a.nav('League');a.tab='World calendar';a.world_tab='Database'
        a.world_country('japan');a.world_kind='staff';a.world_available=True;a.render()
        before={r['id']:r['age'] for r in a.world_query['rows']}
        a.state['day']+=365;a.v=view(a.state);a.render()
        self.assertEqual({r['id']:r['age'] for r in a.world_query['rows']},{pid:age+1 for pid,age in before.items()})

    def test_world_player_history_and_recruitment_from_rendered_controls(self):
        a=self.app;a.nav('League');self.click('World calendar');self.click('Database')
        for label in ('All','Europe','South America','North America'):self.click('Region: '+label)
        while not any(n['id']=='japan' for n in sorted([n for n in a.v['world_population']['nations'] if n['region']=='Asia'],key=lambda n:n['name'])[a.page*10:a.page*10+10]):self.click('Next')
        self.click('Japan');self.click('All active people');self.click('History',0)
        pid=a.world_person;self.click('Add to recruitment');self.click('Confirm')
        self.assertEqual(a.profile,pid);self.assertIn(pid,a.state['world_population']['claimed'])
        p=next(p for p in a.v['players'] if p['id']==pid)
        self.assertEqual(p['nationality'],'Japan');self.assertIsNone(p['report']);self.assertIsNone(p['club'])
        self.click('Request scouting');self.click('Confirm');self.assertIn(pid,a.state['scouting'])

    def test_staff_entry_preserves_assessment_gate_and_legacy_creation(self):
        a=self.app;a.nav('League');self.click('World calendar');self.click('Database')
        a.world_country('japan');self.click('Players');self.click('All active people');self.click('History',0)
        pid=a.world_person;self.click('Add to recruitment');self.click('Confirm')
        self.assertEqual(a.screen,'Staff');p=next(p for p in a.v['staff']['people'] if p['id']==pid)
        self.assertIsNone(p['assessment']);self.assertIsNone(p['club'])
        self.assertTrue(a.command('staff_contact',id=pid))
        a.state['world_population'].update(blob=None,claimed=[],manifest={});a.v=view(a.state)
        a.nav('League');a.tab='World calendar';a.world_tab='Database'
        self.click('Create world database');self.click('Confirm');self.assertTrue(a.v['world_population']['enabled'])

if __name__=='__main__':unittest.main()
