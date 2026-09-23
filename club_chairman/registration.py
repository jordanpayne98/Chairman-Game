"""Fictional Northshire competition rules, shared by every club.

Employment and eligibility are separate. Loan returns preserve employment even
when there is no list place; they never silently displace another registration.
"""
from copy import deepcopy
from . import world_calendar

DEFAULTS = dict(name='Northshire League', senior_limit=25, exempt_under=21,
                minimum_age=16, non_homegrown_limit=17, loan_limit=5,
                minimum_players=7, starting_players=11, bench_limit=9,
                substitutions=5, substitution_windows=3, yellow_limit=5,
                red_ban=3, second_yellow_ban=1, loan_against_parent=False)


def initialise(s):
    cfg=s['config'].setdefault('competition',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    if 'registration' not in s:
        s['registration']={c['id']:[p['id'] for p in s['players'] if p['club']==c['id'] and not p['youth'] and not p['retired']]
                           for c in s['clubs']}
        s['registration_history']=[]


def list_players(s,cid,ids=None):
    ids=set(s['registration'][cid] if ids is None else ids)
    return [p for p in s['players'] if p['id'] in ids and p['club']==cid and not p['retired'] and not p['youth']]


def reserved(s,cid,exclude=None):
    ids=set()
    for o in s['career']['offers'].values():
        if cid=='c0' and o['kind']!='renew' and o['status'] in ('medical','ready'):ids.add(o['player'])
    for d in s['market']['deals'].values():
        if d['target']==cid and d['status'] in ('medical','ready'):ids.add(d['player'])
    for d in s.get('club_ai',{}).get('decisions',[]):
        if d['club']==cid and d['status']=='medical':ids.add(d['player'])
    ids.discard(exclude)
    return [p for p in s['players'] if p['id'] in ids and p['club']!=cid]


def capacity_errors(s,cid,players):
    cfg=s['config']['competition']
    senior=[p for p in players if world_calendar.age(s,p)>=cfg['exempt_under']]
    result=[]
    if len(senior)>cfg['senior_limit']:result.append(f"The senior list allows {cfg['senior_limit']} players aged {cfg['exempt_under']} or over.")
    if sum(not p['homegrown'] for p in senior)>cfg['non_homegrown_limit']:result.append('The non-homegrown allowance is full.')
    if any(p['age']<cfg['minimum_age'] for p in players):result.append(f"Senior competition requires age {cfg['minimum_age']} or over.")
    return result


def check_arrival(s,p,cid,is_loan=False):
    from .simulation import require
    players=list_players(s,cid)+reserved(s,cid,p['id'])
    if p['id'] not in {q['id'] for q in players}:players.append(p)
    errors=capacity_errors(s,cid,players)
    require(not errors,' '.join(errors)+' Review Squad > Registration before signing.')
    if is_loan:
        active={l['player'] for l in s['market']['loans'] if l['target']==cid and l['status']=='active'}
        active.update(d['player'] for d in s['market']['deals'].values() if d['kind']=='loan' and d['target']==cid and d['status'] in ('medical','ready'))
        active.add(p['id'])
        require(len(active)<=s['config']['competition']['loan_limit'],'The receiving club has reached its incoming-loan limit.')


def sync(s,previous=None):
    """Follow employment changes after committed commands/opening returns only."""
    if 'registration' not in s:return
    previous=previous or {}
    known={p['id']:p for p in s['players']}
    for cid,ids in s['registration'].items():
        s['registration'][cid]=[pid for pid in ids if pid in known and known[pid]['club']==cid and not known[pid]['youth'] and not known[pid]['retired']]
    for p in s['players']:
        cid=p['club']
        if not cid or p['youth'] or p['retired']:continue
        if previous.get(p['id'])==cid:continue
        if p['id'] in s['registration'][cid]:continue
        players=list_players(s,cid)+[p]
        if not capacity_errors(s,cid,players):s['registration'][cid].append(p['id'])
        elif cid=='c0':
            from .simulation import news
            news(s,'Registration needs review',p['name']+' is employed but has no senior list place. Review Squad > Registration.')


def reason(s,p,cid,opponent=None,day=None):
    day=s['day'] if day is None else day
    cfg=s['config']['competition']
    if p['club']!=cid:return 'Registered elsewhere'
    if p['retired']:return 'Retired'
    if p['youth']:return 'Academy: promotion required'
    if p['age']<cfg['minimum_age']:return 'Below senior minimum age'
    if p['contract_end'] is None or p['contract_end']<day:return 'Employment expired'
    if p['id'] not in s['registration'][cid]:return 'Not on competition list'
    if p['injury_until']>day:return 'Injured'
    if p['discipline']['ban']>0:return f"Suspended: {p['discipline']['ban']} match(es)"
    if p['condition']<35:return 'Not match fit'
    recovery=world_calendar.recovery_reason(s,p,day)
    if recovery:return recovery
    if opponent and not cfg['loan_against_parent']:
        from .market import active_loan
        loan=active_loan(s,p['id'])
        if loan and loan['source']==opponent:return 'Loan: cannot face parent club'
    return None


def apply(s,action,data):
    if action!='registration_submit':return None
    from .simulation import require,news
    from .career import window_end
    require(s['match'] is None and s['day']<=window_end(s) and not s['season_done'],'Competition lists can be edited during the registration window outside matchday.')
    ids=data.get('players')
    require(isinstance(ids,list) and all(isinstance(i,str) for i in ids) and len(ids)==len(set(ids)),'Submit unique player identities.')
    own={p['id']:p for p in s['players'] if p['club']=='c0' and not p['youth'] and not p['retired']}
    require(set(ids)<=set(own),'Only active senior players at this club can be registered.')
    players=[own[pid] for pid in ids]
    errors=capacity_errors(s,'c0',players+reserved(s,'c0'))
    require(not errors,' '.join(errors))
    require(len(players)>=s['config']['competition']['minimum_players'] and any(p['role']=='GK' for p in players),'Keep at least seven players including a goalkeeper on the list.')
    s['registration_history'].append(dict(day=s['day'],club='c0',before=list(s['registration']['c0']),after=list(ids)))
    s['registration']['c0']=list(ids)
    news(s,'Competition list submitted',f'{len(ids)} players registered. Injury, suspension and loan restrictions still apply on matchday.')
    return 'Competition list saved. Unlisted players retain their employment and wages.'


def snapshot(s):
    from .career import window_end
    own=list_players(s,'c0');cfg=s['config']['competition']
    senior=[p for p in own if world_calendar.age(s,p)>=cfg['exempt_under']]
    return dict(rules=deepcopy(cfg),players=list(s['registration']['c0']),
                ages={p['id']:world_calendar.age(s,p) for p in s['players'] if p['club']=='c0'},
                cutoff=s.get('world_calendar',{}).get('cutoffs',{}).get(str(s['career']['season'])),
                senior=len(senior),exempt=len(own)-len(senior),non_homegrown=sum(not p['homegrown'] for p in senior),
                reserved=len(reserved(s,'c0')),deadline=window_end(s))


def validate(s):
    from .simulation import require
    known={p['id'] for p in s['players']}
    require(set(s['registration'])=={c['id'] for c in s['clubs']},'Unknown competition club.')
    for cid,ids in s['registration'].items():
        require(len(ids)==len(set(ids)) and set(ids)<=known,'Invalid competition registration.')
