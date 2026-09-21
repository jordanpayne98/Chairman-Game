from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from club_chairman import people
from club_chairman.simulation import Command, execute, new_career, view, validate
from club_chairman.persistence import load, save
from club_chairman.planning import player_rows


class CurrentAbilityTests(unittest.TestCase):
    def setUp(self):self.s=new_career(42)

    def row(self,p):return next(x for x in view(self.s)['players'] if x['id']==p['id'])

    def act(self,action,**data):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))

    def test_club_access_tracks_actual_development_without_rewriting_evidence(self):
        p=self.s['players'][2];stored=deepcopy(self.s['reports'][p['id']])
        p['attrs']['passing']=60.5
        r=self.row(p)['report']
        self.assertEqual(r['ranges']['passing'],[61,61])
        self.assertEqual(r['overall'],[people.overall(p)]*2)
        self.assertTrue(r['exact_current']);self.assertEqual(r['knowledge'],'Club access')
        self.s['day']=84;p['attrs']['passing']=62.49
        r=self.row(p)['report'];self.assertEqual(r['ranges']['passing'],[62,62])
        self.assertFalse(r['stale']);self.assertTrue(r['forecast_stale'])
        self.assertNotEqual(*r['potential']);self.assertEqual(stored,self.s['reports'][p['id']])
        before=deepcopy(self.s);view(self.s);self.assertEqual(before,self.s)
        self.s['reports'].pop(p['id']);self.assertEqual(self.row(p)['report']['knowledge'],'Club access')
        self.assertNotIn('potential',self.row(p)['report'])

    def test_commission_delivers_full_coverage_then_expires_to_frozen_evidence(self):
        self.act('hire',id='m0');self.act('scout',id='p144')
        due=self.s['scouting']['p144']
        while self.s['day']<due:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')
        p=next(p for p in self.s['players'] if p['id']=='p144')
        stored=deepcopy(self.s['reports'][p['id']]);r=self.row(p)['report']
        self.assertEqual(r['knowledge'],'Fully scouted');self.assertTrue(r['exact_current'])
        self.assertEqual(r['overall'],[people.overall(p)]*2)
        self.s['day']=stored['coverage_until']-1;p['attrs']['passing']=50.5
        self.assertEqual(self.row(p)['report']['ranges']['passing'],[51,51])
        self.s['day']+=1;r=self.row(p)['report']
        self.assertEqual(r['knowledge'],'Stale');self.assertFalse(r['exact_current'])
        self.assertNotEqual(*r['ranges']['passing'])
        p['attrs']['passing']=99;p['potential']=100
        self.assertEqual(r,self.row(p)['report']);self.assertEqual(stored,self.s['reports'][p['id']])
        # Hiring grants live access; leaving does not retain it after coverage expiry.
        p['club']='c0';self.assertEqual(self.row(p)['report']['ranges']['passing'],[99,99])
        p['club']=None;self.assertEqual(r,self.row(p)['report'])

    def test_partial_unknown_and_hidden_fields_are_invariant(self):
        p=self.s['players'][144];unknown=self.row(p)
        p['attrs']['passing']=99;p['potential']=100
        self.assertEqual(unknown,self.row(p))
        self.s['reports'][p['id']]=people.report(self.s,p,'Partial observation',6)
        partial=self.row(p);self.assertEqual(partial['report']['knowledge'],'Partial')
        p['attrs']['passing']=10;p['potential']=80
        self.assertEqual(partial,self.row(p))
        self.s['reports'][p['id']]=people.report(self.s,p,'Completed assignment',6,complete=True)
        full=self.row(p)
        p['potential']=100;p['hidden']={k:100 for k in people.HIDDEN}
        self.assertEqual(full,self.row(p))
        raw=json.dumps(full)
        for secret in ('potential_code','professionalism','injury_susceptibility','peak_overall','"attrs"'):
            self.assertNotIn(secret,raw)

    def test_sorting_uses_authorised_exact_values_and_partial_midpoints(self):
        a,b=self.s['players'][144:146]
        a['attrs']['passing']=80.5;b['attrs']['passing']=40
        for p in (a,b):self.s['reports'][p['id']]=people.report(self.s,p,'Assignment',9,complete=True)
        rows=player_rows(view(self.s),True,sort='Passing',descending=True)
        self.assertEqual([p['id'] for p in rows[:2]],[a['id'],b['id']])
        a['attrs']['passing']=20
        rows=player_rows(view(self.s),True,sort='Passing',descending=True)
        self.assertEqual([p['id'] for p in rows[:2]],[b['id'],a['id']])
        self.s['day']=28;ordered=player_rows(view(self.s),True,sort='Passing',descending=True)
        a['attrs']['passing']=99;b['attrs']['passing']=1
        self.assertEqual(ordered,player_rows(view(self.s),True,sort='Passing',descending=True))

    def test_save_roundtrip_and_schema13_preserve_evidence_and_original_bytes(self):
        p=self.s['players'][144]
        self.s['reports'][p['id']]=people.report(self.s,p,'Assignment',9,complete=True)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'new.sqlite3';save(self.s,path)
            self.assertEqual(self.s,load(path));self.assertEqual(view(self.s),view(load(path)))
            old=deepcopy(self.s);old['schema']=13;old['config']['people'].pop('full_coverage_days')
            for r in old['reports'].values():r.pop('knowledge',None);r.pop('coverage_until',None)
            path=Path(root)/'old.sqlite3';raw=json.dumps(old)
            with sqlite3.connect(path) as db:
                db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE entities(id TEXT,payload TEXT);')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','13'),('checksum',hashlib.sha256(raw.encode()).hexdigest())])
                db.execute('INSERT INTO entities VALUES (?,?)',('world',raw))
            original=path.read_bytes();loaded=load(path);self.assertEqual(path.read_bytes(),original)
            self.assertEqual(loaded['reports'],old['reports'])
            self.assertEqual(next(x for x in view(loaded)['players'] if x['id']==p['id'])['report']['knowledge'],'Partial')
            loaded['schema']=13;loaded['config']['people'].pop('full_coverage_days')
            self.assertEqual(old,loaded)

    def test_invalid_coverage_rejected(self):
        self.s['config']['people']['full_coverage_days']=0
        with self.assertRaisesRegex(ValueError,'coverage'):validate(self.s)
        self.s['config']['people']['full_coverage_days']=28
        self.s['reports']['p144']=dict(day=0,knowledge='Fully scouted',coverage_until=0)
        with self.assertRaisesRegex(ValueError,'coverage'):validate(self.s)
