"""Validate nation-supplied league round dates for the shared format.

This does not manufacture an official national calendar. Cup and international
dates enter as blackouts supplied by the same dated scheduling plan.
"""
from datetime import date

from .league_structures import _integer, _require, round_robin_rounds


def schedule_shared_rounds(tier, members, calendar):
    """Make home/away league fixtures after checking a full dated round plan."""
    _require(isinstance(calendar, dict) and isinstance(members, list) and
             len(members) == tier.get('membership') and
             tier.get('rulebook_profile') == f'english-tier-{tier.get("tier")}-2026' and
             tier.get('membership') in (20, 24),
             'Shared season membership or calendar missing.')
    source_ids = calendar.get('source_ids')
    _require(isinstance(source_ids, list) and source_ids and
             all(isinstance(x, str) and x for x in source_ids) and
             isinstance(calendar.get('plan_id'), str) and calendar['plan_id'],
             'Dated national calendar plan and provenance required.')
    rounds = round_robin_rounds(members, 2)
    supplied = calendar.get('round_dates')
    _require(isinstance(supplied, list) and len(supplied) == len(rounds) and
             isinstance(calendar.get('blocked_dates'), list) and
             _integer(calendar.get('minimum_rest_days')),
             'Every league round needs an authored date and rest policy.')
    try:
        start, end = date.fromisoformat(calendar['start']), date.fromisoformat(calendar['end'])
        dates = [date.fromisoformat(s) for s in supplied]
        blocked = {date.fromisoformat(s) for s in calendar['blocked_dates']}
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid authored national calendar date.') from exc
    _require(start <= end and all(start <= d <= end and d not in blocked for d in dates),
             'League round falls outside its window or on a blocked date.')
    _require(all((b-a).days > calendar['minimum_rest_days']
                 for a, b in zip(dates, dates[1:])),
             'Rounds overlap or violate the authored minimum rest interval.')
    fixtures = [dict(round=n, played_on=day.isoformat(), home=home, away=away)
                for n, (day, pairs) in enumerate(zip(dates, rounds), 1)
                for home, away in pairs]
    _require(len(fixtures) == tier['membership']*tier['format']['games_per_club']//2,
             'Authored league dates do not reconcile with approved match count.')
    return dict(plan_id=calendar['plan_id'], source_ids=source_ids[:],
                tier_id=tier['id'], fixtures=fixtures)
