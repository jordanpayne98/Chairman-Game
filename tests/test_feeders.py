"""Feeder movement is sporting, persistent, conservative and playable."""
from contextlib import closing
from copy import deepcopy
import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from club_chairman import feeders,leagues,competitions,career,market,detail
from club_chairman.persistence import save,load,migrate
from club_chairman.simulation import new_career,execute,Command,validate,close_season,start_match,view


def act(s,action,**payload):
    return execute(s,Command('feeder:'+str(s['revision']),s['revision'],action,payload))[0]


def place_owner(s,division_id):
    source=leagues.division_for(s);target=next(d for d in s['leagues']['divisions'] if d['id']==division_id)
    other=target['members'][0];source['members'][source['members'].index('c0')]=other;target['members'][0]='c0'
    detail.synchronise(s)
    leagues.prepare_order(s);leagues.schedule(s);competitions.start_season(s);validate(s)
    return s


def finish(s,owner_wins=False):
    # Explicit sporting boundary fixture, not a substitute for engine tests.
    for f in s['fixtures']:
        if f.get('knockout'):continue
        home_wins=True
        if 'c0' in (f['home'],f['away']):home_wins=(f['home']=='c0')==owner_wins
        f['result']={'score':[2,0] if home_wins else [0,2]}
        for side,cid in enumerate((f['home'],f['away'])):
            c=next(c for c in s['clubs'] if c['id']==cid);gf,ga=f['result']['score'][side],f['result']['score'][1-side]
            c['played']+=1;c['gf']+=gf;c['ga']+=ga;c['won' if gf>ga else 'lost']+=1
            c['points']+=3 if gf>ga else 0;c['form'].append('W' if gf>ga else 'L')
    while not competitions.complete(s):
        for f in s['fixtures']:
            if f.get('knockout') and f['result'] is None:f['result']={'score':[1,0],'winner':f['home']}
        competitions.progress(s)
    s['day']=career.season_end(s);close_season(s);validate(s)
    return s


