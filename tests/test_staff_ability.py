from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from club_chairman import staff,delegation
from club_chairman.simulation import new_career,execute,Command,view,validate
from club_chairman.persistence import load,save,migrate


class StaffAbilityTests(unittest.TestCase):
    def setUp(self):self.s=new_career(83)
    def p(self):return staff.person(self.s,'staff:0:0')
    def row(self):return next(p for p in view(self.s)['staff']['people'] if p['id']=='staff:0:0')
    def act(self,action,**data):self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))

    def test_eleven_capabilities_absolute_role_rating_and_live_access(self):
        self.assertEqual(len(staff.CAPABILITIES),11)
        self.assertTrue(all(set(p['capabilities'])==set(staff.CAPABILITIES) for p in self.s['staff']['people']))
        p=self.p();p.update(club='c0',start=0,end=300)
        p['capabilities'].update(people_management=60,financial_control=61)
        r=self.row()['assessment'];self.assertEqual(r['overall'],[61,61]);self.assertEqual(r['role'],'Executive')
        self.assertEqual(r['knowledge'],'Club access');self.assertTrue(r['exact_current'])
        p['capabilities']['adaptability']=71.5
        self.assertEqual(self.row()['assessment']['ranges']['adaptability'],[72,72])
        # Organisation, salary and workload change effectiveness, not underlying CA.
        p.update(reputation=99,workload=100,wage=200000)
        self.assertEqual(self.row()['assessment']['overall'],[61,61])
        p['capabilities']['financial_control']=80
        self.assertEqual(self.row()['assessment']['overall'],[70,70])
        p['club']=None;self.assertIsNone(self.row()['assessment'])

    def test_partial_full_expired_and_renewed_coverage_preserve_snapshots(self):
        self.act('hire',id='m0');self.act('staff_contact',id='staff:0:0')
        r=self.row()['assessment'];self.assertEqual(r['knowledge'],'Partial')
        p=self.p();p['capabilities']['coaching']=99;p['risk']='Ambitious'
        self.assertEqual(r,self.row()['assessment'])
        self.act('continue');self.act('staff_interview',id='staff:0:0')
        stored=deepcopy(self.s['staff']['assessments']['staff:0:0']);r=self.row()['assessment']
        self.assertEqual(r['knowledge'],'Fully assessed');self.assertEqual(r['ranges']['coaching'],[99,99])
        p=self.p();p['capabilities']['coaching']=87
        self.s['day']=stored['coverage_until']-1;self.assertEqual(self.row()['assessment']['ranges']['coaching'],[87,87])
        self.s['day']+=1;r=self.row()['assessment'];self.assertEqual(r['knowledge'],'Stale')
        p['capabilities']['coaching']=1;self.assertEqual(r,self.row()['assessment'])
        self.assertEqual(stored,self.s['staff']['assessments']['staff:0:0'])
        staff.assess(self.s,p,6,complete=True);self.assertEqual(self.row()['assessment']['ranges']['coaching'],[1,1])
        self.assertEqual(self.row()['assessment']['knowledge'],'Fully assessed')

    def test_pending_hire_does_not_grant_club_access_and_start_does(self):
        self.act('hire',id='m0');self.act('budget',value=4000000)
        self.act('staff_contact',id='staff:0:0');self.act('continue');self.act('staff_interview',id='staff:0:0')
        self.act('staff_propose',id='staff:0:0',wage=self.p()['expected_wage']*12//10,duration=2)
        self.act('staff_accept',id='staff:0:0')
        self.assertEqual(self.row()['assessment']['knowledge'],'Fully assessed')
        start=self.p()['pending']['start']
        while self.s['day']<start:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')
        self.assertEqual(self.row()['assessment']['knowledge'],'Club access')
        self.s['day']=100;self.assertEqual(self.row()['assessment']['knowledge'],'Club access')
        before=deepcopy(self.s);view(self.s);self.assertEqual(before,self.s)
        self.p()['risk']='Cautious';r=self.row();self.assertNotIn('risk',r);self.assertNotIn('capabilities',r)

    def test_old_assessment_remains_partial_and_migration_is_additive(self):
        old=deepcopy(self.s);old['schema']=14
        for key in ('weights','full_coverage_days'):old['config']['staff'].pop(key)
        for p in old['staff']['people']:p['capabilities'].pop('adaptability')
        old['staff']['assessments']['staff:0:0']=dict(day=0,source='Legacy interview',ranges={'coaching':[35,45]})
        raw=json.dumps(old)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'old.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE entities(id TEXT,payload TEXT);')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','14'),('checksum',hashlib.sha256(raw.encode()).hexdigest())])
                db.execute('INSERT INTO entities VALUES (?,?)',('world',raw));db.commit()
            original=path.read_bytes();self.s=load(path);self.assertEqual(path.read_bytes(),original)
            self.assertEqual(self.row()['assessment']['knowledge'],'Partial')
            self.assertNotIn('adaptability',self.row()['assessment']['ranges']);self.assertNotIn('overall',self.row()['assessment'])
            self.assertEqual(migrate(self.s),self.s)
            fresh=Path(root)/'new.sqlite3';save(self.s,fresh);self.assertEqual(load(fresh),self.s)
        restored=deepcopy(self.s);restored['schema']=14
        for key in ('weights','full_coverage_days'):restored['config']['staff'].pop(key)
        for p in restored['staff']['people']:p['capabilities'].pop('adaptability')
        self.assertEqual(restored,old)

    def test_confirmed_coverage_matches_live_preview_despite_old_reports(self):
        for pid,actual,old in (('staff:0:0',95,10),('staff:1:0',20,90)):
            p=staff.person(self.s,pid);p.update(club='c0',start=0,end=300)
            p['capabilities']={key:actual for key in staff.CAPABILITIES}
            self.s['staff']['assessments'][pid]=dict(day=0,source='Old references',ranges={key:[old,old] for key in staff.CAPABILITIES})
        preview=delegation.cover_plan(view(self.s))
        self.assertEqual(preview['recruitment'],'staff:0:0')
        self.assertEqual(preview,delegation.cover_plan(self.s))
        self.act('delegation_cover')
        self.assertEqual(preview,{key:r['delegate'] for key,r in self.s['delegation']['responsibilities'].items() if r['delegate']})

    def test_role_weights_validate_and_hidden_changes_cannot_change_unknowns(self):
        before=self.row();p=self.p();p['capabilities']={k:100 for k in staff.CAPABILITIES};p['risk']='Cautious'
        self.assertEqual(before,self.row())
        self.assertEqual(staff.rating(self.s,p),100)
        for bad in ({'coaching':-.1,'operations':1.1},{'coaching':float('nan')},{'unknown':1},{'coaching':.9}):
            s=deepcopy(self.s);s['config']['staff']['weights']['Executive']=bad
            with self.assertRaisesRegex(ValueError,'weights'):validate(s)
        self.s['config']['staff']['full_coverage_days']=0
        with self.assertRaisesRegex(ValueError,'coverage'):validate(self.s)

    def test_coverage_planner_uses_live_known_skills_without_changing_state(self):
        a,b=self.s['staff']['people'][:2]
        for p in (a,b):p.update(club='c0',start=0,end=300)
        a['capabilities']['ability_assessment']=99;b['capabilities']['ability_assessment']=1
        first=delegation.cover_plan(view(self.s));self.assertEqual(first['recruitment'],a['id'])
        a['capabilities']['ability_assessment']=1;b['capabilities']['ability_assessment']=99
        before=deepcopy(self.s);second=delegation.cover_plan(view(self.s))
        self.assertEqual(second['recruitment'],b['id']);self.assertEqual(before,self.s)
