from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from club_chairman import dynamics as dyn, football, relationships
from club_chairman.simulation import new_career,execute,Command,view,validate
from club_chairman.persistence import save,load,migrate


class DynamicsTests(unittest.TestCase):
    def setUp(self):self.s=new_career(42)

    def train(self,day=1):
        self.s['day']=day;dyn.process_day(self.s)

    def match(self):
        self.s,_=execute(self.s,Command('hire',self.s['revision'],'hire',{'id':'m0'}))
        f=next(f for f in self.s['fixtures'] if 'c0' in (f['home'],f['away']))
        self.s['day']=f['day'];self.s['match']=football.start(self.s,f)
        return self.s['match']

    def test_contact_is_evidence_based_idempotent_and_not_ability_or_mood(self):
        before=deepcopy(self.s);self.assertIsNone(dyn.group(self.s,'c0')['value'])
        self.train();d=deepcopy(self.s['dynamics']);dyn.process_day(self.s);self.assertEqual(d,self.s['dynamics'])
        self.assertTrue(d['links']);self.assertEqual(before['players'],self.s['players'])
        self.assertEqual(before['preparation'],self.s['preparation']);self.assertEqual(before['mood'],self.s['mood'])
        for r in d['links'].values():self.assertEqual(r['sessions'],1)
        changed=deepcopy(self.s)
        for p in changed['players']:p['reputation']=100;p['wage']*=10;p['attrs']={k:100 for k in p['attrs']}
        self.assertEqual(dyn.public(self.s),dyn.public(changed))

    def test_settling_departures_injuries_and_no_fabricated_history(self):
        p=self.s['players'][2];p['injury_until']=10
        self.train();self.assertFalse(any(r['source']==p['id'] for r in self.s['dynamics']['links'].values()))
        p['club']='c1';dyn.sync(self.s)
        self.assertFalse(self.s['dynamics']['members'][p['id']]['settled'])
        self.assertNotIn(p['id'],[r['id'] for r in dyn.public(self.s)['players']])
        self.assertEqual(self.s['dynamics']['members'][p['id']]['days'],0)
        self.assertEqual(dyn.public(self.s)['summary']['trend'],'Not comparable')

    def test_same_day_return_and_departure_keep_distinct_events(self):
        p=self.s['players'][2]
        for cid in ('c1','c0','c1'):
            p['club']=cid;dyn.sync(self.s)
        events=self.s['dynamics']['events']
        self.assertEqual(len(events),3)
        self.assertEqual(len({e['id'] for e in events}),3)
        dyn.validate(self.s)

    def test_departure_order_does_not_depend_on_saved_dictionary_order(self):
        a=deepcopy(self.s);b=deepcopy(self.s)
        b['dynamics']['members']=dict(reversed(list(b['dynamics']['members'].items())))
        for world in (a,b):
            for p in world['players']:
                if p['id'] in ('p2','p10','p12'):p['club']=None
            dyn.sync(world)
        self.assertEqual(a['dynamics'],b['dynamics'])

    def test_participant_specific_bounded_edges_and_departed_influence(self):
        a,b,c=dyn.roster(self.s,'c0')[:3]
        for _ in range(100):dyn.contact(self.s,'c0',a,b,2)
        m=dict(home='c0',away='c1',lineups=[[a['id'],b['id']],[p['id'] for p in dyn.roster(self.s,'c1')[:2]]],bench=[[c['id']],[]])
        m['on_pitch']=deepcopy(m['lineups']);dyn.snapshot(self.s,m)
        edge=dyn.edge(m,0,a['id']);self.assertGreater(edge,0);self.assertLessEqual(edge,self.s['config']['dynamics']['maximum_edge'])
        m['on_pitch'][0]=[a['id'],c['id']];self.assertEqual(dyn.edge(m,0,a['id']),0)
        self.assertEqual(dyn.edge(m,0,b['id']),0)
        b['club']='c2';dyn.sync(self.s)
        self.assertEqual(dyn.influence(self.s,'c0',[a['id'],c['id']])[a['id']],0)

    def test_exact_overlap_excludes_unused_subs_and_duplicate_settlement(self):
        m=self.match();a,b=m['on_pitch'][0][:2];sub=m['bench'][0][0]
        for _ in range(5):dyn.tick(m)
        m['on_pitch'][0].remove(b);m['on_pitch'][0].append(sub)
        for _ in range(3):dyn.tick(m)
        dyn.settle(self.s,m);before=deepcopy(self.s);dyn.settle(self.s,m);self.assertEqual(before,self.s)
        links=self.s['dynamics']['links'];cid=m['home']
        self.assertEqual(links[dyn.pair_key(cid,a,b)]['minutes'],5)
        self.assertEqual(links[dyn.pair_key(cid,a,sub)]['minutes'],3)
        self.assertNotIn(dyn.pair_key(cid,b,sub),links)

    def test_private_support_never_spreads_and_raw_links_never_leave_snapshot(self):
        self.train();p=self.s['players'][2];before=deepcopy(self.s['dynamics'])
        relationships.meet(self.s,p,'c0','Listen');self.assertEqual(before,self.s['dynamics'])
        m=self.match();v=view(self.s);self.assertNotIn('dynamics',v['match'])
        self.assertNotIn('links',v['dynamics']);self.assertNotIn('staff_links',v['dynamics'])
        self.assertNotIn('trust',json.dumps(v['dynamics']))

    def test_witness_specific_mixed_staff_reactions_followup_and_real_repair(self):
        m=self.match();coach=next(p for p in self.s['staff']['people'] if p['role']=='Coaching' and p['club'] is None)
        coach['club']='c0';coach['autonomy']='Independent';coach['risk']='Ambitious'
        other=next(p for p in self.s['staff']['people'] if p['role']=='Finance');other['club']='c0'
        dyn.bench_event(self.s,m,'attack','Manager refuses the request.')
        e=self.s['dynamics']['events'][-1]
        self.assertEqual(e['observers'],[coach['id']]);self.assertNotIn(other['id'],str(e))
        reaction=next(r for r in e['reactions'] if r['person']==coach['id'])
        self.assertEqual(reaction['football'],'Supports attacking intent');self.assertIn('pressure',reaction['process'])
        original=deepcopy(self.s['dynamics']);dyn.bench_event(self.s,m,'attack','Again');self.assertEqual(original,self.s['dynamics'])
        self.s['match']=None;r=self.s['dynamics']['staff_links']['c0|'+coach['id']];trust=r['trust']
        dyn.apply(self.s,'dynamics_followup',{'id':coach['id'],'approach':'Respect remit'});self.assertEqual(r['trust'],trust)
        with self.assertRaisesRegex(ValueError,'already'):dyn.apply(self.s,'dynamics_followup',{'id':coach['id'],'approach':'Listen'})
        m['fixture']='next-match';dyn.bench_event(self.s,m,'encourage','Backing the plan')
        self.assertGreater(r['trust'],trust);self.assertIsNone(r['concern'])
        self.assertTrue(dyn.public(self.s)['meetings'])
        coach['club']='c1';self.assertFalse(any(c['person']==coach['id'] for c in dyn.concern_rows(self.s)))

    def test_ai_contact_policy_and_empty_group(self):
        a,b=dyn.roster(self.s,'c0')[:2];c,d=dyn.roster(self.s,'c1')[:2]
        c['hidden']=deepcopy(a['hidden']);d['hidden']=deepcopy(b['hidden'])
        dyn.contact(self.s,'c0',a,b,1);dyn.contact(self.s,'c1',c,d,1)
        aa=self.s['dynamics']['links'][dyn.pair_key('c0',a['id'],b['id'])]
        bb=self.s['dynamics']['links'][dyn.pair_key('c1',c['id'],d['id'])]
        for key in ('trust','respect','familiarity','sessions'):self.assertEqual(aa[key],bb[key])
        self.assertEqual(dyn.group(self.s,'c0',[])['label'],'Not assessed')

    def test_migration_no_old_contact_and_exact_save_resume(self):
        old=deepcopy(self.s);old['schema']=25;old.pop('dynamics');old['config'].pop('dynamics')
        before=deepcopy(old);up=migrate(old);self.assertEqual(old,before);self.assertFalse(up['dynamics']['links'])
        self.assertEqual(up['players'],old['players']);self.assertEqual(up['relationships'],old['relationships'])
        self.train();m=self.match()
        for _ in range(27):football.step(self.s,m)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'career.sqlite';save(self.s,path);other=load(path)
        skip,_=execute(self.s,Command('skip',self.s['revision'],'match_skip',{}))
        while not football.finished(other['match']):
            other,_=execute(other,Command('step'+str(other['revision']),other['revision'],'match_step',{'minutes':7}))
        for k in ('match','dynamics','players','fixtures','cash','ledger','relationships'):
            self.assertEqual(skip[k],other[k],k)

    def test_summary_once_and_corrupt_state_rejected(self):
        self.train(28);self.assertEqual(len(self.s['dynamics']['summaries']),1)
        dyn.process_day(self.s);self.assertEqual(len(self.s['dynamics']['summaries']),1)
        bad=deepcopy(self.s);next(iter(bad['dynamics']['links'].values()))['trust']=float('nan')
        with self.assertRaises(ValueError):validate(bad)
