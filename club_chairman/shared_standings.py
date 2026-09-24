"""Resolve completed shared-league tables without inventing sporting precedence.

No career is activated here. The caller supplies real match results and, when a
published rule cannot separate clubs, a separately recorded association ruling.
"""
from collections import defaultdict

from .league_structures import _integer, _require


def _split(groups, score):
    """Keep tied clubs together; never use club IDs as a sporting tiebreaker."""
    result = []
    for group in groups:
        buckets = defaultdict(list)
        for club in group:
            buckets[score(club)].append(club)
        for value in sorted(buckets, reverse=True):
            result.append(buckets[value])
    return result


def completed_shared_table(tier, members, results, deductions=None,
                           adjudications=None, decisive_cutoffs=None,
                           disciplinary_totals=None):
    """Return groups of equal rank and explicit unresolved decisions.

    ``results`` contains one home result per ordered pair, with ``home``,
    ``away`` and ``goals`` (two nonnegative integers). ``adjudications`` is a
    list of recorded association rulings with decision_id, clubs, order and
    basis. Optional verified disciplinary totals are supplied by the caller;
    this service does not infer cautions or appeal outcomes from scores.
    """
    level = tier.get('tier')
    _require(level in range(1, 6) and tier.get('rulebook_profile') ==
             f'english-tier-{level}-2026', 'Shared English tier required.')
    size = 20 if level == 1 else 24
    _require(tier.get('membership') == size and
             tier.get('format') == dict(kind='round_robin', cycles=2,
                                        games_per_club=2*(size-1)) and
             tier.get('points') == dict(win=3, draw=1, loss=0),
             'Shared league format differs from approved profile.')
    _require(isinstance(members, list) and len(members) == size and
             len(set(members)) == size and all(isinstance(c, str) and c for c in members),
             'Shared league membership does not reconcile.')
    members_set = set(members)
    deductions = deductions or {}
    _require(isinstance(deductions, dict) and set(deductions) <= members_set and
             all(_integer(n) for n in deductions.values()), 'Invalid points deductions.')
    _require(isinstance(results, list) and len(results) == size * (size-1),
             'A completed home-and-away season is required.')
    stats = {c: dict(played=0, won=0, drawn=0, lost=0, goals_for=0,
                     goals_against=0, away_goals=0, points=-deductions.get(c, 0)) for c in members}
    seen = set()
    for game in results:
        _require(isinstance(game, dict), 'Invalid league result.')
        home, away, goals = game.get('home'), game.get('away'), game.get('goals')
        _require(isinstance(home, str) and isinstance(away, str) and
                 home in members_set and away in members_set and home != away and
                 (home, away) not in seen and isinstance(goals, list) and len(goals) == 2 and
                 all(_integer(n) for n in goals), 'Invalid or duplicate league result.')
        seen.add((home, away))
        a, b = goals
        stats[home]['played'] += 1
        stats[away]['played'] += 1
        stats[home]['goals_for'] += a
        stats[home]['goals_against'] += b
        stats[away]['goals_for'] += b
        stats[away]['goals_against'] += a
        stats[away]['away_goals'] += b
        if a == b:
            for club in (home, away):
                stats[club]['drawn'] += 1
                stats[club]['points'] += 1
        else:
            winner, loser = (home, away) if a > b else (away, home)
            stats[winner]['won'] += 1
            stats[winner]['points'] += 3
            stats[loser]['lost'] += 1
    _require(len(seen) == size*(size-1), 'Incomplete league fixture results.')
    for row in stats.values():
        row['goal_difference'] = row['goals_for']-row['goals_against']
    groups = [members[:]]
    for key in ('points', 'goal_difference', 'goals_for'):
        groups = _split(groups, lambda club: stats[club][key])

    if level == 1:
        cutoffs = [] if decisive_cutoffs is None else decisive_cutoffs
        _require(isinstance(cutoffs, list) and all(_integer(c, 1) and c < size
                                                  for c in cutoffs), 'Invalid decisive cutoffs.')
        cutoffs = sorted(set([1, 17, *cutoffs]))
    else:
        _require(decisive_cutoffs is None, 'Only the top tier takes conditional cutoffs.')
        cutoffs = []
    _require(disciplinary_totals is None or
             (level in (2, 3, 4) and isinstance(disciplinary_totals, dict) and
              set(disciplinary_totals) <= members_set),
             'Only EFL tiers accept recorded disciplinary totals.')

    resolved = []
    cursor = 0
    for group in groups:
        first, last = cursor+1, cursor+len(group)
        cursor = last
        if len(group) == 1:
            resolved.append((group, None))
            continue
        if level == 1 and not any(first <= c < last for c in cutoffs):
            resolved.append((group, 'shared_position_non_decisive'))
            continue
        head = {c: dict(points=0, goal_difference=0, goals_for=0, away_goals=0)
                for c in group}
        group_set = set(group)
        for game in results:
            home, away = game['home'], game['away']
            if home not in group_set or away not in group_set:
                continue
            a, b = game['goals']
            head[home]['goal_difference'] += a-b
            head[away]['goal_difference'] += b-a
            head[home]['goals_for'] += a
            head[away]['goals_for'] += b
            head[away]['away_goals'] += b
            if a == b:
                head[home]['points'] += 1
                head[away]['points'] += 1
            else:
                head[home if a > b else away]['points'] += 3
        if level == 5:
            subgroups = _split([group], lambda c: stats[c]['won'])
            # FA rule 12.2.4 does not define numeric subcriteria for the better
            # playing record. Even a two-club tie awaits a recorded ruling.
            resolved.extend((g, 'fa_head_to_head_direction' if len(g) > 1 else None)
                            for g in subgroups)
            continue
        keys = (('points', 'away_goals') if level == 1 else
                ('points', 'goal_difference', 'goals_for'))
        subgroups = [group]
        partially_separated = False
        for key in keys:
            before = subgroups
            subgroups = _split(subgroups, lambda c: head[c][key])
            if len(subgroups) > len(before) and any(len(g) > 1 for g in subgroups):
                partially_separated = True
                break  # Do not guess whether to restart a reduced mini-table.
        if partially_separated:
            reason = 'partial_head_to_head_direction'
        elif level == 1:
            reason = 'pl_multi_club_direction' if len(group) > 2 else 'pl_neutral_decider'
        else:
            if len(subgroups) == 1 or all(len(g) == 1 for g in subgroups):
                subgroups = _split(subgroups, lambda c: stats[c]['won'])
                subgroups = _split(subgroups, lambda c: stats[c]['away_goals'])
            pending = [c for g in subgroups if len(g) > 1 for c in g]
            if pending and disciplinary_totals is not None:
                for club in pending:
                    evidence = disciplinary_totals.get(club)
                    _require(isinstance(evidence, dict) and
                             _integer(evidence.get('first_42_penalty_points')) and
                             evidence.get('matches_assessed') == 42 and
                             isinstance(evidence.get('decision_id'), str) and
                             evidence['decision_id'],
                             'Verified 42-match disciplinary assessment required.')
                subgroups = _split(subgroups, lambda c: -disciplinary_totals[c][
                    'first_42_penalty_points'] if c in pending else 0)
            reason = ('efl_sending_off_or_deciding_match_direction'
                      if disciplinary_totals is not None else 'efl_disciplinary_missing')
        subgroup_start = first
        for g in subgroups:
            sub_reason = reason if len(g) > 1 else None
            if level == 1 and sub_reason and not any(
                    subgroup_start <= c < subgroup_start+len(g)-1 for c in cutoffs):
                sub_reason = 'shared_position_non_decisive'
            resolved.append((g, sub_reason))
            subgroup_start += len(g)

    adjudications = [] if adjudications is None else adjudications
    _require(isinstance(adjudications, list), 'Invalid association adjudications.')
    used = set()
    final = []
    for group, reason in resolved:
        matching = [a for a in adjudications if isinstance(a, dict) and
                    isinstance(a.get('clubs'), list) and
                    all(isinstance(c, str) for c in a['clubs']) and
                    set(a['clubs']) == set(group) and
                    len(a['clubs']) == len(group)]
        _require(len(matching) <= 1, 'Conflicting association adjudications.')
        if matching:
            ruling = matching[0]
            _require(reason not in (None, 'shared_position_non_decisive',
                                    'efl_disciplinary_missing') and
                     isinstance(ruling.get('decision_id'), str) and ruling['decision_id'] and
                     isinstance(ruling.get('basis'), str) and ruling['basis'] and
                     isinstance(ruling.get('order'), list) and
                     len(ruling['order']) == len(group) and
                     all(isinstance(c, str) for c in ruling['order']) and
                     set(ruling['order']) == set(group),
                     'Recorded association ruling required for this exact tie.')
            _require(ruling['decision_id'] not in used, 'Duplicate association decision ID.')
            used.add(ruling['decision_id'])
            final.extend(([c], None) for c in ruling['order'])
        else:
            final.append((group, reason))
    _require(len(used) == len(adjudications), 'Unused association adjudication.')
    rows, unresolved = [], []
    position = 1
    for group, reason in final:
        rows.append(dict(rank=position, clubs=sorted(group),
                         stats={c: stats[c].copy() for c in group}, tie_reason=reason))
        if reason not in (None, 'shared_position_non_decisive'):
            unresolved.append(dict(rank_start=position, rank_end=position+len(group)-1,
                                   clubs=sorted(group), reason=reason))
        position += len(group)
    return dict(rows=rows, unresolved=unresolved, complete=not unresolved)


