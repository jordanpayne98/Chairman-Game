"""Supporting-club reviews preserve deadlines, membership and saved evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from club_chairman import detail,club_ai,leagues
from club_chairman.simulation import new_career,validate,start_match,football
from club_chairman.persistence import migrate,save,load
from test_feeders import act,finish,place_owner


class DetailTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(19,'wales');self.cid=self.s['leagues']['divisions'][-1]['members'][0]

    def squad(self,s=None):
        return [p for p in (s or self.s)['players'] if p['club']==self.cid and not p['retired'] and not p['youth']]

    def test_routine_reviews_reduce_work_but_keep_primary_weekly(self):
        s=self.s;s['club_ai']['last_review']={c['id']:28 for c in s['clubs'][1:]}
        for day in range(35,113,7):s['day']=day;club_ai.process_day(s)
        reduced=[e['day'] for e in s['club_ai']['finance'] if e['club']==self.cid and e['kind']=='finance']
        primary=[e['day'] for e in s['club_ai']['finance'] if e['club']=='c1' and e['kind']=='finance']
        self.assertEqual(reduced,[56,84,112]);self.assertEqual(primary,list(range(35,113,7)))
        self.assertEqual(len(reduced)*4,len(primary));validate(s)

    def test_urgent_cover_expiries_bills_and_window_keep_weekly_review(self):
        base=self.s;base['day']=35;base['club_ai']['last_review'][self.cid]=28
        self.assertFalse(detail.review_due(base,self.cid,self.squad()))
        mutations=[lambda s:s.update(day=21),
                   lambda s:self.squad(s)[0].update(club=None),
                   lambda s:self.squad(s)[0].update(contract_end=40),
                   lambda s:next(p for p in s['staff']['people'] if p['club']==self.cid).update(end=40),
                   lambda s:s['market']['obligations'].append(dict(source=self.cid,status='scheduled',due=40)),
                   lambda s:[p.update(injury_until=50) for p in self.squad(s)]]
        for i,change in enumerate(mutations):
            s=deepcopy(base)
            change(s)
            self.assertTrue(detail.review_due(s,self.cid,self.squad(s)),i)
        s=deepcopy(base);p=self.squad(s)[0];p['contract_end']=40
        club_ai.process_day(s);self.assertGreater(p['contract_end'],40);self.assertEqual(s['club_ai']['last_review'][self.cid],35)

    def test_daily_payment_expiry_and_pending_medical_do_not_wait_for_review(self):
        s=act(self.s,'hire',id='m0');s['day']=35
        p=self.squad(s)[0];pid=p['id'];p['contract_end']=35
        s['club_ai']['last_review'][self.cid]=35
        s['market']['obligations'].append(dict(id='detail-bill',source=self.cid,target='c0',amount=12345,due=36,status='scheduled',player=pid))
        # A medical finishing outside the registration window must cancel now.
        free=next(p for p in s['players'] if p['club'] is None)
        s['club_ai']['decisions'].append(dict(id='detail-medical',club=self.cid,player=free['id'],source=None,status='medical',due=36,fee=0,signing_fee=0,wage=free['wage']))
        before=s['cash'];s=act(s,'continue')
        self.assertEqual(s['day'],36);self.assertEqual(s['cash'],before+12345)
        self.assertEqual(s['market']['obligations'][-1]['paid'],36)
        self.assertIsNone(next(p for p in s['players'] if p['id']==pid)['club'])
        self.assertEqual(s['club_ai']['decisions'][-1]['status'],'cancelled')
        self.assertEqual(s['club_ai']['last_review'][self.cid],35);validate(s)

    def test_transitions_precede_schedule_and_owner_stays_detailed(self):
        s=finish(place_owner(self.s,'wales-2'));before=deepcopy(s)
        promoted=[m['club'] for m in s['leagues']['movements'] if m['source']=='wales-regional']
        schedule=leagues.schedule
        def checked(state):
            self.assertTrue(all(state['detail']['levels'][c]=='detailed' for c in leagues.primary_members(state)))
            return schedule(state)
        with patch('club_chairman.leagues.schedule',side_effect=checked):s=act(s,'next_season')
        self.assertEqual(s['detail']['levels']['c0'],'detailed')
        self.assertEqual(sum(v=='reduced' for v in s['detail']['levels'].values()),7)
        self.assertTrue(all(s['detail']['levels'][c]=='detailed' for c in promoted))
        for key in ('players','staff','market','cash','ledger','reports','planning'):self.assertEqual(s[key],before[key],key)
        self.assertEqual(s['career']['history'][-1]['detail']['levels'],before['detail']['levels'])
        same=deepcopy(s);detail.synchronise(s);self.assertEqual(s,same)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'detail.sqlite3';save(s,path);self.assertEqual(load(path),s)
        validate(s)

    def test_schema12_midmatch_preserves_existing_state_and_activates_next_season(self):
        old=deepcopy(self.s);old['schema']=12;old.pop('detail');old['config'].pop('detail')
        f=next(f for f in old['fixtures'] if not f.get('knockout') and 'c0' in (f['home'],f['away']))
        old['day']=f['day'];old['match']=start_match(old,f)
        for _ in range(27):football.step(old,old['match'])
        before=deepcopy(old);new=migrate(old);self.assertEqual(old,before)
        self.assertEqual(new['detail']['activation_season'],2)
        self.assertTrue(all(v=='detailed' for v in new['detail']['levels'].values()))
        restored=deepcopy(new);restored['schema']=12;restored.pop('detail');restored['config'].pop('detail');self.assertEqual(restored,old)
        self.assertEqual(migrate(new),new)
        a=act(new,'match_skip');b=act(deepcopy(new),'match_skip');self.assertEqual(a,b)
        # Fresh old-format career exercises deferred activation at rollover.
        old=deepcopy(self.s);old['schema']=12;old.pop('detail');old['config'].pop('detail')
        s=act(finish(migrate(old)),'next_season')
        self.assertEqual(sum(v=='reduced' for v in s['detail']['levels'].values()),8);validate(s)

    def test_invalid_detail_state_is_rejected_and_views_do_not_expose_private_estimates(self):
        from club_chairman.simulation import view
        for change in (lambda s:s['detail']['levels'].update(c0='reduced'),
                       lambda s:s['detail']['levels'].update(c1='reduced'),
                       lambda s:s['config']['detail'].update(routine_days=1),
                       lambda s:s['detail'].update(activation_season=0)):
            s=deepcopy(self.s);change(s)
            with self.assertRaises(ValueError):validate(s)
        before=deepcopy(self.s);v=view(self.s);self.assertEqual(before,self.s)
        self.assertNotIn('observations',v['club_ai']);self.assertEqual(v['detail']['levels']['c0'],'detailed')
