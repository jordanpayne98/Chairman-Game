from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import transfer_rights as rights,market,clauses,career,club_ai,contract_terms
from club_chairman.simulation import validate,view,execute,Command
from club_chairman.persistence import save,load,migrate
from club_chairman.contract_review import attention
import test_market

class TransferRightsTests(unittest.TestCase):
    setUp=test_market.MarketTests.setUp
    act=test_market.MarketTests.act
    progress=test_market.MarketTests.progress

    def p(self,pid):return career.person(self.s,pid)

    def sell(self,**terms):
        self.s['club_ai']['enabled']=False
        self.act('sale_enquire',id='p2',club='c1');key=next(reversed(self.s['market']['deals']))
        if terms:self.act('sale_terms',id=key,**terms)
        self.act('market_accept',id=key);self.progress(2);self.act('market_complete',id=key)
        return key

    def complete_personal(self,pid):
        self.act('enquire',id=pid);p=self.p(pid)
        self.act('propose_offer',id=pid,wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id=pid);self.progress(self.s['day']+2);self.act('complete_offer',id=pid)

    def bid(self,**changes):
        p=self.p('p2');d=dict(id='outside',club='c2',target='c2',source='c1',player='p2',day=self.s['day'],due=self.s['day']+2,
           status='medical',fee=300000,upfront=150000,defer_days=28,signing_fee=p['fee'],wage=p['wage'],end=career.contractual_end(self.s,2),
           reason='Test buyer',outcome=None,appearance_fee=50000,appearance_count=3,promotion_fee=25000,sell_on_kind='profit',sell_on_percent=10)
        d.update(changes);self.s['club_ai']['decisions'].append(d)
        self.assertTrue(rights.notify(self.s,d,'ai'));return self.s['clauses']['notices'][-1]

    def test_buyback_dates_price_steps_consent_and_settlement(self):
        fee=market.quote(self.s,self.p('p2'))*2
        self.sell(buy_back_fee=fee,buy_back_later=fee+500000,rights_seasons=2)
        r=self.s['clauses']['rights'][0];before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'No active buy-back'):self.act('right_enquire',id='p2')
        self.assertEqual(before,self.s)
        self.progress(r['start']);self.s['config']['market']['minimum_squad']=99
        self.assertEqual(market.quote(self.s,self.p('p2'),'c2'),self.p('p2')['fee']*self.s['config']['market']['asking_multiple'])
        self.act('right_enquire',id='p2');self.assertEqual(self.p('p2')['club'],'c1')
        d=next(reversed(self.s['market']['deals'].values()));self.assertEqual(d['fee'],fee)
        self.complete_personal('p2');self.assertEqual(self.p('p2')['club'],'c0')
        self.assertEqual(self.s['clauses']['rights'][0]['status'],'exercised');validate(self.s)
        self.s['day']=r['second'];self.assertEqual(rights.price(self.s,r),fee+500000)

    def test_expiry_release_and_third_party_departure_end_buyback(self):
        self.sell(buy_back_fee=9000000,first_refusal=True)
        r=self.s['clauses']['rights'][0];self.s['day']=r['expiry']+1;rights.process_day(self.s)
        self.assertTrue(all(r['status']=='expired' for r in self.s['clauses']['rights']))
        self.setUp();self.sell(buy_back_fee=9000000)
        clauses.release(self.s,'p2','c1');self.assertEqual(self.s['clauses']['rights'][0]['status'],'ended')

    def test_match_copies_whole_package_and_requires_separate_personal_consent(self):
        self.sell(first_refusal=True);n=self.bid();self.assertEqual(n['status'],'pending')
        self.assertTrue(any(a['label']=='First-refusal response required' for a in attention(view(self.s))))
        cash=self.s['cash'];self.act('refusal_match',id=n['id'])
        matched=next(reversed(self.s['market']['deals'].values()))
        self.assertEqual(rights.package(matched),n['package']);self.assertEqual(self.p('p2')['club'],'c1');self.assertEqual(cash,self.s['cash'])
        self.complete_personal('p2')
        self.assertEqual(self.s['clauses']['notices'][0]['status'],'completed')
        self.assertEqual(self.s['club_ai']['decisions'][0]['status'],'cancelled')
        self.assertEqual(self.s['market']['obligations'][-1]['amount'],150000)
        self.assertEqual(len(self.s['clauses']['conditional']),2);validate(self.s)

    def test_decline_timeout_changed_package_and_failed_consent_release_hold(self):
        self.sell(first_refusal=True);n=self.bid();key=n['id']
        self.act('refusal_decline',id=key);original=self.s['club_ai']['decisions'][0]
        self.assertEqual(original['status'],'medical');self.assertFalse(rights.notify(self.s,original,'ai'))
        original['fee']+=10000;self.assertTrue(rights.notify(self.s,original,'ai'));n=self.s['clauses']['notices'][-1]
        self.s['day']=n['deadline']+1;rights.process_day(self.s)
        self.assertEqual(n['status'],'expired');self.assertEqual(original['status'],'medical')
        self.setUp();self.sell(first_refusal=True);n=self.bid();self.act('refusal_match',id=n['id'])
        d=next(reversed(self.s['market']['deals'].values()));self.act('market_withdraw',id=d['id']);rights.process_day(self.s)
        self.assertEqual(self.s['clauses']['notices'][0]['status'],'failed');self.assertEqual(self.s['club_ai']['decisions'][0]['status'],'medical')

    def test_buyout_is_funded_player_exit_and_does_not_trigger_transfer_sellon(self):
        self.sell(first_refusal=True,sell_on_kind='gross',sell_on_percent=10)
        c=self.s['clauses']['employment']['p2'];self.assertEqual(c['release_kind'],'buyout')
        fee=c['release_fee'];cash=self.s['cash'];self.act('buyout_enquire',id='p2')
        self.assertEqual(self.s['cash'],cash);self.assertEqual(self.p('p2')['club'],'c1')
        self.complete_personal('p2');b=self.s['clauses']['buyouts'][0]
        self.assertEqual((b['amount'],b['sponsor'],b['employer']),(fee,'c0','c1'))
        self.assertTrue(b['player_consent']);self.assertEqual(self.s['clauses']['sell_on'][0]['status'],'expired')
        self.assertEqual(self.s['clauses']['notices'],[]);validate(self.s)

    def test_buyout_changed_contract_and_unfunded_exit_are_atomic(self):
        self.sell();self.act('buyout_enquire',id='p2');self.act('enquire',id='p2');p=self.p('p2')
        self.act('propose_offer',id='p2',wage=p['wage'],fee=p['fee'],duration=2);self.act('accept_offer',id='p2');self.progress(4)
        self.s['clauses']['employment']['p2']['release_fee']+=1;before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'buy-out amount'):self.act('complete_offer',id='p2')
        self.assertEqual(before,self.s)

    def test_country_profiles_gate_new_terms_and_player_can_reject_ai_exit(self):
        self.assertIn('buyout',rights.allowed_kinds(self.s))
        self.s['config']['clauses']['release_profiles']['northshire']=['transfer']
        with self.assertRaisesRegex(ValueError,'country profile'):clauses.validate_terms(self.s,dict(release_kind='buyout',release_fee=500000))
        p=self.p('p2');p['morale']=95
        self.assertFalse(rights.personal_accepts(p,p['wage']*110//100,p['contract_end']+100,self.s['day']))
        self.assertTrue(rights.personal_accepts(p,p['wage']*120//100,p['contract_end']+100,self.s['day']))

    def test_ai_matching_reserves_package_and_keeps_original_sale_paused(self):
        # Buy from c1 while granting it first refusal, then offer a sale to c2.
        self.s['club_ai']['enabled']=False
        self.act('club_enquire',id='p20');d=next(reversed(self.s['market']['deals'].values()))
        self.act('club_propose',id=d['id'],fee=d['fee'],upfront_percent=100,defer_days=28,first_refusal=True)
        self.act('club_accept',id=d['id']);self.complete_personal('p20');self.p('p20')['morale']=50
        self.act('sale_enquire',id='p20',club='c2');d=next(reversed(self.s['market']['deals'].values()))
        self.act('market_accept',id=d['id']);self.assertEqual(self.s['market']['deals'][d['id']]['status'],'rights_wait')
        self.s['day']+=1;rights.process_day(self.s);n=self.s['clauses']['notices'][-1]
        self.assertEqual(n['status'],'matching');self.assertGreater(market.extra_reservations(self.s,'c1')[0],0)
        self.s['club_ai']['enabled']=True;self.s['day']+=2
        club_ai.process_day(self.s)
        # A seeded medical can fail; either outcome must keep transactions exclusive.
        ai=next(d for d in self.s['club_ai']['decisions'] if d['id']==n['match_id'])
        self.assertIn(ai['status'],('completed','cancelled'))
        if ai['status']=='completed':self.assertEqual(self.p('p20')['club'],'c1');self.assertEqual(n['status'],'completed')
        else:rights.process_day(self.s);self.assertEqual(n['status'],'failed')
        validate(self.s)

    def test_roundtrip_pending_rights_and_19_migration_preserves_state(self):
        self.sell(buy_back_fee=9000000,first_refusal=True);self.bid()
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'rights.sqlite3';save(self.s,path);self.assertEqual(load(path),self.s)
        self.setUp();old=deepcopy(self.s);old['schema']=19
        for k in ('rights','notices','buyouts'):old['clauses'].pop(k)
        for k in ('right_notice_days','buyback_discount','refusal_discount','release_profiles','ai_buyout_multiple'):old['config']['clauses'].pop(k)
        before=deepcopy(old);up=migrate(old);self.assertEqual(old,before)
        self.assertEqual(up['players'],old['players']);self.assertEqual(up['clauses']['employment'],old['clauses']['employment'])
        self.assertEqual(up['schema'],20);self.assertEqual(migrate(up),up)

    def test_cancelled_underlying_offer_invalidates_matched_consent_and_releases_money(self):
        self.sell(first_refusal=True);n=self.bid();self.act('refusal_match',id=n['id'])
        p=self.p('p2');self.act('enquire',id='p2')
        self.act('propose_offer',id='p2',wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id='p2');self.progress(4)
        self.assertGreater(career.reservations(self.s)[0],0)
        self.s['club_ai']['decisions'][0]['status']='cancelled';before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'matched offer'):self.act('complete_offer',id='p2')
        self.assertEqual(before,self.s)
        rights.process_day(self.s)
        self.assertEqual(career.reservations(self.s),(0,0))
        self.assertEqual(self.s['clauses']['notices'][0]['status'],'cancelled')
        self.assertEqual(self.p('p2')['club'],'c1');validate(self.s)

    def test_matching_expiry_unwinds_both_bidders_and_a_changed_package_cannot_complete(self):
        self.sell(first_refusal=True);n=self.bid();self.act('refusal_match',id=n['id'])
        d=next(reversed(self.s['market']['deals'].values()));d['appearance_fee']+=1
        with self.assertRaisesRegex(ValueError,'matched offer'):rights.check_exit(self.s,self.p('p2'),d)
        self.s['day']=n['expires']+1;rights.process_day(self.s)
        self.assertEqual(self.s['clauses']['notices'][0]['status'],'cancelled')
        self.assertIsNone(club_ai.pending_for(self.s,'p2'));self.assertIsNone(market.active_deal(self.s,'p2'))

    def test_player_rejection_keeps_buyout_unpaid_and_preserves_signed_rights(self):
        self.sell(first_refusal=True);self.act('buyout_enquire',id='p2');self.act('enquire',id='p2')
        cash=self.s['cash']
        for wage in (10000,10100,10200):self.act('propose_offer',id='p2',wage=wage,fee=0,duration=1)
        self.assertEqual(self.s['career']['offers']['p2']['status'],'rejected')
        self.assertEqual(self.p('p2')['club'],'c1');self.assertEqual(self.s['cash'],cash)
        self.assertEqual(self.s['clauses']['buyouts'],[])
        self.assertEqual(self.s['clauses']['rights'][0]['status'],'active')

    def test_unfunded_buyout_completion_preserves_employment_and_receipts(self):
        self.sell();self.act('buyout_enquire',id='p2');self.act('enquire',id='p2');p=self.p('p2')
        self.act('propose_offer',id='p2',wage=p['wage'],fee=p['fee'],duration=2)
        self.act('accept_offer',id='p2');self.progress(4)
        market.post(self.s,'c0','test:empty',-self.s['cash'],'Test spending');before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'cash'):self.act('complete_offer',id='p2')
        self.assertEqual(before,self.s);self.assertEqual(self.s['clauses']['buyouts'],[])

    def test_right_expiry_caps_notice_response_and_ai_reserves_all_matched_payments(self):
        self.sell(first_refusal=True);self.s['clauses']['rights'][0]['expiry']=self.s['day']+1
        n=self.bid();self.assertEqual(n['deadline'],self.s['day']+1)
        n['beneficiary']='c3';self.p('p2')['morale']=50
        self.s['config']['club_ai']['payroll_income_percent']=100
        rights.match(self.s,n)
        d=self.s['club_ai']['decisions'][-1]
        expected=d['fee']+d['signing_fee']+d['appearance_fee']+d['promotion_fee']
        self.assertEqual(market.extra_reservations(self.s,'c3')[0],expected)

    def test_national_dates_and_default_country_gate_do_not_invent_old_buyouts(self):
        from datetime import date,timedelta
        from club_chairman.simulation import new_career
        s=new_career(42,'wales');origin=date.fromisoformat(s['config']['start_date'])
        start,second,end=rights.dates(s,2)
        self.assertEqual([origin+timedelta(days=d) for d in (start,second,end)],
                         [date(2027,8,1),date(2028,8,1),date(2029,5,31)])
        self.assertEqual(rights.allowed_kinds(s),['transfer'])
        self.assertEqual(s['clauses']['employment'],{})
        s['clubs'][0]['nation']='spain';self.assertIn('buyout',rights.allowed_kinds(s))

    def test_loan_purchase_cannot_bypass_a_third_clubs_first_refusal(self):
        self.sell(first_refusal=True);self.s['clauses']['rights'][0]['beneficiary']='c3'
        self.act('loan_enquire',id='p2');d=next(reversed(self.s['market']['deals'].values()))
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'first-refusal'):
            self.act('loan_terms',id=d['id'],share=100,days=14,purchase_kind='option')
        self.assertEqual(before,self.s)
        self.act('loan_terms',id=d['id'],share=100,days=14,purchase_kind='none')

    def test_read_model_excludes_other_clubs_private_rights_and_employment(self):
        self.sell(first_refusal=True);self.s['clauses']['rights'][0]['beneficiary']='c3';self.bid()
        v=view(self.s)
        self.assertEqual(v['clauses']['rights'],[]);self.assertEqual(v['clauses']['notices'],[])
        self.assertNotIn('p2',v['clauses']['employment'])
        self.assertGreater(next(p for p in v['players'] if p['id']=='p2')['buyout_amount'],0)

if __name__=='__main__':unittest.main()
