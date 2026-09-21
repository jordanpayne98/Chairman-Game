from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from club_chairman import football,manager_selection,managers,registration
from club_chairman.simulation import new_career,execute,Command,view,validate,record_result
from club_chairman.persistence import migrate,save,load


class ManagerSelectionTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42)
        self.s,_=execute(self.s,Command('hire',0,'hire',{'id':'m0'}))
        self.s['manager']['preferences'].update(formation='4-4-2',rotation='Balanced',youth='Readiness first')
        self.fixture=next(f for f in self.s['fixtures'] if f['home']=='c0')
    def choose(self):return manager_selection.choose(self.s,'c0',self.fixture['away'])
    def player(self,pid):return next(p for p in self.s['players'] if p['id']==pid)
    def equalise(self):
        for p in self.s['players']:
            if p['club']=='c0' and not p['youth']:
                p['attrs']={k:60 for k in p['attrs']};p.update(condition=100,fatigue=0,age=26)

    def test_shortage_adapts_shape_without_rewriting_preference(self):
        for pid in ('p15','p16','p17'):self.player(pid)['injury_until']=30
        self.s['manager']['capabilities'].update(tactical_judgement=80,adaptability=90)
        ids,bench,plan=self.choose()
        self.assertEqual(plan['formation'],'4-5-1');self.assertEqual(plan['selected_roles'],dict(GK=1,DEF=4,MID=5,FWD=1))
        self.assertEqual(plan['preferred'],'4-4-2');self.assertEqual(self.s['manager']['preferences']['formation'],'4-4-2')
        self.assertEqual(len(set(ids+bench)),len(ids+bench))
        self.assertTrue(all(not registration.reason(self.s,self.player(pid),'c0',self.fixture['away']) for pid in ids+bench))
        self.s['manager']['capabilities']['adaptability']=10
        self.assertEqual(self.choose()[2]['formation'],'4-4-2')
        self.s['manager']['capabilities'].update(adaptability=90,tactical_judgement=10)
        self.assertEqual(self.choose()[2]['formation'],'4-4-2')

    def test_working_shape_is_retained_and_ineligible_players_never_selected(self):
        self.s['manager']['capabilities'].update(tactical_judgement=100,adaptability=100)
        self.assertEqual(self.choose()[2]['formation'],'4-4-2')
        self.player('p2')['discipline']['ban']=1;self.s['registration']['c0'].remove('p3')
        ids,bench,_=self.choose();self.assertNotIn('p2',ids+bench);self.assertNotIn('p3',ids+bench)
        self.s['manager']['preferences']['formation']='4-3-3'
        self.assertEqual(self.choose()[2]['selected_roles']['FWD'],3)

    def test_rotation_changes_real_choice_and_recent_history_expires(self):
        self.equalise();a=self.player('p14');b=self.player('p15');c=self.player('p16')
        self.s['manager']['preferences']['formation']='4-5-1'
        # Small ability advantage trades off against freshness; no arbitrary reroll.
        a['attrs']={k:62 for k in a['attrs']};a['fatigue']=10
        self.assertIn(a['id'],self.choose()[0])
        self.s['manager']['preferences']['rotation']='Fresh legs'
        self.assertIn(b['id'],self.choose()[0]);self.assertNotIn(a['id'],self.choose()[0])
        self.equalise();self.s['manager']['preferences']['rotation']='Continuity'
        self.fixture['result']={'lineups':[[c['id']],[]]};self.s['day']=self.fixture['day']+1
        self.assertIn(c['id'],self.choose()[0])
        self.fixture['result']['forfeit']=True;self.assertIn(a['id'],self.choose()[0])
        self.fixture['result']['forfeit']=False
        self.s['day']+=15;self.assertIn(a['id'],self.choose()[0])

    def test_youth_preference_rewards_readiness_without_reading_potential(self):
        self.equalise();self.s['manager']['preferences'].update(formation='4-5-1',youth='Develop prospects')
        self.s['manager']['capabilities']['youth_development']=100
        young=self.player('p17');young['age']=19
        self.assertIn(young['id'],self.choose()[0])
        self.assertEqual(self.choose()[2]['reasons'][young['id']],'ready prospect')
        before=self.choose();young['potential']=100
        self.assertEqual(before,self.choose())
        young['attrs']={k:40 for k in young['attrs']}
        self.assertNotIn(young['id'],self.choose()[0])

    def test_saved_selection_is_frozen_through_substitutions_and_resume(self):
        self.s['match']=football.start(self.s,self.fixture);m=self.s['match'];plan=deepcopy(m['selection_plans'])
        for _ in range(27):football.step(self.s,m)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'match.sqlite3';save(self.s,path);resumed=load(path)
        for state in (self.s,resumed):
            while not football.finished(state['match']):football.step(state,state['match'])
        self.assertEqual(self.s,resumed);self.assertEqual(m['selection_plans'],plan)
        record_result(self.s,m);self.assertEqual(self.fixture['result']['selection_plans'],plan)
        self.s['manager']['preferences']['formation']='3-5-2'
        self.assertEqual(self.fixture['result']['selection_plans'],plan)

    def test_migration_preserves_old_preferences_match_and_snapshot_truth(self):
        self.s['match']=football.start(self.s,self.fixture)
        old=deepcopy(self.s);old['schema']=16;old['config']['managers'].pop('selection');old['match'].pop('selection_plans')
        for p in old['managers']['people']+[old['manager']]:
            p['preferences'].pop('rotation');p['preferences'].pop('youth');p['preferences']['formation']='4-4-2'
        before=deepcopy(old);up=migrate(old);self.assertEqual(before,old)
        self.assertEqual(up['match'],old['match']);self.assertEqual(up['manager']['capabilities'],old['manager']['capabilities'])
        self.assertEqual(up['manager']['preferences']['formation'],'4-4-2')
        self.assertEqual(migrate(up),up)
        before=json.dumps(self.s,sort_keys=True);self.choose();view(self.s)
        self.assertEqual(before,json.dumps(self.s,sort_keys=True))
        self.s['config']['managers']['selection']['youth_bonus']=100
        with self.assertRaisesRegex(ValueError,'Unbounded manager selection'):validate(self.s)


if __name__=='__main__':unittest.main()
