from copy import deepcopy
import unittest
from club_chairman.simulation import view
import test_qol_ui

class ContractExpansionInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_employment_drafts_require_sent_consent_and_clauses_are_reachable(self):
        a=self.app;a.command('hire',id='m0');a.contract_open('p146')
        self.click('Clauses');self.click('Employment clauses');before=deepcopy(a.state)
        self.click('+',0);self.click('+',1);self.click('Player option: None')
        self.assertEqual(a.state,before);self.assertEqual(a.offer_draft['release_fee'],500000);self.assertEqual(a.offer_draft['annual_raise'],5)
        self.click('Send proposal');o=a.state['career']['offers']['p146'];self.assertEqual(o['release_fee'],500000);self.assertTrue(o['player_option'])
        self.click('Performance clauses');self.click('Club option: None')
        self.assertFalse(a.offer_draft['player_option']);self.assertTrue(a.offer_draft['club_option'])

    def test_loan_purchase_terms_and_transfer_conditions_are_editable_before_consent(self):
        a=self.app;a.command('hire',id='m0');a.market_open('loan_enquire','p20');a.render();d=next(reversed(a.state['market']['deals'].values()))
        a.command('loan_terms',id=d['id'],share=75,days=14)
        self.click('Additional terms');self.click('Purchase: none');self.click('Purchase: option');self.click('−1')
        d=a.state['market']['deals'][d['id']];self.assertEqual(d['purchase_kind'],'obligation');self.assertEqual(d['purchase_count'],1)
        self.click('Back to deal');a.command('market_withdraw',id=d['id'])
        a.market_open('club_enquire','p22');a.render();self.click('Additional terms');before=deepcopy(a.state);self.click('+',0)
        self.assertEqual(before,a.state);self.assertEqual(a.market_draft['appearance_fee'],50000)
        self.click('Back to deal');self.click('Send club offer');d=next(reversed(a.state['market']['deals'].values()))
        self.assertEqual(d['appearance_fee'],50000)

if __name__=='__main__':unittest.main()
