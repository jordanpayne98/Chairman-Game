import unittest
from copy import deepcopy

from club_chairman.content_gate import load
from club_chairman.shared_exchange import settle_shared_pyramid
from test_shared_standings import season


def inputs(country):
    memberships = {}
    results, playoffs = {}, {}
    for tier in country['tier_rules']:
        level = tier['tier']
        clubs = [f'{country["id"]}-tier{level}-{i:02}'
                 for i in range(tier['membership'])]
        memberships[tier['id']] = clubs
        results[level] = season(clubs)
        if level > 1:
            seed = {2: 3, 3: 3, 4: 4, 5: 2}[level]
            playoffs[level] = dict(winner=clubs[seed-1], eligible=True,
                                   decision_id=f'playoff-{country["id"]}-{level}')
    feeder = [f'{country["id"]}-feeder-{i:02}' for i in range(30)]
    memberships['feeder'] = feeder
    outgoing = len(country['tier_rules'][-1]['progression']['automatic_relegation_ranks'])
    entrants = [dict(club=c, eligible=True, decision_id='feeder-'+c)
                for c in feeder[:outgoing]]
    deductions = {level: {c: n for n, c in enumerate(memberships[tier['id']])}
                  for level, tier in enumerate(country['tier_rules'], 1)}
    return dict(memberships=memberships), results, playoffs, entrants, deductions


class SharedExchangeTests(unittest.TestCase):
    def test_all_fourteen_nations_exchange_without_losing_a_club(self):
        for country in load()['countries']:
            with self.subTest(country=country['id']):
                state, results, playoffs, entrants, deductions = inputs(country)
                before = deepcopy(state)
                settled = settle_shared_pyramid(country, state, '2026/27', results,
                                                playoffs, entrants, deductions)
                self.assertEqual(state, before)
                self.assertEqual(set(settled['memberships']), set(state['memberships']))
                for tier in country['tier_rules']:
                    self.assertEqual(len(settled['memberships'][tier['id']]),
                                     tier['membership'])
                self.assertEqual(len(settled['memberships']['feeder']), 30)
                self.assertEqual({club for group in settled['memberships'].values()
                                  for club in group},
                                 {club for group in state['memberships'].values()
                                  for club in group})
                self.assertEqual(len(settled['settlements']['2026/27']['routes']),
                                 2*sum(len(t['progression']['automatic_relegation_ranks'])
                                       for t in country['tier_rules']))

    def test_absent_or_ineligible_outcome_cannot_become_a_club_movement(self):
        country = next(c for c in load()['countries'] if c['id'] == 'england')
        state, results, playoffs, entrants, deductions = inputs(country)
        before = deepcopy(state)
        for mutation in ('ineligible_playoff', 'wrong_playoff', 'missing_feeder',
                         'ineligible_feeder', 'unresolved_table', 'wrong_tier_five'):
            candidate_playoffs = deepcopy(playoffs)
            candidate_feeder = deepcopy(entrants)
            candidate_deductions = deepcopy(deductions)
            if mutation == 'ineligible_playoff':
                candidate_playoffs[5]['eligible'] = False
            elif mutation == 'wrong_playoff':
                candidate_playoffs[2]['winner'] = state['memberships'][country['tier_rules'][1]['id']][0]
            elif mutation == 'missing_feeder':
                candidate_feeder.pop()
            elif mutation == 'ineligible_feeder':
                candidate_feeder[0]['eligible'] = False
            elif mutation == 'wrong_tier_five':
                candidate_playoffs[5]['winner'] = state['memberships'][
                    country['tier_rules'][4]['id']][8]
            else:
                candidate_deductions.pop(2)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                settle_shared_pyramid(country, state, '2026/27', results,
                                      candidate_playoffs, candidate_feeder,
                                      candidate_deductions)
            self.assertEqual(state, before)

    def test_tier_five_sporting_winner_needs_no_admission_approval(self):
        country = next(c for c in load()['countries'] if c['id'] == 'england')
        state, results, playoffs, entrants, deductions = inputs(country)
        playoffs[5]['association_approved'] = False  # Stale former gate is ignored.
        settled = settle_shared_pyramid(country, state, '2026/27', results,
                                        playoffs, entrants, deductions)
        self.assertIn(playoffs[5]['winner'], settled['memberships'][
            country['tier_rules'][3]['id']])


if __name__ == '__main__':
    unittest.main()
