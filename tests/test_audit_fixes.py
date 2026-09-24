from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from club_chairman import career, clauses, scouting
from club_chairman.persistence import save, load
from club_chairman.simulation import new_career, execute, Command, view, payroll
from test_leagues import completed_world


class AuditFixTests(unittest.TestCase):
    def test_travel_uses_club_location_not_passport(self):
        s=new_career(42);p=career.person(s,'p20')
        p['nationality']='Antigua and Barbuda'
        local=scouting.quote(s,p)
        p['nationality']='England'
        self.assertEqual(local,scouting.quote(s,p))
        self.assertFalse(local['remote'])
        club=next(c for c in s['clubs'] if c['id']==p['club']);club['nation']='japan'
        remote=scouting.quote(s,p)
        self.assertTrue(remote['remote']);self.assertEqual(remote['location_nation'],'japan')
        self.assertEqual(remote['cost'],local['cost']*2)
        self.assertEqual(remote['due'],local['due']+3)

    def test_free_agent_location_and_committed_quote_survive_save(self):
        s=new_career(42);p=career.person(s,'p144')
        p['nationality']='England';p['location_nation']='japan'
        s,_=execute(s,Command('scout-remote',s['revision'],'scout',{'id':p['id']}))
        job=deepcopy(s['scouting_work']['jobs'][-1])
        self.assertTrue(job['remote'])
        career.person(s,p['id'])['location_nation']='england'
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'quote.sqlite3';save(s,path);s=load(path)
        self.assertEqual(s['scouting_work']['jobs'][-1],job)
        s['day']=job['due'];scouting.process_day(s)
        self.assertEqual(s['reports'][p['id']]['context'],'Travel assessment')
        self.assertEqual(s['reports'][p['id']]['job'],job['id'])

    def test_unknown_location_does_not_invent_a_passport_surcharge(self):
        s=new_career(42);p=career.person(s,'p144');p.pop('location_nation')
        p['nationality']='Japan';quote=scouting.quote(s,p)
        self.assertIsNone(quote['location_nation']);self.assertFalse(quote['remote'])
        scouting.commission(s,p['id']);s['day']=quote['due'];scouting.process_day(s)
        self.assertEqual(s['reports'][p['id']]['context'],'Base assessment; location unrecorded')

    def test_owned_retirement_rollover_preserves_identity_debts_and_resume(self):
        s=completed_world();p=career.person(s,'p2');p['age']=36;p['birth_day']=s['day']-36*365
        p['appearances']=9;p['goals']=2
        clauses.sign(s,p,dict(id='retirement-contract',end=p['contract_end'],appearance_bonus=1200,club_option=True))
        clauses.record_match(s,dict(home='c0',away='c1',fixture='retirement-earned',lineups=[['p2'],[]],events=[]))
        bills=deepcopy(s['clauses']['payables']);cash=s['cash'];before_payroll=payroll(s);wage=p['wage'];name=p['name']
        command=Command('retirement-rollover',s['revision'],'next_season',{})
        s,_=execute(s,command);p=career.person(s,'p2')
        self.assertTrue(p['retired']);self.assertIsNone(p['club']);self.assertEqual(p['name'],name)
        self.assertEqual((p['career_appearances'],p['career_goals']),(9,2))
        self.assertEqual(p['retirement']['club'],'c0');self.assertNotIn('p2',s['registration']['c0'])
        self.assertNotIn('p2',s['clauses']['employment']);self.assertEqual(s['clauses']['payables'],bills)
        self.assertEqual(s['cash'],cash);self.assertEqual(payroll(s),before_payroll-wage)
        self.assertEqual(sum(n['title']=='Player retirement' for n in s['inbox']),1)
        self.assertEqual(execute(s,command)[0],s)
        once=deepcopy(s);career.retire_player(s,p);self.assertEqual(s,once)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'retirement.sqlite3';save(s,path);s=load(path)
        self.assertEqual(s,once)
        row=next(p for p in view(s)['players'] if p['id']=='p2')
        self.assertEqual(row['availability'],'Retired');self.assertEqual(row['retirement']['club'],'c0')
        self.assertIsNone(row['scout_quote'])
        clauses.settle_payables(s);paid=s['cash'];clauses.settle_payables(s)
        self.assertEqual(s['cash'],paid);self.assertEqual(paid,cash-1200)
        with self.assertRaises(ValueError):execute(s,Command('retired-enquiry',s['revision'],'enquire',{'id':'p2'}))

    def test_retirement_threshold_is_configurable_and_shared_with_rivals(self):
        s=completed_world();s['config']['career']['retirement_age']=37
        for pid in ('p2','p20'):
            p=career.person(s,pid);p['age']=36;p['birth_day']=s['day']-36*365
        s,_=execute(s,Command('below-retirement',s['revision'],'next_season',{}))
        self.assertFalse(career.person(s,'p2')['retired']);self.assertFalse(career.person(s,'p20')['retired'])
        s=completed_world()
        for pid in ('p2','p20'):
            p=career.person(s,pid);p['age']=36;p['birth_day']=s['day']-36*365
        s,_=execute(s,Command('at-retirement',s['revision'],'next_season',{}))
        self.assertTrue(career.person(s,'p2')['retired']);self.assertTrue(career.person(s,'p20')['retired'])


if __name__=='__main__':unittest.main()
