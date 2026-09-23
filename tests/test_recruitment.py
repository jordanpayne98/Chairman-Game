from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from club_chairman import career, recruitment, club_ai, market
from club_chairman.simulation import new_career, execute, Command, view
from club_chairman.persistence import save, load, migrate


class RecruitmentTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83)
        self.act('hire',id='m0');self.act('budget',value=4000000)

    def act(self,action,**payload):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,payload))

    def p(self,pid):return career.person(self.s,pid)

    def elite(self,pid):
        p=self.p(pid);r=self.s['recruitment']
        r['players'][pid]['value']=95
        r['clubs']['c0']['value']=20
        r['priorities'][pid].update(status=90,minutes=50,money=80,security=40,
                                   firm_status=True,prestige_tolerance=18)
        return p

    def test_veteran_opportunity_can_offset_prestige_but_firm_priority_cannot(self):
        p=self.p('p26');p.update(age=34,role='MID')
        for q in self.s['players']:
            if q['club']=='c1':q['role']='MID'
        r=self.s['recruitment'];r['players'][p['id']]['value']=85
        r['clubs']['c1']['value']=85;r['clubs']['c0']['value']=60
        r['priorities'][p['id']].update(status=35,minutes=90,money=50,security=70,firm_status=False)
        before=deepcopy(self.s)
        result=recruitment.assess(self.s,p,'c0',p['wage']*110//100,730)
        self.assertTrue(result['acceptable']);self.assertEqual(self.s,before)
        r['priorities'][p['id']].update(status=90,firm_status=True,prestige_tolerance=18)
        self.assertFalse(recruitment.assess(self.s,p,'c0',p['wage']*4,1095)['acceptable'])

    def test_counteroffer_is_actually_acceptable_and_cash_still_has_final_authority(self):
        p=self.p('p144')
        self.act('enquire',id=p['id'])
        self.act('propose_offer',id=p['id'],wage=10000,fee=0,duration=2)
        o=self.s['career']['offers'][p['id']]
        self.assertEqual(o['status'],'counter');self.assertTrue(o['interest']['acceptable'])
        self.s['cash']=0;before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'cash'):self.act('accept_offer',id=p['id'])
        self.assertEqual(before,self.s)

    def test_firm_priority_declines_talks_and_reopening_cannot_reroll(self):
        p=self.elite('p144')
        self.act('enquire',id=p['id']);o=self.s['career']['offers'][p['id']]
        self.assertEqual(o['status'],'rejected');feedback=deepcopy(o['interest'])
        self.act('enquire',id=p['id'])
        self.assertEqual(self.s['career']['offers'][p['id']]['interest'],feedback)
        self.assertEqual(career.reservations(self.s),(0,0))

    def test_declined_matching_talks_release_the_original_sale(self):
        from test_transfer_rights import TransferRightsTests
        t=TransferRightsTests();t.setUp();t.sell(first_refusal=True);n=t.bid()
        t.act('refusal_match',id=n['id'])
        self.s=t.s;self.elite('p2');self.act('enquire',id='p2')
        self.assertEqual(self.s['career']['offers']['p2']['status'],'rejected')
        self.assertEqual(self.s['clauses']['notices'][0]['status'],'failed')
        self.assertEqual(self.s['club_ai']['decisions'][0]['status'],'medical')
        self.assertEqual(career.reservations(self.s),(0,0))

    def test_minimum_counter_survives_medical_delay_with_same_package(self):
        p=self.p('p144');r=self.s['recruitment']
        r['players'][p['id']]['value']=95
        r['priorities'][p['id']].update(status=90,minutes=50,money=80,security=70,firm_status=False)
        self.act('enquire',id=p['id'])
        self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2)
        o=self.s['career']['offers'][p['id']]
        self.assertEqual(o['status'],'counter');self.assertGreater(o['wage'],p['wage'])
        self.act('accept_offer',id=p['id'])
        self.act('continue');self.act('continue')
        self.assertEqual(self.s['career']['offers'][p['id']]['status'],'ready')
        self.act('complete_offer',id=p['id'])
        self.assertEqual(self.p(p['id'])['club'],'c0')

    def test_candidate_reservation_does_not_count_as_a_competing_teammate(self):
        p=self.p('p144');before=recruitment.assess(self.s,p,'c0',p['wage'],730)
        self.s['career']['offers'][p['id']]=dict(player=p['id'],kind='sign',status='medical')
        context=recruitment.roster_context(self.s)
        self.assertEqual(recruitment.assess(self.s,p,'c0',p['wage'],730,context),before)
        # A second incoming goalkeeper is genuine competition for the same place.
        q=self.p('p148');q['club']=None
        self.s['career']['offers'][q['id']]=dict(player=q['id'],kind='sign',status='medical')
        self.assertLess(recruitment.opportunity(self.s,p,'c0'),recruitment.opportunity(self.s,p,'c0',context))

    def test_no_affordable_counter_cannot_be_accepted_as_consent(self):
        p=self.elite('p144');self.s['recruitment']['priorities'][p['id']]['firm_status']=False
        self.s['recruitment']['priorities'][p['id']].update(status=100,minutes=1,money=1,security=1)
        self.act('enquire',id=p['id'])
        self.act('propose_offer',id=p['id'],wage=500000,fee=p['fee'],duration=2)
        self.assertEqual(self.s['career']['offers'][p['id']]['status'],'draft')
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('accept_offer',id=p['id'])
        self.assertEqual(before,self.s)

    def test_context_change_blocks_accepted_package_without_spending(self):
        p=self.p('p144');self.act('enquire',id=p['id'])
        self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2)
        self.elite(p['id']);before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'Player consent'):self.act('accept_offer',id=p['id'])
        self.assertEqual(before,self.s)

    def test_outgoing_seller_fee_cannot_override_personal_refusal(self):
        p=self.p('p2');r=self.s['recruitment'];r['players'][p['id']]['value']=95
        r['clubs']['c1']['value']=10;r['priorities'][p['id']].update(firm_status=True,prestige_tolerance=18)
        self.act('sale_enquire',id=p['id'],club='c1')
        d=next(reversed(self.s['market']['deals'].values()));d['fee']*=2;before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'Player consent'):self.act('market_accept',id=d['id'])
        self.assertEqual(before,self.s)

    def test_ai_pending_consent_uses_same_policy_and_releases_reservations(self):
        p=self.elite('p144');r=self.s['recruitment'];r['clubs']['c1']['value']=20
        d=dict(id='test-interest',club='c1',target='c1',source=None,player=p['id'],day=0,due=0,
               status='medical',fee=0,signing_fee=p['fee'],wage=p['wage']*2,end=730,
               interest_policy=1,reason='Test employment',outcome=None)
        self.s['club_ai']['decisions'].append(d)
        self.s['day']=1;cash=market.club_cash(self.s,'c1');before=p['club']
        club_ai.process_day(self.s)
        self.assertEqual(d['status'],'cancelled');self.assertIn('Player consent',d['outcome'])
        self.assertEqual(market.extra_reservations(self.s,'c1'),(0,0))
        self.assertEqual(market.club_cash(self.s,'c1'),cash);self.assertEqual(p['club'],before)

    def test_hidden_attributes_do_not_drive_public_standing_or_feedback(self):
        p=self.p('p144');before=deepcopy(self.s['recruitment'])
        result=recruitment.assess(self.s,p,'c0',p['wage'],730)
        for k in p['attrs']:p['attrs'][k]=99
        p['potential']=100;p['hidden']={k:100 for k in p['hidden']}
        recruitment.sync(self.s)
        self.assertEqual(before,self.s['recruitment'])
        self.assertEqual(result,recruitment.assess(self.s,p,'c0',p['wage'],730))
        snapshot=view(self.s)
        self.assertNotIn('priorities',json.dumps(snapshot));self.assertNotIn('firm_status',json.dumps(snapshot))

    def test_save_reload_and_reopening_do_not_reroll_preferences(self):
        p=self.p('p144');self.act('enquire',id=p['id']);old=deepcopy(self.s['career']['offers'][p['id']]['interest'])
        self.act('withdraw_offer',id=p['id']);self.act('enquire',id=p['id'])
        self.assertEqual(old,self.s['career']['offers'][p['id']]['interest'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'career.sqlite3';save(self.s,path);restored=load(path)
        self.assertEqual(restored,self.s)

    def test_schema20_migration_retains_contracts_matches_and_old_consents(self):
        self.act('enquire',id='p144')
        o=self.s['career']['offers']['p144'];o.pop('interest_policy');o.pop('interest')
        old=deepcopy(self.s);old['schema']=20;old.pop('recruitment');old['config'].pop('recruitment')
        before=deepcopy(old);new=migrate(old)
        self.assertEqual(old,before);self.assertEqual(new['schema'],29)
        self.assertEqual(new['players'],old['players']);self.assertEqual(new['career'],old['career'])
        self.assertEqual(new['match'],old['match']);self.assertEqual(new['cash'],old['cash'])
        self.assertEqual(migrate(new),new)


if __name__=='__main__':unittest.main()
