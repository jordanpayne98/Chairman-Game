from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from club_chairman.simulation import execute, Command, view, posting, record_result, validate
from club_chairman.persistence import save, load, migrate
from club_chairman.market import club_cash, active_loan
from club_chairman.planning import forecast
from club_chairman.contract_review import review
import test_market


class ClauseTests(unittest.TestCase):
    setUp=test_market.MarketTests.setUp
    act=test_market.MarketTests.act
    progress=test_market.MarketTests.progress

    def player(self,pid):return next(p for p in self.s['players'] if p['id']==pid)

    def sign(self,pid='p146',**extra):
        p=self.player(pid)
        self.act('enquire',id=pid)
        self.act('propose_offer',id=pid,wage=p['wage'],fee=p['fee'],duration=2,**extra)
        self.act('accept_offer',id=pid)
        self.progress(self.s['day']+2);self.act('complete_offer',id=pid)

    def purchase(self,pid='p20',kind='gross',percent=20):
        self.act('club_enquire',id=pid);d=next(reversed(self.s['market']['deals'].values()))
        self.act('club_propose',id=d['id'],fee=d['fee'],upfront_percent=50,defer_days=28,sell_on_kind=kind,sell_on_percent=percent)
        self.act('club_accept',id=d['id']);self.sign(pid)
        return self.s['market']['deals'][d['id']]

    def sale(self,pid,club='c2',kind='none',percent=0):
        self.act('sale_enquire',id=pid,club=club);d=next(reversed(self.s['market']['deals'].values()))
        self.act('sale_terms',id=d['id'],sell_on_kind=kind,sell_on_percent=percent)
        self.act('market_accept',id=d['id']);self.progress(self.s['day']+2)
        return self.s['market']['deals'][d['id']]

    def test_bonus_live_skip_and_midmatch_resume_pay_same_events_once(self):
        self.sign(appearance_bonus=2500,goal_bonus=5000)
        self.player('p146')['attrs']['passing']=100
        self.player('p146')['potential']=100  # Keep the boosted selection fixture valid.
        while not self.s['match']:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')
        self.assertIn('p146',sum(self.s['match']['lineups'],[]))
        base=deepcopy(self.s);self.act('match_skip');skipped=deepcopy(self.s)
        self.s=base;self.act('match_step',minutes=27)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'midmatch.sqlite3';save(self.s,path);self.s=load(path)
        while not self.s['match'].get('finished',self.s['match']['minute']>=90):self.act('match_step',minutes=1)
        for key in ('cash','players','ledger','clauses','fixtures'):
            self.assertEqual(self.s[key],skipped[key],key)
        match=self.s['match'];goals=sum(e['kind']=='goal' and e.get('player')=='p146' for e in match['events'])
        bills=self.s['clauses']['payables']
        self.assertEqual(sum(b['amount'] for b in bills),2500+5000*goals)
        self.assertEqual(sum(b['paid'] for b in bills),2500+5000*goals)
        before=deepcopy(self.s);record_result(self.s,match);self.assertEqual(self.s,before)

    def test_bonus_arrears_survive_expiry_and_are_settled_by_funding(self):
        self.sign(appearance_bonus=100000)
        self.player('p146')['attrs']['passing']=100;self.player('p146')['potential']=100
        self.s['config']['capacity']=0
        while not self.s['match']:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')
        posting(self.s,'test:empty-cash',-self.s['cash'],'Test fixture')
        self.act('match_skip')
        bill=self.s['clauses']['payables'][0]
        self.assertEqual((bill['amount'],bill['paid'],bill['status']),(100000,0,'arrears'))
        projected=forecast(view(self.s),horizon=0);self.assertEqual(projected['cash'],-100000)
        self.act('match_close');self.player('p146')['contract_end']=5
        from club_chairman.clauses import release
        release(self.s,'p146','c0');self.player('p146')['club']=None
        self.act('fund');self.assertEqual(self.s['cash'],4900000)
        self.assertEqual(self.s['clauses']['payables'][0]['status'],'paid')
        self.act('fund');self.assertEqual(self.s['cash'],9900000)

    def test_option_extends_once_survives_save_and_does_not_pay_immediately(self):
        self.sign(club_option=True,appearance_bonus=2500)
        p=self.player('p146');old=p['contract_end'];cash=self.s['cash']
        command=self.act('exercise_option',id=p['id'])
        self.assertEqual(self.player('p146')['contract_end'],old+110)
        self.assertEqual(self.s['cash'],cash)
        again,_=execute(self.s,command);self.assertEqual(self.s,again)
        with self.assertRaises(ValueError):self.act('exercise_option',id=p['id'])
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'option.sqlite3';save(self.s,path);self.assertEqual(load(path),self.s)

    def test_new_terms_require_consent_and_invalid_clauses_leave_no_trace(self):
        p=self.player('p146');self.act('enquire',id=p['id'])
        for bad in ({'appearance_bonus':-1},{'goal_bonus':True},{'club_option':1}):
            before=deepcopy(self.s)
            with self.assertRaises(ValueError):self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2,**bad)
            self.assertEqual(self.s,before)
        self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2,appearance_bonus=2500)
        self.act('accept_offer',id=p['id']);before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2,appearance_bonus=0)
        self.assertEqual(self.s,before)

    def test_gross_resale_distributes_cash_and_retains_deferred_debt(self):
        purchase=self.purchase();d=self.sale('p20')
        balances={c:club_cash(self.s,c) for c in ('c0','c1','c2')};fee=d['fee'];cut=fee*20//100
        cmd=self.act('market_complete',id=d['id'])
        self.assertEqual(club_cash(self.s,'c0'),balances['c0']+fee-cut)
        self.assertEqual(club_cash(self.s,'c1'),balances['c1']+cut)
        self.assertEqual(club_cash(self.s,'c2'),balances['c2']-fee)
        self.assertEqual(self.s['market']['obligations'][0]['amount'],purchase['fee']-purchase['upfront'])
        self.assertEqual(self.s['clauses']['sell_on'][0]['status'],'settled')
        again,_=execute(self.s,cmd);self.assertEqual(again,self.s)

    def test_profit_right_uses_total_acquisition_fee_and_no_loss_payment(self):
        self.purchase(kind='profit');self.player('p20')['fee']+=1000000
        d=self.sale('p20');self.act('market_complete',id=d['id'])
        self.assertEqual(self.s['clauses']['sell_on'][0]['amount'],600000)
        self.setUp();self.purchase(kind='profit');self.player('p20')['fee']-=100000
        d=self.sale('p20');self.act('market_complete',id=d['id'])
        self.assertEqual(self.s['clauses']['sell_on'][0]['amount'],0)

    def test_sale_right_and_repurchase_receipt_match_review(self):
        d=self.sale('p2',club='c1',kind='gross',percent=10)
        self.act('market_complete',id=d['id'])
        self.act('club_enquire',id='p2');d=next(reversed(self.s['market']['deals'].values()))
        self.act('club_propose',id=d['id'],fee=d['fee'],upfront_percent=50,defer_days=28)
        self.act('club_accept',id=d['id']);p=self.player('p2')
        self.act('enquire',id=p['id']);self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id=p['id']);self.progress(self.s['day']+2)
        expected=review(view(self.s),self.s['career']['offers'][p['id']]);self.assertGreater(expected['sell_on_receipt'],0)
        self.act('complete_offer',id=p['id']);self.assertEqual(self.s['cash'],expected['cash_after'])

    def test_sell_on_is_retained_on_loan_and_expires_on_release(self):
        self.purchase();self.act('loan_enquire',id='p20',club='c2')
        d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(4);self.act('market_complete',id=d['id'])
        self.assertEqual(self.s['clauses']['sell_on'][0]['status'],'active')
        self.act('loan_recall',id=d['id']);self.player('p20')['contract_end']=4
        self.progress(6);self.assertEqual(self.s['clauses']['sell_on'][0]['status'],'expired')

    def test_new_loan_term_starts_on_delayed_registration_and_employment_rechecked(self):
        self.act('loan_enquire',id='p20');d=next(reversed(self.s['market']['deals'].values()))
        self.act('loan_terms',id=d['id'],share=75,days=14);self.act('market_accept',id=d['id'])
        self.progress(4);self.act('market_complete',id=d['id'])
        loan=active_loan(self.s,'p20');self.assertEqual((loan['start'],loan['end']),(4,18))
        self.progress(18);self.assertIsNotNone(active_loan(self.s,'p20'))
        self.progress(19);self.assertIsNone(active_loan(self.s,'p20'))
        self.act('loan_enquire',id='p22');d=next(reversed(self.s['market']['deals'].values()))
        self.act('loan_terms',id=d['id'],share=100,days=14);self.act('market_accept',id=d['id'])
        self.progress(21);self.player('p22')['contract_end']=34
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('market_complete',id=d['id'])
        self.assertEqual(self.s,before)

    def test_schema_four_migration_adds_no_clauses_and_preserves_legacy_loan_dates(self):
        self.act('loan_enquire',id='p20');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(2);self.act('market_complete',id=d['id'])
        old=deepcopy(self.s);old['schema']=4;del old['clauses'];del old['config']['clauses']
        upgraded=migrate(old)
        self.assertEqual(upgraded['clauses'],dict(employment={},history=[],payables=[],sell_on=[]))
        for key in ('cash','players','ledger','market'):self.assertEqual(upgraded[key],old[key])
        self.assertEqual(old['schema'],4);validate(upgraded)
