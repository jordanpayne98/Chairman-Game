"""Sourced national access operations; inputs are resolved sporting decisions.

These legacy validation services do not activate a production career or infer
licences. GDD 0.18 supersedes their national formats for new careers.
"""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from .league_structures import _require, create_playoff, eligible_ranked_clubs


def _reference_tier(tier_id):
    """Load an explicitly superseded format, never the active shared profile."""
    path = Path(__file__).resolve().parents[1] / 'data' / 'reference_national_leagues_2026.json'
    reference = json.loads(path.read_text(encoding='utf-8'))
    return next(t for c in reference['countries'] for t in c['tier_rules'] if t['id'] == tier_id)


def _clubs(order, count):
    _require(len(order) == count and all(isinstance(c, str) and c for c in order)
             and len(set(order)) == count, 'Resolved table membership does not reconcile.')


def german_return_host(clubs, last_league_dates, first_leg_date, draw=None):
    """DFL SpOL 3(2): fewer free days hosts leg two; equality requires a draw."""
    _clubs(clubs, 2)
    _require(set(last_league_dates) == set(clubs), 'Missing last league fixture date.')
    first = date.fromisoformat(first_leg_date)
    rest = {c: (first-date.fromisoformat(last_league_dates[c])).days-1 for c in clubs}
    _require(min(rest.values()) >= 0, 'Playoff cannot precede completion of league fixtures.')
    if rest[clubs[0]] != rest[clubs[1]]:
        _require(draw is None, 'A draw cannot override the rest-day hosting rule.')
        host = min(rest, key=rest.get)
    else:
        _require(isinstance(draw, dict) and draw.get('decision_id') and draw.get('return_host') in clubs,
                 'Equal rest requires a recorded hosting draw.')
        host = draw['return_host']
    return dict(return_host=host, free_days=rest, draw=deepcopy(draw), source_id='GER-DFL-26')


def portuguese_playoff(upper_order, lower_order, assessments, draw, career_start):
    """Liga Portugal RC 31(1): first eligible challenger after two first-team promotions."""
    _clubs(upper_order, 18)
    _clubs(lower_order, 18)
    _require(not set(upper_order) & set(lower_order), 'Club assigned to both divisions.')
    candidates = eligible_ranked_clubs(lower_order, assessments, 3, skip_reserves=True)
    upper, lower = upper_order[15], candidates[2]
    _require(assessments.get(upper, {}).get('licensed') is True,
             'Upper participant eligibility requires direction.')
    _require(isinstance(draw, dict) and draw.get('decision_id') and draw.get('first_host') in (upper, lower),
             'A recorded Portuguese hosting draw is required.')
    definition = dict(id='portugal-top-access', slots=['upper', 'lower'],
                      ties=[dict(id='barrage', entrants=['slot:upper', 'slot:lower'], mode='aggregate',
                                 decider='extra_time_penalties',
                                 hosting='first' if draw['first_host'] == upper else 'second')],
                      outputs=['barrage'], source_ids=['POR-RC-26'], hosting_draw=deepcopy(draw))
    return create_playoff(definition, dict(upper=upper, lower=lower), [upper, lower], career_start)


def vacancy_candidate(candidates, admissions):
    """Explicit yes/no assessments; unknown facts cannot be treated as a refusal."""
    for club in candidates:
        assessment = admissions.get(club, {})
        _require(assessment.get('decision_id') and type(assessment.get('admitted')) is bool,
                 'Admission decision required: '+club)
        if assessment['admitted']:
            return dict(club=club, decision_id=assessment['decision_id'])
    raise ValueError('Association direction required: no admissible replacement.')


def portuguese_playoff_place(state, admissions):
    """RC 31(4): winner, then defeated finalist. No extra replacement inferred."""
    from .league_structures import restore_playoff
    state = restore_playoff(state)
    _require(state['definition'].get('id') == 'portugal-top-access', 'Wrong national playoff.')
    _require('barrage' in state['outcomes'], 'Playoff is unfinished.')
    outcome = state['outcomes']['barrage']
    return dict(vacancy_candidate([outcome['winner'], outcome['loser']], admissions), source_id='POR-RC-26')


def french_barrage_replacement(state, upper_order, admissions, vacancy_decision):
    """FFF annex 3: eligible defeated finalist, then upper ranks 17 and 18.

Call only for an independently established vacancy after the barrage.
"""
    from .league_structures import restore_playoff
    state = restore_playoff(state)
    _require(isinstance(vacancy_decision, str) and vacancy_decision,
             'Recorded post-barrage vacancy decision required.')
    _clubs(upper_order, 18)
    _require(state['definition'].get('id') == 'france-third-access', 'Wrong national playoff.')
    _require(state['entrants'].get('upper16') == upper_order[15], 'Upper participant does not reconcile.')
    _require('barrage' in state['outcomes'], 'Playoff is unfinished.')
    loser = state['outcomes']['barrage']['loser']
    return dict(vacancy_candidate([loser, *upper_order[16:18]], admissions),
                source_id='FRA-L3-26', vacancy_decision=vacancy_decision)


