"""Persistent public standing and private, deterministic employment preferences.

Provisional domestic baselines are independent of ability and potential. This
first policy uses roster opportunity, not a promise of manager selection.
"""
from copy import deepcopy
from math import log2

DEFAULTS = dict(club_baseline=50, tier_step=10, baseline_spread=5,
                status_scale=.5, minutes_scale=.18, money_scale=.24,
                money_cap=20, security_scale=.04, transfer_margin=6,
                free_margin=8, renewal_margin=8, settled_morale=85, settled_cost=20, max_wage=500000)
SLOTS = {'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2}


def initialise(s):
    cfg=s['config'].setdefault('recruitment',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    s.setdefault('recruitment',dict(clubs={},leagues={},players={},priorities={}))
    sync(s)


def league_id(s,cid):
    return next((d['id'] for d in s['leagues']['divisions'] if cid in d['members']),None)


def record(value,day,source):
    return dict(value=max(1,min(100,int(value))),day=day,scope='Domestic',
                trend=0,source=source)


def sync(s):
    """Add new identities without rewriting reputations or consuming match RNG."""
    from .simulation import rng_for
    r=s['recruitment'];cfg=s['config']['recruitment']
    for d in s['leagues']['divisions']:
        r['leagues'].setdefault(d['id'],record(cfg['club_baseline']-(d['tier']-1)*cfg['tier_step'],s['day'],'Provisional division baseline; history not yet assessed.'))
    for c in s['clubs']:
        if c['id'] in r['clubs']:continue
        lid=league_id(s,c['id']);base=r['leagues'][lid]['value'] if lid else cfg['club_baseline']-cfg['tier_step']
        spread=rng_for(s['seed'],'club-standing:'+c['id']).randint(-cfg['baseline_spread'],cfg['baseline_spread'])
        r['clubs'][c['id']]=record(base+spread,s['day'],'Provisional club baseline; no honours inferred.')
    for p in s['players']:
        if p['id'] not in r['players']:
            rng=rng_for(s['seed'],'player-standing:'+p['id'])
            base=r['clubs'].get(p['club'],{'value':cfg['club_baseline']-cfg['tier_step']})['value']
            r['players'][p['id']]=record(base+rng.randint(-cfg['baseline_spread'],cfg['baseline_spread']),s['day'],'Provisional career-entry baseline; independent of ability.')
        if p['id'] not in r['priorities']:
            rng=rng_for(s['seed'],'career-priorities:'+p['id'])
            r['priorities'][p['id']]=dict(status=rng.randint(35,85),minutes=rng.randint(35,85),
                money=rng.randint(35,85),security=rng.randint(35,85),
                firm_status=rng.random()<.18,prestige_tolerance=rng.randint(18,35))


def prestige(s,cid):
    if cid is None:return None
    r=s['recruitment'];lid=league_id(s,cid);club=r['clubs'][cid]['value']
    return .7*club+.3*r['leagues'].get(lid,{'value':club})['value']


def roster_context(s):
    """One public-roster pass per AI club review, refreshed after commitments."""
    counts={};pending=set();players={p['id']:p for p in s['players']}
    for p in s['players']:
        if p['club'] and not p['retired'] and not p['youth']:
            key=(p['club'],p['role']);counts[key]=counts.get(key,0)+1
    pending.update(('c0',o['player']) for o in s['career']['offers'].values()
                   if o['kind']!='renew' and o['status'] in ('medical','ready'))
    pending.update((d['club'],d['player']) for d in s['club_ai']['decisions']
                   if d['status'] in ('medical','rights_wait'))
    for cid,pid in pending:
        p=players[pid]
        if p['club']!=cid:
            key=(cid,p['role']);counts[key]=counts.get(key,0)+1
    return counts,pending


def opportunity(s,p,cid,context=None):
    # Public roster only: no hidden CA, potential, manager estimates or ratings.
    counts,pending=context if context is not None else roster_context(s)
    own_place=int(p['club']==cid and not p['retired'] and not p['youth'] or
                  p['club']!=cid and (cid,p['id']) in pending)
    peers=counts.get((cid,p['role']),0)-own_place
    return max(-1,min(1,1-peers/(SLOTS[p['role']]*2)))


def assess(s,p,cid,wage,end,context=None,terms_day=None,playing_role=None):
    """Same policy for owned and AI clubs; result contains agent-safe reasons only."""
    if p['id'] not in s['recruitment']['priorities']:sync(s)
    cfg=s['config']['recruitment'];r=s['recruitment'];prefs=r['priorities'][p['id']]
    target=prestige(s,cid);source=prestige(s,p['club'])
    reference=max(r['players'][p['id']]['value'],source if source is not None else 0)
    gap=target-reference;renew=p['club']==cid
    if context is None:context=roster_context(s)
    target_space=opportunity(s,p,cid,context)
    old_space=opportunity(s,p,p['club'],context) if p['club'] else 0
    # Age affects the value of security, never an automatic earnings preference.
    years=max(0,(end-(s['day'] if terms_day is None else terms_day))/365)
    security=min(3,years)*prefs['security']*cfg['security_scale']*(1.2 if p['age']>=30 else 1)
    wage_value=max(-cfg['money_cap'],min(cfg['money_cap'],log2(max(1,wage)/max(1,p['wage']))*prefs['money']*cfg['money_scale']))
    score=(cfg['renewal_margin'] if renew else cfg['free_margin'] if p['club'] is None else cfg['transfer_margin'])
    score+=gap*prefs['status']/100*cfg['status_scale']+security+wage_value
    if not renew:score+=(target_space-old_space)*prefs['minutes']*cfg['minutes_scale']
    settled=not renew and p['club'] is not None and p['morale']>=cfg['settled_morale']
    if settled:score-=cfg['settled_cost']
    firm=not renew and prefs['firm_status'] and gap < -prefs['prestige_tolerance']
    from . import playing_time
    commitment=playing_time.active(s,p['id'],cid)
    concern=bool(commitment and commitment['concern'])
    credible,role_reason=playing_time.credibility(s,p,cid,playing_role)
    if concern:score-=s['config']['playing_time']['concern_cost']
    if playing_role and credible and not concern:
        score+=s['config']['playing_time']['promise_value']*prefs['minutes']/100*playing_time.policy(s,playing_role)[1]/100
    reasons=[]
    if concern:reasons.append('Concern: this club has not yet resolved the recorded playing-time shortfall.')
    if playing_role:reasons.append('Proposed role: '+playing_role+'. '+role_reason)
    if settled:reasons.append('Concern: settled in current employment and needs a compelling reason to leave.')
    if gap < -5:reasons.append('Concern: the destination offers a lower level of public standing.')
    elif gap > 5:reasons.append('Attraction: a step up in club and league standing.')
    if not renew and target_space-old_space > .1:reasons.append('Attraction: less competition for this position than at the current club.')
    elif not renew and target_space-old_space < -.1:reasons.append('Concern: more competition for places; regular minutes look less likely.')
    if wage>p['wage']:reasons.append('Attraction: improved guaranteed weekly pay, with limited value from further increases.')
    if years>=1:reasons.append('Attraction: the proposed term offers employment security.')
    if firm:reasons.append('Agent: maintaining competition standing is a firm priority; extra pay will not resolve this move.')
    elif score<0:reasons.append('Agent: staying or waiting is preferable to this package; improve the terms or revisit after circumstances change.')
    else:reasons.append('Agent: willing to discuss this package, subject to the normal financial and contract review.')
    return dict(day=s['day'],willing=not firm,acceptable=not firm and score>=0,
                reasons=reasons,opportunity=('Explicit role proposed; it begins only on completed employment. The manager retains selection authority.' if playing_role else 'Roster-based indication only; no new playing-time promise. Existing agreements remain in force.'))


def counter_wage(s,p,cid,end,wage,playing_role=None):
    """Find an acceptable bounded wage, or retain an explicitly unaccepted draft."""
    ceiling=s['config']['recruitment']['max_wage']
    if assess(s,p,cid,wage,end,playing_role=playing_role)['acceptable']:return wage
    if wage>ceiling or not assess(s,p,cid,ceiling,end,playing_role=playing_role)['acceptable']:return None
    low=wage;high=ceiling
    while low<high:
        mid=(low+high)//2
        if assess(s,p,cid,mid,end,playing_role=playing_role)['acceptable']:high=mid
        else:low=mid+1
    return low


def check(s,p,cid,wage,end,terms_day=None,playing_role=None):
    from .simulation import require
    result=assess(s,p,cid,wage,end,terms_day=terms_day,playing_role=playing_role)
    require(result['acceptable'],'Player consent: '+' '.join(result['reasons']))
    return result


def public(s):
    return {key:deepcopy(s['recruitment'][key]) for key in ('clubs','leagues','players')}


def validate(s):
    from .simulation import require
    r=s['recruitment']
    for key in ('clubs','leagues','players'):
        for value in r[key].values():
            require(type(value['value']) is int and 1<=value['value']<=100,'Invalid public reputation.')
    require(all(p['id'] in r['players'] and p['id'] in r['priorities'] for p in s['players']),'Missing recruitment identity.')
    for prefs in r['priorities'].values():
        require(all(type(prefs[k]) is int and 1<=prefs[k]<=100 for k in ('status','minutes','money','security','prestige_tolerance')) and type(prefs['firm_status']) is bool,'Invalid career priorities.')
