"""Knockout progression, league isolation and existing-career continuity."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import competitions, football
from club_chairman.persistence import save, load, migrate
from club_chairman.simulation import new_career, execute, Command, start_match, table, validate, restore_rng


class CompetitionTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(42)
        self.act('budget',value=4000000);self.act('hire',id='m0')

    def act(self,action,**payload):
        c=Command('cup-test:'+str(self.s['revision']),self.s['revision'],action,payload)
        self.s,_=execute(self.s,c)
        return c

    def prepare_tie(self):
        f=next(f for f in self.s['fixtures'] if f.get('knockout') and 'c0' in (f['home'],f['away']))
        self.s['day']=f['day'];self.s['match']=start_match(self.s,f)
        return f

    def test_seeded_draw_dates_and_non_power_of_two_byes(self):
        self.assertEqual(self.s['competitions'],new_career(42)['competitions'])
        cup=self.s['competitions']['cup'];self.assertEqual(len(cup['rounds'][0]['fixtures']),8)
        self.assertEqual(cup['dates'],[22,43,64,85]);competitions.validate(self.s)
        # Six entrants: two real byes, two opening ties, then four semi-finalists.
        s=deepcopy(self.s);s['clubs']=s['clubs'][:6];s['fixtures']=[]
        s['leagues']['divisions']=[dict(s['leagues']['divisions'][0],members=[c['id'] for c in s['clubs']])]
        competitions.start_season(s);r=s['competitions']['cup']['rounds'][0]
        self.assertEqual(len(r['byes']),2);self.assertEqual(len(r['fixtures']),2)
        for f in s['fixtures']:f['result']={'winner':f['home']}
        competitions.progress(s);self.assertEqual(len(s['competitions']['cup']['rounds'][1]['entrants']),4)
        competitions.validate(s)
        broken=deepcopy(s);broken['competitions']['cup']['rounds'][1]['entrants'][0]='missing'
        with self.assertRaises(ValueError):competitions.validate(broken)

    def test_live_skip_resume_match_and_draw_are_identical(self):
        self.prepare_tie();before=deepcopy(table(self.s));start=deepcopy(self.s)
        self.act('match_step',minutes=27)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'cup.sqlite3';save(self.s,path);self.s=load(path)
        self.act('match_skip');played=deepcopy(self.s)
        self.s=start;command=self.act('match_skip')
        self.assertEqual(self.s['fixtures'],played['fixtures'])
        self.assertEqual(self.s['competitions'],played['competitions'])
        self.assertEqual(self.s['players'],played['players'])
        self.assertEqual(self.s['ledger'],played['ledger'])
        self.assertEqual(table(self.s),before)
        again,_=execute(self.s,command);self.assertEqual(again,self.s)
        state=deepcopy(self.s);competitions.progress(self.s);self.assertEqual(self.s,state)

    def test_extra_time_shootout_advances_without_changing_match_goals(self):
        self.prepare_tie();m=self.s['match']
        # Resume an unresolved tied game at the extra-time boundary.
        m.update(phase='extra_second',phase_minute=15,phase_length=15,added=0,added_announced=True,minute=120)
        # Engine phase names are part of its persisted public contract.
        m['phase']='extra_second'
        football.end_phase(self.s,m,restore_rng(m['rng']))
        self.assertEqual(m['phase'],'shootout')
        self.act('match_skip');m=self.s['match']
        self.assertTrue(m['finished']);self.assertIn(m['winner'],(m['home'],m['away']))
        self.assertEqual(m['score'],[0,0]);self.assertNotEqual(*m['shootout'])
        f=next(f for f in self.s['fixtures'] if f['id']==m['fixture'])
        self.assertIn('pens',competitions.result_text(f));self.assertEqual(m['winner'],f['result']['winner'])

    def test_eliminated_owner_does_not_block_background_round_or_final(self):
        cup=self.s['competitions']['cup']
        # Complete the opening round without the owner's club qualifying.
        for f in self.s['fixtures']:
            if f.get('knockout'):
                winner=f['away'] if f['home']=='c0' else f['home']
                f['result']={'winner':winner,'score':[0,0]}
        self.s['day']=22;competitions.progress(self.s)
        self.assertNotIn('c0',cup['rounds'][-1]['entrants'])
        self.s['day']=42;self.s['decision']=None;self.act('continue')
        self.assertIsNone(self.s['match']);self.assertEqual(len(self.s['competitions']['cup']['rounds']),3)
        self.s['day']=63;self.s['decision']=None;self.act('continue')
        self.s['competitions']['cup']['prize']=125000
        self.s['day']=84;self.s['decision']=None;self.act('continue')
        self.assertIsNone(self.s['match']);self.assertTrue(self.s['competitions']['cup']['settled'])
        winner=self.s['competitions']['cup']['winner']
        awards=[e for e in self.s['market']['accounts'][winner]['ledger'] if e['reason']=='Cup winner prize']
        self.assertEqual([e['amount'] for e in awards],[125000])
        state=deepcopy(self.s);competitions.progress(self.s);self.assertEqual(state,self.s)
        self.assertFalse(self.s['season_done']) # league fixtures still remain

    def test_double_forfeit_records_advancement_without_player_achievements(self):
        f=self.prepare_tie()
        self.s['registration'][f['home']]=[];self.s['registration'][f['away']]=[]
        self.s['match']=start_match(self.s,f);m=self.s['match']
        self.assertTrue(m['finished']);self.assertEqual(m['participants'],[[],[]])
        self.assertEqual(m['score'],[0,0]);self.assertIn(m['winner'],(f['home'],f['away']))
        self.assertTrue(any(e['kind']=='administrative_draw' for e in m['events']))
        self.assertEqual(m['winner'],start_match(self.s,f)['winner'])

    def test_old_save_migration_preserves_schedule_state_and_rng(self):
        old=deepcopy(self.s);old['schema']=7;old.pop('competitions');old['config'].pop('cup')
        old['fixtures']=[f for f in old['fixtures'] if not f.get('knockout')]
        old['day']=5;old['match']=start_match(old,old['fixtures'][0])
        for _ in range(27):football.step(old,old['match'])
        before=deepcopy(old);new=migrate(old)
        self.assertEqual(old,before);self.assertEqual(new['schema'],16)
        self.assertIsNone(new['competitions']['cup'])
        for key in ('fixtures','match','players','cash','ledger','career','reports'):self.assertEqual(new[key],old[key],key)
        validate(new)

    def test_reserved_final_keeps_contract_and_forecast_boundary_stable(self):
        from club_chairman.career import season_end, contractual_end
        from club_chairman.simulation import view
        from club_chairman.planning import forecast
        self.s['fixtures']=[f for f in self.s['fixtures'] if not f.get('knockout')]
        self.s['config']['cup']['round_days']=[22,43,64,110]
        competitions.start_season(self.s)
        self.assertEqual(season_end(self.s),110)
        contract=contractual_end(self.s,2)
        self.assertEqual(contract,234)
        self.assertEqual(view(self.s)['season_end'],110)
        self.assertEqual(forecast(view(self.s),horizon=200)['end'],110)
        for round_day in (22,43,64):
            self.s['day']=round_day
            for f in self.s['fixtures']:
                if f.get('knockout') and f['day']==round_day:f['result']={'winner':f['home']}
            competitions.progress(self.s)
            self.assertEqual(season_end(self.s),110)
            self.assertEqual(contractual_end(self.s,2),contract)
            self.assertEqual(forecast(view(self.s),horizon=200)['end'],110)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'reserved-final.sqlite3';save(self.s,path);loaded=load(path)
        self.assertEqual(season_end(loaded),110);self.assertEqual(contractual_end(loaded,2),contract)

    def test_invalid_overlap_and_repeat_participants_rejected(self):
        broken=deepcopy(self.s);f=next(f for f in broken['fixtures'] if f.get('knockout'))
        broken['fixtures'].append(dict(f,id='duplicate'))
        with self.assertRaises(ValueError):competitions.validate(broken)
        broken=deepcopy(self.s);broken['competitions']['cup']['rounds'][0]['byes']=['c0']
        with self.assertRaises(ValueError):competitions.validate(broken)
