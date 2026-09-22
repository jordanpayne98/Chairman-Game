from copy import deepcopy
import unittest
from club_chairman.simulation import view
import test_qol_ui
import test_transfer_rights


class TransferRightsInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_draft_rights_are_sent_with_club_offer_and_accepted_terms_are_locked(self):
        a=self.app;a.command('hire',id='m0');a.market_open('club_enquire','p20');a.render()
        self.click('Additional terms');self.click('Transfer rights');before=deepcopy(a.state)
        self.click('Buy-back: Off');self.click('First refusal: Off');self.click('+£5k',1)
        self.assertEqual(a.state,before)
        self.click('Back to deal');self.click('Send club offer')
        d=next(reversed(a.state['market']['deals'].values()))
        self.assertTrue(d['first_refusal']);self.assertGreater(d['buy_back_later'],d['buy_back_fee'])
        self.click('Review club consent');self.click('Confirm')
        self.assertEqual(a.state['market']['deals'][d['id']]['status'],'seller_agreed')
        self.click('Additional terms');before=deepcopy(a.state);a.render();self.assertEqual(a.state,before)

    def test_match_notice_review_and_withdrawal_use_real_commands(self):
        t=test_transfer_rights.TransferRightsTests();t.setUp();t.sell(first_refusal=True);n=t.bid()
        a=self.app;a.state=t.s;a.v=view(t.s);a.nav('Transfers');a.market_section('Rights')
        before=deepcopy(a.state);a.render();self.assertEqual(a.state,before)
        self.click('Review match');self.assertEqual(a.state,before)
        self.assertIn('balance after',a.modal[1]);self.click('Confirm')
        self.assertEqual(a.state['clauses']['notices'][0]['status'],'matching')
        self.click('Personal terms');self.assertEqual(a.screen,'Contracts')
        self.assertEqual(a.offer_id,'p2');self.assertEqual(a.state['cash'],before['cash'])
        a.command('withdraw_offer',id='p2')
        self.assertEqual(a.state['clauses']['notices'][0]['status'],'failed')
        self.assertEqual(a.state['club_ai']['decisions'][0]['status'],'medical')

    def test_buyout_profile_action_opens_personal_workflow_without_payment(self):
        t=test_transfer_rights.TransferRightsTests();t.setUp();t.sell()
        a=self.app;a.state=t.s;a.v=view(t.s);a.nav('Recruitment');a.open_profile('p2')
        cash=a.state['cash'];self.click('Review buy-out');self.click('Confirm')
        d=next(reversed(a.state['market']['deals'].values()))
        self.assertEqual(d['exit_kind'],'buyout');self.assertEqual(a.state['cash'],cash)
        self.click('Personal terms');self.assertEqual(a.screen,'Contracts')
        self.click('Clauses');self.click('Employment clauses');self.click('Exit: Club release')
        self.assertEqual(a.offer_draft['release_kind'],'buyout')


if __name__=='__main__':unittest.main()
