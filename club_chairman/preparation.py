"""Recorded tactical practice, distinct from ability, morale and relationships."""
from copy import deepcopy
import math
from . import staff, manager_selection

DEFAULTS=dict(daily_gain=.8,match_gain=1.2,maximum_edge=2.,light_load=.5)
STYLES=('Balanced','Attacking','Cautious')


def system(formation,style):return formation+' / '+style


def initialise(s):
    cfg=s['config'].setdefault('preparation',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    s.setdefault('preparation',dict(players={},transitions=[],current=None,last_day=s['day'],report=None))
    appoint(s)


def appoint(s):
    data=s['preparation'];m=s['manager']
    target=dict(manager=m['id'],system=system(m['preferences']['formation'],m['preferences']['style'])) if m else None
    if data['current']==target:return
    data['current']=target
    data['transitions'].append(dict(day=s['day'],target=deepcopy(target)))
    # Appointment records a brief, not completed training or lost learning.


def record(s,pid,key):
    return s['preparation']['players'].setdefault(pid,{}).setdefault(key,dict(value=0.,sessions=0,minutes=0,last_day=s['day']))


def learn(s,pid,key,gain,minutes=0):
    r=record(s,pid,key)
    r['value']=round(min(100,r['value']+gain*(1-r['value']/100)),6)
    r['sessions']+=int(minutes==0);r['minutes']+=minutes;r['last_day']=s['day']


def process_day(s):
    data=s['preparation'];day=s['day']
    if day<=data['last_day']:return
    data['last_day']=day;appoint(s)
    if not s['manager']:return
    key=data['current']['system'];cfg=s['config']['preparation']
    matchday=any(f['day']==day and 'c0' in (f['home'],f['away']) for f in s['fixtures'])
    coach=staff.capability(s,'c0','coaching',default=0)
    teaching=(s['manager']['capabilities']['coaching']+coach)/200
    facilities=min(5,s['career']['facilities']['training'])
    rows=[]
    for p in s['players']:
        if p['club']!='c0' or p['retired'] or p['youth']:continue
        reason='Matchday' if matchday else 'Rehabilitation' if p['injury_until']>day else 'Recovery' if p['condition']<65 or p['fatigue']>70 else None
        before=value(s,p['id'],key)
        if not reason:
            load=cfg['light_load'] if p['development']['load']=='Light' else 1
            readiness=(p['condition']/100)*(1-p['fatigue']/100)
            gain=cfg['daily_gain']*(.5+teaching)*(1+.04*facilities)*load*readiness
            learn(s,p['id'],key,gain)
        rows.append(dict(player=p['id'],name=p['name'],status=reason or 'Trained',gain=round(value(s,p['id'],key)-before,3)))
    data['report']=dict(day=day,system=key,rows=rows)


def value(s,pid,key):return s['preparation']['players'].get(pid,{}).get(key,{}).get('value',0.)


def snapshot(s,m):
    if 'selection_plans' not in m:return
    entries=[None,None]
    for side,plan in enumerate(m['selection_plans']):
        if not plan:continue
        key=system(plan['formation'],s['manager']['preferences']['style'])
        entries[side]=dict(system=key,values={pid:value(s,pid,key) for pid in m['lineups'][side]+m['bench'][side]},
                           maximum_edge=s['config']['preparation']['maximum_edge'],match_gain=s['config']['preparation']['match_gain'])
    m['preparation']=entries


def edge(m,side):
    entry=m.get('preparation',[None,None])[side]
    ids=m['on_pitch'][side]
    if not entry or not ids:return 0.
    return entry['maximum_edge']*sum(entry['values'].get(pid,0) for pid in ids)/len(ids)/100


def settle(s,m):
    if m.get('forfeit'):return
    for side,entry in enumerate(m.get('preparation',[None,None])):
        if not entry:continue
        for pid in m['participants'][side]:
            minutes=min(90,m['stats'][pid]['minutes'])
            if minutes>0:learn(s,pid,entry['system'],entry['match_gain']*minutes/90,minutes)


def view(s):
    data=s['preparation'];current=data['current'];key=current['system'] if current else None
    rows=[]
    for p in s['players']:
        if p['club']!='c0' or p['retired'] or p['youth']:continue
        records=data['players'].get(p['id'],{});r=records.get(key)
        rows.append(dict(id=p['id'],name=p['name'],role=p['role'],value=round(r['value'],1) if r else None,
                         sessions=r['sessions'] if r else 0,minutes=r['minutes'] if r else 0,retained=len(records)))
    return dict(current=deepcopy(current),since=data['transitions'][-1]['day'] if data['transitions'] else None,
                report=deepcopy(data['report']),rows=rows)


def validate(s):
    from .simulation import require
    cfg=s['config']['preparation'];data=s['preparation']
    for k,limit in (('daily_gain',3),('match_gain',5),('maximum_edge',3),('light_load',1)):
        require(type(cfg[k]) in (int,float) and math.isfinite(cfg[k]) and 0<=cfg[k]<=limit,'Invalid tactical preparation setting.')
    known={p['id'] for p in s['players']}
    keys={system(f,t) for f in manager_selection.FORMATIONS for t in STYLES}
    require(type(data['last_day']) is int and 0<=data['last_day']<=s['day'],'Invalid preparation date.')
    require(set(data['players'])<=known,'Unknown preparation player.')
    for records in data['players'].values():
        require(set(records)<=keys,'Unknown preparation system.')
        for r in records.values():
            require(type(r['value']) in (int,float) and math.isfinite(r['value']) and 0<=r['value']<=100,'Invalid tactical preparation.')
            require(all(type(r[k]) is int and r[k]>=0 for k in ('sessions','minutes','last_day')) and r['last_day']<=s['day'],'Invalid preparation evidence.')
