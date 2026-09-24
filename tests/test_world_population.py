from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from club_chairman import career,identities,people,staff,world_population as wp
from club_chairman.simulation import new_career,execute,Command,view,validate
from club_chairman.persistence import save,load,migrate


def small_world():
    cfg=deepcopy(identities.catalogue());cfg['nations']=[n for n in cfg['nations'] if n['id'] in ('england','japan')]
    for n in cfg['nations']:n['clubs']=2
    s=dict(seed=42,day=0,config={'world_population':cfg},world_population=dict(claimed=[],last_day=0))
    s['world_population']['blob']=wp.build(42,0,json.dumps(cfg,sort_keys=True),'',0);wp.manifest(s)
    return s


class WorldPopulationTests(unittest.TestCase):
    def test_employed_move_preserves_identity_and_balances_both_clubs(self):
        s=small_world();db=deepcopy(wp.unpack(s['world_population']['blob']))
        clubs=sorted(db['clubs']);seller,buyer=clubs[:2]
        source=next(p for p in db['people'].values() if p['club']==buyer and p['role']=='DEF' and p['group']=='Seniors')
        # Create a vacancy and surplus without generating or replacing anyone.
        source['club']=seller
        source['history'].append(dict(day=0,event='Prior move',club=seller))
        # Make this identity the best fit; stature now creates different club levels.
        wp.set_attributes(source,{k:db['clubs'][buyer]['level'] for k in people.ATTRIBUTES})
        source['potential']=max(source['potential'],wp.overall(source))
        for candidate in db['people'].values():
            if candidate['club']==seller and candidate['id']!=source['id'] and candidate['kind']=='player' and candidate['role']=='DEF':
                wp.set_attributes(candidate,{k:10 for k in people.ATTRIBUTES})
        db['clubs'][buyer]['cash']+=5000000;db['clubs'][buyer]['opening_cash']+=5000000
        db['clubs'][buyer]['payroll_limit']+=5000000
        db['people'][source['id']]=source
        roster={cid:[p for p in db['people'].values() if p['club']==cid] for cid in clubs}
        chosen_seed=None
        for seed in range(500):
            s['seed']=seed
            trial=deepcopy(db);teams={cid:[trial['people'][p['id']] for p in roster[cid]] for cid in clubs}
            events={'transfers':0}
            wp._employed_moves(s,trial,teams,30,events)
            if trial['people'][source['id']]['club']==buyer:
                chosen_seed=seed;break
        self.assertIsNotNone(chosen_seed,'A funded surplus-to-vacancy move should be possible')
        blocked=deepcopy(db);blocked['clubs'][buyer]['cash']=0
        blocked_teams={cid:[p for p in blocked['people'].values() if p['club']==cid] for cid in clubs}
        wp._employed_moves(s,blocked,blocked_teams,30,{'transfers':0})
        self.assertEqual(blocked['people'][source['id']]['club'],seller)
        self.assertFalse(any(e.get('transfer') for c in blocked['clubs'].values() for e in c['ledger']))
        no_cover=deepcopy(db);no_cover['people'][source['id']]['club']=None
        no_cover_teams={cid:[p for p in no_cover['people'].values() if p['club']==cid] for cid in clubs}
        wp._employed_moves(s,no_cover,no_cover_teams,30,{'transfers':0})
        self.assertFalse(any(e.get('transfer') for c in no_cover['clubs'].values() for e in c['ledger']))
        s['seed']=chosen_seed;s['world_population']['blob']=wp.pack(db);wp.manifest(s)
        s['day']=30;wp.process_day(s)
        moved=wp.unpack(s['world_population']['blob']);person=moved['people'][source['id']]
        self.assertEqual(person['id'],source['id'])
        transfer=next(e for e in person['history'] if e['event']=='Transferred')
        self.assertEqual((transfer['from_club'],transfer['club']),(seller,buyer))
        fee=transfer['fee'];self.assertGreater(fee,0)
        self.assertTrue(any(e.get('person')==source['id'] and e['transfer']==-fee for e in moved['clubs'][buyer]['ledger']))
        self.assertTrue(any(e.get('person')==source['id'] and e['transfer']==fee for e in moved['clubs'][seller]['ledger']))
        self.assertGreaterEqual(s['world_population']['manifest']['recent_cycles'][-1]['transfers'],1)
        # The player might appear on a later browser page; the search name is
        # public identity, never the private attribute or potential record.
        page=next(i for i in range(100) if any(r['id']==source['id'] for r in wp.search(s,person['nation_id'],page=i)['rows']))
        row=next(r for r in wp.search(s,person['nation_id'],page=page)['rows'] if r['id']==source['id'])
        self.assertIn(moved['clubs'][seller]['name'],next(h['summary'] for h in row['history'] if h['event']=='Transferred'))
        self.assertNotIn('ratings',json.dumps(row));self.assertNotIn('potential',json.dumps(row))
        wp.validate_database(s)
        restored=deepcopy(s)
        restored['day']+=30;s['day']+=30
        wp.process_day(restored);wp.process_day(s)
        self.assertEqual(restored['world_population'],s['world_population'])

    def test_catalogue_and_complete_persistent_population(self):
        s=new_career();cfg=identities.definition(s);db=wp.unpack(s['world_population']['blob'])
        self.assertEqual(len(cfg['nations']),239);self.assertEqual(len(cfg['names']),68)
        self.assertEqual(sum(n['clubs'] for n in cfg['nations'] if n['playable']),636)
        self.assertEqual(len(db['clubs']),1086)
        expected=sum(c['stature']['squad_size']+cfg['settings']['youth_target']+cfg['settings']['reserve_target']+len(c['stature']['roles']) for c in db['clubs'].values())+len(cfg['nations'])*(cfg['settings']['free_players_per_nation']+cfg['settings']['free_staff_per_nation'])
        self.assertEqual(len(db['people']),expected)
        self.assertEqual(len({r['id'] for r in db['people'].values()}),expected)
        self.assertTrue(all(c['players'] and c['staff'] for c in s['world_population']['manifest']['counts'].values()))
        self.assertFalse(identities.nation(s,'japan')['playable']);wp.validate_database(s)
        before=s['world_population']['blob'];rows=wp.search(s,'japan')['rows']
        self.assertTrue(rows);self.assertEqual(before,s['world_population']['blob'])
        public=json.dumps(rows);self.assertNotIn('ratings',public);self.assertNotIn('potential',public);self.assertNotIn('hidden',public)

    def test_seeded_identity_independent_of_traits_and_survives_regeneration(self):
        s=new_career();s2=deepcopy(s)
        p=career.new_person(s,'FWD',14,35,'cohort:test',True)
        s2['config'].pop('world_population');q=career.new_person(s2,'FWD',14,35,'cohort:test',True)
        for k in ('attrs','hidden','potential','birth_day','id'):self.assertEqual(p[k],q[k],k)
        self.assertEqual(p['name'],identities.make(s,p['id'])['name'])
        names=[identities.make(s,'identity:'+str(i),nationality='japan') for i in range(100)]
        self.assertGreater(len({x['name'] for x in names}),50)
        self.assertTrue(all(x['name']==x['family_name']+' '+x['given_name'] for x in names))
        self.assertEqual(names,[identities.make(s,'identity:'+str(i),nationality='japan') for i in range(100)])
        self.assertNotEqual(names,[identities.make(dict(s,seed=43),'identity:'+str(i),nationality='japan') for i in range(100)])

    def test_development_decline_retirement_and_cash_continue_without_matches(self):
        s=small_world();db=deepcopy(wp.unpack(s['world_population']['blob']))
        young=next(r for r in db['people'].values() if r['group']=='Youth' and r['role']=='MID')
        older=next(r for r in db['people'].values() if r['group']=='Seniors' and r['club'] and r['role']=='DEF')
        retire=next(r for r in db['people'].values() if r['kind']=='staff' and r['club'])
        young.update(birth_day=-14*365,potential=99,professionalism=100)
        older['birth_day']=-34*365;retire['birth_day']=-70*365
        initial=deepcopy(db);s['world_population']['blob']=wp.pack(db);wp.manifest(s)
        s['day']=360;wp.process_day(s);db=wp.unpack(s['world_population']['blob'])
        self.assertGreater(wp.overall(db['people'][young['id']]),wp.overall(initial['people'][young['id']]))
        self.assertLess(wp.attributes(db['people'][older['id']])['pace'],wp.attributes(initial['people'][older['id']])['pace'])
        s['day']=390;wp.process_day(s);db=wp.unpack(s['world_population']['blob'])
        self.assertEqual(db['people'][retire['id']]['status'],'retired')
        self.assertEqual(db['people'][retire['id']]['name'],retire['name'])
        self.assertGreater(sum(c['intakes'] for c in db['cycles']),0)
        wp.validate_database(s)
        again=deepcopy(s);wp.process_day(s);self.assertEqual(s,again)

    def test_long_term_new_entries_exits_and_resume_are_deterministic(self):
        s=small_world();other=deepcopy(s);original=deepcopy(wp.unpack(s['world_population']['blob']))
        s['day']=365*5;wp.process_day(s)
        for day in range(30,365*5+1,30):other['day']=day;wp.process_day(other)
        self.assertEqual(s['world_population'],other['world_population'])
        db=wp.unpack(s['world_population']['blob']);self.assertTrue(set(original['people'])<=set(db['people']))
        self.assertGreater(sum(c['staff_entries'] for c in db['cycles']),0)
        self.assertGreater(sum(c['inactive_exits'] for c in db['cycles']),0)
        self.assertGreater(sum(c['signings'] for c in db['cycles']),0)
        self.assertGreater(sum(c['expiries'] for c in db['cycles']),0)
        self.assertLess(sum(r['status']=='active' for r in db['people'].values()),len(original['people'])*2)
        for r in db['people'].values():
            if r['id'] not in original['people']:
                self.assertIn(r['history'][0]['event'],('Career entry','Regional staff entry'))
                self.assertEqual(r['name'],identities.make(s,r['id'],nationality=r['nation_id'],domestic=r['nation_id'])['name'])
        self.assertTrue(all(c['intakes']<=4*6 for c in db['cycles']))
        wp.validate_database(s)

    def test_activation_preserves_player_staff_and_save_identity(self):
        s=new_career();db=wp.unpack(s['world_population']['blob'])
        for kind in ('player','staff'):
            source=next(r for r in db['people'].values() if r['kind']==kind and r['club'] is None and r['nation_id']=='japan')
            s,_=execute(s,Command('activate:'+kind,s['revision'],'world_person_activate',{'id':source['id']}))
            p=next(p for p in (s['players'] if kind=='player' else s['staff']['people']) if p['id']==source['id'])
            for k in ('name','nationality','birth_day'):self.assertEqual(p[k],source[k])
            actual=p['attrs'] if kind=='player' else p['capabilities']
            self.assertEqual(wp.attributes(source),{k:actual[k] for k in wp.attributes(source)})
            if kind=='player':
                self.assertEqual(p['hidden'],source['hidden']);self.assertEqual(p['potential'],source['potential'])
                row=next(r for r in view(s)['players'] if r['id']==p['id']);self.assertIsNone(row['report'])
            else:self.assertEqual(p['risk'],source['risk']);self.assertIsNone(staff.observed_assessment(s,p))
            with self.assertRaises(ValueError):wp.activate(s,source['id'])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'world.sqlite3';save(s,path);restored=load(path)
        self.assertEqual(s,restored);validate(restored)
        for state in (s,restored):state['day']=30;wp.process_day(state)
        self.assertEqual(s,restored)

    def test_legacy_migration_does_not_create_or_rename_and_staff_retirement_after_activation(self):
        old=new_career();old['schema']=28;old.pop('world_population');old['config'].pop('world_population')
        before=deepcopy(old);up=migrate(old)
        self.assertEqual(old,before);self.assertEqual(old['players'],up['players']);self.assertEqual(old['staff'],up['staff'])
        self.assertIsNone(up['world_population']['blob']);self.assertEqual(up,migrate(up))
        wp.enable(up);p=next(r for r in wp.unpack(up['world_population']['blob'])['people'].values() if r['kind']=='staff' and not r['club'])
        wp.activate(up,p['id']);person=staff.person(up,p['id']);person['birth_day']=-70*365
        up['day']=365;staff.process_day(up)
        self.assertTrue(person['retired']);self.assertIsNone(person['club'])
        with self.assertRaises(ValueError):staff.apply(up,'staff_contact',{'id':p['id']})


if __name__=='__main__':unittest.main()
