import unittest
from copy import deepcopy

from club_chairman.content_gate import load
from club_chairman.shared_standings import completed_shared_table, shared_access_preview


def season(members):
    return [dict(home=home, away=away, goals=[0, 0])
            for home in members for away in members if home != away]


class SharedStandingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()
        cls.tiers = {t['tier']: t for c in cls.data['countries']
                     if c['id'] == 'england' for t in c['tier_rules']}

    def members(self, level):
        return [f'club-{n:02}' for n in range(self.tiers[level]['membership'])]

    def test_same_profile_works_across_all_fourteen_nations(self):
        for country in self.data['countries']:
            for tier in country['tier_rules']:
                members = [f'club-{n:02}' for n in range(tier['membership'])]
                result = completed_shared_table(tier, members, season(members))
                self.assertEqual(sum(len(r['clubs']) for r in result['rows']), tier['membership'])
                self.assertEqual(result['rows'][0]['stats'][members[0]]['played'],
                                 tier['format']['games_per_club'])

    def test_title_tie_requires_recorded_ruling_and_replays_identically(self):
        members = self.members(1)
        matches = season(members)
        for game in matches:
            if game['home'] in members[:2] and game['away'] not in members[:2]:
                game['goals'] = [2, 0]
            elif game['away'] in members[:2] and game['home'] not in members[:2]:
                game['goals'] = [0, 2]
        tied = completed_shared_table(self.tiers[1], members, matches)
        self.assertEqual(tied['unresolved'][0]['clubs'], members[:2])
        self.assertFalse(tied['complete'])
        ruling = dict(clubs=members[:2], order=members[1::-1],
                      decision_id='board-title-2027', basis='recorded neutral deciding match')
        ordered = completed_shared_table(self.tiers[1], members, matches,
                                         adjudications=[ruling])
        self.assertEqual(ordered['rows'][0]['clubs'], [members[1]])
        self.assertEqual(ordered['rows'][1]['clubs'], [members[0]])
        self.assertTrue(all(members[0] not in g['clubs'] and members[1] not in g['clubs']
                            for g in ordered['unresolved']))
        self.assertEqual(ordered, completed_shared_table(self.tiers[1], members[::-1],
                                                          matches[::-1], adjudications=[ruling]))

    def test_efl_points_deduction_and_later_ties_do_not_invent_discipline(self):
        members = self.members(2)
        matches = season(members)
        tied = completed_shared_table(self.tiers[2], members, matches)
        self.assertEqual(tied['unresolved'][0]['reason'],
                         'efl_disciplinary_missing')
        with self.assertRaisesRegex(ValueError, 'Recorded association ruling'):
            completed_shared_table(self.tiers[2], members, matches,
                                   adjudications=[dict(clubs=members, order=members,
                                                       decision_id='arbitrary', basis='claim')])
        discipline = {club: dict(first_42_penalty_points=n, matches_assessed=42,
                                 decision_id='discipline-'+club)
                      for n, club in enumerate(members)}
        separated = completed_shared_table(self.tiers[2], members, matches,
                                           disciplinary_totals=discipline)
        self.assertTrue(separated['complete'])
        self.assertEqual(separated['rows'][0]['clubs'], [members[0]])
        with self.assertRaisesRegex(ValueError, '42-match'):
            bad = deepcopy(discipline)
            bad[members[0]]['matches_assessed'] = 46
            completed_shared_table(self.tiers[2], members, matches,
                                   disciplinary_totals=bad)
        adjusted = completed_shared_table(self.tiers[2], members, matches,
                                          deductions={members[0]: 4})
        self.assertEqual(adjusted['rows'][-1]['clubs'], [members[0]])
        self.assertEqual(adjusted['rows'][-1]['stats'][members[0]]['points'], 42)

    def test_head_to_head_away_goals_and_seed_access(self):
        for level in (1, 2):
            members = self.members(level)
            matches = season(members)
            for game in matches:
                if game['home'] == members[0] and game['away'] == members[1]:
                    game['goals'] = [1, 0]
                elif game['home'] == members[1] and game['away'] == members[0]:
                    game['goals'] = [2, 1]
            deductions = {club: n for n, club in enumerate(members[2:])}
            table = completed_shared_table(self.tiers[level], members, matches,
                                           deductions=deductions)
            self.assertTrue(table['complete'])
            self.assertEqual([r['clubs'] for r in table['rows'][:2]],
                             [[members[0]], [members[1]]])
            access = shared_access_preview(self.tiers[level], members, matches,
                                           deductions=deductions)
            self.assertEqual(access['champion'], members[0])
            if level == 1:
                self.assertEqual(access['automatic_relegation_candidates'], members[-3:])
            else:
                self.assertEqual(access['automatic_promotion_candidates'], members[:2])
                self.assertEqual(access['playoff_seeds'], members[2:8])

    def test_access_refuses_a_tie_crossing_a_promotion_or_relegation_boundary(self):
        members = self.members(2)
        matches = season(members)
        with self.assertRaisesRegex(ValueError, 'Association direction'):
            shared_access_preview(self.tiers[2], members, matches)
        self.assertTrue(completed_shared_table(self.tiers[2], members, matches)['unresolved'])

    def test_nls_tie_does_not_invent_head_to_head_subcriteria(self):
        members = self.members(5)
        result = completed_shared_table(self.tiers[5], members, season(members))
        self.assertEqual(result['unresolved'][0]['reason'], 'fa_head_to_head_direction')

    def test_incomplete_corrupt_or_discretionary_input_is_rejected(self):
        members = self.members(3)
        matches = season(members)
        before = deepcopy(matches)
        for bad in (matches[:-1], matches[:-1] + matches[:1],
                    matches[:-1] + [dict(home=members[0], away=members[1], goals=[True, 0])]):
            with self.assertRaises(ValueError):
                completed_shared_table(self.tiers[3], members, bad)
        self.assertEqual(matches, before)
        with self.assertRaisesRegex(ValueError, 'Unused association'):
            completed_shared_table(self.tiers[3], members, matches,
                                   adjudications=[dict(clubs=['unknown'], order=['unknown'],
                                                       decision_id='x', basis='claim')])
        with self.assertRaisesRegex(ValueError, 'Recorded association ruling'):
            completed_shared_table(self.tiers[3], members, matches,
                                   adjudications=[dict(clubs=members, order=members,
                                                       decision_id='x', basis='')])
        altered = deepcopy(self.tiers[3])
        altered['progression']['automatic_promotion_ranks'] = [1, 2, 3]
        with self.assertRaisesRegex(ValueError, 'approved shared profile'):
            shared_access_preview(altered, members, matches)


if __name__ == '__main__':
    unittest.main()
