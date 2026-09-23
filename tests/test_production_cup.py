import json
import unittest
from copy import deepcopy
from datetime import timedelta

from club_chairman.content_gate import audit
from reference_leagues import load_reference as load
from club_chairman import production_cup as cup
from club_chairman.cup_finance import official_payment, record_match_payables


class ProductionCupTests(unittest.TestCase):
    def setUp(self):
        self.data=load()
        self.state=cup.create_validation_cup(self.data,73,'2026-07-01')

    def first_round(self):
        return cup.draw_next(self.state,'2026-07-10')

    def confirm(self, state, fid, on):
        fixture=next(f for f in state['fixtures'] if f['id']==fid)
        kwargs={}
        # Tests explicitly approve a real existing fixture-specific alternative.
        # No automatic upgrades or generated facilities in the service.
        if fixture['round']=='final' or all(cup.welsh_cup_ground_issues(state['clubs'][cid]['cup_ground'],fixture['round']) for cid in (fixture['home'],fixture['away'])):
            ground=deepcopy(state['clubs']['wal-cardiff-copperworks']['cup_ground'])
            kwargs=dict(approved_venue=dict(id='test-alternative:'+fid,name='Test approved venue '+fid,facilities=ground),association_approved=True)
        return cup.confirm_fixture(state,fid,on=on,**kwargs)

    def play_round(self,state,index):
        rd=state['definition']['rounds'][index]['id']
        day=state['definition']['calendar']['rounds'][rd]['conference_date']
        ids=cup.draw_next(state,day)
        for fid in ids:
            f=self.confirm(state,fid,day)
            cup.record_result(state,fid,on=f['date'],score=[1,1],shootout=[4,3])
            record_match_payables(state,fid)

    def test_full_284_club_cup_and_json_resume_are_identical(self):
        original=deepcopy(self.data)
        self.assertEqual(self.state['events'],[])
        self.assertEqual(self.state['fixtures'],[])
        for index in range(4):self.play_round(self.state,index)
        resumed=cup.restore_validation_cup(json.dumps(self.state))
        for index in range(4,9):
            self.play_round(self.state,index);self.play_round(resumed,index)
        self.assertEqual(resumed,self.state)
        cup.validate_state(resumed)
        self.assertEqual(self.data,original)
        self.assertEqual(len(self.state['fixtures']),283)
        self.assertEqual(len({f['id'] for f in self.state['fixtures']}),283)
        self.assertIn(self.state['winner'],self.state['allocation']['club_ids'])
        self.assertEqual(sum(line['amount_pence'] for record in self.state['finance_records'].values() for line in record['lines']),200000)
        for r in self.state['rounds']:
            self.assertEqual(len(r['entrants']),len(set(r['entrants'])))
            self.assertTrue(all(len(ids)%2==0 for ids in r['groups'].values()))
            self.assertEqual(set(r['groups']),{'open'} if r['id'] not in self.state['definition']['draw_policy']['regional_rounds'] else {'north','south'})
        self.assertTrue(self.state['rounds'][1]['group_moves'])
        self.assertEqual(len(cup.calendar_rows(self.state)),283)
        self.assertTrue(audit(self.data))  # Exercising one cup must not release the world.

    def test_draw_requires_results_and_is_independent_of_input_order(self):
        other=deepcopy(self.state)
        other['allocation']['entry_rounds']['qualifying_1'].reverse()
        self.first_round();cup.draw_next(other,'2026-07-10')
        self.assertEqual(self.state['rounds'],other['rounds'])
        self.assertEqual(self.state['fixtures'],other['fixtures'])
        before=deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'unfinished'):cup.draw_next(self.state,'2026-08-01')
        self.assertEqual(self.state,before)
        with self.assertRaisesRegex(ValueError,'pre-career'):cup.create_validation_cup(self.data,1,'2026-08-01')

    def test_venue_reversal_and_unsuitable_alternative_fail_atomically(self):
        fid=self.first_round()[0];f=self.state['fixtures'][0];home,away=f['home'],f['away']
        cup.confirm_fixture(self.state,fid,on='2026-07-10',unavailable=[home])
        self.assertEqual(f['home'],away)
        before=deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'Neither registered'):
            cup.confirm_fixture(self.state,fid,on='2026-07-10',unavailable=[home,away])
        self.assertEqual(before,self.state)
        with self.assertRaisesRegex(ValueError,'does not meet'):
            cup.confirm_fixture(self.state,fid,on='2026-07-10',approved_venue=dict(id='bad',name='Bad ground',facilities={}),association_approved=True)
        self.assertEqual(before,self.state)

    def test_postponements_keep_original_eligibility_and_reverse_only_on_second(self):
        fid=self.first_round()[0];f=self.state['fixtures'][0]
        self.confirm(self.state,fid,'2026-07-10');original_home=f['home']
        deadline=cup.registration_deadline(f)
        cup.postpone(self.state,fid,on='2026-07-25',decision_id='weather-1',distance_miles=100,floodlit=True)
        self.assertEqual(f['reschedule_by'],'2026-07-29')
        before=deepcopy(self.state)
        cup.postpone(self.state,fid,on='2026-07-25',decision_id='weather-1',distance_miles=100,floodlit=True)
        self.assertEqual(before,self.state)
        cup.confirm_fixture(self.state,fid,on='2026-07-25',play_on='2026-07-29',association_approved=True)
        cup.postpone(self.state,fid,on='2026-07-29',decision_id='authority',association_ordered=True,distance_miles=100,floodlit=True)
        self.assertEqual(f['postponements'],1)
        cup.confirm_fixture(self.state,fid,on='2026-07-29',play_on='2026-08-01',association_approved=True)
        cup.postpone(self.state,fid,on='2026-08-01',decision_id='weather-2',distance_miles=101,floodlit=True)
        self.assertEqual(f['reschedule_by'],'2026-08-09')
        self.assertNotEqual(f['home'],original_home)
        self.assertEqual(cup.registration_deadline(f),deadline)
        player=dict(club=f['home'],registered_at=deadline.isoformat(),association_eligible=True,
                    suspended_on_match_date=False,on_loan=True,written_parent_consent_submitted=True)
        self.assertEqual(cup.player_eligibility_issues(f,player),[])
        player['registered_at']=(deadline+timedelta(seconds=1)).isoformat()
        self.assertTrue(cup.player_eligibility_issues(f,player))
        player['registered_at']=deadline.isoformat();player['written_parent_consent_submitted']=False
        self.assertTrue(cup.player_eligibility_issues(f,player))

    def test_registration_deadline_uses_local_time_and_supplied_bank_holidays(self):
        f=dict(conference_date='2026-08-31',timezone='Europe/London')
        self.assertEqual(cup.registration_deadline(f).isoformat(),'2026-08-28T17:00:00+01:00')
        self.assertEqual(cup.registration_deadline(f,['2026-08-28']).isoformat(),'2026-08-27T17:00:00+01:00')

    def test_unconfirmed_drawn_or_changed_result_is_rejected(self):
        fid=self.first_round()[0]
        with self.assertRaisesRegex(ValueError,'confirmed fixture'):cup.record_result(self.state,fid,on='2026-07-25',score=[2,0])
        self.confirm(self.state,fid,'2026-07-10')
        with self.assertRaisesRegex(ValueError,'penalty shootout'):cup.record_result(self.state,fid,on='2026-07-25',score=[1,1])
        result=cup.record_result(self.state,fid,on='2026-07-25',score=[1,1],shootout=[5,4])
        before=deepcopy(self.state)
        self.assertEqual(cup.record_result(self.state,fid,on='2026-07-25',score=[1,1],shootout=[5,4]),result)
        self.assertEqual(before,self.state)
        with self.assertRaisesRegex(ValueError,'cannot be replaced'):cup.record_result(self.state,fid,on='2026-07-25',score=[0,1])

    def test_restore_rejects_corrupted_result_and_pre_career_event(self):
        self.play_round(self.state,0)
        changed=deepcopy(self.state)
        changed['fixtures'][0]['result']['winner']='invented-club'
        with self.assertRaisesRegex(ValueError,'winner disagrees'):
            cup.restore_validation_cup(json.dumps(changed))
        changed=deepcopy(self.state);changed['events'][0]['on']='2025-01-01'
        with self.assertRaisesRegex(ValueError,'predate'):
            cup.restore_validation_cup(json.dumps(changed))

    def test_late_round_requires_explicit_association_rescheduling(self):
        before=deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'scheduling decision'):
            cup.draw_next(self.state,'2026-07-27')
        self.assertEqual(before,self.state)
        fid=cup.draw_next(self.state,'2026-07-27',association_reschedule={
            'decision_id':'schedule-1','play_on':'2026-08-01'})[0]
        f=cup.confirm_fixture(self.state,fid,on='2026-07-27',association_approved=True)
        self.assertEqual(f['date'],'2026-08-01')
        self.assertEqual(f['conference_date'],'2026-07-25')
        cup.validate_state(self.state)

    def test_calendar_mutations_cannot_pass_setup(self):
        definition=next(c for c in self.data['countries'] if c['id']=='wales')['domestic_cups'][0]
        definition['calendar']['rounds']['round_2']['conference_date']='2026-09-01'
        with self.assertRaisesRegex(ValueError,'exclude'):cup.create_validation_cup(self.data,1,'2026-07-01')

    def test_expenses_fee_halving_receipt_cap_and_integer_money(self):
        rules=self.state['definition']['financial_rules']['officials']
        p=official_payment(rules,fee_pence=5000,travel_mode='car',miles=151,meal_receipt_pence=1500)
        self.assertEqual(p,dict(fee_pence=5000,travel_pence=8305,meal_pence=1000,total_pence=14305))
        p=official_payment(rules,fee_pence=5001,travel_mode='motorcycle',miles=150,meal_receipt_pence=900,played=False)
        self.assertEqual(p['total_pence'],2501+3600)
        with self.assertRaises(ValueError):official_payment(rules,fee_pence=True,travel_mode='car')
        with self.assertRaises(ValueError):official_payment(rules,fee_pence=100,travel_mode='car',fare_pence=100)

    def test_later_invoice_is_added_once_and_cannot_charge_a_second_match(self):
        ids=self.first_round()
        for fid in ids[:2]:
            self.confirm(self.state,fid,'2026-07-10')
            cup.record_result(self.state,fid,on='2026-07-25',score=[1,0])
        record_match_payables(self.state,ids[0])
        invoice=dict(id='unique-invoice',official_id='official',claim=dict(fee_pence=1000,travel_mode='car',miles=10))
        record=record_match_payables(self.state,ids[0],official_invoices=[invoice])
        self.assertEqual(record['lines'][0]['amount_pence'],1550)
        self.assertEqual(record_match_payables(self.state,ids[0]),record)
        before=deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'another fixture'):
            record_match_payables(self.state,ids[1],official_invoices=[invoice])
        self.assertEqual(before,self.state)

    def test_actual_host_pays_and_tv_allocation_is_conserved_once(self):
        fid=self.first_round()[0];f=self.state['fixtures'][0];original=f['home']
        cup.confirm_fixture(self.state,fid,on='2026-07-10',unavailable=[original])
        cup.record_result(self.state,fid,on='2026-07-25',score=[2,0])
        invoice=dict(id='fee-1',official_id='referee-1',claim=dict(fee_pence=5000,travel_mode='bus',fare_pence=1200))
        award=dict(decision_id='broadcast-1',amount_pence=10001,shares={f['home']:5001,f['away']:5000})
        record=record_match_payables(self.state,fid,official_invoices=[invoice],tv_award=award)
        self.assertEqual(record['lines'][0]['payer'],f['home'])
        self.assertEqual(record['lines'][0]['amount_pence'],6200)
        before=deepcopy(self.state)
        self.assertEqual(record_match_payables(self.state,fid,official_invoices=[invoice],tv_award=award),record)
        self.assertEqual(before,self.state)
        award['amount_pence']=10000
        with self.assertRaisesRegex(ValueError,'reconcile'):record_match_payables(self.state,fid,official_invoices=[invoice],tv_award=award)
        self.assertEqual(before,self.state)


if __name__=='__main__':unittest.main()
