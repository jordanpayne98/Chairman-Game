import json
from contract_support import prepare_signings
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from club_chairman.simulation import Command, execute, new_career, view, validate, payroll
from club_chairman.persistence import save, load, SaveError, SaveStore


class CareerTests(unittest.TestCase):
    def setUp(self):self.s=new_career(42)
    def act(self,action,**payload):
        self.s,message=execute(self.s,Command(f"test:{self.s['revision']}",self.s['revision'],action,payload))
        return message
    def manager(self):self.act('budget',value=4000000);self.act('hire',id='m0')
    def match(self):
        self.manager()
        while not self.s['match']:
            if self.s['decision']:self.act('decision',choice='decline')
            self.act('continue')

    def test_invalid_command_is_atomic(self):
        before=json.dumps(self.s,sort_keys=True)
        with self.assertRaises(ValueError):self.act('sign',id='p144')
        self.assertEqual(before,json.dumps(self.s,sort_keys=True))

    def test_duplicate_and_stale_commands(self):
        c=Command('hire',0,'hire',{'id':'m0'})
        self.s,_=execute(self.s,c)
        cash=self.s['cash'];revision=self.s['revision']
        self.s,_=execute(self.s,c)
        self.assertEqual(cash,self.s['cash']);self.assertEqual(revision,self.s['revision'])
        with self.assertRaises(ValueError):execute(self.s,Command('stale',0,'continue',{}))
        with self.assertRaises(ValueError):execute(self.s,Command('hire',0,'fund',{}))

    def test_scouting_and_signing(self):
        self.manager();self.act('scout',id='p144')
        self.assertNotIn('p144',self.s['reports'])
        for _ in range(3):self.act('continue')
        self.assertIn('p144',self.s['reports'])
        old=payroll(self.s);p=next(p for p in self.s['players'] if p['id']=='p144')
        prepare_signings(self,['p144'])
        agreed=self.s['career']['offers']['p144']['wage']
        self.act('complete_offer',id='p144');self.assertEqual(payroll(self.s),old+agreed)
        with self.assertRaises(ValueError):self.act('sign',id='p144')
        validate(self.s)

    def test_view_never_exposes_hidden_attributes(self):
        snap=view(self.s)
        self.assertTrue(all('attrs' not in p for p in snap['players']))
        self.assertTrue(all(p['report'] is None for p in snap['players'] if p['club'] is None))
        raw=json.dumps(snap)
        self.assertNotIn('rng',raw);self.assertNotIn('skill',raw)

    def test_required_decision_stops_continue(self):
        self.manager()
        for _ in range(3):self.act('continue')
        with self.assertRaises(ValueError):self.act('continue')
        self.assertEqual(self.s['day'],3)
        self.act('decision',choice='decline');self.act('continue');self.assertEqual(self.s['day'],4)

    def test_owner_funding_conserves_combined_cash(self):
        total=self.s['cash']+self.s['owner_cash']
        self.act('fund');self.assertEqual(total,self.s['cash']+self.s['owner_cash']);validate(self.s)

    def test_live_skip_and_saved_resume_are_identical(self):
        self.match();self.act('match_step',minutes=22);self.act('intervene',choice='attack')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'save.sqlite3';save(self.s,path);saved=load(path)
        skipped,_=execute(self.s,Command('skip',self.s['revision'],'match_skip',{}))
        while not saved['match'].get('finished',saved['match']['minute']>=90):
            saved,_=execute(saved,Command(f"step:{saved['revision']}",saved['revision'],'match_step',{'minutes':1}))
        for key in ('fixtures','cash','ledger','clubs','players'):
            self.assertEqual(skipped[key],saved[key],key)

    def test_complete_season_integrity(self):
        self.manager()
        while not self.s['season_done']:
            if self.s['decision']:self.act('decision',choice='approve')
            elif self.s['match']:
                if not self.s['match'].get('finished',self.s['match']['minute']>=90):self.act('match_skip')
                else:self.act('match_close')
            else:self.act('continue')
        self.assertTrue(all(c['played']==14 for c in self.s['clubs']))
        self.assertEqual(len([f for f in self.s['fixtures'] if f['result']]),56)
        self.assertEqual(sum(c['gf'] for c in self.s['clubs']),sum(c['ga'] for c in self.s['clubs']))
        self.assertEqual(len([e for e in self.s['ledger'] if e['id']=='season:prize']),1)
        for f in self.s['fixtures']:
            self.assertEqual(sum(f['result']['score']),sum(e['kind']=='goal' for e in f['result']['events']))
        with self.assertRaises(ValueError):self.act('match_skip')
        validate(self.s)

    def test_backup_and_failed_replace_preserve_manual(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'manual.sqlite3';save(self.s,path);original=path.read_bytes()
            self.act('fund');save(self.s,path)
            self.assertEqual(path.with_suffix('.backup.sqlite3').read_bytes(),original)
            current=path.read_bytes();self.act('fund')
            with patch('club_chairman.persistence.os.replace',side_effect=OSError('disk full')):
                with self.assertRaises(SaveError):save(self.s,path)
            self.assertEqual(path.read_bytes(),current)
            path.write_bytes(b'broken')
            with self.assertRaises(SaveError):load(path)
            with self.assertRaises(SaveError):save(self.s,path)
            self.assertEqual(path.read_bytes(),b'broken')
            self.assertEqual(load(path.with_suffix('.backup.sqlite3'))['cash'],new_career(42)['cash'])

    def test_three_autosave_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            store=SaveStore(temp)
            for i in range(6):self.act('tickets',value=1000+i*200);store.autosave(self.s)
            self.assertEqual(len(list(Path(temp).glob('*/auto[123].sqlite3'))),3)
            self.assertTrue(all(e['valid'] for e in store.entries()))

if __name__=='__main__':unittest.main()
