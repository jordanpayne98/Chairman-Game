import json
import unittest
from copy import deepcopy
from datetime import date, timedelta

from club_chairman.league_access import (
    argentine_metropolitan_playoff, argentine_national_playoff, argentine_national_seeds,
    french_access_playoff, french_barrage_replacement, german_return_host,
    portuguese_playoff, portuguese_playoff_place,
)
from club_chairman.league_structures import (
    bracket_issues, next_fixture, record_playoff_result, restore_playoff, settle_membership,
)


def clubs(prefix, count):
    return [prefix+str(i) for i in range(1, count+1)]


def licences(order):
    return {c: dict(licensed=True, reserve=False) for c in order}


def admission(allowed):
    return {c: dict(admitted=v, decision_id='decision-'+c) for c, v in allowed.items()}


def complete_tie(state, tid, day, upset=False):
    tie = next(t for t in state['definition']['ties'] if t['id'] == tid)
    result = record_playoff_result(state, tid, day.isoformat(), [0, 1] if upset else [1, 0])
    if tie['mode'] == 'aggregate':
        day += timedelta(days=1)
        # Preserve the winner of leg one despite changing home/away order.
        result = record_playoff_result(state, tid, day.isoformat(), [1, 0] if upset else [0, 1])
    return day + timedelta(days=1), result


