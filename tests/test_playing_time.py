from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import playing_time as pt, football, recruitment
from club_chairman.simulation import new_career, execute, Command, view, validate
from club_chairman.persistence import save, load, migrate


class PlayingTimeTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42)
        self.p=next(p for p in self.s['players'] if p['club']=='c0' and not p['youth'])

    def agree(self,role='Regular starter'):
        pt.sign(self.s,self.p,'c0',role,'test-agreement')
        return pt.active(self.s,self.p['id'])

    def match(self,number,minutes=0,started=False,reason=None):
        s=self.s;s['day']=number+1
        m=dict(engine=2,fixture='fixture-'+str(number),home='c0',away='c1',events=[],
            lineups=[[self.p['id']] if started else [],[]],stats={self.p['id']:dict(minutes=minutes)})
        self.p['condition']=100;self.p['injury_until']=s['day']+1 if reason=='injury' else 0
        self.p['discipline']['ban']=1 if reason=='ban' else 0
        pt.snapshot(s,m)
        if reason=='in-match':m['events'].append(dict(kind='injury',player=self.p['id']))
        pt.collect(s,m)
        return m

    def test_meaningful_starts_exceptions_and_once_only_review(self):
        row=self.agree()
        self.match(0,1,False);self.match(1,90,True);m=self.match(2,1,True)
        self.match(3,0,False,'injury');self.match(4,0,False,'ban');self.match(5,9,True,'in-match')
        before=deepcopy(row);pt.collect(self.s,m);self.assertEqual(before,row)
        self.s['day']=28;pt.review(self.s)
        r=row['reviews'][0];self.assertEqual((r['fixtures'],r['starts'],r['excused']),(3,1,3))
        self.assertEqual(r['outcome'],'Below agreement');self.assertIsNotNone(row['concern'])
        before=deepcopy(self.s);pt.review(self.s);self.assertEqual(self.s,before)
        # A quiet following period cannot erase a real unresolved complaint.
        self.s['day']=56;pt.review(self.s);self.assertIsNotNone(row['concern'])

    def test_fulfilment_resolves_concern_without_repeated_morale_effect(self):
        row=self.agree();morale=self.p['morale']
        for n in range(3):self.match(n)
        self.s['day']=28;pt.review(self.s)
        before=recruitment.assess(self.s,self.p,'c0',self.p['wage'],400)
        self.assertTrue(any('shortfall' in r for r in before['reasons']))
        for n in range(29,32):self.match(n,90,True)
        self.s['day']=56;pt.review(self.s)
        self.assertIsNone(row['concern']);self.assertEqual(self.p['morale'],morale)
        self.assertFalse(any('shortfall' in r for r in recruitment.assess(self.s,self.p,'c0',self.p['wage'],400)['reasons']))

    def test_registration_omission_is_not_an_excuse_or_selection_order(self):
        self.agree();self.s['registration']['c0'].remove(self.p['id'])
        m=self.match(0)
        e=pt.active(self.s,self.p['id'])['evidence'][0]
        self.assertFalse(e['excused']);self.assertEqual(e['reason'],'Not on competition list')
        self.assertEqual(m['lineups'],[[],[]])

    def test_legacy_and_administrative_matches_never_gain_evidence(self):
        row=self.agree();m=self.match(0);row['evidence']=[]
        m['forfeit']=True;pt.collect(self.s,m);self.assertFalse(row['evidence'])
        m.pop('forfeit');m.pop('playing_time_snapshot');pt.collect(self.s,m);self.assertFalse(row['evidence'])

    def test_renewals_manager_changes_and_club_movement_preserve_history(self):
        row=self.agree();self.match(0)
        pt.sign(self.s,self.p,'c0','Regular starter','renewal');self.assertIs(row,pt.active(self.s,self.p['id']))
        self.s['manager']=None;pt.reconcile(self.s);self.assertIs(row,pt.active(self.s,self.p['id']))
        self.p['club']='c1';pt.reconcile(self.s)
        self.assertIsNone(pt.active(self.s,self.p['id']))
        self.assertEqual(self.s['playing_time']['history'][0]['evidence'],row['evidence'])

    def test_competing_promises_receive_no_credit_and_do_not_change_ability(self):
        s=self.s;p=self.p;p['role']='GK'
        other=next(q for q in s['players'] if q['club']=='c0' and q!=p and not q['youth']);other['role']='GK'
        pt.sign(s,other,'c0','Key starter','other')
        self.assertFalse(pt.credibility(s,p,'c0','Regular starter')[0])
        before=deepcopy(p);self.agree();self.assertEqual(before,p)
        assessment=recruitment.assess(s,p,'c0',p['wage'],400,playing_role='Regular starter')
        self.assertTrue(any('Risk:' in r for r in assessment['reasons']))

    def test_refused_downgrade_is_recorded_and_cannot_erase_window(self):
        row=self.agree('Key starter');pid=self.p['id']
        self.s['recruitment']['priorities'][pid]['minutes']=90
        for n in range(3):self.match(n)
        self.s['day']=28;pt.review(self.s);before=deepcopy(row)
        text=pt.apply(self.s,'discuss_playing_role',dict(id=pid,role='Squad cover'))
        self.assertIn('do not accept',text);self.assertEqual(row,before)
        with self.assertRaisesRegex(ValueError,'review period'):
            pt.apply(self.s,'discuss_playing_role',dict(id=pid,role='Rotation'))

    def test_save_and_migrate_do_not_invent_agreements_or_change_old_world(self):
        old=deepcopy(self.s);old['schema']=22;old.pop('playing_time');old['config'].pop('playing_time')
        before=deepcopy(old);new=migrate(old);self.assertEqual(old,before)
        self.assertFalse(new['playing_time']['agreements'])
        new.pop('playing_time');new['config'].pop('playing_time');new['schema']=22;self.assertEqual(old,new)
        self.agree();self.match(0)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'save.sqlite3';save(self.s,path);self.assertEqual(load(path),self.s)

    def test_public_snapshot_hides_opponent_agreements_and_live_inputs(self):
        self.agree();m=self.match(0)
        q=next(p for p in self.s['players'] if p['club']=='c1')
        pt.sign(self.s,q,'c1','Rotation','ai')
        self.assertNotIn(q['id'],view(self.s)['playing_time']['agreements'])
        self.assertNotIn('playing_time_snapshot',football.public_match(m))

    def test_catchup_reviews_partition_evidence_and_roundtrip_during_match(self):
        row=self.agree()
        for n in range(3):self.match(n,90,True)
        for n in range(30,33):self.match(n)
        self.s['day']=56;pt.review(self.s)
        self.assertEqual([r['outcome'] for r in row['reviews']],['Fulfilled','Below agreement'])
        self.assertEqual(row['next_review'],84)

    def test_concern_changes_actual_consent_and_loan_suspends_parent_coverage(self):
        row=self.agree();s=self.s;p=self.p
        old=recruitment.counter_wage(s,p,'c0',400,10000)
        row['concern']=dict(id='test:shortfall',since=28)
        self.assertGreater(recruitment.counter_wage(s,p,'c0',400,10000),old)
        s['market']['loans'].append(dict(player=p['id'],source='c0',target='c1',status='active'))
        p['club']='c1';pt.reconcile(s);self.assertIs(pt.active(s,p['id']),row)
        m=dict(home='c1',away='c0',lineups=[[],[]]);pt.snapshot(s,m)
        self.assertNotIn('playing_time_snapshot',m)
        p['club']='c0';s['market']['loans'][-1]['status']='returned';pt.reconcile(s)
        self.assertIs(pt.active(s,p['id']),row)

    def test_accepted_change_preserves_concern_and_pending_employment_blocks_conflict(self):
        row=self.agree('Key starter');s=self.s;pid=self.p['id']
        s['recruitment']['priorities'][pid]['minutes']=40
        for n in range(3):self.match(n)
        s['day']=28;pt.review(s);before=deepcopy(row)
        result=pt.apply(s,'discuss_playing_role',dict(id=pid,role='Rotation'))
        self.assertIn('I accept',result)
        for key in ('id','next_review','evidence','reviews','concern'):self.assertEqual(row[key],before[key])
        s['career']['offers'][pid]=dict(status='ready')
        with self.assertRaisesRegex(ValueError,'employment talks'):
            pt.apply(s,'discuss_playing_role',dict(id=pid,role='Key starter'))

    def test_real_match_collects_all_agreed_players_and_save_resumes_identically(self):
        self.agree();s=self.s
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']))
        s['day']=f['day'];m=football.start(s,f)
        for _ in range(27):football.step(s,m)
        a=deepcopy(s);b=deepcopy(s);ma=deepcopy(m);mb=deepcopy(m)
        b['match']=mb
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'match.sqlite3';save(b,path);b=load(path);mb=b['match']
        while not football.finished(ma):football.step(a,ma)
        while not football.finished(mb):football.step(b,mb)
        self.assertEqual(ma,mb)
        pt.collect(a,ma);pt.collect(b,mb)
        self.assertEqual(a['playing_time'],b['playing_time'])
        self.assertEqual(len(pt.active(a,self.p['id'])['evidence']),1)


if __name__=='__main__':unittest.main()
