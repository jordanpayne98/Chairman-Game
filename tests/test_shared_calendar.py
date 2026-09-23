import unittest
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta

from club_chairman.content_gate import load
from club_chairman.shared_calendar import schedule_shared_rounds


def plan(tier):
    start = date(2026, 7, 1)
    count = 2*(tier['membership']-1)
    return dict(plan_id='synthetic-fixture-check', source_ids=['synthetic-test-plan'],
                start=start.isoformat(), end=(start+timedelta(days=7*count)).isoformat(),
                round_dates=[(start+timedelta(days=7*n)).isoformat()
                             for n in range(count)],
                blocked_dates=[], minimum_rest_days=2)


class SharedCalendarTests(unittest.TestCase):
    def test_each_national_tier_needs_full_dated_plan(self):
        for country in load()['countries']:
            for tier in country['tier_rules']:
                with self.subTest(country=country['id'], tier=tier['tier']):
                    clubs = [f'{country["id"]}-{tier["tier"]}-{n}'
                             for n in range(tier['membership'])]
                    output = schedule_shared_rounds(tier, clubs, plan(tier))
                    self.assertEqual(len(output['fixtures']),
                                     tier['membership']*tier['format']['games_per_club']//2)
                    hosted = Counter(f['home'] for f in output['fixtures'])
                    self.assertEqual(set(hosted.values()), {tier['membership']-1})

    def test_blackout_rest_short_window_and_missing_round_block_schedule(self):
        tier = next(c for c in load()['countries'] if c['id'] == 'england')['tier_rules'][1]
        clubs = [str(n) for n in range(tier['membership'])]
        original = plan(tier)
        for defect in ('cup_clash', 'short_window', 'missing_round', 'short_rest', 'no_source'):
            altered = deepcopy(original)
            if defect == 'cup_clash':
                altered['blocked_dates'] = [altered['round_dates'][3]]
            elif defect == 'short_window':
                altered['end'] = '2026-12-31'
            elif defect == 'missing_round':
                altered['round_dates'].pop()
            elif defect == 'short_rest':
                altered['round_dates'][1] = '2026-07-02'
            else:
                altered['source_ids'] = []
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                schedule_shared_rounds(tier, clubs, altered)
            self.assertEqual(original, plan(tier))


if __name__ == '__main__':
    unittest.main()