class NationalLeagueAccessTests(unittest.TestCase):
    def test_german_rest_days_override_division_and_require_draw_only_when_equal(self):
        dates = {'upper': '2027-05-15', 'lower': '2027-05-16'}
        result = german_return_host(['upper', 'lower'], dates, '2027-05-20')
        self.assertEqual(result['return_host'], 'lower')
        self.assertEqual(result['free_days'], {'upper': 4, 'lower': 3})
        with self.assertRaisesRegex(ValueError, 'override'):
            german_return_host(['upper', 'lower'], dates, '2027-05-20', {'decision_id': 'x', 'return_host': 'upper'})
        dates['upper'] = dates['lower']
        with self.assertRaisesRegex(ValueError, 'recorded hosting draw'):
            german_return_host(['upper', 'lower'], dates, '2027-05-20')
        result = german_return_host(['upper', 'lower'], dates, '2027-05-20', {'decision_id': 'lot-1', 'return_host': 'upper'})
        self.assertEqual(result['return_host'], 'upper')
        with self.assertRaisesRegex(ValueError, 'precede'):
            german_return_host(['upper', 'lower'], dates, '2027-05-16')

    def test_portuguese_reserves_draw_extra_time_and_failed_winner_licence(self):
        upper, lower = clubs('u', 18), clubs('l', 18)
        assessments = licences(upper+lower)
        assessments['l1']['reserve'] = True
        assessments['l3']['reserve'] = True
        draw = {'decision_id': 'draw-1', 'first_host': 'u16'}
        state = portuguese_playoff(upper, lower, assessments, draw, '2026-07-01')
        self.assertEqual(state['entrants']['lower'], 'l5')
        self.assertEqual(next_fixture(state, 'barrage')['home'], 'u16')
        record_playoff_result(state, 'barrage', '2027-05-20', [0, 0])
        record_playoff_result(state, 'barrage', '2027-05-27', [0, 0], extra=[1, 0])
        state = restore_playoff(json.dumps(state))
        self.assertEqual(state['outcomes']['barrage']['winner'], 'l5')
        decisions = admission({'l5': False, 'u16': True})
        place = portuguese_playoff_place(state, decisions)
        self.assertEqual(place['club'], 'u16')
        with self.assertRaisesRegex(ValueError, 'Admission decision'):
            portuguese_playoff_place(state, admission({'u16': True}))
        with self.assertRaisesRegex(ValueError, 'no admissible'):
            portuguese_playoff_place(state, admission({'l5': False, 'u16': False}))
        assessments['l2']['licensed'] = False
        with self.assertRaisesRegex(ValueError, 'Licensing direction'):
            portuguese_playoff(upper, lower, assessments, draw, '2026-07-01')

    def test_portuguese_admitted_winner_drives_balanced_membership_exchange(self):
        upper, lower = clubs('u', 18), clubs('l', 18)
        state = portuguese_playoff(upper, lower, licences(upper+lower),
                                  {'decision_id': 'draw', 'first_host': 'l3'}, '2026-07-01')
        record_playoff_result(state, 'barrage', '2027-05-20', [1, 0])
        record_playoff_result(state, 'barrage', '2027-05-27', [0, 1])
        place = portuguese_playoff_place(state, admission({'l3': True}))
        self.assertEqual(place['club'], 'l3')
        routes = []
        for origin, destination, movers in [('upper', 'lower', ['u16', 'u17', 'u18']),
                                            ('lower', 'upper', ['l1', 'l2', place['club']])]:
            for club in movers:
                routes.append(dict(club=club, **{'from': origin, 'to': destination}, eligible=True, decision_id='sport-'+club))
        result = settle_membership({'memberships': {'upper': upper, 'lower': lower}}, '2026/27', routes,
                                   {'upper': 18, 'lower': 18})
        self.assertTrue({'l1', 'l2', 'l3'} <= set(result['memberships']['upper']))
        self.assertNotIn('u16', result['memberships']['upper'])

    def test_french_complete_barrage_and_vacancy_priority(self):
        upper, lower = clubs('u', 18), clubs('l', 18)
        state = french_access_playoff(upper, lower, licences(upper+lower), '2026-07-01')
        record_playoff_result(state, 'semi1', '2027-05-01', [0, 1])  # sixth beats third
        record_playoff_result(state, 'semi2', '2027-05-01', [1, 0])
        self.assertEqual(next_fixture(state, 'final')['home'], 'l4')
        record_playoff_result(state, 'final', '2027-05-08', [1, 0])
        self.assertEqual(next_fixture(state, 'barrage')['home'], 'l4')
        record_playoff_result(state, 'barrage', '2027-05-15', [0, 0])
        self.assertEqual(next_fixture(state, 'barrage')['home'], 'u16')
        record_playoff_result(state, 'barrage', '2027-05-22', [0, 0], extra=[0, 0], penalties=[4, 3])
        state = restore_playoff(state)
        replacement = french_barrage_replacement(state, upper,
                            admission({'l4': False, 'u17': True}), 'vacancy-1')
        self.assertEqual(replacement['club'], 'u17')
        replacement = french_barrage_replacement(state, upper,
                            admission({'l4': False, 'u17': False, 'u18': True}), 'vacancy-1')
        self.assertEqual(replacement['club'], 'u18')
        with self.assertRaisesRegex(ValueError, 'Admission decision'):
            french_barrage_replacement(state, upper, admission({'u17': True}), 'vacancy-1')
        assessments = licences(upper+lower);assessments['l6']['licensed'] = False
        with self.assertRaisesRegex(ValueError, 'withdrawal requires direction'):
            french_access_playoff(upper, lower, assessments, '2026-07-01')

    def test_argentine_metropolitan_reseeds_survivors_after_upsets(self):
        order = clubs('m', 22)
        state = argentine_metropolitan_playoff(order, licences(order), '2026-01-01')
        day = date(2026, 11, 1)
        # Lower seed hosts first leg: home wins mean four upsets.
        for tid in ('q1', 'q2', 'q3', 'q4'):
            day, _ = complete_tie(state, tid, day)
        self.assertEqual(next_fixture(state, 's1')['home'], 'm9')
        self.assertEqual(next_fixture(state, 's1')['away'], 'm6')
        self.assertEqual(next_fixture(state, 's2')['home'], 'm8')
        self.assertEqual(next_fixture(state, 's2')['away'], 'm7')
        for tid in ('s1', 's2', 'final'):
            record_playoff_result(state, tid, day.isoformat(), [0, 0])
            day += timedelta(days=1)
            record_playoff_result(state, tid, day.isoformat(), [0, 0], penalties=[3, 4])
            day += timedelta(days=1)
            state = restore_playoff(json.dumps(state))
        self.assertIn('final', state['outcomes'])
        self.assertEqual(len(state['results']), 14)

    def test_french_all_nonempty_withdrawal_combinations_keep_bracket_places(self):
        upper, lower = clubs('u', 18), clubs('l', 18)
        for mask in range(1, 15):
            with self.subTest(mask=mask):
                assessments = licences(upper+lower)
                withdrawn = {lower[2+i] for i in range(4) if mask & (1 << i)}
                for club in withdrawn:
                    assessments[club] = dict(withdrawn=True, decision_id='withdraw-'+club)
                state = french_access_playoff(upper, lower, assessments, '2026-07-01')
                self.assertTrue(state['definition']['administrative_byes'])
                self.assertNotIn('l7', state['entrants'].values())
                self.assertEqual(state['results'], [])
                day = date(2027, 5, 1)
                for tie in state['definition']['ties']:
                    fixture = next_fixture(state, tie['id'])
                    self.assertFalse(withdrawn & {fixture['home'], fixture['away']})
                    day, _ = complete_tie(state, tie['id'], day)
                    state = restore_playoff(json.dumps(state))
                self.assertIn('barrage', state['outcomes'])
                self.assertTrue(all(r['home'] not in withdrawn and r['away'] not in withdrawn for r in state['results']))
        for club in lower[2:6]:
            assessments[club] = dict(withdrawn=True, decision_id='withdraw-'+club)
        with self.assertRaisesRegex(ValueError, 'no lower playoff participant'):
            french_access_playoff(upper, lower, assessments, '2026-07-01')

    def test_french_withdrawal_needs_a_recorded_decision(self):
        upper, lower = clubs('u', 18), clubs('l', 18)
        assessments = licences(upper+lower)
        assessments['l6'] = dict(withdrawn=True)
        with self.assertRaisesRegex(ValueError, 'withdrawal decision'):
            french_access_playoff(upper, lower, assessments, '2026-07-01')

    def test_argentine_cross_zone_order_and_required_lots(self):
        zones = {'a': clubs('a', 18), 'b': clubs('b', 18)}
        stats = {c: {'points': 40, 'gf': 30, 'ga': 20} for c in zones['a']+zones['b']}
        with self.assertRaisesRegex(ValueError, 'seeding lot'):
            argentine_national_seeds(zones, stats)
        lot = {'decision_id': 'lot-1', 'clubs': zones['b'][:8]+zones['a'][:8]}
        _, order = argentine_national_seeds(zones, stats, lot)
        self.assertEqual(order[:4], ['b1', 'a1', 'b2', 'a2'])
        stats['a2']['points'] = 41
        _, order = argentine_national_seeds(zones, stats, lot)
        self.assertEqual(order[2:4], ['a2', 'b2'])

    def test_argentine_title_loser_reentry_draw_advantage_and_final_penalties(self):
        zones = {'a': clubs('a', 18), 'b': clubs('b', 18)}
        all_clubs = zones['a']+zones['b']
        stats = {c: dict(points=50 if c.startswith('a') else 49, gf=30, ga=20) for c in all_clubs}
        state = argentine_national_playoff(zones, stats, licences(all_clubs), '2026-01-01')
        record_playoff_result(state, 'title', '2026-10-31', [1, 0])
        for i in range(1, 8):
            record_playoff_result(state, 'first'+str(i), '2026-10-31', [0, 0])
        # The title-final loser receives top seed regardless of other clubs' points.
        self.assertEqual(next_fixture(state, 'q1')['away'], 'b1')
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            record_playoff_result(state, 'q1', '2026-10-31', [0, 0])
        state = restore_playoff(json.dumps(state))
        day = date(2026, 11, 7)
        for tid in ('q1', 'q2', 'q3', 'q4', 's1', 's2'):
            first = next_fixture(state, tid)
            record_playoff_result(state, tid, day.isoformat(), [0, 0])
            day += timedelta(days=1)
            record_playoff_result(state, tid, day.isoformat(), [0, 0])
            self.assertEqual(state['outcomes'][tid]['winner'], first['away'])
            day += timedelta(days=1)
        record_playoff_result(state, 'final', day.isoformat(), [0, 0])
        day += timedelta(days=1)
        before = deepcopy(state)
        with self.assertRaisesRegex(ValueError, 'Shootout required'):
            record_playoff_result(state, 'final', day.isoformat(), [0, 0])
        self.assertEqual(state, before)
        record_playoff_result(state, 'final', day.isoformat(), [0, 0], penalties=[3, 4])
        state = restore_playoff(json.dumps(state))
        self.assertEqual(len(state['results']), 22)
        self.assertNotEqual(state['outcomes']['title']['winner'], state['outcomes']['final']['winner'])
        corrupt = deepcopy(state);corrupt['seed_order'][0:2] = corrupt['seed_order'][0:2][::-1]
        with self.assertRaisesRegex(ValueError, 'Seeding evidence'):
            restore_playoff(corrupt)

    def test_reseeding_waits_for_entire_round_and_rejects_forward_pools(self):
        order = clubs('m', 22)
        state = argentine_metropolitan_playoff(order, licences(order), '2026-01-01')
        complete_tie(state, 'q1', date(2026, 11, 1))
        with self.assertRaisesRegex(ValueError, 'unfinished'):
            next_fixture(state, 's1')
        graph = deepcopy(state['definition'])
        graph['seed_pools']['semis'][0] = 'winner:final'
        self.assertTrue(bracket_issues(graph))


if __name__ == '__main__':
    unittest.main()
