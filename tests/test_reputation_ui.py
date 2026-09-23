from copy import deepcopy
import unittest
import test_qol_ui
from club_chairman import reputation
from club_chairman.simulation import view


class ReputationInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_club_competition_and_player_evidence_are_read_only_and_navigable(self):
        a=self.app
        for i in range(5):reputation.change(a.state,'clubs','c0',str(i),1,'Domestic league champions',{})
        a.v=view(a.state);before=deepcopy(a.state)
        a.nav('Career');self.click('Reputation');self.assertEqual(a.screen,'Reputation')
        self.click('Evidence >');self.assertEqual(a.reputation_page,1)
        self.click('Leagues');self.assertEqual(a.reputation_kind,'leagues')
        self.click('Domestic cup');self.assertEqual(a.reputation_kind,'cups')
        self.click('Clubs');self.click('Evidence',0)
        a.nav('Squad');a.open_profile('p2');self.click('Contract');self.click('Reputation history')
        self.assertEqual(a.profile_tab,'Reputation');a.render()
        self.assertEqual(before,a.state)
        self.click('Attributes');a.render();self.assertEqual(before,a.state)


if __name__=='__main__':unittest.main()