def shared_access_preview(tier, members, results, deductions=None,
                          adjudications=None, decisive_cutoffs=None,
                          disciplinary_totals=None):
    """Identify ordinary sporting places; leave playoffs pending.

    When a tie straddles an access boundary, or a playoff seed needs an exact
    position, the preview refuses to assign a club until a ruling is recorded.
    Relegation places are *candidates* because a genuine sporting vacancy can
    change final membership. No successor club is fabricated here.
    """
    table = completed_shared_table(tier, members, results, deductions,
                                   adjudications, decisive_cutoffs,
                                   disciplinary_totals)
    progression = tier['progression']
    promoted = progression['automatic_promotion_ranks']
    relegated = progression['automatic_relegation_ranks']
    expected = {1: ([], [18, 19, 20]),
                2: ([1, 2], [22, 23, 24]),
                3: ([1, 2], [21, 22, 23, 24]),
                4: ([1, 2, 3], [23, 24]),
                5: ([1], [21, 22, 23, 24])}
    _require((promoted, relegated) == expected[tier['tier']],
             'Access positions differ from approved shared profile.')
    playoff_ranks = ({2: list(range(3, 9)), 3: list(range(3, 7)),
                      4: list(range(4, 8))}.get(tier['tier'], []))

    def occupants(places, exact):
        result = []
        for row in table['rows']:
            first = row['rank']
            last = first+len(row['clubs'])-1
            overlapping = [n for n in places if first <= n <= last]
            if not overlapping:
                continue
            _require(len(overlapping) == len(row['clubs']) and
                     (not exact or len(row['clubs']) == 1),
                     'Association direction required at access boundary or playoff seed.')
            result.extend(row['clubs'])
        return result

    return dict(table=table, automatic_promotion_candidates=occupants(promoted, False),
                automatic_relegation_candidates=occupants(relegated, False),
                playoff_seeds=occupants(playoff_ranks, True),
                playoff_status=('pending_current_National_League_rules' if tier['tier'] == 5
                                else 'no_domestic_playoff' if tier['tier'] == 1
                                else 'match_deciders_not_yet_verified'),
                champion=(table['rows'][0]['clubs'][0] if len(table['rows'][0]['clubs']) == 1
                          else None))
