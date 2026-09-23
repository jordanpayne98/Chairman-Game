from copy import deepcopy
import unittest
import test_qol_ui
from club_chairman.simulation import view
from club_chairman import morale,playing_time


class MoraleInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_real_profile_navigation_is_read_only(self):
        a=self.app;a.nav('Squad');a.open_profile('p2')
        self.click('Contract');self.click('Morale and support')
        self.assertEqual(a.profile_tab,'Morale')
        before=deepcopy(a.state);a.render();self.assertEqual(before,a.state)
        self.click('Review playing time');self.assertEqual(a.profile_tab,'Playing time')

    def test_reason_pagination(self):
        a=self.app;p=a.state['players'][2]
        for n in range(5):morale.add(a.state,p,str(n),'result',1,'A dated match reaction',end=7)
        morale.reconcile(a.state);a.v=view(a.state);a.nav('Squad');a.open_profile(p['id'])
        self.click('Contract');self.click('Morale and support');self.click('Reasons >')
        self.assertEqual(a.page,1);self.click('< Reasons');self.assertEqual(a.page,0)

    def test_private_meeting_confirmation_and_followup(self):
        a=self.app;a.nav('Squad');a.open_profile('p2')
        self.click('Contract');self.click('Morale and support');self.click('Private support')
        before=deepcopy(a.state);self.click('Offer encouragement');self.click('Cancel');self.assertEqual(before,a.state)
        self.click('Offer encouragement');self.click('Confirm')
        self.assertEqual(len(a.state['relationships']['meetings']),1)
        self.click('Morale reasons');self.assertEqual(a.profile_tab,'Morale')
