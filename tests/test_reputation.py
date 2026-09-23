from copy import deepcopy
from pathlib import Path
import tempfile
import json
import unittest

from club_chairman import reputation, recruitment, football, leagues
from club_chairman.simulation import new_career, execute, Command, view, start_match, step_match, record_result
from club_chairman.persistence import save, load, migrate


class ReputationTests(unittest.TestCase):
    def setUp(self):self.s=new_career(83)

    def evidence(self,s=None,number=0,forfeit=False,abandoned=False,minutes=95,rating=8):
        s=s or self.s
        f=next(f for f in s['fixtures'] if not f.get('knockout') and 'c0' in (f['home'],f['away']))
        f=deepcopy(f);f['id']='rep-test-'+str(number);s['fixtures'].append(f)
        pid=next(p['id'] for p in s['players'] if p['club']==f['home'])
        m=dict(fixture=f['id'],engine=2,home=f['home'],away=f['away'],score=[3,0],
            forfeit=forfeit,abandoned=abandoned,participants=[[pid],[]],
            stats={pid:dict(minutes=minutes,rating=rating,goals=1)})
        reputation.collect(s,m)
        return pid,m

    def test_source_once_and_awarded_or_abandoned_games_give_no_performance(self):
        pid,m=self.evidence();before=deepcopy(self.s['reputation_progress'])
        reputation.collect(self.s,m);self.assertEqual(before,self.s['reputation_progress'])
        self.evidence(number=1,forfeit=True);self.evidence(number=2,abandoned=True)
        self.assertEqual(self.s['reputation_progress']['period']['players'][pid]['matches'],1)
        self.assertEqual(len(self.s['reputation_progress']['seen']),3)

    def test_sustained_public_performance_changes_slowly_not_ability_or_cash(self):
        s=self.s;pid,_=self.evidence(number=0);self.evidence(number=1)
        before=deepcopy(s);s['day']=28;reputation.review(s)
        rec=s['recruitment']['players'][pid]
        self.assertEqual(len(rec['reviews']),1)
        self.assertLessEqual(abs(rec['value']-before['recruitment']['players'][pid]['value']),1)
        for key in ('players','cash','market','rng','career'):
            if key in s:self.assertEqual(s[key],before[key])
        self.assertEqual(rec['reviews'][0]['evidence']['minutes'],190)
        before=deepcopy(s);reputation.review(s);self.assertEqual(s,before)

    def test_single_cameo_or_inactivity_cannot_earn_a_performance_review(self):
        pid,_=self.evidence(minutes=1);self.s['day']=28;reputation.review(self.s)
        self.assertFalse(self.s['recruitment']['players'][pid]['reviews'])
        self.s['day']=200;before=deepcopy(self.s['recruitment']);reputation.review(self.s)
        self.assertEqual(before,self.s['recruitment']);self.assertGreater(self.s['reputation_progress']['next_review'],200)

    def test_public_export_has_evidence_but_no_private_preferences_or_accumulators(self):
        pid,_=self.evidence();self.evidence(number=1);self.s['day']=28;reputation.review(self.s)
        r=view(self.s)
        self.assertIn('reviews',r['reputation']['players'][pid])
        self.assertNotIn('priorities',r['reputation']);self.assertNotIn('carry',r['reputation'])
        before=deepcopy(self.s);view(self.s);self.assertEqual(before,self.s)

    def test_shared_season_budget_bounds_awards_and_performance(self):
        s=self.s;pid=next(iter(s['recruitment']['players']));r=s['recruitment']['players'][pid];value=r['value']
        for i in range(20):reputation.change(s,'players',pid,str(i),1,'Recorded achievement',{})
        self.assertEqual(r['value']-value,s['config']['reputation']['player_season_cap'])
        before=deepcopy(s);reputation.change(s,'players',pid,'0',1,'Duplicate',{});self.assertEqual(s,before)
        reputation.change(s,'players',pid,'down',-1,'Decline',{})
        self.assertEqual(r['value']-value,5)
        reputation.validate(s)

    def test_stature_retained_after_a_poor_period_and_bounded_at_edges(self):
        s=self.s;pid,_=self.evidence(rating=3);self.evidence(number=1,rating=3)
        rec=s['recruitment']['players'][pid];rec.update(value=95);rec['baseline']['value']=95
        s['reputation_progress']['reference']['players'][pid]=95;s['day']=28
        reputation.review(s);self.assertGreaterEqual(rec['value'],94)
        reputation.change(s,'players',pid,'edge',1000,'Large award',{})
        self.assertLessEqual(rec['value'],100);reputation.validate(s)

    def test_simultaneous_competition_review_uses_prior_values_and_credits_contributors(self):
        s=self.s;state=s['reputation_progress'];d=s['leagues']['divisions'][0];winner=d['members'][0]
        pid=next(p['id'] for p in s['players'] if p['club']==winner)
        state['contributions'][f"leagues:{d['id']}:{winner}"]={pid:190}
        for div in s['leagues']['divisions']:
            s['leagues']['final_tables'][div['id']]=[deepcopy(next(c for c in s['clubs'] if c['id']==cid)) for cid in div['members']]
        prior=deepcopy(state['reference']);reputation.close_season(s)
        rec=s['recruitment']['leagues'][d['id']]['reviews'][-1]
        self.assertEqual(rec['evidence']['prior_mean'],round(sum(prior['clubs'][cid] for cid in d['members'])/len(d['members']),2))
        self.assertIn('champions',s['recruitment']['players'][pid]['reviews'][-1]['summary'])
        teammate=next(p['id'] for p in s['players'] if p['club']==winner and p['id']!=pid)
        self.assertFalse(s['recruitment']['players'][teammate]['reviews'])
        before=deepcopy(s);reputation.close_season(s);self.assertEqual(before,s)

    def test_new_season_and_transfers_do_not_farm_publicity(self):
        s=self.s;before=deepcopy(s['recruitment']);p=s['players'][0]
        for cid in ('c1','c0','c2','c0'):
            p['club']=cid;recruitment.sync(s);reputation.sync(s)
        self.assertEqual(before,s['recruitment'])
        s['reputation_progress']['budgets']={'players:'+p['id']:5}
        s['career']['season']+=1;reputation.sync(s)
        self.assertEqual(s['reputation_progress']['budgets'],{})
        self.assertEqual(before,s['recruitment'])

    def test_migration_preserves_in_progress_match_and_blocks_old_result_replay(self):
        s=self.s
        s,_=execute(s,Command('hire',s['revision'],'hire',{'id':'m0'}))
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']) and not f.get('knockout'))
        s['day']=f['day'];s['match']=start_match(s,f)
        for _ in range(27):step_match(s,s['match'])
        old=deepcopy(s);old['schema']=21;old.pop('reputation_progress');old['config'].pop('reputation')
        old['recruitment'].pop('cups')
        for kind in ('clubs','leagues','players'):
            for r in old['recruitment'][kind].values():r.pop('baseline');r.pop('reviews')
        before=deepcopy(old);new=migrate(old);self.assertEqual(old,before)
        self.assertEqual(new['match'],old['match']);self.assertEqual(new['players'],old['players'])
        self.assertEqual(new['cash'],old['cash']);self.assertEqual(new['career'],old['career'])
        self.assertEqual(migrate(new),new)
        a=deepcopy(old);b=deepcopy(new)
        for kind in ('clubs','leagues','players'):
            for r in b['recruitment'][kind].values():r['value']=100
        while not football.finished(a['match']):step_match(a,a['match'])
        while not football.finished(b['match']):step_match(b,b['match'])
        self.assertEqual(a['match'],b['match']);self.assertEqual(a['players'],b['players'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'career.sqlite3';save(new,path);self.assertEqual(json.dumps(load(path),sort_keys=True),json.dumps(new,sort_keys=True))

    def test_fixture_settlement_collects_real_stats_and_roundtrips_pending_evidence(self):
        s,_=execute(self.s,Command('hire',0,'hire',{'id':'m0'}))
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']) and not f.get('knockout'))
        s['day']=f['day'];m=start_match(s,f)
        while not football.finished(m):step_match(s,m)
        record_result(s,m)
        self.assertIn(f['id'],s['reputation_progress']['seen'])
        before=deepcopy(s);record_result(s,m);self.assertEqual(s,before)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'career.sqlite3';save(s,path);loaded=load(path)
        self.assertEqual(loaded,s)
        loaded['day']=28;s['day']=28;reputation.review(loaded);reputation.review(s)
        self.assertEqual(loaded,s)

    def test_upgrade_does_not_replay_completed_fixture_or_award_an_old_cup(self):
        s=self.s;pid,m=self.evidence()
        f=next(f for f in s['fixtures'] if f['id']==m['fixture']);f['result']={'score':[3,0]}
        s.pop('reputation_progress');s['competitions']['cup']['settled']=True
        reputation.initialise(s);before=deepcopy(s['recruitment'])
        reputation.collect(s,m)
        self.assertFalse(s['reputation_progress']['period']['players'])
        reputation.honour(s,'cups',s['competitions']['cup']['id'],'c0','season:1:cup','Old trophy',1)
        self.assertEqual(before,s['recruitment'])

    def test_invalid_tuning_and_pending_minutes_are_rejected(self):
        self.evidence();self.s['config']['reputation']['player_rate']=float('nan')
        with self.assertRaisesRegex(ValueError,'tuning'):reputation.validate(self.s)
        self.s['config']['reputation']['player_rate']=.06
        next(iter(self.s['reputation_progress']['period']['players'].values()))['minutes']=0
        with self.assertRaisesRegex(ValueError,'minutes'):reputation.validate(self.s)


if __name__=='__main__':unittest.main()
