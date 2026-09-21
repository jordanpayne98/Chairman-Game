from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import clauses,contract_terms,loan_clauses,market,career,football
from club_chairman.simulation import execute,Command,view,validate,record_result,posting
from club_chairman.persistence import migrate,save,load
from club_chairman.contract_review import review
from club_chairman.planning import forecast,projected_wage
import test_market
import test_clauses


class ContractExpansionTests(unittest.TestCase):
    setUp=test_market.MarketTests.setUp
    act=test_market.MarketTests.act
    progress=test_market.MarketTests.progress
    player=test_clauses.ClauseTests.player
    sign=test_clauses.ClauseTests.sign

    def loan(self,kind='option',pid='p20',count=1,club=None):
        self.act('loan_enquire',id=pid,club=club);key=next(reversed(self.s['market']['deals']))
        self.act('loan_terms',id=key,share=75,days=14,purchase_kind=kind,purchase_count=count)
        self.act('market_accept',id=key);self.progress(self.s['day']+2);self.act('market_complete',id=key)
        return key

    def test_employment_consent_rules_and_annual_forecast(self):
        self.sign(annual_raise=10,relegation_cut=20,promotion_bonus=50000,release_fee=500000)
        p=self.player('p146');c=self.s['clauses']['employment'][p['id']]
        c['end']=p['contract_end']=900;wage=p['wage'];due=c['next_raise']
        self.assertEqual(projected_wage(next(p for p in view(self.s)['players'] if p['id']=='p146'),due,view(self.s)),wage*110//100)
        self.s['day']=due;contract_terms.process_day(self.s);self.assertEqual(p['wage'],wage*110//100)
        before=deepcopy(self.s);contract_terms.process_day(self.s);self.assertEqual(before,self.s)
        self.s['leagues']['movements']=[dict(club='c0',kind='Relegated')]
        contract_terms.movements(self.s,rollover=True);self.assertEqual(p['wage'],(wage*110//100)*80//100)
        before=p['wage'];contract_terms.movements(self.s,rollover=True);self.assertEqual(p['wage'],before)
        with self.assertRaises(ValueError):clauses.validate_terms(self.s,dict(club_option=True,player_option=True))
        self.s['config']['clauses']['allowed_employment'].remove('annual_raise')
        with self.assertRaises(ValueError):clauses.validate_terms(self.s,dict(annual_raise=10))

    def test_player_decides_option_and_owner_cannot_exercise_it(self):
        self.sign(player_option=True);p=self.player('p146');c=self.s['clauses']['employment'][p['id']];old=p['contract_end']
        with self.assertRaisesRegex(ValueError,'No unused club option'):self.act('exercise_option',id=p['id'])
        self.s['day']=old-14;p['morale']=80;contract_terms.process_day(self.s)
        self.assertEqual(p['contract_end'],c['option_end']);self.assertEqual(c['option_status'],'exercised')
        before=deepcopy(self.s);contract_terms.process_day(self.s);self.assertEqual(before,self.s)
        self.setUp();self.sign(player_option=True);p=self.player('p146');c=self.s['clauses']['employment'][p['id']]
        p['morale']=1;p['wage']=10000;self.s['day']=c['end']-14;contract_terms.process_day(self.s)
        self.assertEqual(c['option_status'],'declined')

    def test_release_fee_enforced_without_waiving_player_consent(self):
        self.sign(release_fee=500000);p=self.player('p146')
        self.assertEqual(market.quote(self.s,p),500000)
        self.act('sale_enquire',id=p['id'],club='c1');d=next(reversed(self.s['market']['deals'].values()))
        self.assertEqual(d['fee'],500000);self.assertEqual(p['club'],'c0')
        self.act('market_accept',id=d['id']);self.progress(4);self.act('market_complete',id=d['id'])
        self.assertEqual(self.player('p146')['club'],'c1');self.assertNotIn('p146',self.s['clauses']['employment'])

    def test_conditional_fees_and_promotion_bonus_earned_once_survive_exit(self):
        self.sign(promotion_bonus=50000)
        d=dict(id='test-sale',player='p146',source='c1',target='c0',appearance_fee=25000,appearance_count=2,promotion_fee=75000,employment_end=100)
        contract_terms.signed_sale(self.s,d)
        m=dict(fixture='one',home='c0',away='c1',lineups=[['p146'],[]],participants=[['p146'],[]],events=[])
        contract_terms.record_match(self.s,m);contract_terms.record_match(self.s,m)
        self.assertEqual(self.s['clauses']['conditional'][0]['count'],1)
        m['fixture']='two';m['forfeit']=True;contract_terms.record_match(self.s,m)
        self.assertEqual(self.s['clauses']['conditional'][0]['count'],1)
        m.pop('forfeit');contract_terms.record_match(self.s,m)
        self.s['leagues']['movements']=[dict(club='c0',kind='Promoted')]
        contract_terms.movements(self.s);contract_terms.movements(self.s)
        self.assertEqual(len(self.s['clauses']['payables']),1)
        posting(self.s,'empty',-self.s['cash'],'Test cash depletion');clauses.settle_payables(self.s)
        self.assertEqual(forecast(view(self.s),horizon=0)['cash'],-150000)
        clauses.release(self.s,'p146','c0');self.player('p146')['club']=None
        self.act('fund');self.assertTrue(all(c['status']=='paid' for c in self.s['clauses']['conditional']))
        after=deepcopy(self.s);clauses.settle_payables(self.s);self.assertEqual(after,self.s)

    def test_incoming_option_settles_once_preserves_history_and_releases_restriction(self):
        key=self.loan();l=market.active_loan(self.s,'p20');p=self.player('p20');goals=p['goals'];seller=market.club_cash(self.s,'c1');cash=self.s['cash']
        self.assertEqual(career.reservations(self.s),(0,0))
        cmd=self.act('loan_purchase',id=key)
        self.assertIsNone(market.active_loan(self.s,'p20'));self.assertEqual(self.player('p20')['club'],'c0')
        self.assertEqual(self.player('p20')['goals'],goals);self.assertEqual(self.s['cash'],cash-l['purchase_fee'])
        self.assertEqual(market.club_cash(self.s,'c1'),seller+l['purchase_fee'])
        again,_=execute(self.s,cmd);self.assertEqual(again,self.s)
        with self.assertRaises(ValueError):self.act('loan_purchase',id=key)
        validate(self.s)

    def test_binding_purchase_reserves_full_fee_and_triggers_on_written_condition(self):
        self.s['club_ai']['enabled']=False
        key=self.loan('obligation');l=market.active_loan(self.s,'p20')
        self.assertEqual(career.reservations(self.s)[0],l['purchase_fee'])
        self.assertGreater(career.reservations(self.s)[1],0)
        # Run the real match engine and saved match settlement for the condition.
        p=self.player('p20');p['condition']=100;p['fatigue']=0;p['attrs']={k:90 for k in p['attrs']};p['potential']=100
        self.progress(17)
        self.assertEqual(next(l for l in self.s['market']['loans'] if l['id']==key)['status'],'purchased')
        self.assertEqual(career.reservations(self.s),(0,0));validate(self.s)
        self.setUp();key=self.loan('obligation',count=30);self.progress(17)
        self.assertEqual(next(l for l in self.s['market']['loans'] if l['id']==key)['status'],'returned')
        self.assertEqual(career.reservations(self.s),(0,0))

    def test_obligation_recall_cannot_cancel_and_failed_purchase_is_atomic(self):
        key=self.loan('obligation',pid='p2',club='c1')
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'binding purchase'):self.act('loan_recall',id=key)
        self.assertEqual(before,self.s)
        self.setUp();key=self.loan();posting(self.s,'empty',-self.s['cash'],'Test fixture');before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('loan_purchase',id=key)
        self.assertEqual(self.s,before)

    def test_completed_purchase_creates_and_settles_conditional_appearance_fee(self):
        self.s['club_ai']['enabled']=False
        self.act('club_enquire',id='p20');d=next(reversed(self.s['market']['deals'].values()))
        self.act('club_propose',id=d['id'],fee=d['fee'],upfront_percent=100,defer_days=28,appearance_fee=50000,appearance_count=1,promotion_fee=100000)
        self.act('club_accept',id=d['id']);p=self.player('p20')
        self.act('enquire',id=p['id']);self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id=p['id']);self.progress(2);self.act('complete_offer',id=p['id'])
        self.assertEqual(len(self.s['clauses']['conditional']),2)
        p=self.player('p20');p['attrs']={k:90 for k in p['attrs']};p['potential']=100
        self.progress(6)
        row=self.s['clauses']['conditional'][0];self.assertEqual((row['status'],row['paid']),('paid',50000))
        self.assertEqual(self.s['clauses']['conditional'][1]['status'],'pending')

    def test_outgoing_bonus_package_is_priced_and_overvaluation_is_atomic(self):
        self.act('sale_enquire',id='p2',club='c1');key=next(reversed(self.s['market']['deals']))
        fee=self.s['market']['deals'][key]['fee']
        self.act('sale_terms',id=key,appearance_fee=50000,promotion_fee=75000)
        d=self.s['market']['deals'][key];self.assertEqual(d['fee']+125000,fee)
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'total valuation'):
            self.act('sale_terms',id=key,appearance_fee=fee+1)
        self.assertEqual(before,self.s)

    def test_outgoing_optional_purchase_uses_recorded_minutes_and_budget(self):
        self.s['club_ai']['enabled']=False
        key=self.loan('option',pid='p2',club='c1',count=1)
        l=market.active_loan(self.s,'p2')
        # A recorded appearance meets the AI borrower's declared first policy.
        loan_clauses.record_match(self.s,dict(fixture='exposure',home='c1',away='c2',lineups=[['p2'],[]],participants=[['p2'],[]]))
        self.progress(17)
        l=next(l for l in self.s['market']['loans'] if l['id']==key)
        self.assertEqual(l['status'],'purchased');self.assertEqual(self.player('p2')['club'],'c1')
        self.assertEqual(l['purchased'],l['end'])
        validate(self.s)

    def test_old_save_keeps_terms_and_active_match_and_new_clauses_roundtrip(self):
        self.sign(annual_raise=10,player_option=True,release_fee=500000)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'contract.sqlite3';save(self.s,path);self.assertEqual(self.s,load(path))
        self.setUp();old=deepcopy(self.s);old['schema']=18;old['clauses'].pop('conditional');old['config']['clauses'].pop('allowed_employment');old['config']['clauses'].pop('player_option_notice')
        f=next(f for f in old['fixtures'] if f['home']=='c0');old['match']=football.start(old,f)
        before=deepcopy(old);up=migrate(old)
        self.assertEqual(before,old);self.assertEqual(up['match'],old['match']);self.assertEqual(up['clauses']['employment'],{})
        self.assertEqual(migrate(up),up)


if __name__=='__main__':unittest.main()
