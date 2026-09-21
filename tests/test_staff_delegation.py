from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import staff,delegation,club_ai
from club_chairman.simulation import new_career,execute,Command,view,payroll,validate,posting
from club_chairman.persistence import save,load
from club_chairman.planning import forecast
from club_chairman.career import reservations


class StaffDelegationTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83);self.act('budget',value=4000000);self.act('hire',id='m0')

    def act(self,action,**data):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))

    def advance(self,day):
        while self.s['day']<day or self.s['match'] or self.s['decision']:
            if self.s['match']:self.act('match_close') if self.s['match']['finished'] else self.act('match_skip')
            elif self.s['decision']:self.act('decision',choice='decline')
            else:self.act('continue')

    def hire_staff(self,ids=('staff:0:0',),autonomy='Advisory'):
        for pid in ids:self.act('staff_contact',id=pid)
        self.advance(self.s['day']+1)
        for pid in ids:
            self.act('staff_interview',id=pid)
            p=staff.person(self.s,pid)
            self.act('staff_propose',id=pid,wage=p['expected_wage']*12//10,duration=2,autonomy=autonomy)
            self.act('staff_accept',id=pid)
        self.advance(max(staff.person(self.s,pid)['pending']['start'] for pid in ids))

    def assign(self,key,pid='staff:0:0',mode='Autonomous',limit=8000000,days=365):
        self.act('delegation_set',key=key,delegate=pid,mode=mode,limit=limit,days=days,objective='Maintain')

    def test_interviews_improve_saved_evidence_without_revealing_truth(self):
        pid='staff:0:0';self.act('staff_contact',id=pid)
        initial=deepcopy(self.s['staff']['assessments'][pid]);self.advance(1);self.act('staff_interview',id=pid)
        current=self.s['staff']['assessments'][pid]
        self.assertLess(sum(b-a for a,b in current['ranges'].values()),sum(b-a for a,b in initial['ranges'].values()))
        before=view(self.s)
        for p in self.s['staff']['people']:
            if p['id']!=pid:p['capabilities']={k:1 for k in staff.CAPABILITIES}
            p['risk']='Ambitious'
        self.assertEqual(before,view(self.s))
        with self.assertRaises(ValueError):self.act('staff_interview',id=pid)

    def test_joining_reserves_payroll_and_forecast_includes_dated_salary(self):
        pid='staff:0:0';self.act('staff_contact',id=pid);self.advance(1);self.act('staff_interview',id=pid)
        p=staff.person(self.s,pid);w=p['expected_wage']*12//10
        self.act('staff_propose',id=pid,wage=w,duration=2);baseline=payroll(self.s)
        self.act('staff_accept',id=pid)
        self.assertEqual(payroll(self.s),baseline);self.assertEqual(reservations(self.s)[1],w)
        self.s['config']['capacity']=0
        expected=forecast(view(self.s),horizon=13)['cash'];self.advance(14)
        self.assertEqual(self.s['cash'],expected);self.assertEqual(payroll(self.s),baseline+w)
        self.assertEqual(reservations(self.s)[1],0)
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'staff.sqlite3';save(self.s,p);self.assertEqual(self.s,load(p))

    def test_department_capacity_and_protected_approval_are_enforced(self):
        self.hire_staff(autonomy='Approval required')
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'contract requires approval'):self.assign('finance')
        self.assertEqual(before,self.s)
        for key in ('finance','executive','commercial','operations'):self.assign(key,mode='Approval required')
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'capacity'):self.assign('recruitment',mode='Approval required')
        self.assertEqual(before,self.s)
        self.act('delegation_preset',preset='Executive')
        self.assertTrue(all(r['mode']!='Autonomous' for r in self.s['delegation']['responsibilities'].values()))

    def test_unauthorised_staff_spend_is_atomic_and_case_can_be_reviewed(self):
        self.hire_staff();self.assign('recruitment',limit=0)
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'commitment limit'):
            execute(self.s,Command('bad-spend',self.s['revision'],'scout',{'id':'p144'},'staff:0:0','c0','recruitment'))
        self.assertEqual(before,self.s)
        delegation.propose(self.s,'recruitment','scout',dict(id='p144'),'Review affordable squad cover.')
        case=self.s['delegation']['cases'][-1];self.assertEqual(case['status'],'pending')
        cash=self.s['cash'];self.act('delegation_case',id=case['id'],choice='approve')
        self.assertEqual(cash-self.s['cash'],self.s['config']['scout_fee'])
        self.assertEqual(self.s['delegation']['cases'][-1]['status'],'approved')
        with self.assertRaises(ValueError):self.act('delegation_case',id=case['id'],choice='approve')

    def test_expired_delegate_loses_authority_and_unsigned_work(self):
        self.hire_staff();self.assign('contracts')
        delegation.perform(self.s,'contracts','enquire',dict(id='p2'),'Renew soon.')
        staff.person(self.s,'staff:0:0')['end']=self.s['day']
        self.advance(self.s['day']+1)
        rule=self.s['delegation']['responsibilities']['contracts']
        self.assertIsNone(rule['delegate']);self.assertEqual(rule['mode'],'Manual')
        self.assertEqual(self.s['career']['offers']['p2']['status'],'withdrawn')
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p2')['club'],'c0')

    def test_departure_pays_notice_and_does_not_erase_signed_commitments(self):
        self.hire_staff();self.assign('commercial')
        for action,data in (('sponsor_enquire',dict(right='digital')),('sponsor_propose',dict(right='digital',weekly=80000,weeks=8)),('sponsor_accept',dict(right='digital'))):
            delegation.perform(self.s,'commercial',action,data,'Negotiate unused inventory.')
        agreement=deepcopy(self.s['commercial']['contracts'][0]);cost=staff.severance(self.s,staff.person(self.s,'staff:0:0'));cash=self.s['cash']
        self.act('staff_dismiss',id='staff:0:0')
        self.assertEqual(self.s['cash'],cash-cost);self.assertEqual(self.s['commercial']['contracts'][0],agreement)
        self.assertIsNone(self.s['delegation']['responsibilities']['commercial']['delegate'])

    def test_delegated_month_runs_with_reconciled_digest_and_saved_resume(self):
        self.hire_staff(('staff:0:0','staff:1:0','staff:7:0'))
        self.act('delegation_cover');self.act('delegation_preset',preset='Executive')
        self.assertTrue(all(r['delegate'] for r in self.s['delegation']['responsibilities'].values()))
        next(p for p in self.s['players'] if p['id']=='p2')['contract_end']=20
        base=deepcopy(self.s);self.advance(31);complete=deepcopy(self.s)
        self.s=base;self.advance(17)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'month.sqlite3';save(self.s,path);self.s=load(path)
        self.advance(31)
        self.assertEqual(self.s,complete)
        self.assertTrue(any(n['title']=='Executive monthly digest' for n in self.s['inbox']))
        actions={e['action'] for e in self.s['delegation']['log']}
        self.assertTrue({'complete_offer','scout','sponsor_accept','decision','development_plan'}<=actions,actions)
        self.assertEqual(next(p for p in self.s['players'] if p['id']=='p2')['club'],'c0')
        self.assertTrue(any(d['status']=='completed' for d in self.s['club_ai']['decisions']))
        validate(self.s)

    def test_ai_cannot_spend_owed_bills_or_exceed_payroll_authority(self):
        for a in self.s['market']['accounts'].values():
            a['ledger'].append(dict(id='fixture:reduce',day=0,amount=-a['cash'],reason='Test',balance=0));a['cash']=0
        self.s['day']=7;club_ai.process_day(self.s)
        self.assertFalse(self.s['club_ai']['decisions'])
        for a in self.s['market']['accounts'].values():
            a['cash']=100000000;a['ledger'].append(dict(id='fixture:fund',day=7,amount=100000000,reason='Test',balance=100000000))
        self.s['config']['club_ai']['payroll_income_percent']=1
        employee=staff.person(self.s,'staff:c1:Executive');employee['end']=20
        player=next(p for p in self.s['players'] if p['club']=='c1');player['contract_end']=20
        self.s['day']=14;club_ai.process_day(self.s);self.assertFalse(self.s['club_ai']['decisions'])
        self.assertEqual(employee['end'],20);self.assertEqual(player['contract_end'],20)
        self.act('sale_enquire',id='p2',club='c1');deal=next(reversed(self.s['market']['deals'].values()))
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'authorise these wages'):self.act('market_accept',id=deal['id'])
        self.assertEqual(before,self.s)

    def test_rolling_limits_cannot_be_bypassed_by_splitting_commissions(self):
        self.hire_staff();self.assign('recruitment',limit=2*self.s['config']['scout_fee'])
        for pid in ('p144','p145'):
            self.s,_=execute(self.s,Command('scout:'+pid,self.s['revision'],'scout',dict(id=pid),'staff:0:0','c0','recruitment'))
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'commitment limit'):
            execute(self.s,Command('scout:p146',self.s['revision'],'scout',dict(id='p146'),'staff:0:0','c0','recruitment'))
        self.assertEqual(before,self.s)

    def test_future_salary_is_checked_and_a_changed_case_is_not_approved(self):
        self.hire_staff();self.assign('contracts',limit=1)
        delegation.perform(self.s,'contracts','enquire',dict(id='p2'),'Retain squad cover.')
        p=next(p for p in self.s['players'] if p['id']=='p2');p['contract_end']=self.s['day']+10
        self.act('propose_offer',id='p2',wage=p['wage'],fee=0,duration=2)
        delegation.propose(self.s,'contracts','accept_offer',dict(id='p2'),'Review guaranteed salary.')
        c=self.s['delegation']['cases'][-1]
        self.assertGreater(c['exposure']['cost'],0);self.assertIn('commitment limit',c['issue'])
        self.s['career']['offers']['p2']['wage']+=50000;before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'Terms changed'):self.act('delegation_case',id=c['id'],choice='approve')
        self.assertEqual(before,self.s)

    def test_poaching_pays_compensation_and_changes_payroll_on_the_start_date(self):
        pid='staff:c1:Executive';p=staff.person(self.s,pid);source_cash=self.s['market']['accounts']['c1']['cash']
        self.act('staff_contact',id=pid);self.advance(1);self.act('staff_interview',id=pid)
        self.act('staff_propose',id=pid,wage=72000,duration=2)
        before=self.s['cash'];self.act('staff_accept',id=pid);p=staff.person(self.s,pid)
        self.assertEqual(before-self.s['cash'],240000);self.assertEqual(self.s['market']['accounts']['c1']['cash']-source_cash,240000)
        self.assertEqual(p['club'],'c1');start=p['pending']['start'];self.advance(start-1);self.assertEqual(staff.person(self.s,pid)['club'],'c1')
        self.advance(start);self.assertEqual(staff.person(self.s,pid)['club'],'c0');self.assertEqual(staff.person(self.s,pid)['wage'],72000)

    def test_completed_staff_reports_do_not_expose_ai_targets(self):
        self.advance(8)
        snapshot=view(self.s);before=deepcopy(snapshot)
        for report in self.s['club_ai']['observations'].values():
            for r in report.values():r['estimate']=1;r['range']=[1,1]
        for d in self.s['club_ai']['decisions']:
            if d['status']=='medical':d['reason']='Private priority';d['wage']+=50000
        self.assertEqual(before,view(self.s))

    def test_ai_policy_uses_existing_observations_and_public_contracts(self):
        for cid in [c['id'] for c in self.s['clubs'][1:]]:
            for p in self.s['players']:club_ai.observation(self.s,cid,p)
        original=deepcopy(self.s)
        for p in self.s['players']:
            p['potential']=100
            for k in people_keys(p):p['attrs'][k]=99
        self.s['day']=original['day']=7
        club_ai.process_day(self.s);club_ai.process_day(original)
        self.assertEqual(self.s['club_ai']['decisions'],original['club_ai']['decisions'])


def people_keys(p):return list(p['attrs'])


if __name__=='__main__':unittest.main()
