from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import morale, playing_time as pt, football
from club_chairman.simulation import new_career, view, validate
from club_chairman.persistence import migrate,save,load


class MoraleTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42);self.p=self.s['players'][2]

    def concern(self):
        pt.sign(self.s,self.p,'c0','Key starter','test')
        r=pt.active(self.s,self.p['id']);r['concern']=dict(id='test:shortfall',since=0)
        return r

    def test_persistent_source_no_repeated_penalty_resolution_and_recurrence(self):
        r=self.concern();morale.reconcile(self.s);value=self.p['morale'];attrs=deepcopy(self.p['attrs'])
        self.assertLess(value,50)
        for day in range(1,8):self.s['day']=day;morale.reconcile(self.s)
        self.assertEqual(value,self.p['morale']);self.assertEqual(attrs,self.p['attrs'])
        self.assertEqual(len(self.s['mood']['players'][self.p['id']]['sources']),1)
        r['concern']=None;morale.reconcile(self.s);self.assertEqual(self.p['morale'],50)
        self.s['day']=8;r['concern']=dict(id='test:shortfall',since=8);morale.reconcile(self.s)
        self.assertEqual(value,self.p['morale'])

    def test_related_cap_decay_and_bands(self):
        for n in range(10):morale.add(self.s,self.p,str(n),'result',-8,'Loss',end=7)
        morale.reconcile(self.s);self.assertEqual(self.p['morale'],40)
        self.s['day']=7;morale.reconcile(self.s);self.assertEqual(self.p['morale'],50)
        self.assertEqual([morale.band(x) for x in (1,20,21,40,41,60,61,80,81,100)],
            ['Very unhappy']*2+['Unhappy']*2+['Content']*2+['Happy']*2+['Delighted']*2)

    def test_result_once_only_real_participants_shared_policy(self):
        p=self.p;q=next(p for p in self.s['players'] if p['club']=='c1')
        m=dict(fixture='test',home='c0',away='c1',lineups=[[p['id']],[q['id']]],score=[2,0],stats={p['id']:{'minutes':90},q['id']:{'minutes':90}})
        before=deepcopy(self.s);morale.collect(self.s,m);self.assertEqual(before,self.s)
        morale.kickoff(self.s,m);morale.collect(self.s,m);morale.reconcile(self.s)
        self.assertGreater(p['morale'],50);self.assertLess(q['morale'],50)
        before=deepcopy(self.s);morale.collect(self.s,m);self.assertEqual(before,self.s)
        self.assertNotIn('mood_expectations',football.public_match(m))

    def test_same_cohort_trend_privacy_and_empty_squad(self):
        self.concern();morale.reconcile(self.s)
        self.s['day']=7;self.p['club']='c1';morale.reconcile(self.s)
        v=view(self.s);squad=v['mood']['squad']
        self.assertEqual((squad['trend'],squad['departures']),('Stable',1))
        self.assertNotIn(self.p['id'],v['mood']['players'])
        self.assertEqual(squad['compared'],26)
        for p in self.s['players']:
            if p['club']=='c0':p['club']=None
        morale.reconcile(self.s);squad=morale.public(self.s)['squad']
        self.assertEqual(squad['band'],'No squad data');self.assertIsNone(squad['value'])

    def test_personality_response_preserves_attributes_and_suspended_concern(self):
        r=self.concern();self.p['hidden']['ambition']=10;morale.reconcile(self.s);first=self.p['morale']
        # A separate otherwise-identical person reacts to the same circumstance.
        q=self.s['players'][3];q['hidden']['ambition']=90
        pt.sign(self.s,q,'c0','Key starter','other');pt.active(self.s,q['id'])['concern']=dict(id='other:shortfall',since=0)
        morale.reconcile(self.s);self.assertLess(q['morale'],first)
        self.p['club']='c1';morale.reconcile(self.s);self.assertEqual(self.p['morale'],50)
        self.p['club']='c0';morale.reconcile(self.s);self.assertEqual(self.p['morale'],first)

    def test_migration_preserves_current_values_without_fake_history_and_roundtrip(self):
        old=deepcopy(self.s);old['schema']=23;old.pop('mood');old['config'].pop('morale');old['players'][2]['morale']=73
        before=deepcopy(old);s=migrate(old)
        self.assertEqual(old,before);self.assertEqual(s['players'][2]['morale'],73)
        self.assertEqual(migrate(s),s);self.assertEqual(morale.public(s)['players'][self.p['id']]['trend'],'Collecting history')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.sqlite';save(s,path);self.assertEqual(load(path),s)
        s['day']=14;morale.reconcile(s);self.assertEqual(s['players'][2]['morale'],50);validate(s)
