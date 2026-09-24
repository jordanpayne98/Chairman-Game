"""Settle an ordinary shared-English pyramid from recorded sporting outcomes.

All club identities, playoff decisions and feeder entrants are supplied by the
caller. Cessations and genuine sporting vacancies need a separate recorded
decision and cannot take this ordinary path.
"""
from .league_structures import _require, settle_membership
from .shared_standings import shared_access_preview


def settle_shared_pyramid(country, state, season, results, playoffs,
                          feeder_entrants, deductions=None,
                          adjudications=None, disciplinary_totals=None):
    """Exchange all playable levels plus an explicitly named background feeder.

    Membership keys are the actual tier IDs and ``feeder``. Playoff results are
    recorded dicts with winner, decision_id and eligible=True; this function
    never generates a bracket or treats a candidate as a winner. Feeder
    entrants use the same fields with ``club`` instead of ``winner``.
    """
    tiers = country['tier_rules']
    depth = country['minimum_playable_depth']
    _require(1 <= depth <= 5 and len(tiers) == depth and
             sorted(t['tier'] for t in tiers) == list(range(1, depth+1)) and
             country.get('league_model') == 'shared-english-2026-v1',
             'A complete shared national pyramid is required.')
    _require(isinstance(season, str) and season and
             isinstance(results, dict) and isinstance(playoffs, dict) and
             isinstance(feeder_entrants, list), 'Invalid season exchange inputs.')
    _require(season not in state.get('settlements', {}),
             'An already settled season requires its original receipt and replay path.')
    keys = {t['tier']: t['id'] for t in tiers}
    members = state.get('memberships', {})
    _require(set(members) == set(keys.values()) | {'feeder'} and
             all(isinstance(v, list) for v in members.values()),
             'Named membership for every tier and its feeder is required.')
    deductions = deductions or {}
    adjudications = adjudications or {}
    disciplinary_totals = disciplinary_totals or {}
    _require(all(isinstance(d, dict) and set(d) <= set(keys)
                 for d in (results, deductions, adjudications, disciplinary_totals)) and
             set(results) == set(keys), 'Incomplete or unknown tier outcome.')
    access = {}
    for level, tier_id in keys.items():
        tier = next(t for t in tiers if t['tier'] == level)
        access[level] = shared_access_preview(
            tier, members[tier_id], results[level], deductions.get(level),
            adjudications.get(level),
            disciplinary_totals=disciplinary_totals.get(level))
    _require(set(playoffs) == {n for n in keys if n in (2, 3, 4, 5)},
             'Every playable playoff outcome must be recorded.')

    def route(club, origin, destination, decision_id):
        _require(isinstance(club, str) and club and
                 isinstance(decision_id, str) and decision_id,
                 'Named club and recorded movement decision required.')
        return dict(club=club, **{'from': origin, 'to': destination},
                    decision_id=decision_id, eligible=True)

    movements = []
    for level in range(1, depth):
        upper = access[level]['automatic_relegation_candidates']
        lower = access[level+1]['automatic_promotion_candidates']
        playoff = playoffs[level+1]
        if not isinstance(playoff, dict):
            candidate_valid = False
        elif level+1 == 5:
            # The playoff bracket is still pending verification. A recorded
            # sporting winner must occupy one of the six qualifying places;
            # no separate admission or licence approval is required.
            candidate_valid = any(row['rank'] in range(2, 8) and
                                  row['clubs'] == [playoff.get('winner')]
                                  for row in access[5]['table']['rows'])
        else:
            candidate_valid = playoff.get('winner') in access[level+1]['playoff_seeds']
        _require(isinstance(playoff, dict) and
                 candidate_valid and
                 playoff.get('eligible') is True and playoff.get('decision_id'),
                 'Recorded eligible playoff winner required for playable exchange.')
        promoted = lower+[playoff['winner']]
        _require(len(upper) == len(promoted),
                 'Ordinary exchange counts require association direction.')
        movements.extend(route(c, keys[level], keys[level+1],
                               'ordinary-relegation-'+season+'-'+c) for c in upper)
        movements.extend(route(c, keys[level+1], keys[level],
                               playoff['decision_id'] if c == playoff['winner']
                               else 'automatic-promotion-'+season+'-'+c) for c in promoted)

    bottom = access[depth]['automatic_relegation_candidates']
    _require(len(feeder_entrants) == len(bottom),
             'Background feeder entrants must balance ordinary relegation.')
    selected = []
    for entry in feeder_entrants:
        _require(isinstance(entry, dict) and entry.get('club') in members['feeder'] and
                 entry.get('eligible') is True and entry.get('decision_id'),
                 'Recorded eligible background feeder entrant required.')
        selected.append(entry['club'])
        movements.append(route(entry['club'], 'feeder', keys[depth], entry['decision_id']))
    _require(len(set(selected)) == len(selected), 'Duplicate feeder promotion.')
    movements.extend(route(c, keys[depth], 'feeder',
                           'ordinary-relegation-'+season+'-'+c) for c in bottom)
    expected = {t['id']: t['membership'] for t in tiers}
    expected['feeder'] = len(members['feeder'])
    return settle_membership(state, season, movements, expected)
