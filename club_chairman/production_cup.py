"""Dated cup operations for production-content validation.

This JSON-serialisable state is deliberately separate from the compact career's
development cup. It can exercise a partial national pack without activating that
pack in New Game. No match results, cash balances or histories are generated.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
import json
from zoneinfo import ZoneInfo

from .competition_entries import (audit_cup_allocation, welsh_cup_admission_issues,
                                  welsh_cup_ground_issues)
from .simulation import rng_for


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def calendar_issues(cup, clubs):
    """Require actual dated rounds and a total, original geographic assignment."""
    errors=[]
    calendar=cup.get('calendar',{});rounds=calendar.get('rounds',{})
    definitions=cup.get('rounds',[]);expected=[r['id'] for r in definitions]
    if set(rounds)!=set(expected):errors.append('Cup calendar does not cover every round.')
    previous=None
    for rid in expected:
        try:
            record=rounds[rid];start,end=map(date.fromisoformat,record['window'])
            conference=date.fromisoformat(record['conference_date'])
            if not start<=conference<=end or (previous is not None and start<=previous):
                errors.append('Cup round dates overlap or exclude their conference date.')
            previous=end
        except (KeyError,TypeError,ValueError):
            errors.append('Cup round dates are missing or invalid.')
    if calendar.get('timezone')!='Europe/London':errors.append('Cup local timezone is missing.')
    policy=cup.get('draw_policy',{})
    if (policy.get('regional_rounds')!=expected[:4] or policy.get('zones')!=['north','south']
            or policy.get('odd_group_policy')!='move_first_boundary_priority_club_from_north_to_south'
            or policy.get('basis')!='authored_fictional_association_group_assignment'):
        errors.append('Cup regional/open draw policy is incomplete.')
    priority=policy.get('boundary_priority',[])
    if len(priority)!=len(set(priority)) or set(priority)!=set(clubs):
        errors.append('Cup boundary-club priority does not cover the entrants.')
    if any(c.get('cup_draw_zone') not in ('north','south') for c in clubs.values()):
        errors.append('Cup entrant has no valid geographical draw zone.')
    return errors


def create_validation_cup(data, seed: int, career_start: str) -> dict:
    """Freeze a Welsh cup snapshot for domain validation, not career activation."""
    start=date.fromisoformat(career_start)
    wales=next(c for c in data['countries'] if c['id']=='wales')
    cup=next(c for c in wales['domestic_cups'] if c['id']=='wales-national-cup-2026')
    allocation=next(a for a in data['opening_allocations'] if a['id']==cup['opening_allocation'])
    clubs={c['id']:c for c in data['clubs'] if c['id'] in allocation['club_ids']}
    tiers={1:wales['tier_rules'][0]['first_season_members'],
           2:[cid for t in wales['tier_rules'] if t['tier']==2 for cid in t['first_season_members']],
           3:next(p['club_ids'] for p in wales['supporting_pools'] if p['id']=='wales-ardal-2026')}
    issues=audit_cup_allocation(cup,allocation,clubs,tiers)+calendar_issues(cup,clubs)
    entries=[e for e in data['first_season_entrants'] if e['competition']==cup['id']]
    if len(entries)!=len(clubs) or {e['club'] for e in entries}!=set(clubs):
        issues.append('Opening admission records do not reconcile.')
    for entry in entries:
        issues.extend(welsh_cup_admission_issues(entry.get('eligibility_evidence'),cup['admission_rules']))
        rid=entry.get('entry_round')
        if entry['club'] not in allocation['entry_rounds'].get(rid,[]):
            issues.append('Opening admission round differs from allocation.')
        issues.extend(welsh_cup_ground_issues(clubs.get(entry['club'],{}).get('cup_ground',{}),rid))
    _require(not issues,'Cup setup blocked: '+'; '.join(issues))
    first=date.fromisoformat(cup['calendar']['rounds'][cup['rounds'][0]['id']]['window'][0])
    _require(start<=first,'A fresh cup cannot create pre-career results for missed rounds.')
    return deepcopy(dict(schema=1,mode='content_validation',seed=seed,career_start=career_start,
        definition=cup,allocation=allocation,clubs=clubs,rounds=[],fixtures=[],events=[],
        finance_records={},winner=None))


def geographic_groups(state, entrants, round_id):
    policy=state['definition']['draw_policy']
    if round_id not in policy['regional_rounds']:return {'open':sorted(entrants)},[]
    groups={z:sorted(cid for cid in entrants if state['clubs'][cid]['cup_draw_zone']==z)
            for z in policy['zones']}
    moves=[]
    if len(groups['north'])%2:
        _require(len(groups['south'])%2==1,'An odd cup field cannot be paired.')
        cid=next(c for c in policy['boundary_priority'] if c in groups['north'])
        groups['north'].remove(cid);groups['south'].append(cid)
        moves.append(dict(club=cid,from_zone='north',to_zone='south',
                          basis=policy['basis']))
    return groups,moves


def _event(state, kind, on, subject):
    state['events'].append(dict(id=f"{state['definition']['id']}:{kind}:{subject}",
                                kind=kind,on=on,subject=subject))


def _fixture(state, fixture_id):
    return next(f for f in state['fixtures'] if f['id']==fixture_id)


def draw_next(state, on: str, *, association_reschedule=None) -> list[str]:
    day=date.fromisoformat(on);cup=state['definition'];number=len(state['rounds'])
    _require(day>=date.fromisoformat(state['career_start']),'Draw predates career start.')
    _require(number<len(cup['rounds']) and state['winner'] is None,'Cup is complete.')
    survivors=[]
    if number:
        fixtures=[_fixture(state,fid) for fid in state['rounds'][-1]['fixtures']]
        _require(all(f['result'] is not None for f in fixtures),'Previous round is unfinished.')
        _require(all(f['result']['on']<=on for f in fixtures),'Draw predates a qualifying result.')
        survivors=[f['result']['winner'] for f in fixtures]
    definition=cup['rounds'][number];rid=definition['id']
    entrants=survivors+state['allocation']['entry_rounds'].get(rid,[])
    _require(len(entrants)==len(set(entrants))==definition['entrants'],'Advancement does not reconcile.')
    calendar=cup['calendar']['rounds'][rid]
    play_on=calendar['conference_date']
    if association_reschedule is not None:
        _require(association_reschedule.get('decision_id'),'Association rescheduling needs a decision ID.')
        play_on=association_reschedule['play_on'];date.fromisoformat(play_on)
    _require(on<=play_on,'Conference date has passed; association scheduling decision required.')
    groups,moves=geographic_groups(state,entrants,rid)
    fixtures=[]
    for zone,members in sorted(groups.items()):
        ids=sorted(members)
        rng_for(state['seed'],f"{cup['id']}:{rid}:{zone}").shuffle(ids)
        _require(len(ids)%2==0,'Geographic draw group has an odd number of entrants.')
        for i in range(0,len(ids),2):
            fid=f"{cup['id']}:{rid}:{len(fixtures)+1}"
            fixtures.append(dict(id=fid,round=rid,group=zone,drawn_home=ids[i],drawn_away=ids[i+1],
                home=ids[i],away=ids[i+1],conference_date=calendar['conference_date'],
                date=play_on,kickoff=cup['calendar']['default_kickoff'],
                timezone=cup['calendar']['timezone'],venue=None,status='awaiting_confirmation',
                postponements=0,postponement_ids=[],reschedule_by=None,result=None))
    state['fixtures'].extend(fixtures)
    state['rounds'].append(dict(id=rid,drawn_on=on,entrants=sorted(entrants),groups=groups,
                               group_moves=moves,association_reschedule=deepcopy(association_reschedule),
                               fixtures=[f['id'] for f in fixtures]))
    _event(state,'draw',on,rid)
    return [f['id'] for f in fixtures]


def confirm_fixture(state, fixture_id: str, *, on: str, play_on: str | None=None,
                    kickoff: str | None=None, unavailable=(), approved_venue=None,
                    association_approved=False, clubs_agreed=False):
    """Resolve a venue and date atomically. Unresolved cases remain blocked.

    Alternative/final venues require an explicit association decision. The caller
    supplies actual facilities and availability; the service never improves them.
    """
    old=_fixture(state,fixture_id);f=deepcopy(old);cup=state['definition'];rid=f['round']
    _require(f['result'] is None,'A completed fixture cannot be changed.')
    draw=next(r for r in state['rounds'] if r['id']==rid)
    _require(draw['drawn_on']<=on,'Confirmation predates the draw.')
    date.fromisoformat(on)
    play_on=play_on or f['date'];kickoff=kickoff or f['kickoff']
    play_day=date.fromisoformat(play_on);time.fromisoformat(kickoff)
    _require(play_on>=on,'Fixture cannot be confirmed in the past.')
    window=cup['calendar']['rounds'][rid]['window']
    changed=play_on!=f['conference_date'] or kickoff!=cup['calendar']['default_kickoff']
    _require(not changed or association_approved,'Changed date/time requires association approval.')
    _require(window[0]<=play_on<=window[1] or association_approved,'Fixture is outside its round window.')
    if changed and not f['postponement_ids'] and not draw.get('association_reschedule'):
        _require(clubs_agreed,'Voluntary date/time change requires both clubs to agree.')
    if f['reschedule_by']:
        _require(play_on<=f['reschedule_by'],'Replay deadline exceeded; new association direction required.')
    if approved_venue is not None:
        _require(association_approved,'Alternative/final venue requires association approval.')
        _require(approved_venue.get('id') and approved_venue.get('name'),'Venue identity is missing.')
        _require(not welsh_cup_ground_issues(approved_venue.get('facilities',{}),rid),'Approved venue does not meet ground criteria.')
        _require(approved_venue['id'] not in unavailable,'Approved venue is unavailable.')
        f['venue']=deepcopy(approved_venue)
    else:
        _require(rid!='final','Final requires an association-selected venue.')
        chosen=None
        hosts=(f['home'],) if f.get('mandatory_host') else (f['home'],f['away'])
        for host in hosts:
            club=state['clubs'][host]
            if host not in unavailable and club['ground'] not in unavailable and not welsh_cup_ground_issues(club['cup_ground'],rid):
                chosen=host;break
        _require(chosen is not None,'Neither registered ground is suitable/available; association decision required.')
        if chosen==f['away']:f['home'],f['away']=f['away'],f['home']
        club=state['clubs'][chosen]
        f['venue']=dict(id=chosen,name=club['ground'],facilities=deepcopy(club['cup_ground']))
    # Exact club and ground conflicts are not silently moved to another day.
    for other in state['fixtures']:
        if other['id']==fixture_id or other['status']!='scheduled' or other['date']!=play_on:continue
        _require(not {f['home'],f['away']}&{other['home'],other['away']},'Club has another fixture on this date.')
        _require(other['venue']['id']!=f['venue']['id'] and other['venue']['name']!=f['venue']['name'],
                 'Shared ground conflict requires an association scheduling decision.')
    f.update(date=play_day.isoformat(),kickoff=kickoff,status='scheduled')
    old.clear();old.update(f)
    _event(state,'fixture_confirmation',on,fixture_id+':'+str(sum(e['kind']=='fixture_confirmation' for e in state['events'])))
    return deepcopy(f)


def postpone(state, fixture_id: str, *, on: str, decision_id: str,
             association_ordered=False, distance_miles: int, floodlit: bool):
    f=_fixture(state,fixture_id)
    _require(bool(decision_id),'Postponement needs a stable decision ID.')
    if decision_id in f['postponement_ids']:return deepcopy(f)
    _require(f['result'] is None and f['status']=='scheduled','Only a scheduled unfinished tie can be postponed.')
    _require(type(distance_miles) is int and distance_miles>=0,'Invalid travel distance.')
    day=date.fromisoformat(on)
    _require(state['career_start']<=on<=f['date'],'Postponement date is outside the fixture timeline.')
    scheduled=date.fromisoformat(f['date'])
    if distance_miles<=100 and floodlit:
        deadline=scheduled+timedelta(days=(2-scheduled.weekday())%7 or 7)
    else:
        deadline=scheduled+timedelta(days=6-scheduled.weekday()+(7 if scheduled.weekday()>=4 else 0))
    f['postponement_ids'].append(decision_id)
    if not association_ordered:
        f['postponements']+=1
        if f['postponements']==2:
            f['home'],f['away']=f['away'],f['home']
            f['mandatory_host']=True
    f.update(status='awaiting_confirmation',venue=None,reschedule_by=None if association_ordered else deadline.isoformat())
    _event(state,'postponement',day.isoformat(),fixture_id+':'+decision_id)
    return deepcopy(f)


def registration_deadline(fixture, holidays=()) -> datetime:
    """Original conference-date eligibility survives postponement and reversal."""
    day=date.fromisoformat(fixture['conference_date'])-timedelta(days=1)
    while day.weekday()>=5 or day.isoformat() in holidays:day-=timedelta(days=1)
    return datetime.combine(day,time(17),ZoneInfo(fixture['timezone']))


def player_eligibility_issues(fixture, registration, *, holidays=()) -> list[str]:
    issues=[];club=registration.get('club')
    if club not in (fixture['home'],fixture['away']):issues.append('Player is not registered to a participating club.')
    try:
        registered=datetime.fromisoformat(registration['registered_at'])
        if registered.utcoffset() is None or registered>registration_deadline(fixture,holidays):
            issues.append('Player was not registered by the original conference deadline.')
    except (KeyError,ValueError,TypeError):issues.append('Player registration timestamp is invalid.')
    if registration.get('association_eligible') is not True:issues.append('Association registration/clearance is not confirmed.')
    if type(registration.get('on_loan')) is not bool:issues.append('Loan status is unresolved.')
    # Suspension status is supplied for the actual match date, not the old date.
    if registration.get('suspended_on_match_date') is not False:issues.append('Player is suspended or suspension status is unresolved.')
    if registration.get('on_loan') is True and registration.get('written_parent_consent_submitted') is not True:
        issues.append('Loan permission has not been submitted.')
    return issues


def record_result(state, fixture_id: str, *, on: str, score, shootout=None):
    f=_fixture(state,fixture_id)
    _require(isinstance(score,(list,tuple)) and len(score)==2 and all(type(x) is int and x>=0 for x in score),'Invalid normal-time score.')
    tied=score[0]==score[1]
    if tied:
        _require(isinstance(shootout,(list,tuple)) and len(shootout)==2
                 and all(type(x) is int and x>=0 for x in shootout) and shootout[0]!=shootout[1],
                 'A drawn tie requires a decisive penalty shootout, never extra time.')
    else:_require(shootout is None,'A decisive normal-time result cannot have a shootout.')
    deciding=shootout if tied else score
    result=dict(on=on,score=list(score),shootout=list(shootout) if shootout else None,
                winner=f['home'] if deciding[0]>deciding[1] else f['away'])
    if f['result'] is not None:
        _require(f['result']==result,'A confirmed result cannot be replaced.');return deepcopy(result)
    _require(f['status']=='scheduled' and on==f['date'],'Result requires a confirmed fixture on its actual match date.')
    date.fromisoformat(on)
    f.update(result=result,status='complete')
    _event(state,'result',on,fixture_id)
    if f['round']=='final':state['winner']=result['winner']
    return deepcopy(result)


def calendar_rows(state):
    """Public read model; planned rounds stay separate from actual fixtures."""
    names={cid:c['name'] for cid,c in state['clubs'].items()}
    return [dict(id=f['id'],round=f['round'],date=f['date'],conference_date=f['conference_date'],
        kickoff=f['kickoff'],timezone=f['timezone'],status=f['status'],
        home=names[f['home']],away=names[f['away']],venue=f['venue']['name'] if f['venue'] else None,
        result=deepcopy(f['result'])) for f in sorted(state['fixtures'],key=lambda f:(f['date'],f['id']))]


def validate_state(state):
    """Check persisted cup identity, progression, results and financial references."""
    _require(state.get('schema')==1 and state.get('mode')=='content_validation','Unsupported cup state.')
    cup=state['definition'];clubs=state['clubs'];fixtures=state['fixtures']
    _require(not calendar_issues(cup,clubs),'Invalid cup calendar/geography snapshot.')
    by_id={f['id']:f for f in fixtures}
    _require(len(by_id)==len(fixtures),'Duplicate persisted cup fixture.')
    _require(len(state['rounds'])<=len(cup['rounds']),'Too many cup rounds.')
    previous=[];listed=[]
    for index,record in enumerate(state['rounds']):
        definition=cup['rounds'][index];rid=definition['id']
        _require(record['id']==rid,'Cup round order is invalid.')
        _require(record['drawn_on']>=state['career_start'],'Persisted draw predates career start.')
        entrants=previous+state['allocation']['entry_rounds'].get(rid,[])
        _require(sorted(record['entrants'])==sorted(entrants) and len(set(entrants))==definition['entrants'],
                 'Persisted cup progression does not reconcile.')
        _require(len(record['fixtures'])==definition['ties'],'Persisted tie count is invalid.')
        groups,moves=geographic_groups(state,entrants,rid)
        _require(record['groups']==groups and record['group_moves']==moves,'Persisted draw geography is invalid.')
        participants=[];previous=[]
        for fid in record['fixtures']:
            _require(fid in by_id,'Persisted cup fixture is missing.')
            f=by_id[fid];listed.append(fid)
            participants.extend((f['drawn_home'],f['drawn_away']))
            _require(f['round']==rid and f['drawn_home']!=f['drawn_away']
                     and {f['home'],f['away']}=={f['drawn_home'],f['drawn_away']},'Persisted fixture participants are invalid.')
            _require(f['drawn_home'] in groups.get(f['group'],[]) and f['drawn_away'] in groups.get(f['group'],[]),
                     'Persisted fixture crosses draw groups.')
            _require(f['conference_date']==cup['calendar']['rounds'][rid]['conference_date'],
                     'Original eligibility conference date was changed.')
            _require(f['date']>=record['drawn_on'],'Persisted fixture predates its draw.')
            date.fromisoformat(f['date']);time.fromisoformat(f['kickoff'])
            _require(f['status'] in ('awaiting_confirmation','scheduled','complete'),'Invalid persisted fixture status.')
            if f['status'] in ('scheduled','complete'):
                _require(isinstance(f['venue'],dict) and not welsh_cup_ground_issues(f['venue'].get('facilities',{}),rid),
                         'Persisted confirmed fixture has no suitable venue.')
            if f['result'] is None:
                _require(index==len(state['rounds'])-1 and f['status']!='complete','Unfinished fixture has completed successors.')
            else:
                result=f['result'];score=result['score'];shootout=result.get('shootout')
                _require(f['status']=='complete' and result['on']==f['date'],'Persisted result has invalid status/date.')
                _require(len(score)==2 and all(type(x) is int and x>=0 for x in score),'Invalid persisted normal-time score.')
                tied=score[0]==score[1]
                _require((not tied and shootout is None) or (tied and isinstance(shootout,list)
                    and len(shootout)==2 and all(type(x) is int and x>=0 for x in shootout) and shootout[0]!=shootout[1]),
                    'Persisted result has invalid penalty resolution.')
                deciding=shootout if tied else score
                _require(result['winner']==(f['home'] if deciding[0]>deciding[1] else f['away']),
                         'Persisted winner disagrees with the score.')
                previous.append(result['winner'])
                if index+1<len(state['rounds']):
                    _require(result['on']<=state['rounds'][index+1]['drawn_on'],'Later draw predates a qualifying result.')
        _require(sorted(participants)==sorted(entrants),'Persisted draw duplicates or omits a club.')
    _require(len(listed)==len(set(listed)) and set(listed)==set(by_id),'Cup has orphan or repeated fixtures.')
    champion=previous[0] if len(state['rounds'])==len(cup['rounds']) and len(previous)==1 else None
    _require(state['winner']==champion,'Persisted champion does not match the final.')
    for fid,record in state['finance_records'].items():
        _require(fid in by_id and by_id[fid]['result'] is not None and record['fixture']==fid,
                 'Cup payables reference an unfinished or unknown fixture.')
        _require(record['currency']=='GBP' and record['on']==by_id[fid]['result']['on'],'Cup payable date/currency is invalid.')
        lines=record['lines']
        _require(len({line['id'] for line in lines})==len(lines),'Duplicate cup payable.')
        _require(all(type(line['amount_pence']) is int and line['amount_pence']>=0 and line['payer']!=line['payee']
                     for line in lines),'Invalid cup payable money/counterparty.')
    _require(all(e['on']>=state['career_start'] for e in state['events']),'Cup events predate career start.')
    return state


def restore_validation_cup(payload: str) -> dict:
    state=json.loads(payload)
    try:return validate_state(state)
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('Malformed cup state.') from exc
