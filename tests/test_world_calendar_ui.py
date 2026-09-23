import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
import test_qol_ui


class WorldCalendarInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_competition_calendar_population_and_back(self):
        a=self.app;a.nav('League');before=a.state['revision']
        self.click('World calendar');self.assertEqual(a.tab,'World calendar')
        self.click('Population');self.click('Next');self.click('Reconciliation');self.click('Calendar')
        self.click('< Competitions');self.assertEqual(a.tab,'League');self.assertEqual(a.state['revision'],before)
