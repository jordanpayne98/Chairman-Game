from copy import deepcopy
import unittest
import test_qol_ui


class RecruitmentInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_interest_tab_uses_recorded_feedback_and_keeps_drafts_uncommitted(self):
        a=self.app;a.command('hire',id='m0');a.contract_open('p144')
        before=deepcopy(a.state);self.click('Player interest');a.render()
        self.assertEqual(before,a.state);self.assertEqual(a.offer_tab,'Player interest')
        self.click('Terms');self.click('+');self.assertEqual(before,a.state)
        self.click('Send proposal');self.click('Player interest')
        self.assertIn('interest',a.state['career']['offers']['p144'])
        before=deepcopy(a.state);a.render();self.assertEqual(before,a.state)


if __name__=='__main__':unittest.main()
