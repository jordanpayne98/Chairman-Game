"""Regression checks for planning without advancing or leaking the simulation."""
from copy import deepcopy
from contract_support import prepare_signings
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from club_chairman.simulation import Command, execute, new_career, view
from club_chairman.persistence import load, save
from club_chairman.planning import dated, forecast, player_rows, signing_terms


class PlanningTests(unittest.TestCase):
    def setUp(self):self.s=new_career(73)

    def act(self,action,**payload):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,payload))

    def advance(self,day):
        while self.s['day']<day or self.s['match']:
            if self.s['match']:
                self.act('match_skip') if not self.s['match'].get('finished',self.s['match']['minute']>=90) else self.act('match_close')
            elif self.s['decision']:self.act('decision',choice='decline')
            else:self.act('continue')

    def test_planning_persists_and_changes_no_football_or_money(self):
        old=deepcopy(self.s)
        self.act('planning',key='shortlist',value=['p144'])
        self.act('planning',key='comparison',value=['p144','p145'])
        self.act('planning',key='notes',value={'p144':'Check wages before signing'})
        self.act('planning',key='inbox_read',value=1)
        for key in ('day','cash','ledger','players','fixtures','trust','morale','supporters'):
            self.assertEqual(old[key],self.s[key],key)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'save.sqlite3';save(self.s,path);self.assertEqual(load(path),self.s)
        for key,value in [('comparison',['p144']*2),('comparison',[f'p{i}' for i in range(144,149)]),('shortlist',['p999']),('notes',{'p144':'x'*241}),('inbox_read',5)]:
            with self.assertRaises(ValueError):self.act('planning',key=key,value=value)

    def test_schema_one_midmatch_upgrade_preserves_original_and_rng(self):
        self.act('hire',id='m0');self.advance(4);self.act('continue');self.act('match_step',minutes=17)
        old=deepcopy(self.s);old['schema']=1;old.pop('planning')
        raw=json.dumps(old)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'old.sqlite3'
            db=sqlite3.connect(path)
            try:
                db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE entities(id TEXT,payload TEXT);')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','1'),('checksum',hashlib.sha256(raw.encode()).hexdigest())])
                db.execute('INSERT INTO entities VALUES (?,?)',('world',raw));db.commit()
            finally:db.close()
            original=path.read_bytes();upgraded=load(path)
            self.assertEqual(path.read_bytes(),original);self.assertEqual(upgraded['schema'],17)
            original_finish,_=execute(self.s,Command('end',self.s['revision'],'match_skip',{}))
            loaded_finish,_=execute(upgraded,Command('end',upgraded['revision'],'match_skip',{}))
            for key in ('fixtures','cash','clubs','players','ledger'):
                self.assertEqual(original_finish[key],loaded_finish[key])

    def test_sorting_uses_reports_and_keeps_unknowns_last(self):
        for pid,rating in [('p144',30),('p145',60)]:
            self.s['reports'][pid]={'confidence':'Low','source':'Test report','day':0,'ranges':{k:[rating-5,rating+5] for k in ('passing','finishing','tackling','goalkeeping')}}
        snap=view(self.s)
        ordered=player_rows(snap,True,sort='Passing',descending=True)
        self.assertEqual([p['id'] for p in ordered[:2]],['p145','p144'])
        self.assertTrue(all(p['report'] is None for p in ordered[2:]))
        for p in self.s['players']:
            p['attrs']={k:100-v for k,v in p['attrs'].items()}
        self.assertEqual(ordered,player_rows(view(self.s),True,sort='Passing',descending=True))
        self.assertEqual(player_rows(snap,True,role='GK')[0]['role'],'GK')
        self.assertEqual(player_rows(snap,True,search='does not exist'),[])
        self.assertNotIn('attrs',json.dumps(ordered))

    def test_forecast_reconciles_actual_settlements_including_partial_week(self):
        # Remove only uncertain gate receipts; the cash settlement schedule stays real.
        self.s['config']['capacity']=0
        self.act('budget',value=4000000);self.act('hire',id='m0');self.advance(4)
        prepare_signings(self,['p144','p145'])
        snap=view(self.s);players=[p for p in snap['players'] if p['id'] in ('p144','p145')]
        before=deepcopy(snap);planned=forecast(snap,players,horizon=25)
        self.assertEqual(snap,before)
        for p in players:self.act('complete_offer',id=p['id'])
        self.advance(31)
        self.assertEqual(planned['cash'],self.s['cash'])
        self.assertEqual(planned['accrued'],self.s['accrued_costs']//7)
        self.assertEqual(planned['cash'],planned['low']);self.assertEqual(planned['cash'],planned['high'])
        late=forecast(view(self.s),horizon=100)
        self.advance(96)
        prize=next(e['amount'] for e in self.s['ledger'] if e['id']=='season:prize')
        self.assertEqual(late['cash'],self.s['cash']-prize)
        self.assertEqual(late['accrued'],0)
        self.assertEqual(forecast(view(self.s))['cash'],self.s['cash'])

    def test_combined_plan_detects_budget_and_retains_signed_pins(self):
        self.act('hire',id='m0')
        v=view(self.s);players=[p for p in v['players'] if p['club'] is None][:4]
        t=signing_terms(v,players)
        self.assertIn('Exceeds the weekly wage limit',t['reasons'])
        self.assertEqual(t['fee'],sum(p['fee'] for p in players))
        self.act('planning',key='comparison',value=[p['id'] for p in players])
        self.act('budget',value=4000000);prepare_signings(self,[players[0]['id']]);self.act('complete_offer',id=players[0]['id'])
        v=view(self.s);selected=[p for p in v['players'] if p['id'] in v['planning']['comparison']]
        self.assertEqual(len(selected),4);self.assertEqual(signing_terms(v,selected)['count'],3)

    def test_configured_calendar_and_scouting_terms(self):
        self.s['config'].update(start_date='2027-01-11',scout_fee=98700,scout_days=2)
        self.act('hire',id='m0');self.act('scout',id='p144')
        v=view(self.s)
        self.assertEqual(dated(v,5),'16 Jan 2027')
        self.assertEqual(v['terms']['scout_fee'],98700)
        self.assertEqual(v['terms']['scout_days'],2)
        self.assertEqual(self.s['scouting']['p144'],2)
        self.assertEqual(self.s['ledger'][-1]['amount'],-98700)
        self.advance(2);self.assertIn('p144',self.s['reports'])
