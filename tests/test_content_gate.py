import unittest
from copy import deepcopy

from club_chairman.content_gate import audit,load,require_verified
from reference_leagues import load_reference


class ContentGateTests(unittest.TestCase):
    def test_incomplete_tiers_and_entrants_cannot_pass(self):
        source=load();original=deepcopy(source);issues=audit(source)
        self.assertEqual(source,original)
        self.assertTrue(any('england/england-premier-2026: tier remains PARTIAL' in e for e in issues))
        self.assertFalse(any('opening sporting eligibility remains unverified' in e for e in issues))
        self.assertTrue(any('regional_competitions' in e for e in issues))
        with self.assertRaisesRegex(ValueError,'Production world content blocked'):
            require_verified(source)

    def test_status_flag_cannot_override_missing_rules(self):
        source=load();source['status']='VERIFIED'
        self.assertTrue(audit(source))
        source['countries'][0]['tier_rules']=[dict(id='example',nation='england',tier=1)]
        issues=audit(source)
        self.assertTrue(any('missing mandatory rule field' in e for e in issues))
        self.assertTrue(any('first-season membership' in e for e in issues))

    def test_wales_sourced_format_is_partial_until_clubs_and_rules_reconcile(self):
        source=load_reference();wales=next(c for c in source['countries'] if c['id']=='wales')
        top,north,south=wales['tier_rules']
        self.assertEqual([t['membership'] for t in (top,north,south)],[16,16,16])
        self.assertEqual(top['format']['phase_2_groups'],[6,4,6])
        self.assertEqual(top['format']['phase_2_matches'],[5,3,5])
        self.assertEqual(top['registration']['homegrown_basis'],'two_consecutive_FA_Wales_youth_seasons_irrespective_of_nationality')
        self.assertTrue(top['registration']['homegrown_shortfall_reduces_max'])
        self.assertEqual(top['progression']['rank_14'],'single_leg_playoff_at_tier_2_club')
        issues=audit(source)
        self.assertFalse(any('wales-premier-2026: first-season membership' in e for e in issues))
        self.assertFalse(any('wales-ardal-2026: supporting club membership' in e for e in issues))
        self.assertFalse(any('twenty' in e or 'historical result' in e for e in issues))

    def test_welsh_identity_inventory_and_references(self):
        source=load();wales=next(c for c in source['countries'] if c['id']=='wales')
        clubs={c['id']:c for c in source['clubs'] if c['nation']=='wales'}
        self.assertEqual(len(clubs),284)
        self.assertEqual(len({c['name'] for c in clubs.values()}),284)
        self.assertEqual(len({c['ground'] for c in clubs.values()}),284)
        pool=wales['supporting_pools'][0]
        self.assertEqual([len(ids) for ids in pool['group_members'].values()],[16]*4)
        for rivalry in source['rivalries']:
            a,b=(clubs[cid] for cid in rivalry['club_ids'])
            self.assertEqual((a['rival_id'],b['rival_id']),(b['id'],a['id']))
        self.assertFalse(any('historical figure' in issue for issue in audit(source)))
        pool['group_members']['north_east'][0]=pool['group_members']['north_west'][0]
        issues=audit(source)
        self.assertTrue(any('regional groups do not reconcile' in issue for issue in issues))

    def test_welsh_calendars_do_not_mix_competition_phases(self):
        wales=next(c for c in load_reference()['countries'] if c['id']=='wales')
        top,north,south=wales['tier_rules']
        self.assertNotIn('final_round',top['calendar'])
        for tier in (north,south):
            self.assertNotIn('phase_2_first',tier['calendar'])
            self.assertNotIn('winter_break',tier['calendar'])
            self.assertEqual(tier['calendar']['final_round'],['2027-04-16','2027-04-17'])

    def test_club_id_alone_is_not_a_production_identity(self):
        source=load();wales=next(c for c in source['countries'] if c['id']=='wales')
        wales['tier_rules'][0]['first_season_members']=['made-up-'+str(i) for i in range(16)]
        source['clubs']=[{'id':'made-up-'+str(i)} for i in range(16)]
        issues=audit(source)
        self.assertTrue(any('incomplete original club identity' in e for e in issues))


    def test_no_pregame_history_or_earned_opening_places(self):
        source=load_reference()
        self.assertEqual(source['history_policy'],'career_start_only')
        self.assertNotIn('competition_history',source)
        self.assertNotIn('historical_people',source)
        self.assertFalse(any('wales' in issue and 'opening tier allocation' in issue for issue in audit(source)))
        source['competition_history']=[{'season':'2025/26'}]
        source['opening_allocations'][0]['club_ids']=[]
        issues=audit(source)
        self.assertTrue(any('Pre-game historical content' in issue for issue in issues))
        self.assertTrue(any('opening tier allocation does not reconcile' in issue for issue in issues))

    def test_first_season_entry_requires_allocation_and_eligibility(self):
        source=load();allocation=source['opening_allocations'][0]
        entry=dict(competition=allocation['competition'],club=allocation['club_ids'][0],
                   opening_allocation=allocation['id'],eligibility_evidence='opening sporting allocation')
        source['first_season_entrants']=[entry]
        self.assertFalse(any('First-season entrant' in issue for issue in audit(source)))
        entry['opening_allocation']='missing'
        self.assertTrue(any('does not match its opening allocation' in issue for issue in audit(source)))


if __name__=='__main__':unittest.main()