def argentine_national_seeds(zones, statistics, lot_order=None):
    """AFA 6823 art.7: zone rank, points, GD, goals scored, then recorded lot.

Zone orders must already include any separately resolved table ties.
"""
    _require(set(zones) == {'a', 'b'}, 'Two Argentine zones required.')
    for clubs in zones.values():
        _clubs(clubs, 18)
    _require(not set(zones['a']) & set(zones['b']), 'Duplicate zone membership.')
    slots = {zone+str(rank): club for zone, clubs in zones.items()
             for rank, club in enumerate(clubs[:8], 1)}
    position = {club: int(slot[1:]) for slot, club in slots.items()}
    keys = {}
    for club in slots.values():
        row = statistics.get(club, {})
        _require(all(type(row.get(k)) is int for k in ('points', 'gf', 'ga'))
                 and row['gf'] >= 0 and row['ga'] >= 0, 'Missing or invalid seeding statistics: '+club)
        keys[club] = (position[club], -row['points'], row['ga']-row['gf'], -row['gf'])
    if len(set(keys.values())) != len(keys):
        _require(isinstance(lot_order, dict) and lot_order.get('decision_id')
                 and len(lot_order.get('clubs', [])) == len(slots)
                 and set(lot_order['clubs']) == set(slots.values()), 'Recorded seeding lot required.')
        lottery = lot_order['clubs']
    else:
        lottery = list(slots.values())
    return slots, sorted(slots.values(), key=lambda c: (*keys[c], lottery.index(c)))


def _national_playoff(tier_id, entrants, seeds, assessments, career_start):
    for club in entrants.values():
        _require(assessments.get(club, {}).get('licensed') is True,
                 'Participant eligibility/withdrawal requires direction: '+club)
    tier = _reference_tier(tier_id)
    return create_playoff(tier['league_structure']['brackets'][0], entrants, seeds, career_start)


def argentine_national_playoff(zones, statistics, assessments, career_start, lot_order=None):
    entrants, seeds = argentine_national_seeds(zones, statistics, lot_order)
    state = _national_playoff('argentina-national-2026', entrants, seeds, assessments, career_start)
    state['definition']['seeding_evidence'] = dict(zones=deepcopy(zones), statistics=deepcopy(statistics),
                                                  lot_order=deepcopy(lot_order))
    return state


def argentine_metropolitan_playoff(order, assessments, career_start):
    _clubs(order, 22)
    entrants = {'r'+str(rank): order[rank-1] for rank in range(2, 10)}
    return _national_playoff('argentina-metropolitan-2026', entrants, order[1:9], assessments, career_start)


def french_access_playoff(upper_order, lower_order, assessments, career_start):
    """Annex 3bis withdrawals keep their empty bracket place; never invite rank 7.

Bye advances are administrative references in the frozen definition, not results.
Both sides vacant through the whole lower bracket requires association direction.
"""
    _clubs(upper_order, 18)
    _clubs(lower_order, 18)
    _require(not set(upper_order) & set(lower_order), 'Club assigned to both divisions.')
    entrants = {'r'+str(rank): lower_order[rank-1] for rank in range(3, 7)}
    entrants['upper16'] = upper_order[15]
    tier = _reference_tier('france-third-2026')
    graph = deepcopy(tier['league_structure']['brackets'][0])
    withdrawals = {}
    for slot, club in entrants.items():
        assessment = assessments.get(club, {})
        if assessment.get('withdrawn') is True:
            _require(slot != 'upper16' and assessment.get('decision_id'),
                     'Recorded lower-playoff withdrawal decision required.')
            withdrawals[slot] = dict(club=club, decision_id=assessment['decision_id'])
        else:
            _require(assessment.get('licensed') is True,
                     'Participant eligibility/withdrawal requires direction: '+club)
    if not withdrawals:
        return create_playoff(graph, entrants, list(entrants.values()), career_start)
    graph['withdrawal_decisions'] = withdrawals
    graph['administrative_byes'] = []
    retained = []
    next_refs = {}
    for tie in graph['ties'][:3]:
        refs = []
        for ref in tie['entrants']:
            kind, key = ref.split(':')
            replacement = (None if key in withdrawals else ref) if kind == 'slot' else next_refs[key]
            if replacement is not None:
                refs.append(replacement)
        if len(refs) == 2:
            tie['entrants'] = refs
            retained.append(tie)
            next_refs[tie['id']] = 'winner:'+tie['id']
        else:
            next_refs[tie['id']] = refs[0] if refs else None
            graph['administrative_byes'].append(dict(tie=tie['id'], advanced_reference=next_refs[tie['id']]))
    _require(next_refs['final'] is not None, 'Association direction required: no lower playoff participant remains.')
    barrage = graph['ties'][-1]
    barrage['entrants'][0] = next_refs['final']
    graph['ties'] = retained + [barrage]
    return create_playoff(graph, entrants, list(entrants.values()), career_start)
