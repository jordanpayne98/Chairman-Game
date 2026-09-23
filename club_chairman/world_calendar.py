"""Shared domestic/development reservations and dated population evidence.

Existing careers activate new scheduling and age rules at their next season.
No international entrants or past appearances are manufactured during migration.
"""
from copy import deepcopy

DEFAULTS = dict(development_offset=3, development_search_days=14,
                minimum_rest_days=2, youth_age_limit=18)


def initialise(s, legacy=False):
    cfg=s['config'].setdefault('world_calendar',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('world_calendar',dict(activation_season=s['career']['season']+int(legacy),
        start_day=s['day'],population=[],reconciliations=[],cutoffs={}))
    freeze(s)


def active(s):
    return 'world_calendar' in s and s['career']['season']>=s['world_calendar']['activation_season']


def freeze(s):
    if not active(s):return
    key=str(s['career']['season'])
    s['world_calendar']['cutoffs'].setdefault(key,s['career']['start'])


def age(s,p):
    """Use the same 365-day birth clock as this career; do not rewrite birthdays."""
    if not active(s):return p['age']
    cutoff=s['world_calendar']['cutoffs'][str(s['career']['season'])]
    return max(0,(cutoff-p['birth_day'])//365)


def blocked_days(s):
    return set((s.get('calendar') or {}).get('blocked_days',[]))


def reservations(s,cid):
    """Include undrawn cup rounds, so advancement never displaces a youth game."""
    dates={f['day'] for f in s['fixtures'] if cid in (f['home'],f['away'])}
    cup=s['competitions']['cup']
    if cup and cid in cup['entrants']:dates.update(cup['dates'])
    return dates


def development_schedule(s):
    from . import career
    cfg=s['config']['world_calendar'];w=s['pathways'];season=s['career']['season']
    if w['season']==season:return
    freeze(s)
    rest=max(cfg['minimum_rest_days'],s['config']['pathways']['recovery_days'])
    blocked=blocked_days(s)
    senior={c['id']:reservations(s,c['id']) for c in s['clubs']}
    occupied={}
    for f in w['fixtures']:
        if f['season']==season and f['status']!='conflict':
            for cid in (f['home'],f['away']):occupied.setdefault((cid,f['group']),set()).add(f['day'])
    known={f['id'] for f in w['fixtures']}
    for f in sorted(s['fixtures'],key=lambda f:(f['day'],f['id'])):
        if f.get('competition') not in (None,'league'):continue
        target=f['day']+cfg['development_offset']
        for group in ('Youth','Reserves'):
            ident=f"dev:{season}:{f['id']}:{group}"
            if ident in known:continue
            start=max(s['day']+1,s['career']['start'],target-cfg['development_search_days'])
            end=min(career.season_end(s),target+cfg['development_search_days'])
            dates=sorted(range(start,end+1),key=lambda d:(abs(d-target),d))
            day=next((d for d in dates if d not in blocked and all(
                all(abs(d-other)>=rest for other in senior[cid]|occupied.get((cid,group),set()))
                for cid in (f['home'],f['away']))),None)
            reason='' if day is not None else 'Calendar conflict: no date satisfies recovery, cup reservations and blackout windows.'
            w['fixtures'].append(dict(id=ident,season=season,day=target if day is None else day,
                planned_day=target,home=f['home'],away=f['away'],group=group,
                status='conflict' if day is None else 'scheduled',result=None,reason=reason))
            if day is not None:
                for cid in (f['home'],f['away']):occupied.setdefault((cid,group),set()).add(day)
    w['season']=season


def recovery_reason(s,p,day):
    if not active(s):return None
    last=p['development'].get('last_played')
    if last is not None and 0<=day-last<s['config']['world_calendar']['minimum_rest_days']:
        return 'Recovery after a recent appearance'
    return None


def population(s):
    counts=dict(active=0,youth=0,reserves=0,seniors=0,free=0,retired=0)
    clubs={c['id']:dict(club=c['id'],youth=0,reserves=0,seniors=0,keepers=0) for c in s['clubs']}
    for p in s['players']:
        if p['retired']:counts['retired']+=1;continue
        counts['active']+=1
        if not p['club']:counts['free']+=1;continue
        group='youth' if p['youth'] else 'reserves' if p['development']['group']=='Reserves' else 'seniors'
        counts[group]+=1;clubs[p['club']][group]+=1
        if p['role']=='GK':clubs[p['club']]['keepers']+=1
    return dict(day=s['day'],season=s['career']['season'],counts=counts,clubs=list(clubs.values()))


def capture(s):
    return {p['id']:dict(club=p['club'],retired=p['retired'],youth=p['youth']) for p in s['players']}


def reconcile(s,before):
    """Audit the existing season population operations without rerolling anyone."""
    w=s['world_calendar'];season=s['career']['season']
    if any(r['season']==season for r in w['reconciliations']):return
    changes=[]
    for p in s['players']:
        old=before.get(p['id'])
        if old is None:
            action='Background squad vacancy' if p['club'] else 'Free-agent pool vacancy'
        elif not old['retired'] and p['retired']:action='Retirement / inactive exit'
        elif old['club']!=p['club']:action='Club change'
        elif old['youth'] and not p['youth']:action='Senior promotion'
        else:continue
        changes.append(dict(player=p['id'],action=action,previous=old,club=p['club']))
    w['reconciliations'].append(dict(day=s['day'],season=season,before=len(before),after=len(s['players']),changes=changes))
    w['population'].append(population(s))


def public(s):
    w=s['world_calendar'];season=s['career']['season'];names={p['id']:p['name'] for p in s['players']}
    fixtures=[dict(id=f['id'],day=f['day'],group='Senior',home=f['home'],away=f['away'],
                   status='played' if f['result'] is not None else 'scheduled',reason='')
              for f in s['fixtures'] if 'c0' in (f['home'],f['away'])]
    fixtures.extend(deepcopy([f for f in s['pathways']['fixtures'] if f['season']==season and 'c0' in (f['home'],f['away'])]))
    fixtures.sort(key=lambda f:(f['day']<s['day'],abs(f['day']-s['day']),f['id']))
    audit=deepcopy(w['reconciliations'][-1]) if w['reconciliations'] else None
    if audit:
        for r in audit['changes']:r['name']=names[r['player']]
    return dict(active=active(s),activation=w['activation_season'],cutoff=w['cutoffs'].get(str(season)),
        fixtures=fixtures,blackouts=sorted(blocked_days(s)),population=population(s),audit=audit,
        conflicts=sum(f['status']=='conflict' for f in s['pathways']['fixtures'] if f['season']==season),
        minimum_rest_days=s['config']['world_calendar']['minimum_rest_days'])


def validate(s):
    from .simulation import require
    cfg=s['config']['world_calendar'];w=s['world_calendar'];season=s['career']['season']
    require(all(type(cfg[k]) is int and cfg[k]>=0 for k in DEFAULTS),'Invalid world calendar tuning.')
    require(cfg['minimum_rest_days']>=2 and cfg['youth_age_limit']>=14,'Invalid recovery or age cutoff.')
    require(1<=w['activation_season']<=season+1,'Invalid calendar activation season.')
    if active(s):require(w['cutoffs'].get(str(season))==s['career']['start'],'Competition age cutoff does not match season opening.')
    known={p['id'] for p in s['players']};seen=set()
    for r in w['reconciliations']:
        require(r['season'] not in seen,'Duplicate population reconciliation.');seen.add(r['season'])
        require(all(c['player'] in known for c in r['changes']),'Population record lost its identity.')
        require(r['after']-r['before']==sum(c['previous'] is None for c in r['changes']),'Population creation count does not reconcile.')
    if not active(s):return
    slots={};blocked=blocked_days(s);rest=max(cfg['minimum_rest_days'],s['config']['pathways']['recovery_days'])
    senior={c['id']:reservations(s,c['id']) for c in s['clubs']}
    for f in s['pathways']['fixtures']:
        if f['season']!=season or f['status']=='conflict':continue
        require(f['day'] not in blocked,'Development fixture violates a blackout window.')
        for cid in (f['home'],f['away']):
            require(all(abs(f['day']-d)>=rest for d in senior[cid]),'Development fixture violates a senior reservation.')
            key=(cid,f['group']);previous=slots.setdefault(key,[])
            require(all(abs(f['day']-d)>=rest for d in previous),'Development fixtures violate recovery spacing.')
            previous.append(f['day'])
