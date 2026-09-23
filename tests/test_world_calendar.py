from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import career,pathways,registration,world_calendar
from club_chairman.simulation import new_career,validate
from club_chairman.persistence import migrate,save,load


class WorldCalendarTests(unittest.TestCase):
    def test_reservations_include_future_cup_rounds_and_determinism(self):
        s=new_career(51);world_calendar.validate(s)
        self.assertFalse(world_calendar.public(s)['conflicts'])
        cup=s['competitions']['cup'];self.assertGreater(len(cup['dates']),len(cup['rounds']))
        for f in s['pathways']['fixtures']:
            for cid in (f['home'],f['away']):
                self.assertTrue(all(abs(f['day']-d)>=2 for d in world_calendar.reservations(s,cid)))
        before=deepcopy(s);pathways.schedule(s);self.assertEqual(s,before)
        self.assertEqual(s['pathways']['fixtures'],new_career(51)['pathways']['fixtures'])

    def test_blackouts_and_infeasible_calendar_are_explicit(self):
        s=new_career();s['calendar']={'blocked_days':list(range(200)),'end':100}
        s['pathways']['fixtures']=[];s['pathways']['season']=0;pathways.schedule(s)
        self.assertTrue(s['pathways']['fixtures'])
        self.assertTrue(all(f['status']=='conflict' and f['result'] is None for f in s['pathways']['fixtures']))
        s['day']=100;pathways.process_day(s)
        self.assertFalse(s['pathways']['records']);world_calendar.validate(s)

    def test_birthdays_do_not_change_frozen_age_and_new_arrivals_use_cutoff(self):
        s=new_career();p=next(p for p in s['players'] if p['club']=='c0' and p['youth'])
        p['birth_day']=-18*365+2;p['age']=17
        s['day']=3;p['age']=18
        self.assertEqual(world_calendar.age(s,p),17)
        # Match eligibility uses frozen age; group synchronisation cannot expel a birthday player.
        pathways.sync(s);self.assertTrue(pathways.eligible(s,p,'c0','Youth'))
        q=career.person(s,'p0');q['birth_day']=-21*365+2;q['age']=21
        s['config']['competition']['senior_limit']=0
        self.assertFalse(registration.capacity_errors(s,'c0',[q]))
        s['career']['season']=2;s['career']['start']=110;world_calendar.freeze(s)
        self.assertEqual(world_calendar.age(s,p),18)
        self.assertTrue(registration.capacity_errors(s,'c0',[q]))

    def test_recovery_prevents_cross_group_and_senior_appearance(self):
        s=new_career();p=career.person(s,'p2');p['development']['last_played']=5;s['day']=6
        self.assertEqual(registration.reason(s,p,'c0'),'Recovery after a recent appearance')
        s['day']=7;self.assertIsNone(registration.reason(s,p,'c0'))

    def test_migration_preserves_current_season_and_activates_next(self):
        old=new_career();old['schema']=27;old.pop('world_calendar');old['config'].pop('world_calendar')
        before=deepcopy(old);up=migrate(old);self.assertEqual(before,old)
        self.assertFalse(world_calendar.active(up));self.assertEqual(old['players'],up['players'])
        self.assertEqual(old['pathways'],up['pathways']);self.assertEqual(old['fixtures'],up['fixtures'])
        self.assertEqual(up,migrate(up))
        up['career']['season']=2;up['career']['start']=110;world_calendar.freeze(up)
        self.assertTrue(world_calendar.active(up));self.assertEqual(up['world_calendar']['cutoffs']['2'],110)

    def test_population_audit_retains_identities_and_reconciles_creation(self):
        s=new_career();before=world_calendar.capture(s);p=career.person(s,'p18');p.update(retired=True,club=None)
        p=career.new_person(s,'GK',19,40,'audit-test');s['players'].append(p);pathways.sync(s)
        world_calendar.reconcile(s,before);record=s['world_calendar']['reconciliations'][-1]
        self.assertEqual(record['after']-record['before'],1)
        self.assertEqual(len(record['changes']),2);self.assertEqual(len({p['id'] for p in s['players']}),len(s['players']))
        once=deepcopy(s);world_calendar.reconcile(s,before);self.assertEqual(s,once)
        self.assertNotIn('potential',str(world_calendar.public(s)))
        world_calendar.validate(s)

    def test_save_load_calendar_and_next_fixture_are_identical(self):
        s=new_career(51)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'calendar.sqlite3';save(s,path);other=load(path)
            self.assertEqual(s,other)
            day=min(f['day'] for f in s['pathways']['fixtures'])
            for world in (s,other):world['day']=day;pathways.process_day(world)
            self.assertEqual(s,other);validate(s)

    def test_national_calendar_year_and_cross_year_scenarios(self):
        from club_chairman import nations
        for profile in nations.catalogue()['nations']:
            if not profile['playable']:continue
            s=new_career(51,profile['id']);world_calendar.validate(s)
            self.assertTrue(s['pathways']['fixtures'])
            self.assertTrue(all(f['status']=='conflict' or f['day'] not in world_calendar.blocked_days(s) for f in s['pathways']['fixtures']))
