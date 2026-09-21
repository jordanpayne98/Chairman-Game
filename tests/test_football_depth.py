from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from club_chairman import football, people, registration
from club_chairman.simulation import new_career, execute, Command, view, validate, record_result
from club_chairman.persistence import save, load


class FootballDepthTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(247)

    def act(self,action,**data):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))

    def start(self):
        self.act('hire',id='m0')
        while not self.s['match']:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')

    def play_direct(self,state=None,fixture=None):
        s=state or self.s;m=football.start(s,fixture or s['fixtures'][0])
        for _ in range(400):
            if football.finished(m):break
            football.step(s,m)
        self.assertTrue(football.finished(m))
        return m

    def test_attribute_catalogue_potential_and_training_are_persistent(self):
        self.assertEqual(len(people.ATTRIBUTES),37)
        self.assertEqual(len(set(people.ATTRIBUTES)),37)
        for p in self.s['players']:
            self.assertLessEqual(people.overall(p),p['potential'])
            self.assertTrue(set(people.ATTRIBUTES)<=set(p['attrs']))
        self.act('development_plan',id='p2',focus='Technical',load='Light')
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'people.sqlite3';save(self.s,path);self.assertEqual(self.s,load(path))
        original=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('development_plan',id='p20',focus='Technical',load='Intense')
        self.assertEqual(original,self.s)

    def test_scout_refresh_staleness_and_views_do_not_reveal_truth(self):
        p=self.s['players'][145]
        self.s['reports'][p['id']]=people.report(self.s,p,'Test observer',9)
        self.s['day']=56
        older=view(self.s);row=next(x for x in older['players'] if x['id']==p['id'])
        self.assertTrue(row['report']['stale'])
        self.assertGreater(row['report']['ranges']['passing'][1],self.s['reports'][p['id']]['ranges']['passing'][1])
        for person in self.s['players']:
            if person['club']=='c0':continue
            person['potential']=100;person['hidden']={k:100 for k in people.HIDDEN}
            for key in people.ATTRIBUTES:person['attrs'][key]=99
        self.assertEqual(older,view(self.s))
        raw=json.dumps(older)
        for secret in ('potential_code','professionalism','injury_susceptibility','peak_overall','"attrs"'):
            self.assertNotIn(secret,raw)

    def test_live_skip_and_saved_resume_match_with_stoppage_cards_and_subs(self):
        self.start();base=deepcopy(self.s)
        self.act('match_skip');skipped=deepcopy(self.s)
        self.assertGreater(self.s['match']['minute'],90)
        self.assertTrue(any(e['kind']=='substitution' for e in self.s['match']['events']))
        self.s=base;self.act('match_step',minutes=45)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'halftime.sqlite3';save(self.s,path);self.s=load(path)
        while not football.finished(self.s['match']):self.act('match_step',minutes=1)
        for key in ('players','fixtures','cash','ledger','clubs','clauses'):
            self.assertEqual(self.s[key],skipped[key],key)
        before=deepcopy(self.s);record_result(self.s,self.s['match']);self.assertEqual(before,self.s)

    def test_ineligible_players_never_selected_and_bans_serve_once(self):
        p0,p2,p3=self.s['players'][0],self.s['players'][2],self.s['players'][3]
        p0['injury_until']=20;p2['discipline']['ban']=2
        self.s['registration']['c0'].remove(p3['id'])
        self.start();m=self.s['match']
        self.assertFalse({'p0','p2','p3'}&set(m['on_pitch'][0]+m['bench'][0]))
        self.act('match_skip');self.assertEqual(self.s['players'][2]['discipline']['ban'],1)
        before=deepcopy(self.s);record_result(self.s,self.s['match']);self.assertEqual(before,self.s)

    def test_dismissed_and_substituted_players_have_no_later_actions(self):
        self.s['config']['football'].update(foul_rate=.22,yellow_rate=.65,red_rate=.04)
        m=self.play_direct();left={}
        for e in m['events']:
            for key in ('player','against'):
                if key in e and e['kind'] not in ('red','yellow','injury_exit'):
                    self.assertNotIn(e[key],left,(e,left))
            if e['kind']=='red':left[e['player']]=e['minute']
            if e['kind']=='substitution':left[e['off']]=e['minute']
        self.assertTrue(left)
        self.assertEqual(sum(m['score']),sum(e['kind']=='goal' for e in m['events']))

    def test_injury_forces_removal_and_recovery_is_dated(self):
        self.s['config']['football']['injury_rate']=1
        m=self.play_direct();injured={e['player'] for e in m['events'] if e['kind']=='injury'}
        self.assertTrue(injured)
        self.assertFalse(injured&set(sum(m['on_pitch'],[])))
        for pid in injured:
            p=next(p for p in self.s['players'] if p['id']==pid)
            self.assertGreater(p['injury_until'],self.s['day'])
            self.assertEqual(registration.reason(self.s,p,p['club']),'Injured')
        self.s['day']=40;people.process_day(self.s)
        self.assertTrue(all(p['condition']<=100 for p in self.s['players']))

    def test_registration_limit_and_draft_failures_are_atomic(self):
        self.s['config']['competition']['senior_limit']=18
        for p in self.s['players']:p['age']=25;p['birth_day']=-25*365
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):registration.check_arrival(self.s,self.s['players'][144],'c0')
        self.assertEqual(before,self.s)
        self.act('registration_submit',players=[f'p{i}' for i in range(17)])
        registration.check_arrival(self.s,self.s['players'][144],'c0')
        self.assertEqual(self.s['players'][17]['club'],'c0')
        self.assertEqual(registration.reason(self.s,self.s['players'][17],'c0'),'Not on competition list')
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('registration_submit',players=['p0']*8)
        self.assertEqual(before,self.s)

    def test_parent_club_restriction_and_return_do_not_overwrite_list(self):
        p=self.s['players'][20];p['club']='c0'
        self.s['market']['loans'].append(dict(id='fixture-loan',player=p['id'],source='c1',target='c0',status='active',start=0,end=20,share=100,fee=0))
        registration.sync(self.s)
        self.assertEqual(registration.reason(self.s,p,'c0','c1'),'Loan: cannot face parent club')
        self.assertIsNone(registration.reason(self.s,p,'c0','c2'))
        self.assertNotIn(p['id'],sum(football.select(self.s,'c1','c0'),[]))

    def test_extra_time_and_shootout_resume_has_one_winner(self):
        m=football.start(self.s,dict(self.s['fixtures'][0],knockout=True))
        m.update(phase='extra_second',phase_minute=15,phase_length=15,added=1,added_announced=True,score=[0,0])
        self.s['config']['football'].update(actions_per_minute=0)
        football.step(self.s,m);self.assertEqual(m['phase'],'shootout')
        football.step(self.s,m);resumed=json.loads(json.dumps(m));s2=deepcopy(self.s)
        while not football.finished(m):football.step(self.s,m)
        while not football.finished(resumed):football.step(s2,resumed)
        self.assertEqual(m['events'],resumed['events']);self.assertEqual(m['winner'],resumed['winner'])
        self.assertEqual(m['score'],[0,0]);self.assertNotEqual(*m['shootout'])
        self.assertFalse(any(e['kind']=='goal' for e in m['events']))

    def test_severe_availability_crisis_awards_fixture_without_deadlock(self):
        for p in self.s['players'][:18]:p['injury_until']=20
        self.start()
        self.assertTrue(football.finished(self.s['match']))
        self.assertTrue(self.s['match']['settled'])
        self.assertEqual(self.s['match']['score'],[0,3])
        self.assertEqual(self.s['match']['winner'],self.s['match']['away'])
        self.assertFalse(self.s['match']['participants'][0])
        self.act('match_close');self.act('continue');validate(self.s)

    def test_potential_cannot_reroll_by_plan_or_report_and_reviews_are_bounded(self):
        p=self.s['players'][10];p['age']=20;p['birth_day']=-20*365
        old=p['potential']
        for day in range(1,366):
            self.s['day']=day
            if day%7==0:p['development']['minutes']=90
            people.process_day(self.s)
            if day%14==0:people.report(self.s,p,'Repeated observer',5)
        self.assertLessEqual(p['potential']-old,3)
        self.assertTrue(all(abs(r['change'])<=1 for r in p['development']['reviews']))
        self.assertGreaterEqual(p['potential'],people.overall(p))


if __name__=='__main__':unittest.main()
