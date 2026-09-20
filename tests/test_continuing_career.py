import json
import unittest
from copy import deepcopy
from club_chairman.simulation import Command,execute,new_career,view,validate,payroll
from club_chairman.career import reservations,available_capacity,manager_severance
from club_chairman.planning import forecast


class ContinuingCareerTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83);self.act('budget',value=4000000);self.act('hire',id='m0')

    def act(self,action,**payload):
        c=Command(f"test:{self.s['revision']}",self.s['revision'],action,payload)
        self.s,message=execute(self.s,c);return c,message

    def progress(self,until=None):
        while not self.s['season_done'] and (until is None or self.s['day']<until):
            if self.s['match']:
                self.act('match_skip') if not self.s['match'].get('finished',self.s['match']['minute']>=90) else self.act('match_close')
            elif self.s['decision']:self.act('decision',choice='decline')
            else:self.act('continue')

    def terms(self,pid,duration=2):
        p=next(p for p in self.s['players'] if p['id']==pid)
        self.act('enquire',id=pid)
        self.act('propose_offer',id=pid,wage=round(p['wage']*1.05),fee=p['fee'] if p['club'] is None else 0,duration=duration)
        self.act('accept_offer',id=pid)

    def test_negotiated_signing_reserves_then_commits_exactly_once(self):
        cash=self.s['cash'];pay=payroll(self.s);self.terms('p144')
        o=self.s['career']['offers']['p144'];self.assertEqual(o['status'],'medical')
        self.assertEqual(self.s['cash'],cash);self.assertEqual(payroll(self.s),pay)
        self.assertEqual(reservations(self.s),(o['fee'],o['wage']))
        with self.assertRaises(ValueError):self.act('sign',id='p144')
        self.progress(2);self.assertEqual(self.s['career']['offers']['p144']['status'],'ready')
        command,_=self.act('complete_offer',id='p144');after=deepcopy(self.s)
        self.s,_=execute(self.s,command);self.assertEqual(self.s,after)
        self.assertEqual(self.s['cash'],cash-o['fee']);self.assertEqual(reservations(self.s),(0,0))
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p144')['club'],'c0')

    def test_competing_offers_cannot_reuse_payroll_and_expiry_releases(self):
        self.terms('p144');first=self.s['career']['offers']['p144']
        self.act('budget',value=payroll(self.s)+first['wage'])
        p=next(p for p in self.s['players'] if p['id']=='p145')
        self.act('enquire',id=p['id']);self.act('propose_offer',id=p['id'],wage=p['wage']*2,fee=p['fee'],duration=2)
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('accept_offer',id=p['id'])
        self.assertEqual(before,self.s)
        self.progress(8);self.assertEqual(reservations(self.s),(0,0));self.assertEqual(first['fee'],before['career']['offers']['p144']['fee'])
        self.assertEqual(self.s['career']['offers']['p144']['status'],'expired')

    def test_manager_replacement_charges_notice_and_resets_authority(self):
        notice=manager_severance(self.s);cash=self.s['cash'];pay=payroll(self.s)
        command,_=self.act('manager_replace',id='m1',duration=2)
        self.assertEqual(self.s['cash'],cash-notice-300000)
        self.assertEqual(payroll(self.s),pay-140000+240000);self.assertEqual(self.s['trust'],55)
        repeated,_=execute(self.s,command);self.assertEqual(repeated,self.s)
        self.assertEqual(len([e for e in self.s['ledger'] if e['reason']=='Manager termination payment']),1)

    def test_agent_accepts_its_own_counteroffer(self):
        # This person seeks a pay rise on a one-season agreement.
        self.s=new_career(1);self.act('budget',value=4000000);self.act('hire',id='m0')
        self.act('enquire',id='p144')
        self.act('propose_offer',id='p144',wage=10000,fee=0,duration=1)
        counter=deepcopy(self.s['career']['offers']['p144'])
        self.assertEqual(counter['status'],'counter')
        self.act('propose_offer',id='p144',wage=counter['wage'],fee=counter['fee'],duration=counter['duration'])
        self.assertEqual(self.s['career']['offers']['p144']['status'],'agreed')
        self.act('accept_offer',id='p144');self.progress(2);self.act('complete_offer',id='p144')
        signed=next(p for p in self.s['players'] if p['id']=='p144')
        self.assertEqual(signed['wage'],counter['wage']);self.assertEqual(signed['club'],'c0')

    def test_academy_identity_and_project_milestones(self):
        self.act('academy_intake');ids=[p['id'] for p in self.s['players'] if p['youth']]
        self.assertEqual(len(ids),6)
        with self.assertRaises(ValueError):self.act('academy_intake')
        pid=next(p['id'] for p in self.s['players'] if p['youth'] and p['age']>=16)
        self.act('academy_admit',id=pid);p=deepcopy(next(p for p in self.s['players'] if p['id']==pid))
        self.act('academy_promote',id=pid);promoted=next(p for p in self.s['players'] if p['id']==pid)
        self.assertEqual(promoted['contract_end'],p['contract_end']);self.assertEqual(promoted['wage'],p['wage']);self.assertFalse(promoted['youth'])
        self.act('project_plan',kind='stadium');self.progress(3)
        project=self.s['career']['projects'][0];self.act('project_approve',id=project['id'])
        self.assertEqual(available_capacity(self.s),5200)
        self.progress(38)
        self.assertEqual(self.s['career']['projects'][0]['status'],'operational')
        self.assertEqual(available_capacity(self.s),6800);self.assertEqual(self.s['config']['weekly_overheads'],390000)
        postings=len(self.s['ledger']);self.act('continue');self.assertEqual(available_capacity(self.s),6800)
        self.assertEqual(len([e for e in self.s['ledger'] if e['id'].endswith(':build')]),1)

    def test_three_seasons_keep_histories_ids_and_distinct_settlement(self):
        seen=set()
        for season in range(1,4):
            self.progress()
            if self.s['match']:self.act('match_close')
            ids={f['id'] for f in self.s['fixtures']};self.assertFalse(ids&seen);seen|=ids
            self.assertTrue(all(c['played']==14 for c in self.s['clubs']))
            validate(self.s)
            if season<3:
                before=self.s['day'];command,_=self.act('next_season')
                self.assertEqual(self.s['day'],before)
                again,_=execute(self.s,command);self.assertEqual(again,self.s)
        self.assertEqual(len(self.s['career']['history']),2)
        self.assertTrue(all(h['competitions']['cup']['settled'] for h in self.s['career']['history']))
        self.assertTrue(all(h['competitions']['cup']['winner'] for h in self.s['career']['history']))
        self.assertEqual(len([e for e in self.s['ledger'] if e['reason']=='League prize']),3)
        self.assertEqual(len(seen),381)
        self.assertEqual(sum(h['table'][0]['played'] for h in self.s['career']['history']),28)

    def test_end_of_season_renewal_is_not_blocked_by_medical_clock(self):
        self.progress();self.act('match_close')
        p=next(p for p in self.s['players'] if p['id']=='p0');p['contract_end']=self.s['day']
        self.terms('p0');self.assertEqual(self.s['career']['offers']['p0']['status'],'ready')
        self.act('complete_offer',id='p0');self.act('next_season');self.act('continue')
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p0')['club'],'c0')

    def test_final_away_forecast_settles_accrued_costs(self):
        self.progress(96);self.assertEqual(self.s['match']['away'],'c0')
        v=view(self.s);f=forecast(v);accrued=self.s['accrued_costs']//7
        self.assertGreater(accrued,0);self.assertEqual(f['cash'],self.s['cash']-accrued)
        self.assertEqual(f['accrued'],0)
        self.act('match_skip')
        prize=next(e['amount'] for e in self.s['ledger'] if e['reason']=='League prize')
        self.assertEqual(f['cash'],self.s['cash']-prize)
