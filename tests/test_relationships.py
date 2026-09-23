from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import relationships as rel, morale, playing_time as pt
from club_chairman.simulation import new_career,execute,Command,view,validate
from club_chairman.persistence import save,load,migrate


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42);self.p=self.s['players'][2]

    def review(self,outcome,day):
        a=pt.active(self.s,self.p['id'])
        if not a:
            pt.sign(self.s,self.p,'c0','Key starter','test');a=pt.active(self.s,self.p['id'])
        a['reviews'].append(dict(day=day,outcome=outcome,role=a['role']))
        a['concern']=dict(id='test:shortfall',since=0) if outcome=='Below agreement' else None
        self.s['day']=day;rel.process(self.s);morale.reconcile(self.s)
        return a

    def test_private_meeting_receipt_no_spread_no_selection_or_attribute_change(self):
        self.review('Below agreement',0);self.p['hidden']['ambition']=30
        old=deepcopy(self.s);cmd=Command('meeting',self.s['revision'],'support_player',{'id':self.p['id'],'approach':'Listen'})
        s,text=execute(self.s,cmd);self.assertIn('still need',text)
        self.assertEqual(execute(s,cmd)[0],s);self.assertEqual(self.s,old)
        self.assertEqual(s['playing_time'],old['playing_time']);self.assertEqual(s['players'][2]['attrs'],old['players'][2]['attrs'])
        for p,q in zip(s['players'],old['players']):
            if p['id']!=self.p['id']:self.assertEqual(p['morale'],q['morale'])
        e=s['relationships']['events'][-1];self.assertEqual(e['observers'],[]);self.assertFalse(e['public'])
        self.assertLess(s['players'][2]['morale'],50)
        self.assertEqual(s['relationships']['links'][self.p['id']+'>c0:chairman']['trust'],44)
        with self.assertRaisesRegex(ValueError,'cooldown'):
            execute(s,Command('again',s['revision'],'support_player',{'id':self.p['id'],'approach':'Listen'}))
        self.assertEqual(self.s,old)

    def test_unconvinced_response_and_same_concern_cannot_be_farmed(self):
        self.review('Below agreement',0);self.p['hidden']['ambition']=90
        result=rel.apply(self.s,'support_player',dict(id=self.p['id'],approach='Listen'))
        self.assertIn('need to see',result);self.assertFalse(any(i['group']=='support' for i in self.s['mood']['players'][self.p['id']]['sources'].values()))
        self.s['day']=30
        with self.assertRaises(ValueError):rel.apply(self.s,'support_player',dict(id=self.p['id'],approach='Encourage'))

    def test_breach_not_repeated_repair_requires_real_fulfilment(self):
        self.review('Below agreement',0);r=self.s['relationships']['links'][self.p['id']+'>c0:chairman']
        self.assertEqual(r['trust'],44)
        self.review('Below agreement',28);self.assertEqual(r['trust'],44)
        self.review('Fulfilled',56);self.assertEqual(r['trust'],46);self.assertIsNone(r['grievance'])
        before=deepcopy(self.s);rel.process(self.s);self.assertEqual(self.s,before)
        self.assertEqual(self.p['morale'],50)

    def test_privacy_departure_history_and_return(self):
        self.review('Below agreement',0);self.p['club']='c1';pt.reconcile(self.s);rel.process(self.s)
        self.assertNotIn(self.p['id'],view(self.s)['relationships'])
        self.assertTrue(self.s['relationships']['events'])
        self.s['day']=28;rel.process(self.s)
        self.p['club']='c0';row=rel.public(self.s)[self.p['id']]
        self.assertEqual(row['assessment'],'Strained');self.assertFalse(row['grievance'])
        self.assertTrue(row['events'])

    def test_save_roundtrip_and_legacy_reviews_do_not_create_relationships(self):
        self.review('Below agreement',0);old=deepcopy(self.s);old['schema']=24
        old.pop('relationships');old['config'].pop('relationships')
        s=migrate(old);rel.process(s);self.assertFalse(s['relationships']['links']);self.assertFalse(s['relationships']['events'])
        rel.apply(s,'support_player',dict(id=self.p['id'],approach='Listen'));morale.reconcile(s);validate(s)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.sqlite';save(s,p);self.assertEqual(load(p),s)

    def test_ai_uses_same_private_support_policy_and_preserves_other_players(self):
        q=next(p for p in self.s['players'] if p['club']=='c1');q['hidden']['ambition']=30
        pt.sign(self.s,q,'c1','Key starter','ai');a=pt.active(self.s,q['id']);a['concern']=dict(id='ai:shortfall',since=0)
        rel.process(self.s);self.assertEqual(len(self.s['relationships']['meetings']),1)
        self.assertEqual(self.s['relationships']['meetings'][0]['outcome'],'Reassured')
        self.assertNotIn(q['id'],rel.public(self.s));before=deepcopy(self.s);rel.process(self.s);self.assertEqual(before,self.s)

    def test_invalid_targets_and_matchday_are_atomic(self):
        for pid in ('missing','p144'):
            before=deepcopy(self.s)
            with self.assertRaises(ValueError):execute(self.s,Command(pid,0,'support_player',{'id':pid,'approach':'Listen'}))
            self.assertEqual(self.s,before)

    def test_real_review_hooks_apply_and_repair_one_concern(self):
        pt.sign(self.s,self.p,'c0','Key starter','hook')
        for day in (1,2,3):
            self.s['day']=day
            m=dict(engine=2,fixture='hook'+str(day),home='c0',away='c1',events=[],lineups=[[],[]],stats={})
            pt.snapshot(self.s,m);pt.collect(self.s,m)
        self.s['day']=28
        s,_=execute(self.s,Command('review',0,'budget',{'value':self.s['budget']}))
        p=s['players'][2];self.assertLess(p['morale'],50)
        self.assertEqual(pt.active(s,p['id'])['reviews'][-1]['outcome'],'Below agreement')
        self.assertEqual(rel.public(s)[p['id']]['assessment'],'Strained')
        for day in (29,30,31):
            s['day']=day
            m=dict(engine=2,fixture='hook'+str(day),home='c0',away='c1',events=[],lineups=[[p['id']],[]],stats={p['id']:{'minutes':90}})
            pt.snapshot(s,m);pt.collect(s,m)
        s['day']=56;s,_=execute(s,Command('repair',s['revision'],'budget',{'value':s['budget']}))
        self.assertEqual(s['players'][2]['morale'],50)
        self.assertFalse(rel.public(s)[p['id']]['grievance'])

    def test_new_match_resume_and_live_skip_preserve_mood_and_relationships(self):
        from club_chairman import football
        s=self.s;s,_=execute(s,Command('hire',s['revision'],'hire',{'id':'m0'}))
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']));s['day']=f['day'];s['match']=football.start(s,f)
        for _ in range(27):football.step(s,s['match'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.sqlite';save(s,p);b=load(p)
        a,_=execute(s,Command('skip',s['revision'],'match_skip',{}))
        while not football.finished(b['match']):
            b,_=execute(b,Command('step'+str(b['revision']),b['revision'],'match_step',{'minutes':7}))
        for key in ('mood','relationships','cash','ledger','fixtures','players','match'):
            self.assertEqual(a[key],b[key],key)
