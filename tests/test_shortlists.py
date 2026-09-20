"""Named lists remain private, durable and independent of football state."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from club_chairman.simulation import Command, execute, new_career, validate, view
from club_chairman.persistence import load, save, migrate
from club_chairman.planning import player_rows
from club_chairman.shortlists import active


class ShortlistTests(unittest.TestCase):
    def setUp(self):self.s=new_career(73)

    def act(self,action,**payload):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,payload))

    def test_independent_lists_roundtrip_and_no_simulation_effect(self):
        before=deepcopy(self.s)
        self.act('planning',key='shortlist',value=['p144'])
        self.act('shortlist_manage',operation='create',name='Summer targets')
        new_id=active(self.s['planning'])['id']
        self.act('planning',key='shortlist',value=['p144','p145'])
        self.act('shortlist_manage',operation='rename',id=new_id,name='First-team options')
        self.act('shortlist_manage',operation='select',id='list-0')
        self.assertEqual(self.s['planning']['shortlist'],['p144'])
        self.act('shortlist_manage',operation='select',id=new_id)
        self.assertEqual(self.s['planning']['shortlist'],['p144','p145'])
        for key in before:
            if key not in ('planning','revision','receipts'):self.assertEqual(self.s[key],before[key],key)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'save.sqlite3';save(self.s,path);self.assertEqual(self.s,load(path))
        snap=view(self.s);snap['planning']['shortlists']['items'][0]['players'].clear()
        self.assertEqual(self.s['planning']['shortlists']['items'][0]['players'],['p144'])

    def test_rejections_leave_entire_state_unchanged(self):
        for name in ('',' ', 'x'*33,'bad\nname','SHORTLIST',None,42):
            before=deepcopy(self.s)
            with self.assertRaises(ValueError):self.act('shortlist_manage',operation='create',name=name)
            self.assertEqual(self.s,before)
        for operation in ('rename','delete','select','invalid'):
            with self.assertRaises(ValueError):self.act('shortlist_manage',operation=operation,id='missing',name='Name')
        with self.assertRaises(ValueError):self.act('shortlist_manage',operation='delete',id='list-0')
        for i in range(19):self.act('shortlist_manage',operation='create',name=f'Targets {i}')
        before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('shortlist_manage',operation='create',name='Overflow')
        self.assertEqual(before,self.s)

    def test_delete_exact_undo_and_idempotence(self):
        self.act('shortlist_manage',operation='create',name='Goalkeepers')
        self.act('planning',key='shortlist',value=['p144'])
        old=deepcopy(self.s['planning']['shortlists'])
        cmd=Command('delete-once',self.s['revision'],'shortlist_manage',dict(operation='delete',id='list-1'))
        self.s,_=execute(self.s,cmd)
        again,_=execute(self.s,cmd);self.assertEqual(again,self.s)
        self.assertEqual(self.s['planning']['shortlist'],[])
        self.act('planning',key='shortlists',value=old)
        self.assertEqual(self.s['planning']['shortlists'],old)
        self.assertEqual(self.s['planning']['shortlist'],['p144'])
        old['items'][0]['players']=['missing']
        with self.assertRaises(ValueError):self.act('planning',key='shortlists',value=old)

    def test_schema_ten_preserves_original_bytes_and_every_prior_field(self):
        old=deepcopy(self.s);old['schema']=10;old['planning'].pop('shortlists')
        old['planning']['shortlist']=['p144','p145']
        raw=json.dumps(old)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'old.sqlite3'
            with sqlite3.connect(path) as db:
                db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE entities(id TEXT,payload TEXT);')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','10'),('checksum',hashlib.sha256(raw.encode()).hexdigest())])
                db.execute('INSERT INTO entities VALUES (?,?)',('world',raw))
            original=path.read_bytes();new=load(path)
            self.assertEqual(original,path.read_bytes())
            self.assertEqual(active(new['planning'])['players'],['p144','p145'])
            restored=deepcopy(new);restored['schema']=10;restored['planning'].pop('shortlists')
            self.assertEqual(old,restored)
            self.assertEqual(migrate(new),new)
        broken=deepcopy(new);broken['planning']['shortlist']=[]
        with self.assertRaises(ValueError):validate(broken)
        broken=deepcopy(new);broken['planning']['shortlists']['active']='missing'
        with self.assertRaises(ValueError):validate(broken)

    def test_links_survive_transfer_retirement_and_do_not_leak_ratings(self):
        self.act('planning',key='shortlist',value=['p0','p144','p145'])
        snap=view(self.s)
        next(p for p in snap['players'] if p['id']=='p144').update(retired=True,club=None)
        next(p for p in snap['players'] if p['id']=='p145')['club']='c4'
        rows=player_rows(snap,True,only_shortlist=True,market_scope='Free agents')
        self.assertEqual({p['id'] for p in rows},{'p0','p144','p145'})
        self.assertNotIn('attrs',json.dumps(rows))
        self.assertIsNone(next(p for p in rows if p['id']=='p144')['report'])
