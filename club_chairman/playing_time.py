"""Explicit working agreements, distinct from ability and employment wages.

Only post-agreement, pre-kickoff availability evidence can be reviewed. No
selection override, retrospective promise, publicity or repeated morale penalty.
"""
from copy import deepcopy
from . import registration, recruitment

ROLES = {'Key starter': ('starts', 75), 'Regular starter': ('starts', 55),
         'Rotation': ('minutes', 30), 'Squad cover': ('minutes', 10),
         'Development prospect': ('minutes', 15)}
DEFAULTS = dict(review_days=28, minimum_fixtures=3, meaningful_minutes=30,
                concern_cost=6, promise_value=6,
                key_starter=75,regular_starter=55,rotation=30,squad_cover=10,development_prospect=15)


def initialise(s):
    cfg=s['config'].setdefault('playing_time',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    s.setdefault('playing_time',dict(agreements={},history=[],conversations=[]))


def policy(s,role):
    return ROLES[role][0],s['config']['playing_time'][role.lower().replace(' ','_')]


def active(s,pid,cid=None):
    row=s['playing_time']['agreements'].get(pid)
    return row if row and (cid is None or row['club']==cid) else None


def terms(s,p,cid,role):
    from .simulation import require
    require(role is None or isinstance(role,str) and role in ROLES,'Choose a listed playing-time role.')
    previous=active(s,p['id'],cid)
    if previous and role is None:role=previous['role']
    if previous and role!=previous['role']:
        # A renewal cannot silently reset an existing working agreement.
        require(False,'Discuss a role change in the player profile before renewing on different terms.')
    return role


def credibility(s,p,cid,role):
    """Public role-capacity warning, shared across clubs; never hidden CA."""
    if role is None:return True,'No new playing-time commitment.'
    occupied=0
    for row in s['playing_time']['agreements'].values():
        if row['club']==cid and row['position']==p['role'] and row['player']!=p['id']:
            occupied+=row['target']
    for o in s['career']['offers'].values():
        if cid=='c0' and o['player']!=p['id'] and o['status'] in ('medical','ready') and o.get('playing_role'):
            if not active(s,o['player'],cid):
                q=next(q for q in s['players'] if q['id']==o['player'])
                if q['role']==p['role']:occupied+=policy(s,o['playing_role'])[1]
    for d in s['club_ai']['decisions']:
        if d['club']==cid and d['player']!=p['id'] and d['status'] in ('medical','rights_wait') and d.get('playing_role'):
            q=next(q for q in s['players'] if q['id']==d['player'])
            if q['role']==p['role']:occupied+=policy(s,d['playing_role'])[1]
    credible=occupied+policy(s,role)[1]<=recruitment.SLOTS[p['role']]*100
    return credible,('Role capacity fits the recorded commitments; selection remains the manager’s decision.' if credible else
        'Risk: competing role commitments exceed positional capacity. The player gives this promise no recruitment credit; it cannot force selection.')


def sign(s,p,cid,role,source):
    if role is None:return
    prior=active(s,p['id'])
    if prior and prior['club']==cid:return  # Renewals preserve evidence and concern.
    if prior:close(s,p['id'],'Permanent club change')
    cfg=s['config']['playing_time'];metric,target=policy(s,role)
    s['playing_time']['agreements'][p['id']]=dict(id=source+':role',player=p['id'],club=cid,
        position=p['role'],role=role,metric=metric,target=target,start=s['day'],
        next_review=s['day']+cfg['review_days'],review_days=cfg['review_days'],
        minimum_fixtures=cfg['minimum_fixtures'],meaningful_minutes=cfg['meaningful_minutes'],
        scope='Senior domestic league and cup',evidence=[],reviews=[],concern=None,
        changes=[],capacity_warning=credibility(s,p,cid,role)[1])


def close(s,pid,reason):
    row=s['playing_time']['agreements'].pop(pid,None)
    if row:s['playing_time']['history'].append(dict(row,closed=s['day'],closure=reason))


def reconcile(s):
    players={p['id']:p for p in s['players']}
    for pid,row in list(s['playing_time']['agreements'].items()):
        p=players[pid]
        # Temporary loans suspend coverage; the original promise survives return.
        from .market import active_loan
        loan=active_loan(s,pid)
        if p['retired'] or p['contract_end'] is None or p['contract_end']<s['day']:
            close(s,pid,'Employment ended')
        elif p['club']!=row['club'] and not (loan and loan['source']==row['club']):
            close(s,pid,'Permanent club change')


def snapshot(s,m):
    rows={}
    for p in s['players']:
        row=active(s,p['id'],p['club'])
        if not row or p['club'] not in (m['home'],m['away']):continue
        opponent=m['away'] if p['club']==m['home'] else m['home']
        reason=registration.reason(s,p,p['club'],opponent)
        # Dropping someone from a registration list is a club decision, not an
        # availability exemption with which to hide a broken promise.
        excused=bool(reason and reason!='Not on competition list')
        rows[p['id']]=dict(agreement=row['id'],day=s['day'],excused=excused,reason=reason,
            started=p['id'] in m['lineups'][0]+m['lineups'][1])
    if rows:m['playing_time_snapshot']=rows


def collect(s,m):
    if m.get('forfeit') or m.get('abandoned') or m.get('engine')!=2:return
    for pid,item in m.get('playing_time_snapshot',{}).items():
        row=active(s,pid)
        if not row or row['id']!=item['agreement']:continue
        if any(e['fixture']==m['fixture'] for e in row['evidence']):continue
        injured=any(e['kind']=='injury' and e.get('player')==pid for e in m['events'])
        minutes=min(90,max(0,m['stats'].get(pid,{}).get('minutes',0)))
        row['evidence'].append(dict(item,fixture=m['fixture'],minutes=minutes,
            excused=item['excused'] or injured,
            reason='In-match injury' if injured else item['reason'],
            meaningful_start=item['started'] and minutes>=row['meaningful_minutes']))


def review(s):
    from .simulation import news
    for row in s['playing_time']['agreements'].values():
        while s['day']>=row['next_review']:
            cutoff=row['next_review'];start=cutoff-row['review_days']
            rows=[e for e in row['evidence'] if start<=e['day']<cutoff]
            eligible=[e for e in rows if not e['excused']]
            n=len(eligible);minutes=sum(e['minutes'] for e in eligible);starts=sum(e['meaningful_start'] for e in eligible)
            actual=(100*starts/n if row['metric']=='starts' else 100*minutes/(90*n)) if n else None
            outcome='Insufficient opportunities' if n<row['minimum_fixtures'] else 'Fulfilled' if actual>=row['target'] else 'Below agreement'
            record=dict(day=cutoff,start=start,role=row['role'],metric=row['metric'],target=row['target'],
                fixtures=n,excused=len(rows)-n,starts=starts,minutes=minutes,actual=actual,outcome=outcome)
            row['reviews'].append(record)
            if outcome=='Below agreement':
                if row['concern'] is None:row['concern']=dict(id=row['id']+':shortfall',since=cutoff)
            elif outcome=='Fulfilled':row['concern']=None
            # Insufficient evidence does not erase an unresolved concern.
            if row['club']=='c0' and rows:
                p=next(p for p in s['players'] if p['id']==row['player'])
                news(s,'Playing-time review',f"{p['name']}: {outcome.lower()}. {starts} meaningful starts / {minutes} minutes across {n} available fixtures; {len(rows)-n} excused. Open profile > Contract > Playing time.")
            row['next_review']+=row['review_days']


def apply(s,action,data):
    if action!='discuss_playing_role':return None
    from .simulation import require
    from .market import active_loan
    require(s['match'] is None,'Discuss playing time outside matchday.')
    p=next((p for p in s['players'] if p['id']==data.get('id')),None)
    require(p is not None and p['club']=='c0' and not p['retired'] and not p['youth'],'Only your active senior players can discuss a role here.')
    require(active_loan(s,p['id']) is None,'Resolve the loan before agreeing a permanent club role.')
    offer=s['career']['offers'].get(p['id'])
    require(not offer or offer['status'] in ('completed','withdrawn','expired','rejected'),'Finish or withdraw employment talks before changing the role agreement.')
    role=data.get('role');require(isinstance(role,str) and role in ROLES,'Choose a listed playing-time role.')
    row=active(s,p['id'],'c0')
    require(not row or role!=row['role'],'This role is already agreed; its evidence and review date are retained.')
    talks=s['playing_time']['conversations']
    last=next((r for r in reversed(talks) if r['player']==p['id']),None)
    require(not last or s['day']>=last['day']+s['config']['playing_time']['review_days'],'Allow a review period before reopening this role conversation.')
    # Changes wait for a complete review, preventing last-day deadline resets.
    require(not row or row['reviews'] and row['reviews'][-1]['day']==s['day'],'Review the current window first; role changes are discussed on its review day.')
    lower=bool(row and policy(s,role)[1]<row['target'])
    consent=not lower or (row['concern'] is not None and s['recruitment']['priorities'][p['id']]['minutes']<=60)
    message=('Player: I accept '+role+'. The manager retains selection authority.' if consent else
             'Player: I do not accept a reduced role. My current agreement remains in force.')
    talks.append(dict(player=p['id'],club='c0',day=s['day'],role=role,accepted=consent,response=message))
    if consent:
        if row:
            row['changes'].append(dict(day=s['day'],before=row['role'],after=role,response=message))
            row.update(role=role,metric=policy(s,role)[0],target=policy(s,role)[1])
            # Concern is resolved only by a fulfilled future review, not dialogue.
        else:sign(s,p,'c0',role,f"role:{p['id']}:{s['revision']}")
    return message+' '+credibility(s,p,'c0',role)[1]


def public(s):
    state=s['playing_time']
    return dict(settings=deepcopy(s['config']['playing_time']),agreements={pid:deepcopy(r) for pid,r in state['agreements'].items() if r['club']=='c0'},
        history=[deepcopy(r) for r in state['history'] if r['club']=='c0'],
        conversations=[deepcopy(r) for r in state['conversations'] if r['club']=='c0'])


def validate(s):
    from .simulation import require
    for value in s['config']['playing_time'].values():require(type(value) is int and value>0,'Invalid playing-time tuning.')
    require(all(policy(s,role)[1]<=100 for role in ROLES),'Invalid role target.')
    require(s['config']['playing_time']['meaningful_minutes']<=90,'Invalid meaningful-start threshold.')
    known={p['id'] for p in s['players']};clubs={c['id'] for c in s['clubs']}
    for pid,row in s['playing_time']['agreements'].items():
        require(pid in known and row['player']==pid and row['club'] in clubs,'Invalid role identity.')
        require(row['role'] in ROLES and row['metric']==ROLES[row['role']][0] and 0<row['target']<=100,'Invalid agreed role.')
        require(row['next_review']>row['start'] and row['review_days']>0 and row['minimum_fixtures']>0 and 0<row['meaningful_minutes']<=90,'Invalid role review window.')
        require(len({e['fixture'] for e in row['evidence']})==len(row['evidence']),'Duplicate playing-time evidence.')
        require(all(0<=e['minutes']<=90 and e['day']>=row['start'] for e in row['evidence']),'Invalid playing-time evidence.')
