from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from club_chairman import managers, staff, football
from club_chairman.simulation import new_career,execute,Command,view,validate,rng_for
from club_chairman.persistence import migrate,save,load


class ManagerAbilityTests(unittest.TestCase):
    def setUp(self):self.s=new_career(42)
    def act(self,action,**data):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))
    def row(self):return view(self.s)['manager_candidates'][0]

    def test_unknown_full_stale_and_employee_knowledge(self):
        self.assertIsNone(self.row()['assessment'])
        before=self.row();p=managers.candidate(self.s,'m0')
        p['capabilities']={k:99 for k in staff.CAPABILITIES};self.assertEqual(before,self.row())
        self.act('manager_assess',id='m0');p=managers.candidate(self.s,'m0')
        self.assertEqual(self.row()['assessment']['overall'],[99,99])
        snapshot=deepcopy(self.s['managers']['assessments'])
        p['capabilities']['adaptability']=49
        self.assertEqual(self.row()['assessment']['overall'],[89,89])
        self.assertEqual(snapshot,self.s['managers']['assessments'])
        self.s['day']=28;stale=self.row();self.assertEqual(stale['assessment']['knowledge'],'Stale')
        p['capabilities']={k:1 for k in staff.CAPABILITIES};self.assertEqual(stale,self.row())
        self.act('manager_assess',id='m0');self.assertEqual(self.row()['assessment']['overall'],[1,1])
        self.act('hire',id='m0');self.assertEqual(self.row()['assessment']['knowledge'],'Club access')
        self.assertNotIn('capabilities',self.row());self.assertNotIn('skill',self.row())

    def test_departure_preserves_dated_knowledge_without_future_live_access(self):
        from club_chairman import career
        for expiry in (False,True):
            self.s=new_career(42);self.act('budget',value=4000000);self.act('hire',id='m0')
            self.s['manager']['capabilities']['adaptability']=93
            known=deepcopy(self.row()['assessment']['ranges']);self.s['day']=1
            if expiry:
                self.s['manager']['contract_end']=0
                career.process_day(self.s)
                self.assertIsNone(self.s['manager'])
            else:self.act('manager_replace',id='m1')
            report=self.row()['assessment']
            self.assertEqual(report['ranges'],known);self.assertEqual(report['day'],1)
            self.assertFalse(report['exact_current'])
            before=deepcopy(self.row())
            managers.candidate(self.s,'m0')['capabilities']['adaptability']=1
            self.assertEqual(before,self.row())
            self.s['day']=29
            self.assertEqual(self.row()['assessment']['knowledge'],'Stale')
            self.assertEqual(self.s['managers']['assessments']['m0']['ranges'],known)

    def test_role_weights_and_appointment_identity(self):
        self.act('budget',value=4000000);self.act('hire',id='m0')
        self.s['manager']['capabilities']['adaptability']=93
        original=deepcopy(self.s['manager']['capabilities']);prefs=deepcopy(self.s['manager']['preferences'])
        self.act('manager_replace',id='m1');self.act('manager_replace',id='m0')
        self.assertEqual(original,self.s['manager']['capabilities']);self.assertEqual(prefs,self.s['manager']['preferences'])
        weights=self.s['config']['managers']['weights'];weights['adaptability']=0;weights['coaching']+=.2
        with self.assertRaisesRegex(ValueError,'manager ability weights'):validate(self.s)

    def test_adaptability_adjusts_instruction_with_judgement_and_owner_authority(self):
        self.act('hire',id='m0');fixture=next(f for f in self.s['fixtures'] if f['home']=='c0')
        m=football.start(self.s,fixture);m['minute']=70;m['score']=[0,1]
        m['manager_plan']['capabilities']['tactical_judgement']=80
        low=deepcopy(m);high=deepcopy(m)
        low['manager_plan']['capabilities']['adaptability']=20
        high['manager_plan']['capabilities']['adaptability']=90
        for match in (low,high):football.managers(self.s,match,rng_for(42,'test'))
        self.assertAlmostEqual(low['risk'][0],1.044);self.assertAlmostEqual(high['risk'][0],1.198)
        self.assertEqual(high['manager_plan']['baseline'],1.)
        events=len(high['events']);football.managers(self.s,high,rng_for(42,'test'))
        self.assertEqual(events,len(high['events']))
        high['intervened']=True;high['owner_instruction']='attack';high['score']=[2,1];football.managers(self.s,high,rng_for(42,'test'))
        self.assertEqual(high['risk'][0],1.198)
        m['manager_plan']['capabilities']['tactical_judgement']=1
        football.managers(self.s,m,rng_for(42,'test'));self.assertEqual(m['risk'][0],1.)
        self.assertNotIn('manager_plan',football.public_match(m))
        # Encouragement or a refused request must not disable the manager.
        from unittest.mock import patch
        for choice in ('encourage','attack'):
            self.s['match']=deepcopy(low);self.s['match']['risk'][0]=1.
            state=self.s['match']['rng']
            with patch('club_chairman.simulation.restore_rng') as restore:
                restore.return_value.random.return_value=1.
                restore.return_value.getstate.return_value=state
                self.act('intervene',choice=choice)
            live=self.s['match'];self.assertNotIn('owner_instruction',live)
            football.managers(self.s,live,rng_for(42,'test'))
            self.assertAlmostEqual(live['risk'][0],1.044)

    def test_keep_working_plan_and_cover_numerical_disadvantage(self):
        self.act('hire',id='m1');f=next(f for f in self.s['fixtures'] if f['away']=='c0')
        m=football.start(self.s,f);m['minute']=70
        m['manager_plan']['capabilities'].update(tactical_judgement=80,adaptability=100)
        self.assertIsNone(managers.adjustment(m,1))
        m['on_pitch'][1].pop();desired,reason=managers.adjustment(m,1)
        self.assertEqual(desired,.85);self.assertIn('numerical disadvantage',reason)

    def test_migration_preserves_active_match_and_source_and_roundtrips(self):
        self.act('hire',id='m0');self.s['match']=football.start(self.s,next(f for f in self.s['fixtures'] if f['home']=='c0'))
        old=deepcopy(self.s);old['schema']=15;old.pop('managers');old['config'].pop('managers')
        for key in ('capabilities','preferences'):old['manager'].pop(key)
        old['match'].pop('manager_plan');original=deepcopy(old)
        upgraded=migrate(old);self.assertEqual(old,original);self.assertEqual(upgraded['match'],old['match'])
        stripped=deepcopy(upgraded);stripped['schema']=15;stripped.pop('managers');stripped['config'].pop('managers')
        for key in ('capabilities','preferences'):stripped['manager'].pop(key)
        self.assertEqual(stripped,original)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'new.sqlite3';save(upgraded,path);before=path.read_bytes()
            self.assertEqual(load(path),json.loads(json.dumps(upgraded)));self.assertEqual(before,path.read_bytes())
        # An old match keeps the original 65-minute tactical decision.
        upgraded['match']['minute']=70;upgraded['match']['score']=[0,1]
        football.managers(upgraded,upgraded['match'],rng_for(42,'test'))
        self.assertEqual(upgraded['match']['risk'][0],1.22)

    def test_new_match_save_resume_and_unused_capabilities_do_not_add_match_bonus(self):
        self.act('hire',id='m0');f=next(f for f in self.s['fixtures'] if f['home']=='c0')
        self.s['match']=football.start(self.s,f)
        for _ in range(27):football.step(self.s,self.s['match'])
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'live.sqlite3';save(self.s,path);resumed=load(path)
        other=deepcopy(self.s);other['manager']['skill']=100
        other['manager']['capabilities']['commercial_judgement']=100
        for state in (self.s,resumed,other):
            while not football.finished(state['match']):football.step(state,state['match'])
        self.assertEqual(self.s,resumed)
        self.assertEqual(self.s['match'],other['match'])


if __name__=='__main__':unittest.main()
