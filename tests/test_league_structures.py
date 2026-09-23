import json
import unittest
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta

from club_chairman.content_gate import audit, load
from reference_leagues import load_reference
from club_chairman.league_structures import (
    bracket_issues, combine_sections, create_playoff, eligible_ranked_clubs,
    league_coverage, next_fixture, record_playoff_result, restore_playoff,
    round_robin_rounds, settle_membership, split_sections, structure_issues,
)


def definition(nation):
    country = next(c for c in load_reference()['countries'] if c['id'] == nation)
    return next(t['league_structure']['brackets'][0] for t in country['tier_rules']
                if t['league_structure']['brackets'])


def playoff(nation):
    graph = definition(nation)
    entrants = {s: 'club-' + s for s in graph['slots']}
    return create_playoff(graph, entrants, list(entrants.values()), '2026-07-01')


class LeagueStructureTests(unittest.TestCase):
    def test_balanced_round_robins_and_odd_group_byes(self):
        for n, cycles in ((18, 2), (20, 2), (22, 2), (24, 2), (10, 4), (9, 2)):
            with self.subTest(n=n, cycles=cycles):
                clubs = [str(i) for i in range(n)]
                schedule = round_robin_rounds(clubs, cycles)
                self.assertEqual(schedule, round_robin_rounds(clubs[::-1], cycles))
                games = Counter()
                hosts = Counter()
                for rnd in schedule:
                    self.assertEqual(len({c for pair in rnd for c in pair}), 2*len(rnd))
                    for home, away in rnd:
                        games[tuple(sorted((home, away)))] += 1
                        hosts[home] += 1
                self.assertEqual(len(games), n*(n-1)//2)
                self.assertEqual(set(games.values()), {cycles})
                self.assertEqual(set(hosts.values()), {(n-1)*cycles//2})

    def test_split_points_and_rank_boundaries_survive(self):
        order = [str(i) for i in range(16)]
        sections = split_sections(order, [6, 4, 6], dict.fromkeys(order, 40))
        self.assertEqual(sections[1]['rank_start'], 7)
        self.assertEqual(sections[1]['points'], dict.fromkeys(order[6:10], 40))
        rearranged = [s['members'][::-1] for s in sections]
        self.assertEqual(combine_sections(sections, rearranged)[:6], order[:6][::-1])
        rearranged[0][0] = order[-1]
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            combine_sections(sections, rearranged)

    def test_welsh_aggregate_no_away_goals_and_hosted_final(self):
        state = playoff('wales')
        self.assertEqual(next_fixture(state, 'semi')['home'], 'club-south')
        record_playoff_result(state, 'semi', '2027-05-01', [2, 1])
        before = deepcopy(state)
        with self.assertRaisesRegex(ValueError, 'Extra time is not permitted'):
            record_playoff_result(state, 'semi', '2027-05-08', [1, 0], extra=[0, 0], penalties=[4, 3])
        self.assertEqual(state, before)
        record_playoff_result(state, 'semi', '2027-05-08', [1, 0], penalties=[4, 3])
        self.assertEqual(state['outcomes']['semi']['winner'], 'club-north')
        self.assertEqual(next_fixture(state, 'final')['home'], 'club-north')
        record_playoff_result(state, 'final', '2027-05-15', [0, 1])
        self.assertEqual(state['outcomes']['final']['winner'], 'club-top14')
        self.assertEqual(restore_playoff(json.dumps(state)), state)

    def test_retries_resume_dependencies_and_corrupt_outcomes(self):
        state = playoff('france')
        with self.assertRaisesRegex(ValueError, 'unfinished'):
            next_fixture(state, 'final')
        first = record_playoff_result(state, 'semi1', '2027-05-01', [0, 0], penalties=[3, 4])
        state = restore_playoff(state)
        self.assertEqual(record_playoff_result(state, 'semi1', '2027-05-01', [0, 0], penalties=[3, 4]), first)
        self.assertEqual(len(state['results']), 1)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            record_playoff_result(state, 'semi1', '2027-05-01', [1, 0])
        record_playoff_result(state, 'semi2', '2027-05-01', [2, 0])
        self.assertEqual(next_fixture(state, 'final')['home'], 'club-r4')
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            record_playoff_result(state, 'final', '2027-05-01', [1, 0])
        broken = deepcopy(state)
        broken['outcomes']['semi1']['winner'] = 'club-r3'
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            restore_playoff(broken)
        broken = deepcopy(state)
        broken['results'].append(deepcopy(broken['results'][-1]))
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            restore_playoff(broken)

    def test_full_us_bracket_series_are_match_wins_and_save_safe(self):
        state = playoff('usa')
        day = date(2026, 10, 1)
        for tie in state['definition']['ties']:
            tid = tie['id']
            if tie['mode'] == 'best_of_three':
                first_home = next_fixture(state, tid)['home']
                record_playoff_result(state, tid, day.isoformat(), [8, 0])
                day += timedelta(days=1)
                self.assertNotEqual(next_fixture(state, tid)['home'], first_home)
                record_playoff_result(state, tid, day.isoformat(), [1, 0])
                day += timedelta(days=1)
                self.assertNotIn(tid, state['outcomes'])
                self.assertEqual(next_fixture(state, tid)['home'], first_home)
                record_playoff_result(state, tid, day.isoformat(), [0, 0], penalties=[3, 4])
                self.assertNotEqual(state['outcomes'][tid]['winner'], first_home)
            else:
                record_playoff_result(state, tid, day.isoformat(), [0, 0],
                                      extra=[0, 0] if tie['decider'] == 'extra_time_penalties' else None,
                                      penalties=[4, 3])
            state = restore_playoff(json.dumps(state))
            day += timedelta(days=1)
        self.assertIn('final', state['outcomes'])
        self.assertEqual(len(state['results']), 33)

    def test_invalid_scores_and_pre_career_events_are_atomic(self):
        for args in (('2025-01-01', [1, 0], None), ('2027-01-01', [True, 0], None),
                     ('2027-01-01', [1, 0], [4, 3]), ('2027-01-01', [0, 0], [4, 4])):
            state = playoff('france')
            before = deepcopy(state)
            with self.assertRaises(ValueError):
                record_playoff_result(state, 'semi1', args[0], args[1], penalties=args[2])
            self.assertEqual(state, before)

    def test_bracket_rejects_forward_dependency(self):
        graph = definition('france')
        graph['ties'][0]['entrants'][0] = 'winner:final'
        self.assertTrue(bracket_issues(graph))

    def test_reserves_and_licence_failures_do_not_invent_replacements(self):
        assessments = {'a': {'reserve': True}, 'b': {'reserve': False, 'licensed': True},
                       'c': {'reserve': False, 'licensed': False}}
        self.assertEqual(eligible_ranked_clubs(['a', 'b'], assessments, 1, True), ['b'])
        with self.assertRaisesRegex(ValueError, 'Licensing direction'):
            eligible_ranked_clubs(['c', 'b'], assessments, 1, True)

    def test_membership_transaction_conserves_named_clubs_and_is_idempotent(self):
        original = dict(memberships={'league': ['l'+str(i) for i in range(20)],
                                     'feeder': ['f'+str(i) for i in range(10)]})
        routes = [dict(club='l'+str(i), **{'from': 'league', 'to': 'feeder'},
                       decision_id='down-'+str(i), eligible=True) for i in range(2)]
        routes += [dict(club='f'+str(i), **{'from': 'feeder', 'to': 'league'},
                        decision_id='up-'+str(i), eligible=True) for i in range(6)]
        counts = {'league': 24, 'feeder': 6}
        result = settle_membership(original, '2026', routes, counts)
        self.assertEqual(len(original['memberships']['league']), 20)
        self.assertEqual(len(result['memberships']['league']), 24)
        self.assertEqual(settle_membership(result, '2026', routes, counts), result)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            settle_membership(result, '2026', routes[::-1], counts)
        with self.assertRaisesRegex(ValueError, 'closed'):
            settle_membership(original, '2026', routes, counts, ['league'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            settle_membership(original, '2026', routes+routes[:1], counts)
        with self.assertRaisesRegex(ValueError, 'counts'):
            settle_membership(original, '2026', routes, {'league': 20, 'feeder': 10})

    def test_all_approved_levels_mapped_without_claiming_verified_world(self):
        data = load()
        rows = league_coverage(data)
        self.assertEqual(len(rows), 14)
        self.assertEqual(sum(r['mapped_competitions'] for r in rows), 38)
        self.assertTrue(all(not r['missing_levels'] for r in rows))
        self.assertTrue(all(r['status'] == 'BLOCKED' for r in rows))
        self.assertTrue(all(r['structures_verified'] == 0 for r in rows))
        for country in data['countries']:
            for tier in country['tier_rules']:
                for graph in tier['league_structure']['brackets']:
                    self.assertEqual(bracket_issues(graph), [])
        data['status'] = 'VERIFIED'
        for country in data['countries']:
            for tier in country['tier_rules']:tier['status'] = 'VERIFIED'
        self.assertTrue(any('league structure:' in issue for issue in audit(data)))

    def test_split_math_is_checked_independently_of_evidence(self):
        tier = next(c for c in load_reference()['countries'] if c['id'] == 'wales')['tier_rules'][0]
        tier['league_structure']['regular_season']['games_before_split'] = 33
        self.assertIn('Split match counts do not reconcile.', structure_issues(tier, {}))


if __name__ == '__main__':
    unittest.main()
