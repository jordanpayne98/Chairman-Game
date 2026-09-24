import unittest
from copy import deepcopy

from club_chairman.content_gate import DEPTH, audit, load, require_verified
from club_chairman.shared_league_rules import shared_rulebook_issues
from club_chairman.league_structures import round_robin_rounds
from tools.build_welsh_cup_content import build


class SharedLeagueRulesTests(unittest.TestCase):
    def test_all_nations_use_equivalent_tiers_and_open_feeders(self):
        data = load()
        self.assertEqual(shared_rulebook_issues(data), [])
        self.assertEqual(sum(len(c['tier_rules']) for c in data['countries']), 38)
        self.assertEqual(sum(t['membership'] for c in data['countries'] for t in c['tier_rules']), 856)
        for country in data['countries']:
            self.assertEqual(len(country['tier_rules']), DEPTH[country['id']])
            for tier in country['tier_rules']:
                self.assertNotIn('licensing', tier)
                self.assertNotIn('promotion_eligibility', tier)
                self.assertEqual(tier['league_structure']['vertical_link'], 'open')
                self.assertEqual(tier['format']['kind'], 'round_robin')
                self.assertNotIn('selection_status', tier)
            self.assertEqual(country['tier_rules'][-1]['feeder_boundary']['mode'], 'background_feeder')
        self.assertNotIn('european_nomination_rules',
                         next(c for c in data['countries'] if c['id'] == 'wales'))
        self.assertTrue(all('admission_rules' not in cup for c in data['countries']
                            for cup in c['domestic_cups']))

    def test_divergent_national_rules_or_profiles_are_blocked(self):
        data = load()
        for mutate in (
            lambda d: d['countries'][-1]['tier_rules'][0].update(membership=30),
            lambda d: d['countries'][-1]['tier_rules'][0]['league_structure'].update(vertical_link='closed'),
            lambda d: d['countries'][0]['tier_rules'].append(deepcopy(d['countries'][0]['tier_rules'][0])),
            lambda d: d['shared_league_rulebook']['profiles'][0]['definition'].update(membership=30),
            lambda d: d.pop('shared_league_rulebook'),
            lambda d: d['countries'][0]['tier_rules'][0].update(licensing={'required': True}),
            lambda d: next(c for c in d['countries'] if c['id'] == 'wales')[
                'domestic_cups'][0].update(admission_rules={'club_licence': True}),
        ):
            changed = deepcopy(data)
            mutate(changed)
            self.assertTrue(shared_rulebook_issues(changed))
            self.assertTrue(audit(changed))

    def test_approval_does_not_certify_missing_rules_or_population(self):
        data = load()
        original = deepcopy(data)
        with self.assertRaisesRegex(ValueError, 'Production world content blocked'):
            require_verified(data)
        self.assertEqual(data, original)
        for country in data['countries']:
            for tier in country['tier_rules']:
                self.assertFalse(tier['first_season_members'])
                self.assertEqual(tier['status'], 'PARTIAL')
        self.assertEqual(len(data['clubs']), 284)
        self.assertEqual(data['history_policy'], 'career_start_only')

    def test_shared_sizes_produce_balanced_complete_fixtures(self):
        for size in (20, 24):
            members = [f'club-{n}' for n in range(size)]
            rounds = round_robin_rounds(members, 2)
            self.assertEqual(len(rounds), 2*(size-1))
            pairs = [tuple(pair) for rnd in rounds for pair in rnd]
            self.assertEqual(len(pairs), size*(size-1))
            self.assertEqual(set(pairs), {(a,b) for a in members for b in members if a != b})

    def test_legacy_cup_builder_cannot_overwrite_shared_model(self):
        data = load()
        original = deepcopy(data)
        with self.assertRaisesRegex(ValueError, 'require reconciliation'):
            build(data)
        self.assertEqual(data, original)


if __name__ == '__main__':
    unittest.main()
