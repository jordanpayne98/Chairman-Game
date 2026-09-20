"""Division boundaries, sporting outcomes and persistent season ownership."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import leagues, competitions
from club_chairman.persistence import save, load
from club_chairman.simulation import new_career, validate, execute, Command, close_season, table


def completed_world():
    s=new_career(42)
    # Deliberately relegate c0, with transparent results in both divisions.
    for f in s['fixtures']:
        if f.get('knockout'):continue
        winner=f['away'] if f['home']=='c0' else f['home']
        f['result']={'score':[2,0] if winner==f['home'] else [0,2]}
        for side,cid in enumerate((f['home'],f['away'])):
            c=next(c for c in s['clubs'] if c['id']==cid)
            gf,ga=f['result']['score'][side],f['result']['score'][1-side]
            c['played']+=1;c['gf']+=gf;c['ga']+=ga
            c['won' if gf>ga else 'lost']+=1;c['points']+=3 if gf>ga else 0
            c['form'].append('W' if gf>ga else 'L')
    while not competitions.complete(s):
        for f in s['fixtures']:
            if f.get('knockout') and f['result'] is None:
                f['result']={'score':[1,0],'winner':f['home']}
        competitions.progress(s)
    s['day']=96;close_season(s);validate(s)
    return s


class DivisionTests(unittest.TestCase):
    def test_schedules_world_and_original_identities(self):
        s=new_career(42);ds=s['leagues']['divisions']
        self.assertEqual([len(d['members']) for d in ds],[8,8])
        self.assertEqual(len(s['players']),300)
        self.assertEqual(s['players'][144]['id'],'p144');self.assertIsNone(s['players'][144]['club'])
        self.assertEqual([sum(f.get('division')==d['id'] for f in s['fixtures']) for d in ds],[56,56])
        self.assertEqual(len(s['competitions']['cup']['rounds'][0]['entrants']),16)
        self.assertEqual(len(table(s)),8);validate(s)

    def test_relegation_conserves_clubs_contracts_and_settles_correct_prizes_once(self):
        s=completed_world();old=deepcopy(s);moves=s['leagues']['movements']
        self.assertEqual(len(moves),6)
        self.assertEqual(next(m['kind'] for m in moves if m['club']=='c0'),'Relegated')
        self.assertEqual(leagues.division_for(s)['tier'],1)
        close_season(s);self.assertEqual(s,old)
        self.assertEqual([e['amount'] for e in s['ledger'] if e['reason']=='League prize'],[1000000])
        for d in s['leagues']['divisions']:
            for i,c in enumerate(s['leagues']['final_tables'][d['id']]):
                if c['id']=='c0':continue
                awards=[e['amount'] for e in s['market']['accounts'][c['id']]['ledger'] if e['reason']=='League prize']
                self.assertEqual(awards,[d['prizes'][i]])
        cmd=Command('relegate',s['revision'],'next_season',{})
        s,_=execute(s,cmd);self.assertEqual(execute(s,cmd)[0],s)
        self.assertEqual(leagues.division_for(s)['tier'],2)
        self.assertEqual(leagues.division_for(s)['prizes'][-1],500000)
        self.assertEqual({c['id'] for c in s['clubs']},{c['id'] for c in old['clubs']})
        self.assertEqual([len(d['members']) for d in s['leagues']['divisions']],[8,8])
        for p in old['players'][:18]:
            new=next(n for n in s['players'] if n['id']==p['id'])
            for key in ('club','contract_end','wage'):self.assertEqual(p[key],new[key])
        for key in ('cash','ledger','staff','reports','planning'):self.assertEqual(s[key],old[key],key)
        h=s['career']['history'][0];self.assertEqual(h['leagues']['movements'],moves)
        self.assertEqual(h['table'],old['leagues']['final_tables']['northshire-1'])
        self.assertTrue(all(f.get('division')=='northshire-2' for f in s['fixtures'] if not f.get('knockout') and 'c0' in (f['home'],f['away'])))
        self.assertEqual(len(s['competitions']['cup']['rounds'][0]['entrants']),16)
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'divisions.sqlite3';save(s,p);self.assertEqual(load(p),s)
        validate(s)

    def test_head_to_head_then_recorded_draw_and_save_roundtrip(self):
        s=new_career(42);d=s['leagues']['divisions'][0]
        self.assertEqual([c['id'] for c in leagues.standings(s,d)],s['leagues']['draw_order'][d['id']])
        # Equal overall points/GD/GF, but c0 won their direct encounter.
        for c in s['clubs']:
            if c['id'] in ('c0','c1'):c.update(points=3,gf=2,ga=2)
        f=next(f for f in s['fixtures'] if f.get('division')==d['id'] and f['home']=='c0' and f['away']=='c1')
        f['result']={'score':[2,0]}
        rows=leagues.standings(s,d);self.assertEqual([c['id'] for c in rows[:2]],['c0','c1'])
        full=completed_world()
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'finished.sqlite3';save(full,path);restored=load(path)
        self.assertEqual(leagues.snapshot(restored),leagues.snapshot(full))

    def test_corrupt_membership_cross_division_fixture_and_frozen_movement_rejected(self):
        s=new_career(42)
        broken=deepcopy(s);broken['leagues']['divisions'][1]['members'][0]='c0'
        with self.assertRaises(ValueError):validate(broken)
        broken=deepcopy(s);broken['fixtures'][0]['away']='c8'
        with self.assertRaises(ValueError):validate(broken)
        broken=deepcopy(s);broken['clubs'][0].update(points=3,won=1,played=1)
        with self.assertRaises(ValueError):validate(broken)
        broken=completed_world();broken['leagues']['movements'][0]['target']='northshire-1'
        with self.assertRaises(ValueError):validate(broken)
