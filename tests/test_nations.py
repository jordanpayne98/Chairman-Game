"""National formats, calendar reservations and continuing annual careers."""
from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
import tempfile
import unittest
from club_chairman import nations,career,competitions,clauses
from club_chairman.persistence import save,load,migrate
from club_chairman.simulation import new_career,validate,execute,Command,close_season,start_match,view
from club_chairman.planning import signing_terms


def finish_country(s):
    # Sporting boundary fixture: transparent outcomes, independent of football RNG.
    for f in s['fixtures']:
        if f.get('knockout'):continue
        f['result']={'score':[1,0]}
        for side,cid in enumerate((f['home'],f['away'])):
            c=next(c for c in s['clubs'] if c['id']==cid)
            c['played']+=1;c['gf']+=1-side;c['ga']+=side
            c['won' if side==0 else 'lost']+=1;c['points']+=3 if side==0 else 0
            c['form'].append('W' if side==0 else 'L')
    while not competitions.complete(s):
        for f in s['fixtures']:
            if f.get('knockout') and f['result'] is None:f['result']={'score':[1,0],'winner':f['home']}
        competitions.progress(s)
    s['day']=career.season_end(s);close_season(s);validate(s)
    return s


def act(s,action,**payload):return execute(s,Command('national:'+str(s['revision']),s['revision'],action,payload))[0]


