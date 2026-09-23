"""Domestic nomination and playoff planning from completed career outcomes.

FAW Premier Rule 16 supplies three/four-place alternatives. This does not choose
an annual UEFA access list, entry stage or opening entrants. Unspecified licence
interactions return a direction requirement instead of silently reseeding.
"""
from datetime import date


def nomination_plan(*, league_order, cup_winner, licences, total_places,
                    career_start, completed_on):
    if date.fromisoformat(completed_on)<date.fromisoformat(career_start):
        raise ValueError('Qualification cannot use pre-career results.')
    if len(league_order)!=16 or len(set(league_order))!=16:
        raise ValueError('A completed sixteen-club league order is required.')
    if not cup_winner or total_places not in (3,4):
        raise ValueError('Cup outcome and sourced three/four-place access branch required.')
    known=set(league_order)|{cup_winner}
    if any(not isinstance(licences.get(cid),dict) or any(type(licences[cid].get(key)) is not bool
            for key in ('tier_one','european')) for cid in known):
        raise ValueError('Explicit next-season licence decisions are required for every candidate.')
    nominations=[];issues=[]

    def nominate(candidates,route,both=False):
        selected={n['club'] for n in nominations}
        cid=next((c for c in candidates if c not in selected and licences[c]['european']
                  and (not both or licences[c]['tier_one'])),None)
        if cid is None:issues.append('No eligible club for '+route+'.')
        else:nominations.append(dict(club=cid,route=route))
        return cid

    primary=nominate(league_order,'primary_european_place')
    cup_eligible=licences[cup_winner]['european'] and (total_places==3 or licences[cup_winner]['tier_one'])
    cup_candidates=([cup_winner] if cup_eligible else [])+[c for c in league_order if c!=cup_winner]
    cup_place=nominate(cup_candidates,'cup_european_place')
    if total_places==4:
        # Rule 16.3: runner-up's entitlement or next eligible league club.
        runner=league_order[1]
        candidates=([runner] if licences[runner]['tier_one'] and licences[runner]['european'] else [])+league_order[2:]
        nominate(candidates,'league_european_place')
    cup_rank=league_order.index(cup_winner)+1 if cup_winner in league_order else 17
    # The published brackets describe ordinary cup-position branches. Where a
    # substituted direct nominee changes those brackets, retain the nominations
    # but require an association direction rather than invent another bracket.
    ordinary_direct={league_order[0],cup_winner}
    if total_places==4:ordinary_direct.add(league_order[1])
    for cid in league_order:
        if len(ordinary_direct)>=total_places-1:break
        ordinary_direct.add(cid)
    actual_direct={n['club'] for n in nominations}
    if primary!=league_order[0] or not cup_eligible or actual_direct!=ordinary_direct:
        issues.append('Licence/replacement interaction needs an association playoff direction.')
        return dict(completed_on=completed_on,total_places=total_places,direct=nominations,
                    playoff=None,issues=issues,status='DIRECTION_REQUIRED')
    candidates=[cid for cid in league_order[1:7] if cid not in actual_direct]
    rank={cid:i for i,cid in enumerate(league_order)}

    def tie(ident,a,b):
        # Null means a regulatory bye; do not pull an eighth-placed replacement.
        sides=[c if licences[c]['tier_one'] and licences[c]['european'] else None for c in (a,b)]
        winner=next((c for c in sides if c),None) if None in sides else None
        if sides==[None,None]:issues.append(ident+': both clubs ineligible; association direction required.')
        return dict(id=ident,home=sides[0],away=sides[1],automatic_winner=winner,
                    higher_rank_hosts=True,extra_time=False,drawn_after_90='penalties')

    if len(candidates)==6:
        quarter=[tie('qf1',candidates[2],candidates[5]),tie('qf2',candidates[3],candidates[4])]
        semi=[dict(id='sf1',seed=candidates[0],opponent='lowest_ranked_quarterfinal_winner'),
              dict(id='sf2',seed=candidates[1],opponent='other_quarterfinal_winner')]
    elif len(candidates)==5:
        quarter=[tie('qf1',candidates[3],candidates[4])]
        semi=[dict(id='sf1',seed=candidates[0],opponent='qf1_winner'),tie('sf2',candidates[1],candidates[2])]
    elif len(candidates)==4:
        quarter=[];semi=[tie('sf1',candidates[0],candidates[3]),tie('sf2',candidates[1],candidates[2])]
    else:raise ValueError('Nomination branch produced an unsupported playoff field.')
    for fixture in semi:
        if 'seed' in fixture and not (licences[fixture['seed']]['tier_one'] and licences[fixture['seed']]['european']):
            fixture['seed']=None  # Its eventual opponent receives the bye.
    return dict(completed_on=completed_on,total_places=total_places,direct=nominations,
        playoff=dict(quarterfinals=quarter,semifinals=semi,final='semifinal_winners',
                     ranking=rank,qualification_places=1,cup_rank=cup_rank),issues=issues,
        status='DIRECTION_REQUIRED' if issues else 'READY_FOR_PLAYOFFS')


def semifinal_pairings(plan, quarterfinal_winners):
    playoff=plan.get('playoff')
    if not playoff or plan['status']=='DIRECTION_REQUIRED':raise ValueError('Association playoff direction is unresolved.')
    quarters=playoff['quarterfinals']
    if set(quarterfinal_winners)!={q['id'] for q in quarters}:raise ValueError('Quarterfinal results are incomplete.')
    for q in quarters:
        winner=quarterfinal_winners[q['id']]
        if winner not in (q['home'],q['away']) or winner is None or (q['automatic_winner'] and winner!=q['automatic_winner']):
            raise ValueError('Quarterfinal winner is not an eligible advancing club.')
    winners=list(quarterfinal_winners.values());ranking=playoff['ranking'];pairs=[]
    for sf in playoff['semifinals']:
        if 'seed' not in sf:
            pairs.append(dict(sf));continue
        if sf['opponent']=='qf1_winner':other=quarterfinal_winners['qf1']
        elif sf['opponent']=='lowest_ranked_quarterfinal_winner':other=max(winners,key=ranking.get)
        else:other=min(winners,key=ranking.get)
        seed=sf['seed']
        home,away=(seed,other) if seed is None or ranking[seed]<ranking[other] else (other,seed)
        pairs.append(dict(id=sf['id'],home=home,away=away,automatic_winner=other if seed is None else None,
                          higher_rank_hosts=True,extra_time=False,drawn_after_90='penalties'))
    return pairs


def complete_nominations(plan, *, quarterfinal_winners, semifinal_winners, final_winner):
    semifinals=semifinal_pairings(plan,quarterfinal_winners)
    if set(semifinal_winners)!={s['id'] for s in semifinals}:
        raise ValueError('Semifinal outcomes are incomplete.')
    for sf in semifinals:
        winner=semifinal_winners[sf['id']]
        if winner is None or winner not in (sf['home'],sf['away']) or (sf['automatic_winner'] and winner!=sf['automatic_winner']):
            raise ValueError('Invalid semifinal winner.')
    if final_winner is None or final_winner not in semifinal_winners.values():
        raise ValueError('Final winner is not an eligible finalist.')
    nominations=[dict(n) for n in plan['direct']]+[dict(club=final_winner,route='playoff_european_place')]
    if len({n['club'] for n in nominations})!=plan['total_places']:
        raise ValueError('European nominations contain duplicate or missing clubs.')
    return nominations
