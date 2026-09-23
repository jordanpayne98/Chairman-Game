from copy import deepcopy
import unittest
import test_qol_ui
from club_chairman import playing_time as pt
from club_chairman.simulation import view


class PlayingTimeInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_profile_conversation_records_commitment_and_navigation_is_read_only(self):
        a=self.app;a.nav('Squad');a.open_profile('p2')
        self.click('Contract');self.click('Playing time');self.click('Regular starter');self.click('Confirm')
        row=pt.active(a.state,'p2');self.assertIsNotNone(row);self.assertEqual(row['role'],'Regular starter')
        before=deepcopy(a.state);a.render();self.click('Attributes');a.render();self.assertEqual(before,a.state)

    def test_offer_role_requires_submission_and_completion(self):
        a=self.app;a.command('budget',value=4000000);a.command('hire',id='m0')
        a.contract_open('p144');self.click('Playing time');self.click('Role: No new commitment')
        self.assertEqual(a.offer_draft['playing_role'],'Key starter')
        self.assertFalse(a.state['playing_time']['agreements'])
        self.click('Send proposal')
        self.assertEqual(a.state['career']['offers']['p144']['playing_role'],'Key starter')
        self.click('Review conditional acceptance');self.click('Confirm')
        self.assertFalse(a.state['playing_time']['agreements'])
        a.command('continue');a.command('continue');self.click('Review completion');self.click('Confirm')
        self.assertEqual(pt.active(a.state,'p144')['role'],'Key starter')


if __name__=='__main__':unittest.main()
