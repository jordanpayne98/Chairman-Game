"""Production league structure checks and result-driven validation operations.

These services do not activate a partial pack in a career. Definitions, accepted
results and membership decisions remain distinct; no club or result is generated.
"""
from copy import deepcopy
from datetime import date
import json


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def round_robin_rounds(members, cycles):
    """Deterministic pairings, including odd-team byes; dates are assigned later."""
    _require(isinstance(members, list) and len(members) >= 2
             and all(isinstance(x, str) and x for x in members)
             and len(members) == len(set(members)), 'Invalid round-robin membership.')
    _require(_integer(cycles, 1), 'Invalid round-robin cycle count.')
    ring = sorted(members)
    if len(ring) % 2:
        ring.append(None)
    base = []
    for r in range(len(ring) - 1):
        pairs = []
        for i in range(len(ring) // 2):
            a, b = ring[i], ring[-1-i]
            if a is not None and b is not None:
                pairs.append([b, a] if (r+i) % 2 else [a, b])
        base.append(pairs)
        ring = [ring[0], ring[-1], *ring[1:-1]]
    return [deepcopy(pairs) if cycle % 2 == 0 else [[b, a] for a, b in pairs]
            for cycle in range(cycles) for pairs in base]


def split_sections(final_order, sizes, points):
    """Freeze sections from an already resolved table, preserving all points."""
    _require(all(_integer(n, 2) for n in sizes) and sum(sizes) == len(final_order),
             'Split sizes do not reconcile.')
    _require(len(final_order) == len(set(final_order)) and set(points) == set(final_order)
             and all(type(v) is int for v in points.values()), 'Invalid split standings.')
    offset = 0
    sections = []
    for size in sizes:
        clubs = final_order[offset:offset+size]
        sections.append(dict(members=list(clubs), points={c: points[c] for c in clubs},
                             rank_start=offset+1, rank_end=offset+size))
        offset += size
    return sections


def combine_sections(sections, orders):
    """Never let a bottom-section club overtake a top-section club on points."""
    _require(len(sections) == len(orders), 'Missing split section.')
    final = []
    for section, order in zip(sections, orders):
        _require(len(order) == len(set(order)) and set(order) == set(section['members']),
                 'Section order does not reconcile.')
        final.extend(order)
    _require(len(final) == len(set(final)), 'Club appears in multiple sections.')
    return final


def bracket_issues(definition):
    errors = []
    slots = definition.get('slots', [])
    if not slots or len(slots) != len(set(slots)):
        errors.append('Playoff slots are missing or duplicated.')
    seen = set()
    pools = definition.get('seed_pools', {})
    def basic_reference(ref):
        if not isinstance(ref, str) or ':' not in ref:
            return False
        kind, key = ref.split(':', 1)
        return (kind == 'slot' and key in slots) or (kind in ('winner', 'loser') and key in seen)
    for tie in definition.get('ties', []):
        tid = tie.get('id')
        if not tid or tid in seen:
            errors.append('Playoff tie ID missing or duplicated.')
        refs = tie.get('entrants', [])
        if len(refs) != 2 or len(set(refs)) != 2:
            errors.append('A tie needs two distinct entrant references.')
        for ref in refs:
            if isinstance(ref, str) and ref.startswith('seed:'):
                parts = ref.split(':')
                pool = pools.get(parts[1], []) if len(parts) == 3 else []
                if (not pool or len(pool) != len(set(pool)) or not all(basic_reference(r) for r in pool)
                        or not parts[-1].isdigit() or not 1 <= int(parts[-1]) <= len(pool)):
                    errors.append('Invalid or forward reseeding pool: '+ref)
                continue
            if ':' not in ref:
                errors.append('Invalid entrant reference: '+ref)
                continue
            kind, key = ref.split(':', 1)
            if not ((kind == 'slot' and key in slots) or
                    (kind in ('winner', 'loser') and key in seen)):
                errors.append('Missing or forward playoff dependency: '+ref)
        if tie.get('mode') not in ('single', 'aggregate', 'best_of_three'):
            errors.append('Unsupported tie format.')
        if tie.get('decider') not in ('penalties', 'extra_time_penalties', 'higher_seed'):
            errors.append('Unverified tie resolution.')
        if tie.get('hosting') not in ('first', 'second', 'higher_seed', 'lower_seed_first', 'neutral'):
            errors.append('Missing playoff hosting rule.')
        seen.add(tid)
    if not seen:
        errors.append('Playoff has no ties.')
    if any(tid not in seen for tid in definition.get('outputs', [])) or not definition.get('outputs'):
        errors.append('Missing playoff output.')
    return errors


def create_playoff(definition, entrants, seed_order, career_start):
    """Freeze supplied eligible entrants; caller must resolve national access first."""
    _require(not bracket_issues(definition), '; '.join(bracket_issues(definition)))
    _require(set(entrants) == set(definition['slots']), 'Playoff slots do not reconcile.')
    clubs = list(entrants.values())
    _require(all(isinstance(c, str) and c for c in clubs) and len(clubs) == len(set(clubs)),
             'Duplicate or invalid playoff entrant.')
    _require(len(seed_order) == len(clubs) and set(seed_order) == set(clubs),
             'Playoff seed order does not reconcile.')
    date.fromisoformat(career_start)
    return deepcopy(dict(schema=1, mode='content_validation', definition=definition,
                         entrants=entrants, seed_order=seed_order, career_start=career_start,
                         results=[], outcomes={}))


def _entrant(state, reference):
    kind, key = reference.split(':', 1)
    if kind == 'seed':
        pool_id, rank = key.split(':')
        clubs = [_entrant(state, r) for r in state['definition']['seed_pools'][pool_id]]
        _require(len(clubs) == len(set(clubs)), 'Duplicate club in reseeding pool.')
        return sorted(clubs, key=state['seed_order'].index)[int(rank)-1]
    if kind == 'slot':
        return state['entrants'][key]
    _require(key in state['outcomes'], 'Preceding playoff tie is unfinished: '+key)
    return state['outcomes'][key][kind]


def _dependencies(definition, reference):
    kind, key = reference.split(':', 1)
    if kind == 'seed':
        pool, _ = key.split(':')
        return [r.split(':', 1)[1] for r in definition['seed_pools'][pool]
                if not r.startswith('slot:')]
    return [] if kind == 'slot' else [key]


def next_fixture(state, tie_id):
    tie = next((t for t in state['definition']['ties'] if t['id'] == tie_id), None)
    _require(tie is not None, 'Unknown playoff tie.')
    _require(tie_id not in state['outcomes'], 'Playoff tie already complete.')
    a, b = [_entrant(state, ref) for ref in tie['entrants']]
    _require(a != b, 'A club cannot play itself.')
    played = [r for r in state['results'] if r['tie'] == tie_id]
    leg = len(played)+1
    higher = min((a, b), key=state['seed_order'].index)
    lower = b if higher == a else a
    hosting = tie['hosting']
    first = {'first': a, 'second': b, 'neutral': a, 'higher_seed': higher,
             'lower_seed_first': lower}[hosting]
    if tie['mode'] == 'best_of_three':
        home = higher if leg % 2 else lower
    else:
        home = first if leg % 2 else (b if first == a else a)
    return dict(id=tie_id+':'+str(leg), tie=tie_id, leg=leg, home=home,
                away=b if home == a else a, neutral=hosting == 'neutral')


def record_playoff_result(state, tie_id, played_on, goals, extra=None, penalties=None):
    """Accept actual score components atomically; identical retries are harmless."""
    record = dict(tie=tie_id, played_on=played_on, goals=goals, extra=extra, penalties=penalties)
    # One match per tie per date; an earlier leg is retryable after later legs.
    existing = next((r for r in state['results'] if r['tie'] == tie_id and r['played_on'] == played_on), None)
    if existing:
        _require(all(existing[k] == v for k, v in record.items()), 'Conflicting playoff result retry.')
        return deepcopy(existing)
    day = date.fromisoformat(played_on)
    _require(day >= date.fromisoformat(state['career_start']), 'Pre-career result is forbidden.')
    if state['results']:
        _require(day >= date.fromisoformat(state['results'][-1]['played_on']), 'Results must arrive in date order.')
    fixture = next_fixture(state, tie_id)
    tie = next(t for t in state['definition']['ties'] if t['id'] == tie_id)
    for ref in tie['entrants']:
        for key in _dependencies(state['definition'], ref):
            prior = max(r['played_on'] for r in state['results'] if r['tie'] == key)
            _require(played_on > prior, 'A dependent round must follow its predecessor.')
    def score(value):
        return isinstance(value, list) and len(value) == 2 and all(_integer(n) for n in value)
    _require(score(goals), 'Invalid regulation score.')
    _require(extra is None or score(extra), 'Invalid extra-time score.')
    _require(penalties is None or (score(penalties) and penalties[0] != penalties[1]),
             'A shootout must have a winner.')
    home, away = fixture['home'], fixture['away']
    _require(not any(r['played_on'] == played_on and {home, away} & {r['home'], r['away']}
                     for r in state['results']), 'Club already played on this date.')
    total = {home: goals[0], away: goals[1]}
    prior = [r for r in state['results'] if r['tie'] == tie_id]
    final_leg = tie['mode'] != 'aggregate' or fixture['leg'] == 2
    if tie['mode'] == 'aggregate':
        for result in prior:
            total[result['home']] += result['goals'][0]
            total[result['away']] += result['goals'][1]
    winner = None
    tied = total[home] == total[away]
    if not final_leg:
        _require(extra is None and penalties is None, 'First leg cannot have a decider.')
    elif not tied:
        _require(extra is None and penalties is None, 'Decider supplied for a decided score.')
        winner = max(total, key=total.get)
    elif tie['decider'] == 'higher_seed':
        _require(extra is None and penalties is None, 'This tie is resolved by higher seed.')
        winner = min((home, away), key=state['seed_order'].index)
    else:
        if tie['decider'] == 'extra_time_penalties':
            _require(extra is not None, 'Extra-time score required.')
            total[home] += extra[0]
            total[away] += extra[1]
        else:
            _require(extra is None, 'Extra time is not permitted.')
        if total[home] == total[away]:
            _require(penalties is not None, 'Shootout required.')
            winner = home if penalties[0] > penalties[1] else away
        else:
            _require(penalties is None, 'Shootout supplied after decisive extra time.')
            winner = max(total, key=total.get)
    result = dict(record, **fixture, winner=winner)
    outcome = winner
    if tie['mode'] == 'best_of_three':
        wins = sum(r['winner'] == winner for r in prior)+1
        outcome = winner if wins == 2 else None
    # All validation precedes mutation.
    state['results'].append(deepcopy(result))
    if outcome:
        state['outcomes'][tie_id] = dict(winner=outcome, loser=away if outcome == home else home)
    return deepcopy(result)


def restore_playoff(payload):
    """Recompute every outcome; never trust a persisted winner or hosting field."""
    source = json.loads(payload) if isinstance(payload, str) else deepcopy(payload)
    _require(source.get('schema') == 1 and source.get('mode') == 'content_validation', 'Unsupported playoff snapshot.')
    state = create_playoff(source['definition'], source['entrants'], source['seed_order'], source['career_start'])
    seed_evidence = source['definition'].get('seeding_evidence')
    if seed_evidence is not None:
        from .league_access import argentine_national_seeds
        _require(source['definition'].get('id') == 'argentina-national-access', 'Unknown seeding evidence.')
        entrants, order = argentine_national_seeds(**seed_evidence)
        _require(entrants == state['entrants'] and order == state['seed_order'], 'Seeding evidence does not reconcile.')
    for result in source['results']:
        accepted = record_playoff_result(state, result['tie'], result['played_on'], result['goals'],
                                         result['extra'], result['penalties'])
        _require(accepted == result, 'Playoff result does not reconcile.')
    _require(state == source, 'Playoff snapshot does not reconcile.')
    return state


def eligible_ranked_clubs(order, assessments, count, skip_reserves=False):
    """No licence-failure substitution is inferred from a sorting operation."""
    _require(_integer(count, 1) and len(order) == len(set(order)), 'Invalid promotion selection.')
    selected = []
    for club in order:
        record = assessments.get(club, {})
        _require(type(record.get('reserve')) is bool, 'Missing reserve status: '+club)
        if record['reserve'] and skip_reserves:
            continue
        _require(record.get('licensed') is True, 'Licensing direction required: '+club)
        selected.append(club)
        if len(selected) == count:
            return selected
    raise ValueError('Not enough eligible clubs; association direction required.')


def settle_membership(state, season, routes, expected_counts, closed_competitions=()):
    """Apply explicit sporting decisions together, including named feeder clubs.

Caller supplies adjudicated routes, not unverified table guesses. This is a
membership transaction primitive, not a national qualification resolver.
"""
    receipt = dict(season=season, routes=deepcopy(routes), expected_counts=deepcopy(expected_counts),
                   closed_competitions=list(closed_competitions))
    previous = state.get('settlements', {}).get(season)
    if previous:
        _require(previous == receipt, 'Conflicting season settlement retry.')
        return deepcopy(state)
    members = deepcopy(state['memberships'])
    _require(set(expected_counts) == set(members), 'Expected counts must cover every division.')
    all_clubs = [c for clubs in members.values() for c in clubs]
    _require(len(all_clubs) == len(set(all_clubs)), 'Duplicate existing club membership.')
    moved = set()
    for route in routes:
        club, origin, destination = route['club'], route['from'], route['to']
        _require(origin in members and destination in members and origin != destination,
                 'Unknown or identical movement endpoint.')
        _require(origin not in closed_competitions and destination not in closed_competitions,
                 'Sporting movement into or out of a closed competition is forbidden.')
        _require(club not in moved and club in state['memberships'][origin], 'Duplicate or invalid club movement.')
        _require(route.get('decision_id') and route.get('eligible') is True,
                 'Movement requires recorded sporting and eligibility decisions.')
        moved.add(club)
        members[origin].remove(club)
        members[destination].append(club)
    _require(all(_integer(n, 1) and len(members[k]) == n for k, n in expected_counts.items()),
             'Next-season membership counts do not reconcile.')
    _require(sorted(c for clubs in members.values() for c in clubs) == sorted(all_clubs),
             'Season movement created or lost a club.')
    result = deepcopy(state)
    result['memberships'] = members
    result.setdefault('settlements', {})[season] = receipt
    return result


def structure_issues(tier, sources):
    """Evidence completeness is independent of later population/finance passes."""
    structure = tier.get('league_structure')
    if not isinstance(structure, dict):
        return ['League structure not mapped.']
    errors = list(structure.get('open_requirements', []))
    if tier.get('selection_status') == 'PROPOSED_CONTENT_CHOICE':
        errors.append('Competition selection requires an approved content decision.')
    for field in ('tiebreakers', 'progression', 'calendar'):
        if not tier.get(field):
            errors.append(field+': operative definition missing.')
    for component in ('membership', 'format', 'tiebreakers', 'progression', 'playoffs', 'calendar'):
        evidence = structure.get('evidence', {}).get(component, {})
        if evidence.get('status') != 'VERIFIED':
            errors.append(component+': operative evidence incomplete.')
        if not evidence.get('source_ids') or any(sources.get(s, {}).get('status') != 'VERIFIED'
                                                 for s in evidence.get('source_ids', [])):
            errors.append(component+': verified source reference missing.')
    n = tier.get('membership')
    if not _integer(n, 2):
        errors.append('Membership count missing or invalid.')
    fmt = structure.get('regular_season', {})
    if fmt.get('kind') == 'round_robin':
        cycles = fmt.get('cycles')
        if not _integer(cycles, 1) or not _integer(n, 2) or fmt.get('games_per_club') != (n-1)*cycles:
            errors.append('Round-robin match counts do not reconcile.')
    elif fmt.get('kind') == 'split':
        sizes = fmt.get('sections', [])
        if not sizes or any(not _integer(s, 2) for s in sizes) or sum(sizes) != n:
            errors.append('Split section counts do not reconcile.')
        if (not _integer(n, 2) or not _integer(fmt.get('cycles'), 1)
                or fmt.get('games_before_split') != (n-1)*fmt['cycles']
                or not _integer(fmt.get('section_cycles'), 1)):
            errors.append('Split match counts do not reconcile.')
        if not fmt.get('carry_points') or fmt.get('cross_section_reordering') is not False:
            errors.append('Split point/rank policy missing.')
    elif fmt.get('kind') in ('conferences', 'groups'):
        groups = fmt.get('groups', [])
        if not groups or any(not _integer(g, 2) for g in groups) or sum(groups) != n:
            errors.append('Group memberships do not reconcile.')
    else:
        errors.append('Regular-season format missing.')
    for bracket in structure.get('brackets', []):
        errors.extend(bracket_issues(bracket))
    if structure.get('vertical_link') == 'closed' and structure.get('automatic_promotion_ranks'):
        errors.append('Closed league cannot have automatic promotion.')
    return list(dict.fromkeys(errors))


def league_coverage(data):
    from .content_gate import COUNTRIES, DEPTH
    countries = {c['id']: c for c in data['countries']}
    rows = []
    for nation in COUNTRIES:
        country = countries[nation]
        sources = {s['id']: s for s in country.get('evidence', [])}
        tiers = country.get('tier_rules', [])
        details = [dict(id=t['id'], tier=t['tier'], membership=t.get('membership'),
                        issues=structure_issues(t, sources)) for t in tiers]
        missing = sorted(set(range(1, DEPTH[nation]+1)) - {t['tier'] for t in tiers})
        rows.append(dict(nation=nation, depth=DEPTH[nation], missing_levels=missing,
                         mapped_competitions=len(tiers), structures_verified=sum(not t['issues'] for t in details),
                         status='VERIFIED' if details and not missing and all(not t['issues'] for t in details) else 'BLOCKED',
                         tiers=details, career_integration='PENDING_PASS_6'))
    return rows