class NationalTests(unittest.TestCase):
    def test_approved_inventory_and_unsupported_scenario_gate(self):
        data=nations.catalogue();self.assertEqual(len(data['nations']),14)
        self.assertEqual(sum(len(n['division_sizes']) for n in data['nations']),38)
        self.assertEqual(sum(sum(n['division_sizes']) for n in data['nations']),636)
        us=next(n for n in data['nations'] if n['id']=='usa')
        self.assertTrue(us['closed']);self.assertEqual(us['exchange'],0);self.assertEqual(us['playoff_top'],8)
        for id in ('usa','missing'):
            with self.assertRaisesRegex(ValueError,'not yet playable'):new_career(42,id)
        broken=deepcopy(data);broken['nations'][0]['division_sizes'][0]=18
        with self.assertRaises(ValueError):nations.validate_catalogue(broken)

    def test_national_membership_fixture_counts_and_squads(self):
        for id,count,size,exchange in (('england',100,20,3),('wales',24,12,2),('brazil',54,18,2)):
            s=new_career(42,id);validate(s)
            self.assertEqual(len(s['clubs']),count);self.assertEqual(len(s['players']),count*18+12)
            if id=='brazil':self.assertEqual(s['clubs'][1]['city'],'São Paulo')
            self.assertEqual(s['leagues']['exchange'],exchange)
            self.assertEqual(sum(not f.get('knockout') for f in s['fixtures']),count*(size-1))
            self.assertEqual(s['players'][144]['id'],'p144');self.assertIsNone(s['players'][144]['club'])
            self.assertEqual(len(s['competitions']['cup']['entrants']),count)
            self.assertEqual(s['players'][0]['contract_end'],career.contractual_end(s,3))
            self.assertEqual(len(s['staff']['people']),27+(count-1)*3)

    def test_calendars_both_season_types_leap_years_and_conflict_diagnostics(self):
        for id in ('england','wales','brazil'):
            n=nations.scenario(id)
            for year in (2026,2027,2028,2029):
                origin=f"2026-{n['start_month']:02d}-01";cal=nations.plan(n,year,origin)
                ds=sorted(cal['league_days']+cal['cup_days'])
                self.assertEqual(len(ds),len(set(ds)))
                self.assertTrue(all(b-a>=3 for a,b in zip(ds,ds[1:])))
                end=date.fromisoformat(origin)+timedelta(days=cal['end'])
                self.assertEqual(end,date(year+(id!='brazil'),n['end_month'],30 if id=='brazil' else 31))
                self.assertEqual(cal['end'],cal['cup_days'][-1])
        n=nations.scenario('wales');n['blackout_ranges']=[[7,20]]
        self.assertTrue(all(not 7<=d<=20 for d in nations.plan(n,2026,'2026-08-01')['league_days']))
        n['blackout_ranges']=[[0,302]]
        with self.assertRaisesRegex(ValueError,'Calendar conflict'):nations.plan(n,2026,'2026-08-01')

    def test_annual_contracts_options_and_planning_share_exact_dates(self):
        s=new_career(42,'wales');origin=date.fromisoformat(s['config']['start_date'])
        for duration in (1,2,3):self.assertEqual(origin+timedelta(days=career.contractual_end(s,duration)),date(2026+duration,5,31))
        p=s['players'][0];end=career.contractual_end(s,2)
        clauses.sign(s,p,dict(id='calendar-option',end=end,club_option=True))
        self.assertEqual(origin+timedelta(days=s['clauses']['employment'][p['id']]['option_end']),date(2029,5,31))
        v=view(s);free=next(p for p in v['players'] if p['id']=='p144')
        self.assertEqual(signing_terms(v,[free])['contracts'][0]['end'],end)
        s['season_done']=True
        self.assertEqual(origin+timedelta(days=career.contractual_end(s,1)),date(2028,5,31))

    def test_rollover_preserves_annual_anchor_archive_obligations_and_membership(self):
        s=finish_country(new_career(42,'wales'));before=deepcopy(s)
        cmd=Command('annual-rollover',s['revision'],'next_season',{});s,_=execute(s,cmd)
        self.assertEqual(execute(s,cmd)[0],s)
        self.assertEqual(s['day'],before['day']);self.assertEqual(s['career']['start'],365)
        self.assertEqual(s['calendar']['year'],2027);self.assertEqual(s['calendar']['end'],669)
        self.assertEqual(s['career']['history'][0]['calendar'],before['calendar'])
        self.assertEqual(s['cash'],before['cash']);self.assertEqual(s['ledger'],before['ledger'])
        self.assertEqual([len(d['members']) for d in s['leagues']['divisions']],[12,12])
        self.assertEqual(s['players'][0]['contract_end'],before['players'][0]['contract_end'])
        self.assertEqual(len({f['id'] for f in s['fixtures']} & {f['id'] for f in before['fixtures']}),0)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'annual.sqlite3';save(s,path);self.assertEqual(load(path),s)
        # Preseason commits one real day and daily obligations, without skipping to August.
        s=act(s,'budget',value=4000000);s=act(s,'hire',id='m0');day=s['day'];s=act(s,'continue')
        self.assertEqual(s['day'],day+1);self.assertLess(s['day'],s['career']['start'])

    def test_live_skip_and_save_resume_first_brazil_match_are_identical(self):
        s=new_career(42,'brazil');s=act(s,'budget',value=4000000);s=act(s,'hire',id='m0')
        f=next(f for f in s['fixtures'] if 'c0' in (f['home'],f['away']))
        s['day']=f['day'];s['match']=start_match(s,f);before=deepcopy(s)
        s=act(s,'match_step',minutes=27)
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'brazil.sqlite3';save(s,p);s=load(p)
        s=act(s,'match_skip');direct=act(before,'match_skip')
        for k in ('players','fixtures','ledger','calendar','leagues'):self.assertEqual(s[k],direct[k],k)

    def test_legacy_schema9_is_additive_and_bad_national_dates_rejected(self):
        old=new_career(42);old.pop('calendar');old['schema']=9;before=deepcopy(old)
        upgraded=migrate(old);self.assertEqual(old,before);self.assertIsNone(upgraded['calendar'])
        for k in old:
            if k!='schema':self.assertEqual(upgraded[k],old[k])
        broken=new_career(42,'wales');broken['fixtures'][0]['day']+=1
        with self.assertRaises(ValueError):validate(broken)
        broken=new_career(42,'wales');broken['calendar']['cup_days'][-1]+=1
        with self.assertRaises(ValueError):validate(broken)
