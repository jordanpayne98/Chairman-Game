"""Capacity-limited, paid observations and evidence-led recruitment briefs."""
from copy import deepcopy
from . import career, people, staff, market

DEFAULTS = dict(desk_capacity=2, remote_cost_multiplier=2, remote_travel_days=3)


def initialise(s):
    cfg=s['config'].setdefault('scouting_work',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    work=s.setdefault('scouting_work',dict(jobs=[],brief=None,history=[],signings=[]))
    for pid,due in s['scouting'].items():
        if not any(j['player']==pid and j['status']=='queued' for j in work['jobs']):
            work['jobs'].append(dict(id='legacy:'+pid,player=pid,observer='Legacy analyst',observer_id=None,start=min(s['day'],due),due=due,cost=0,legacy=True,remote=False,status='queued'))


def quote(s,p):
    cfg=s['config']['scouting_work'];day=s['day']
    observers=[q for q in s['staff']['people'] if q['club']=='c0' and q['role']=='Recruitment' and q['end']>=day and q['availability']>q['workload']]
    lanes=[(q['id'],q['name'],max(1,cfg['desk_capacity']*(q['availability']-q['workload'])//100)) for q in observers] or [(None,'Commissioned analyst',1)]
    remote=p['nationality']!=s['config'].get('nation',{}).get('name','England')
    duration=s['config']['scout_days']+(cfg['remote_travel_days'] if remote else 0)
    choices=[]
    for ident,name,capacity in lanes:
        jobs=[j for j in s['scouting_work']['jobs'] if j['status']=='queued' and j['observer_id']==ident]
        start=day
        while True:
            points={start}|{j['start'] for j in jobs if start<=j['start']<start+duration}
            collisions=[t for t in points if sum(j['start']<=t<j['due'] for j in jobs)>=capacity]
            if not collisions:break
            start=min(j['due'] for j in jobs if j['start']<=min(collisions)<j['due'])
        choices.append(dict(observer=name,observer_id=ident,start=start,due=start+duration,cost=s['config']['scout_fee']*(cfg['remote_cost_multiplier'] if remote else 1),remote=remote))
    return min(choices,key=lambda q:(q['due'],q['observer_id'] or ''))


def commission(s,pid):
    from .simulation import require, posting
    p=career.person(s,pid)
    require(p['club']!='c0' and not p['retired'] and not p['youth'],'Choose an active external senior player.')
    require(pid not in s['scouting'] and (pid not in s['reports'] or s['reports'][pid]['day']<s['day']),'Scouting is in progress or this player was assessed today.')
    q=quote(s,p);require(career.free_cash(s,q['cost']),'Insufficient available cash for scouting.')
    ident=f"scout:{pid}:{s['revision']}:{len(s['scouting_work']['jobs'])}"
    posting(s,ident,-q['cost'],'Scouting and travel')
    job=dict(q,id=ident,player=pid,status='queued',legacy=False)
    s['scouting_work']['jobs'].append(job);s['scouting'][pid]=q['due']
    return job


def process_day(s):
    from .simulation import news
    for j in s['scouting_work']['jobs']:
        if j['status']!='queued' or j['due']>s['day']:continue
        p=career.person(s,j['player']);s['scouting'].pop(p['id'],None)
        j['status']='unavailable' if p['retired'] else 'complete'
        if p['retired']:continue
        observer=next((q for q in s['staff']['people'] if q['id']==j['observer_id']),None)
        ability=observer['capabilities']['potential_assessment'] if observer else 50
        r=people.report(s,p,j['observer'],max(4,14-ability//10),complete=True)
        r.update(observer=j['observer'],owner='c0',observed_from=j['start'],context='Travel assessment' if j['remote'] else 'Domestic assessment',job=j['id'])
        s['reports'][p['id']]=r;j['report']=deepcopy(r)
        news(s,'Scouting report ready',p['name']+': current ratings assessed; potential remains uncertain.')


def apply(s,action,data):
    if action not in ('scout_batch','recruitment_brief'):return None
    from .simulation import require
    from .playing_time import ROLES
    require(not s['season_done'] and s['match'] is None,'Recruitment is closed during matchday or after season end.')
    if action=='recruitment_brief':
        low=data.get('min_age',16);high=data.get('max_age',30);cost=data.get('ceiling')
        require(data.get('role') in ('GK','DEF','MID','FWD') and type(low) is int and type(high) is int and 16<=low<=high<=45,'Choose a position and valid age range.')
        require(type(cost) is int and cost>0 and data.get('playing_role') in ROLES,'Choose a cost ceiling and playing role.')
        s['scouting_work']['brief']=dict(role=data['role'],min_age=low,max_age=high,ceiling=cost,playing_role=data['playing_role'],day=s['day'])
        return 'Recruitment brief saved. Recommendations use recorded observations only.'
    ids=data.get('ids');require(isinstance(ids,list) and len(ids)<=12 and all(isinstance(pid,str) for pid in ids),'Choose up to twelve saved targets.')
    results=[]
    for pid in dict.fromkeys(ids):
        try:
            j=commission(s,pid);results.append(dict(player=pid,ok=True,message=f"Paid {j['cost']/100:.2f}; report due day {j['due']}.",day=s['day']))
        except ValueError as e:results.append(dict(player=pid,ok=False,message=str(e),day=s['day']))
    s['scouting_work']['history'].extend(results)
    return f"Scouting batch: {sum(r['ok'] for r in results)} commissioned; {sum(not r['ok'] for r in results)} unavailable. Review Batch results."


def recommend(s):
    brief=s['scouting_work']['brief'];rows=[]
    if not brief:return rows
    for p in s['players']:
        if p['club']=='c0' or p['youth'] or p['retired'] or p['role']!=brief['role'] or not brief['min_age']<=p['age']<=brief['max_age']:continue
        r=people.observed_report(s,p)
        if not r or 'overall' not in r:continue
        cost=p['fee']+52*p['wage']
        if p['club']:cost+=market.quote(s,p)
        if cost>brief['ceiling']:continue
        rows.append(dict(id=p['id'],name=p['name'],rating=r['overall'],knowledge=r['knowledge'],day=r['day'],cost=cost,reason='Observed position and age fit; estimated first-year cost within brief.',risk='Terms, willingness and future development remain uncertain.'))
    return sorted(rows,key=lambda r:(-sum(r['rating']),r['cost'],r['id']))[:12]


def record_signings(s,previous):
    w=s['scouting_work']
    for p in s['players']:
        if p['club']!='c0' or p['youth'] or previous.get(p['id'])=='c0':continue
        offer=next((o for o in reversed(list(s['career']['offers'].values())) if o['player']==p['id'] and o['status']=='completed'),None)
        if not offer:continue
        ident=f"{p['id']}:{s['day']}"
        if any(r['id']==ident for r in w['signings']):continue
        r=people.observed_report(s,p)
        w['signings'].append(dict(id=ident,player=p['id'],day=s['day'],brief=deepcopy(w['brief']),wage=p['wage'],end=p['contract_end'],role=offer.get('playing_role','No explicit role'),evidence_day=r['day'] if r else None,appearances=p['career_appearances']+p['appearances'],goals=p['career_goals']+p['goals']))


def public(s):
    w=s['scouting_work'];out=[]
    for r in w['signings']:
        p=career.person(s,r['player']);out.append(dict(deepcopy(r),name=p['name'],club=p['club'],subsequent_appearances=p['career_appearances']+p['appearances']-r['appearances'],subsequent_goals=p['career_goals']+p['goals']-r['goals']))
    return dict(brief=deepcopy(w['brief']),recommendations=recommend(s),jobs=[{k:deepcopy(v) for k,v in j.items() if k!='report'} for j in w['jobs']],history=deepcopy(w['history'][-60:]),signings=out)


def validate(s):
    from .simulation import require
    jobs=s['scouting_work']['jobs'];known={p['id'] for p in s['players']}
    require(len({j['id'] for j in jobs})==len(jobs),'Duplicate scouting job.')
    for j in jobs:require(j['player'] in known and j['due']>=j['start'] and j['cost']>=0 and j['status'] in ('queued','complete','unavailable'),'Invalid scouting job.')
    cfg=s['config']['scouting_work']
    require(all(type(v) is int and v>=0 for v in cfg.values()) and cfg['desk_capacity']>0 and cfg['remote_cost_multiplier']>=1,'Invalid scouting capacity or travel cost.')
