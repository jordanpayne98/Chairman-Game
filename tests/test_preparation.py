from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from club_chairman import football, preparation
from club_chairman.simulation import new_career, execute, Command, record_result, view, validate
from club_chairman.persistence import migrate, save, load


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42)
        self.s,_=execute(self.s,Command('hire',0,'hire',{'id':'m0'}))
        self.p=next(p for p in self.s['players'] if p['id']=='p2')
        self.key=self.s['preparation']['current']['system']
        self.f=next(f for f in self.s['fixtures'] if f['home']=='c0')

    def day(self,n):
        self.s['day']=n;preparation.process_day(self.s)

    def test_real_training_bounded_and_once_per_day(self):
        skills=deepcopy(self.p['attrs']);self.day(1)
        first=preparation.value(self.s,self.p['id'],self.key)
        self.assertGreater(first,0);self.assertLess(first,3)
        before=deepcopy(self.s);preparation.process_day(self.s);self.assertEqual(before,self.s)
        self.p['injury_until']=20;self.day(2)
        self.assertEqual(preparation.value(self.s,self.p['id'],self.key),first)
        self.p['injury_until']=0;self.p['fatigue']=90;self.day(3)
        self.assertEqual(preparation.value(self.s,self.p['id'],self.key),first)
        self.p['fatigue']=0;self.day(self.f['day'])
        self.assertEqual(preparation.value(self.s,self.p['id'],self.key),first)
        self.assertEqual(self.p['attrs'],skills)
        self.assertEqual(self.s['preparation']['report']['rows'][2]['status'],'Matchday')

    def test_coaching_load_and_resources_change_learning_not_capabilities(self):
        weak=deepcopy(self.s);strong=deepcopy(self.s)
        weak['manager']['capabilities']['coaching']=1;strong['manager']['capabilities']['coaching']=100
        for s in (weak,strong):
            for p in s['staff']['people']:p['club']=None
            s['day']=1;preparation.process_day(s)
        self.assertGreater(preparation.value(strong,'p2',self.key),preparation.value(weak,'p2',self.key))
        light=deepcopy(self.s);light['players'][2]['development']['load']='Light';light['day']=1;preparation.process_day(light)
        self.day(1);self.assertLess(preparation.value(light,'p2',self.key),preparation.value(self.s,'p2',self.key))
        upgraded=deepcopy(self.s);upgraded['career']['facilities']['training']=5
        for s in (self.s,upgraded):s['day']=2;preparation.process_day(s)
        self.assertGreater(preparation.value(upgraded,'p2',self.key),preparation.value(self.s,'p2',self.key))

    def test_replacement_retains_learning_and_has_no_instant_training(self):
        self.day(1);learned=deepcopy(self.s['preparation']['players']);attrs=deepcopy(self.p['attrs'])
        self.s,_=execute(self.s,Command('replace',self.s['revision'],'manager_replace',{'id':'m1'}))
        self.assertEqual(learned,self.s['preparation']['players'])
        self.assertEqual(self.s['players'][2]['attrs'],attrs)
        self.assertNotEqual(self.key,self.s['preparation']['current']['system'])
        self.assertIsNone(view(self.s)['preparation']['rows'][2]['value'])
        self.day(2);self.assertEqual(preparation.value(self.s,'p2',self.key),learned['p2'][self.key]['value'])
        self.s,_=execute(self.s,Command('return',self.s['revision'],'manager_replace',{'id':'m0'}))
        self.assertEqual(self.s['preparation']['players']['p2'][self.key],learned['p2'][self.key])
        preparation.process_day(self.s)
        self.assertEqual(self.s['preparation']['players']['p2'][self.key],learned['p2'][self.key])
        validate(self.s)

    def test_frozen_match_preparation_recalculates_from_actual_participants(self):
        m=football.start(self.s,self.f);entry=m['preparation'][0]
        self.assertEqual(preparation.edge(m,0),0)
        for pid in m['on_pitch'][0]:entry['values'][pid]=100
        self.assertEqual(preparation.edge(m,0),2)
        outgoing=m['on_pitch'][0][0];incoming=m['bench'][0][0]
        m['on_pitch'][0][0]=incoming
        self.assertAlmostEqual(preparation.edge(m,0),20/11)
        self.assertEqual(preparation.edge(m,1),0)
        old=deepcopy(m);old.pop('preparation');self.assertEqual(preparation.edge(old,0),0)
        self.assertEqual(entry['values'][outgoing],100)
        m['on_pitch'][0].pop();self.assertAlmostEqual(preparation.edge(m,0),1.8)
        # Observe the real passing probability input, not just the helper.
        rng=Mock();rng.choice.side_effect=lambda items:items[0];rng.random.return_value=.99
        def passing_input(match):
            with patch.object(football,'probability',return_value=.5) as probability:
                football.action(self.s,deepcopy(match),rng)
                return probability.call_args.args[0]
        neutral=deepcopy(m);neutral.pop('preparation')
        self.assertAlmostEqual(passing_input(m)-passing_input(neutral),1.8)
        m['possession_side']=1;neutral['possession_side']=1
        self.assertAlmostEqual(passing_input(m)-passing_input(neutral),-1.8)

    def test_resume_minutes_forfeit_and_settlement_idempotence(self):
        self.day(1);self.s['match']=football.start(self.s,self.f);m=self.s['match']
        snap=deepcopy(m['preparation'])
        for _ in range(27):football.step(self.s,m)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'save.sqlite3';save(self.s,path);resumed=load(path)
        for s in (self.s,resumed):
            while not football.finished(s['match']):football.step(s,s['match'])
            record_result(s,s['match'])
        self.assertEqual(self.s,resumed);self.assertEqual(m['preparation'],snap)
        learned=deepcopy(self.s['preparation']);record_result(self.s,m);self.assertEqual(learned,self.s['preparation'])
        for pid in m['participants'][0]:
            minutes=min(90,m['stats'][pid]['minutes'])
            if minutes:self.assertEqual(self.s['preparation']['players'][pid][snap[0]['system']]['minutes'],minutes)
        m['forfeit']=True;preparation.settle(self.s,m);self.assertEqual(learned,self.s['preparation'])

    def test_migration_keeps_active_match_and_unknown_history(self):
        self.s['match']=football.start(self.s,self.f);self.s['match'].pop('preparation')
        self.s.pop('preparation');self.s['config'].pop('preparation');self.s['schema']=17
        original=deepcopy(self.s);up=migrate(self.s)
        self.assertEqual(self.s,original);self.assertEqual(up['match'],original['match'])
        self.assertEqual(up['preparation']['players'],{});self.assertEqual(migrate(up),up)
        before=deepcopy(up);view(up);self.assertEqual(before,up)
        up['config']['preparation']['maximum_edge']=100
        with self.assertRaisesRegex(ValueError,'preparation setting'):validate(up)


if __name__=='__main__':unittest.main()
