from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman.simulation import new_career,execute,Command,view,payroll,validate
from club_chairman.persistence import save,load
from club_chairman.market import quote,club_cash,active_loan
from club_chairman.career import reservations
from club_chairman.contract_review import review
from club_chairman.planning import forecast

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83);self.act('budget',value=4000000);self.act('hire',id='m0')
    def act(self,action,**payload):
        command=Command(str(self.s['revision']),self.s['revision'],action,payload)
        self.s,message=execute(self.s,command);return command
    def progress(self,day):
        while self.s['day']<day or self.s['match']:
            if self.s['match']:
                self.act('match_skip') if not self.s['match'].get('finished',self.s['match']['minute']>=90) else self.act('match_close')
            elif self.s['decision']:self.act('decision',choice='decline')
            elif self.s['season_done']:self.act('next_season')
            else:self.act('continue')
    def begin_purchase(self,pid='p20',defer=28):
        self.act('club_enquire',id=pid);d=next(reversed(self.s['market']['deals'].values()))
        self.act('club_propose',id=d['id'],fee=d['fee'],upfront_percent=50,defer_days=defer)
        self.act('club_accept',id=d['id']);self.act('enquire',id=pid)
        p=next(p for p in self.s['players'] if p['id']==pid)
        self.act('propose_offer',id=pid,wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id=pid);return d['id']
    def test_purchase_conserves_cash_and_instalment_settles_once(self):
        key=self.begin_purchase();self.progress(2)
        v=view(self.s);r=review(v,v['career']['offers']['p20'])
        cash=self.s['cash'];seller=club_cash(self.s,'c1');d=deepcopy(self.s['market']['deals'][key])
        command=self.act('complete_offer',id='p20')
        p=next(p for p in self.s['players'] if p['id']=='p20')
        self.assertEqual(p['club'],'c0');self.assertEqual(self.s['cash'],r['cash_after'])
        self.assertEqual(club_cash(self.s,'c1')-seller,d['upfront'])
        self.assertEqual(reservations(self.s),(0,0))
        before=deepcopy(self.s);again,_=execute(self.s,command);self.assertEqual(again,before)
        self.progress(30);bill=self.s['market']['obligations'][0]
        self.assertEqual(bill['status'],'paid');self.assertEqual(bill['due'],30)
        self.assertEqual(sum(e['amount'] for e in self.s['ledger'] if e['id']==bill['id']),-bill['amount'])
        self.assertEqual(sum(e['amount'] for e in self.s['market']['accounts']['c1']['ledger'] if e['id']==bill['id']),bill['amount'])
        validate(self.s)
    def test_deferred_forecast_and_sponsor_income_reconcile(self):
        self.s['config']['capacity']=0
        self.begin_purchase();self.progress(2);self.act('complete_offer',id='p20')
        self.act('sponsor_enquire',right='digital');self.act('sponsor_propose',right='digital',weekly=80000,weeks=8);self.act('sponsor_accept',right='digital')
        f=forecast(view(self.s),horizon=35);self.progress(37)
        self.assertEqual(f['cash'],self.s['cash']);self.assertEqual(f['accrued'],self.s['accrued_costs']//7)
    def test_sale_preserves_identity_notes_and_credits_buyer_debit(self):
        self.act('planning',key='notes',value={'p2':'Follow progress after sale'})
        self.act('sale_enquire',id='p2',club='c1');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(2)
        cash=self.s['cash'];buyer=club_cash(self.s,'c1');old=payroll(self.s)
        self.act('market_complete',id=d['id']);p=next(p for p in self.s['players'] if p['id']=='p2')
        self.assertEqual(p['club'],'c1');self.assertEqual(self.s['cash'],cash+d['fee'])
        self.assertEqual(club_cash(self.s,'c1'),buyer-d['fee']);self.assertEqual(payroll(self.s),old-p['wage'])
        self.assertEqual(view(self.s)['planning']['notes']['p2'],'Follow progress after sale')
    def test_loans_return_and_cannot_be_registered_twice(self):
        self.act('loan_enquire',id='p20');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(2);self.act('market_complete',id=d['id'])
        p=next(p for p in self.s['players'] if p['id']=='p20');old_end=p['contract_end']
        self.assertEqual(p['club'],'c0');self.assertIsNotNone(active_loan(self.s,p['id']))
        with self.assertRaises(ValueError):self.act('enquire',id=p['id'])
        with self.assertRaises(ValueError):self.act('loan_enquire',id=p['id'],club='c2')
        self.s['config']['capacity']=0;f=forecast(view(self.s),horizon=60)
        self.progress(59)
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p20')['club'],'c1')
        self.assertIsNone(active_loan(self.s,'p20'))
        self.progress(62);self.assertEqual(f['cash'],self.s['cash'])
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p20')['contract_end'],old_end)
    def test_unfunded_instalment_rolls_back_entire_day(self):
        self.begin_purchase();self.progress(2);self.act('complete_offer',id='p20')
        bill=self.s['market']['obligations'][0];bill['due']=3;bill['amount']=self.s['cash']+1
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('continue')
        self.assertEqual(before,self.s)
    def test_withdrawal_releases_purchase_reservations(self):
        key=self.begin_purchase();self.assertGreater(reservations(self.s)[0],0)
        self.act('market_withdraw',id=key);self.assertEqual(reservations(self.s),(0,0))
        self.assertEqual(self.s['career']['offers']['p20']['status'],'withdrawn')
    def test_market_save_roundtrip_with_live_loan_and_dated_bill(self):
        self.begin_purchase();self.progress(2);self.act('complete_offer',id='p20')
        self.act('loan_enquire',id='p22');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(4);self.act('market_complete',id=d['id'])
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'market.sqlite3';save(self.s,p);self.assertEqual(load(p),self.s)
    def test_sponsor_rights_conflict_no_upfront_cash_and_exact_payments(self):
        cash=self.s['cash'];self.act('sponsor_enquire',right='stadium')
        self.act('sponsor_propose',right='stadium',weekly=200000,weeks=4)
        mood=self.s['supporters'];self.act('sponsor_accept',right='stadium')
        self.assertEqual(self.s['cash'],cash);self.assertEqual(self.s['supporters'],mood-5)
        with self.assertRaises(ValueError):self.act('sponsor_enquire',right='stadium')
        self.progress(29);c=self.s['commercial']['contracts'][0]
        self.assertEqual(c['paid'],800000);self.assertEqual(c['status'],'expired')
        self.act('sponsor_enquire',right='stadium');self.assertEqual(len(self.s['commercial']['contracts']),1)
    def test_outgoing_wage_share_and_recall_refund_prevent_same_day_fee_farming(self):
        self.act('loan_enquire',id='p2',club='c1');d=next(reversed(self.s['market']['deals'].values()))
        self.act('loan_terms',id=d['id'],share=50,days=56);self.act('market_accept',id=d['id']);self.progress(2)
        cash=self.s['cash'];buyer=club_cash(self.s,'c1');wages=payroll(self.s)
        self.act('market_complete',id=d['id']);p=next(p for p in self.s['players'] if p['id']=='p2')
        self.assertEqual(payroll(self.s),wages-p['wage']//2)
        self.act('loan_recall',id=d['id'])
        self.assertEqual(self.s['cash'],cash);self.assertEqual(club_cash(self.s,'c1'),buyer)
        self.assertEqual(payroll(self.s),wages)
        with self.assertRaises(ValueError):self.act('loan_recall',id=d['id'])
    def test_no_last_keeper_sale_or_unfunded_counterparty(self):
        # Give the buyer wage room so this fixture isolates keeper/cash guards.
        self.s['config']['club_ai']['payroll_income_percent']=100
        for p in self.s['players']:
            if p['club']=='c0' and p['role']=='GK' and p['id'] not in ('p0','p1'):p['club']=None
        self.s['recruitment']['clubs']['c1']['value']=100
        self.act('sale_enquire',id='p0',club='c1');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.progress(2);self.act('market_complete',id=d['id'])
        with self.assertRaises(ValueError):self.act('sale_enquire',id='p1',club='c2')
        self.act('sale_enquire',id='p2',club='c2');d=next(reversed(self.s['market']['deals'].values()))
        from club_chairman.market import post
        post(self.s,'c2','test:cash-reduction',-club_cash(self.s,'c2'),'Test fixture')
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('market_accept',id=d['id'])
        self.assertEqual(self.s,before)
    def test_live_loan_and_guaranteed_payment_survive_season_rollover(self):
        self.s['config']['market']['max_installment_days']=140
        self.begin_purchase(defer=120);self.progress(2);self.act('complete_offer',id='p20')
        self.progress(20);self.act('loan_enquire',id='p22')
        d=next(reversed(self.s['market']['deals'].values()));self.act('loan_terms',id=d['id'],share=75,days=84)
        self.act('market_accept',id=d['id']);self.progress(22);self.act('market_complete',id=d['id'])
        self.progress(97);self.assertEqual(self.s['career']['season'],2)
        self.assertEqual(self.s['market']['obligations'][0]['status'],'scheduled')
        self.assertIsNotNone(active_loan(self.s,'p22'))
        self.progress(122)
        self.assertEqual(self.s['market']['obligations'][0]['status'],'paid')
        self.assertIsNone(active_loan(self.s,'p22'));validate(self.s)
    def test_competing_purchase_and_loan_reserve_one_budget(self):
        self.begin_purchase();self.act('loan_enquire',id='p22');d=next(reversed(self.s['market']['deals'].values()))
        fees,wages=reservations(self.s);self.act('budget',value=payroll(self.s)+wages)
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('market_accept',id=d['id'])
        self.assertEqual(self.s,before)
    def test_club_personal_deadlines_release_linked_reservations(self):
        key=self.begin_purchase();self.progress(8)
        self.assertEqual(self.s['market']['deals'][key]['status'],'expired')
        self.assertEqual(self.s['career']['offers']['p20']['status'],'expired')
        self.assertEqual(reservations(self.s),(0,0))
        with self.assertRaises(ValueError):self.act('complete_offer',id='p20')
    def test_market_sorting_uses_known_estimates_and_scouting_external_club(self):
        from club_chairman.planning import player_rows
        self.act('scout',id='p20');self.progress(self.s['scouting']['p20'])
        v=view(self.s);rows=player_rows(v,True,sort='Passing',market_scope='Club players')
        self.assertEqual(rows[0]['id'],'p20');self.assertEqual(len(rows),333)
        self.assertTrue(rows[0]['report']['exact_current'])
        for p in self.s['players']:
            if p['id']!='p20':p['attrs']={k:1 for k in p['attrs']}
        self.assertEqual(rows,player_rows(view(self.s),True,sort='Passing',market_scope='Club players'))
