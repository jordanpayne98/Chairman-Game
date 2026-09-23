"""Structural access-list checks; opening allocations never substitute for rules.

An edge describes a dated, sourced number of places from an outcome to a target
competition. This validates content, not outcome resolution or continental draws.
"""
from datetime import date


def audit_access_graph(data, competitions, sources):
    graph=data.get('qualification_graph')
    if not isinstance(graph,list) or not graph:
        return ['No complete outcome-to-entrant qualification graph.']
    errors=[];ids=set();slots=set();counts={}
    for edge in graph:
        if not isinstance(edge,dict):
            errors.append('Qualification graph contains a non-record edge.');continue
        eid=edge.get('id');prefix='qualification/'+str(eid)
        if not eid or eid in ids:errors.append(prefix+': missing or duplicate edge ID.')
        ids.add(eid)
        source=edge.get('source_competition');target=edge.get('target_competition')
        if source not in competitions or target not in competitions:
            errors.append(prefix+': unknown source or target competition.')
        if edge.get('status')!='VERIFIED':errors.append(prefix+': access rule remains unverified.')
        if not edge.get('source_ids') or any(sources.get(sid,{}).get('status')!='VERIFIED' for sid in edge.get('source_ids',[])):
            errors.append(prefix+': access rule lacks verified evidence.')
        try:
            date.fromisoformat(edge['effective_from'])
        except (KeyError,TypeError,ValueError):errors.append(prefix+': missing valid effective date.')
        if edge.get('outcome') not in ('winner','runner_up','league_positions','playoff_winner','group_positions','title_holder'):
            errors.append(prefix+': missing supported result outcome.')
        count=edge.get('places');slot=edge.get('target_slot')
        if type(count) is not int or count<1:errors.append(prefix+': invalid place count.')
        else:counts[target]=counts.get(target,0)+count
        if not slot or (target,slot) in slots:errors.append(prefix+': missing or duplicate target slot.')
        slots.add((target,slot))
        if not isinstance(edge.get('eligibility'),dict) or not edge['eligibility']:
            errors.append(prefix+': eligibility conditions are missing.')
        if edge.get('duplicate_resolution') not in ('next_eligible_league_club','association_reallocation','next_eligible_group_team'):
            errors.append(prefix+': duplicate/holder resolution is missing.')
        if type(edge.get('season_offset')) is not int or edge['season_offset'] not in (0,1):
            errors.append(prefix+': qualification season timing is missing.')
        if source==target and edge.get('season_offset')!=1:
            errors.append(prefix+': self-qualification requires a following-season holder place.')
    for family in ('regional_competitions','international_competitions'):
        for comp in data.get(family,[]):
            if counts.get(comp.get('id'),0)!=comp.get('entrant_count'):
                errors.append(str(comp.get('id'))+': sourced access places do not reconcile with entrant count.')
    return errors
