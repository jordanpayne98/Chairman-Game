"""Persistent review detail for supporting clubs; no entity is discarded.

This first detail stage reduces routine AI reviews only. Football, development,
financial accrual and dated transactions retain their existing simulation.
"""
from copy import deepcopy
import json
from pathlib import Path


def initialise(s,legacy=False):
    if 'detail' in s:return
    s['config']['detail']=json.loads((Path(__file__).resolve().parent.parent/'data/detail.json').read_text(encoding='utf-8'))
    s['detail']=dict(activation_season=s['career']['season']+int(legacy),levels={},transitions=[])
    synchronise(s)


def expected(s):
    active=s['career']['season']>=s['detail']['activation_season']
    supporting={cid for d in s['leagues']['divisions'] if d.get('supporting') for cid in d['members']}
    return {c['id']:'reduced' if active and c['id'] in supporting and c['id']!='c0' else 'detailed' for c in s['clubs']}


def synchronise(s):
    """Season-boundary change before fixtures; people and obligations stay intact."""
    data=s['detail'];levels=expected(s)
    for cid,level in levels.items():
        old=data['levels'].get(cid)
        if old is not None and old!=level:
            data['transitions'].append(dict(club=cid,previous=old,level=level,day=s['day'],season=s['career']['season']))
    data['levels']=levels


def review_due(s,cid,squad):
    """Urgency retains the existing weekly review; pending deals settle daily."""
    if s['detail']['levels'][cid]=='detailed':return True
    from .career import window_end
    cfg=s['config']['detail'];day=s['day']
    # Keep weekly recruitment in the short registration window, and react to
    # vacancies/expiry before routine scheduling can strand a club.
    if day<=window_end(s):return True
    if any(sum(p['role']==role for p in squad)<n for role,n in cfg['minimum_cover'].items()):return True
    available=sum(p['injury_until']<=day and p['discipline']['ban']==0 for p in squad)
    if available<s['config']['competition']['minimum_players']:return True
    if any(p['contract_end'] is not None and p['contract_end']-day<=cfg['urgent_days'] for p in squad):return True
    employees=[p for p in s['staff']['people'] if p['club']==cid]
    if any(not any(p['role']==role for p in employees) for role in ('Executive','Football director','Coaching')):return True
    if any(p['end']-day<=cfg['urgent_days'] for p in employees):return True
    if any(b['source']==cid and b['status']=='scheduled' and b['due']-day<=cfg['urgent_days'] for b in s['market']['obligations']):return True
    return day-s['club_ai']['last_review'].get(cid,0)>=cfg['routine_days']


def snapshot(s):
    return dict(deepcopy(s['detail']),routine_days=s['config']['detail']['routine_days'])


def validate(s):
    from .simulation import require
    data=s['detail'];cfg=s['config']['detail'];weekly=s['config']['club_ai']['review_days']
    require(type(cfg['routine_days']) is int and cfg['routine_days']>=weekly and cfg['routine_days']%weekly==0,'Invalid supporting-club review interval.')
    require(type(cfg['urgent_days']) is int and cfg['urgent_days']>=weekly,'Invalid urgent review horizon.')
    require(set(cfg['minimum_cover'])=={'GK','DEF','MID','FWD'} and all(type(n) is int and n>0 for n in cfg['minimum_cover'].values()),'Invalid supporting squad cover.')
    require(type(data['activation_season']) is int and 1<=data['activation_season']<=s['career']['season']+1,'Invalid detail activation season.')
    require(data['levels']==expected(s),'Club detail does not match membership or ownership.')
    keys=set()
    for t in data['transitions']:
        require(t['club'] in data['levels'] and t['previous'] in ('reduced','detailed') and t['level'] in ('reduced','detailed') and t['previous']!=t['level'],'Invalid detail transition.')
        require(type(t['day']) is int and 0<=t['day']<=s['day'] and type(t['season']) is int and 1<=t['season']<=s['career']['season'],'Invalid detail transition date.')
        key=(t['club'],t['season']);require(key not in keys,'Duplicate detail transition.');keys.add(key)