class FeederTests(unittest.TestCase):
    def test_all_pools_have_persistent_detail_and_recovery_safe_results_graph(self):
        for nation,total,count in (('england',100,3),('wales',24,2),('brazil',54,2)):
            s=new_career(19,nation);pool=s['leagues']['divisions'][-1]
            self.assertTrue(pool['supporting']);self.assertEqual(len(pool['members']),8)
            self.assertEqual(s['leagues']['exchange'],count)
            self.assertEqual(len(leagues.primary_members(s)),total)
            self.assertFalse(set(pool['members']) & set(s['competitions']['cup']['entrants']))
            for cid in pool['members']:
                self.assertEqual(sum(p['club']==cid for p in s['players']),18)
                self.assertEqual(sum(p['club']==cid for p in s['staff']['people']),3)
                self.assertIn(cid,s['market']['accounts']);self.assertEqual(len(s['registration'][cid]),18)
                fs=[f for f in s['fixtures'] if cid in (f['home'],f['away'])]
                self.assertEqual(len(fs),14)
                dates=sorted(f['day'] for f in fs);self.assertTrue(all(b-a>=3 for a,b in zip(dates,dates[1:])))
                self.assertEqual(dates[-1],s['calendar']['league_days'][-1])
            self.assertEqual(s,new_career(19,nation));validate(s)
        with self.assertRaisesRegex(ValueError,'No validated feeder'):feeders.definition('usa')

    def test_relegation_and_return_preserve_people_money_history_and_cup_eligibility(self):
        s=place_owner(new_career(19,'wales'),'wales-2');s=finish(s)
        pool=s['leagues']['divisions'][-1];ids={c['id'] for c in s['clubs']}
        promoted=[m['club'] for m in s['leagues']['movements'] if m['source']==pool['id']]
        self.assertEqual(len(promoted),2)
        self.assertEqual(next(m['target'] for m in s['leagues']['movements'] if m['club']=='c0'),pool['id'])
        old=deepcopy(s);close_season(s);self.assertEqual(old,s)
        s=act(s,'next_season')
        self.assertTrue(leagues.division_for(s)['supporting']);self.assertNotIn('c0',s['competitions']['cup']['entrants'])
        self.assertEqual([len(d['members']) for d in s['leagues']['divisions']],[12,12,8])
        self.assertEqual(ids,{c['id'] for c in s['clubs']})
        self.assertTrue(set(promoted)<=set(s['competitions']['cup']['entrants']))
        for key in ('players','staff','market','cash','ledger','reports','planning'):
            self.assertEqual(s[key],old[key],key)
        self.assertEqual(s['career']['history'][0]['leagues']['movements'],old['leagues']['movements'])
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'relegated.sqlite3';save(s,path);self.assertEqual(load(path),s)
        s=finish(s,owner_wins=True);s=act(s,'next_season')
        self.assertEqual(leagues.division_for(s)['id'],'wales-2');self.assertIn('c0',s['competitions']['cup']['entrants'])
        self.assertEqual(ids,{c['id'] for c in s['clubs']});self.assertEqual(len(s['career']['history']),2)
        self.assertEqual(len([x for x in s['ledger'] if x['reason']=='League prize']),2)
        for cid in ids-{'c0'}:
            self.assertEqual(len([x for x in s['market']['accounts'][cid]['ledger'] if x['reason']=='League prize']),2)
        validate(s)

    def test_real_pool_match_resumes_identically_and_existing_debt_is_retained(self):
        s=place_owner(new_career(19,'wales'),'wales-regional')
        s=act(s,'hire',id='m0')
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']))
        self.assertEqual(f['division'],'wales-regional')
        s['day']=f['day']-1;s=act(s,'continue')
        self.assertEqual(s['match']['fixture'],f['id'])
        s=act(s,'match_step',minutes=27)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'poolmatch.sqlite3';save(s,path);loaded=load(path)
        self.assertEqual(act(s,'match_skip'),act(loaded,'match_skip'))
        # Debt belongs to the club, independent of movement across the boundary.
        s=finish(place_owner(new_career(19,'wales'),'wales-2'))
        s['market']['obligations'].append(dict(id='retained-bill',player='p20',source='c0',target='c24',amount=125000,due=s['day']+7,status='scheduled'))
        before=deepcopy(s['market']);after=act(s,'next_season');self.assertEqual(after['market'],before)
        after['day']+=7;market.process_day(after)
        self.assertEqual(after['market']['obligations'][0]['status'],'paid')
        self.assertEqual(after['market']['accounts']['c24']['cash'],before['accounts']['c24']['cash']+125000)

    def test_invalid_pool_membership_and_cup_entries_are_rejected(self):
        s=new_career(19,'wales')
        mutations=(lambda b:b['leagues']['divisions'][-1]['members'].__setitem__(0,'c0'),
                   lambda b:b['config']['feeder'].__setitem__('parent','wales-1'),
                   lambda b:b['competitions']['cup']['entrants'].__setitem__(0,'c24'),
                   lambda b:b['config']['feeder']['clubs'][0].__setitem__('name','Changed identity'),
                   lambda b:b['config']['feeder']['clubs'][0].__setitem__('id','missing'))
        for mutation in mutations:
            broken=deepcopy(s);mutation(broken)
            with self.assertRaises(ValueError):validate(broken)
        cfg=feeders.definition('wales');cfg['clubs'][1]['name']=cfg['clubs'][0]['name']
        with patch('club_chairman.feeders.definition',return_value=cfg):
            with self.assertRaisesRegex(ValueError,'unique'):new_career(19,'wales')

    def test_old_national_save_keeps_its_original_structure_and_bytes(self):
        # Use the same constructor with expansion suppressed to represent 0.13.
        with patch('club_chairman.feeders.initialise'):
            old=new_career(19,'wales')
        old['schema']=11;old.pop('detail');old['config'].pop('detail');raw=json.dumps(old)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'old.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE entities(id TEXT,payload TEXT);')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','11'),('checksum',hashlib.sha256(raw.encode()).hexdigest())])
                db.execute('INSERT INTO entities VALUES (?,?)',('world',raw));db.commit()
            original=path.read_bytes();new=load(path)
            self.assertEqual(path.read_bytes(),original);self.assertEqual(new['schema'],16)
            self.assertEqual(len(new['clubs']),24);self.assertNotIn('feeder',new['config'])
            restored=deepcopy(new);restored['schema']=11;restored.pop('detail');restored['config'].pop('detail');self.assertEqual(restored,old)
            self.assertEqual(migrate(new),new)
            new=finish(new);new=act(new,'next_season');self.assertEqual(len(new['clubs']),24)
