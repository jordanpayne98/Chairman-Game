"""Observed social contact and coordination, separate from mood and tactics.

Sparse directed links accrue only from completed contact. Match inputs are frozen
at kickoff; the contributing participants change with substitutions/dismissals.
"""
from copy import deepcopy
from itertools import combinations
import math

DEFAULTS = dict(training_gain=1., minutes_gain=.025, trust_gain=.08,
                maximum_edge=1.5, settling_days=28, grievance_days=28,
                summary_days=28, trust_weight=.3, influence_weight=.2)


def initialise(s):
    cfg=s['config'].setdefault('dynamics',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('dynamics',dict(links={},members={},staff_links={},events=[],
        settled=[],last_day=s['day'],summaries=[],history=[],manager=None))
    sync(s,baseline=True)


def roster(s,cid):
    return sorted((p for p in s['players'] if p['club']==cid and not p['retired'] and not p['youth']),key=lambda p:p['id'])


def pair_key(cid,a,b):return cid+'|'+a+'>'+b


def sync(s,baseline=False):
    d=s['dynamics'];current={p['id']:p for p in s['players'] if p['club'] and not p['youth'] and not p['retired']}
    for pid,r in sorted(d['members'].items()):
        if pid not in current or current[pid]['club']!=r['club']:
            d['events'].append(dict(id=f"departure:{pid}:{r['club']}:{s['day']}:{len(d['events'])}",day=s['day'],club=r['club'],kind='departure',
                person=pid,reason='Left the first-team group; current coordination excludes this player.',public=True))
            del d['members'][pid]
    for pid,p in current.items():
        if pid not in d['members']:
            d['members'][pid]=dict(club=p['club'],since=s['day'],days=0,settled=bool(baseline))
    m=s['manager'];mid=m['id'] if m else None
    if mid!=d['manager']:
        if d['manager'] is not None:
            d['events'].append(dict(id=f"manager:{s['day']}:{len(d['events'])}",day=s['day'],club='c0',kind='manager_change',
                person=d['manager'],reason='Manager changed; personal reactions stay with their original author. Player agreements are retained.',public=True))
        d['manager']=mid


def contact(s,cid,a,b,amount,minutes=0):
    d=s['dynamics'];cfg=s['config']['dynamics']
    for source,target in ((a,b),(b,a)):
        key=pair_key(cid,source['id'],target['id'])
        r=d['links'].setdefault(key,dict(club=cid,source=source['id'],target=target['id'],
            familiarity=0.,trust=50.,respect=50.,alignment=50.,sessions=0,minutes=0,last_day=s['day']))
        r['familiarity']=round(min(100,r['familiarity']+amount),6)
        # Trust is earned from this counterpart's observed working conduct,
        # never from CA, external reputation, wages or an invented leader trait.
        delta=cfg['trust_gain']*(target['hidden']['professionalism']-50)/50*min(1,amount)
        r['trust']=round(max(0,min(100,r['trust']+delta)),6)
        r['respect']=round(max(0,min(100,r['respect']+delta/2)),6)
        r['sessions']+=int(minutes==0);r['minutes']+=minutes;r['last_day']=s['day']


def process_day(s):
    d=s['dynamics'];cfg=s['config']['dynamics'];sync(s)
    if s['day']<=d['last_day']:return
    d['last_day']=s['day']
    fixtures={cid for f in s['fixtures'] if f['day']==s['day'] for cid in (f['home'],f['away'])}
    for c in s['clubs']:
        rows=roster(s,c['id'])
        attending=[p for p in rows if p['injury_until']<=s['day'] and p['condition']>=65 and p['fatigue']<=70]
        if c['id'] not in fixtures:
            for p in attending:
                r=d['members'][p['id']];r['days']+=1
                needed=cfg['settling_days']*(1.5-p['hidden']['adaptability']/100)
                if r['days']>=needed:r['settled']=True
            for a,b in combinations(attending,2):
                # Settling changes the rate of social familiarity only, not a
                # second morale, training-ability or tactical-practice modifier.
                factor=min(1,(d['members'][a['id']]['days']+1)/cfg['settling_days'],
                           (d['members'][b['id']]['days']+1)/cfg['settling_days'])
                contact(s,c['id'],a,b,cfg['training_gain']*(.5+.5*factor))
    for r in d['staff_links'].values():
        if r['concern'] and s['day']>=r['concern']['day']+cfg['grievance_days']:
            r['concern']=None # historical evidence is retained; trust is not reset
    summary=group(s,'c0')
    d['history'].append(dict(day=s['day'],members=[p['id'] for p in roster(s,'c0')],value=summary['value']))
    d['history']=d['history'][-8:]
    if s['day']%cfg['summary_days']==0 and not any(r['day']==s['day'] for r in d['summaries']):
        concerns=concern_rows(s)
        report=dict(day=s['day'],cohesion=summary,concerns=deepcopy(concerns))
        d['summaries'].append(report)
        from .simulation import news
        news(s,'Club dynamics review',f"{summary['label']}; {len(concerns)} concerns. Open Squad > Club dynamics for evidence and private follow-up.")


def influence(s,cid,ids):
    result={}
    for pid in ids:
        incoming=[s['dynamics']['links'].get(pair_key(cid,other,pid)) for other in ids if other!=pid]
        result[pid]=sum(min(1,r['familiarity']/50)*max(0,(r['trust']-50)/50) for r in incoming if r)/max(1,len(incoming))
    return result


def group(s,cid,ids=None):
    ids=sorted(ids if ids is not None else [p['id'] for p in roster(s,cid)])
    cfg=s['config']['dynamics'];leaders=influence(s,cid,ids);total=len(ids)*(len(ids)-1);covered=0;scores=[]
    for a in ids:
        for b in ids:
            if a==b:continue
            r=s['dynamics']['links'].get(pair_key(cid,a,b))
            if r:covered+=1
            scores.append(pair_score(r,leaders.get(b,0),cfg))
    value=max(1,round(50+50*sum(scores)/max(1,total),1)) if covered else None
    return dict(value=value,label='Not assessed' if value is None else 'Strained' if value<45 else 'Developing' if value<65 else 'Established',
                covered=covered,total=total,members=len(ids))


def pair_score(r,influence_value,cfg):
    if not r:return 0.
    familiar=r['familiarity']/100;trust=(r['trust']-50)/50
    # Missing evidence is neutral, never an assumed excellent relationship.
    return max(-1,min(1,((1-cfg['trust_weight'])*familiar+cfg['trust_weight']*trust)*
                         (1+cfg['influence_weight']*influence_value)))


def snapshot(s,m):
    ids=sum(m['lineups']+m['bench'],[]);cfg=s['config']['dynamics']
    m['dynamics']=dict(config=deepcopy(cfg),links={k:deepcopy(v) for k,v in s['dynamics']['links'].items()
        if v['club'] in (m['home'],m['away']) and v['source'] in ids and v['target'] in ids},overlap={})


def tick(m):
    if 'dynamics' not in m:return
    overlap=m['dynamics']['overlap']
    for side,cid in enumerate((m['home'],m['away'])):
        for a,b in combinations(sorted(m['on_pitch'][side]),2):
            k=pair_key(cid,a,b);overlap[k]=overlap.get(k,0)+1


def edge(m,side,pid):
    data=m.get('dynamics')
    if not data:return 0.
    ids=m['on_pitch'][side];cid=(m['home'],m['away'])[side];cfg=data['config']
    if pid not in ids or len(ids)<2:return 0.
    # Cache only frozen evidence, keyed by the actual on-pitch membership.
    cache=data.setdefault('edges',{})
    key=cid+'|'+','.join(sorted(ids))
    if key not in cache:
        leaders={}
        for target in ids:
            rows=[data['links'].get(pair_key(cid,a,target)) for a in ids if a!=target]
            leaders[target]=sum(min(1,r['familiarity']/50)*max(0,(r['trust']-50)/50) for r in rows if r)/len(rows)
        cache[key]={a:cfg['maximum_edge']*sum(pair_score(data['links'].get(pair_key(cid,a,b)),leaders[b],cfg)
                    for b in ids if b!=a)/(len(ids)-1) for a in ids}
    return cache[key][pid]


def settle(s,m):
    d=s['dynamics']
    if 'dynamics' not in m or m.get('forfeit') or m.get('abandoned') or m['fixture'] in d['settled']:return
    d['settled'].append(m['fixture']);players={p['id']:p for p in s['players']}
    for key,minutes in m['dynamics']['overlap'].items():
        cid,pair=key.split('|');a,b=pair.split('>')
        if minutes:contact(s,cid,players[a],players[b],minutes*s['config']['dynamics']['minutes_gain'],minutes)


def staff_people(s,cid):
    rows=[p for p in s['staff']['people'] if p['club']==cid and p['availability']>0]
    if cid=='c0' and s['manager']:rows=rows+[s['manager']]
    return {p['id']:p for p in rows}


def bench_event(s,m,choice,response):
    if 'dynamics' not in m:return # preserve the legacy in-progress match contract
    cid='c0';manager=s['manager'];people=staff_people(s,cid)
    witnesses=sorted(p['id'] for p in people.values() if p.get('role')=='Coaching')
    participants=[cid+':chairman',manager['id']]
    key='bench:'+m['fixture'];d=s['dynamics']
    if any(e['id']==key for e in d['events']):return
    own=0 if m['home']==cid else 1
    suitable=m['score'][own]<m['score'][1-own]
    reactions=[]
    for pid in [manager['id']]+witnesses:
        p=people[pid];link_id=cid+'|'+pid
        r=d['staff_links'].setdefault(link_id,dict(person=pid,club=cid,trust=50,respect=50,alignment=50,concern=None,meetings=[]))
        agreement='Supports attacking intent' if suitable or p.get('risk')=='Ambitious' else 'Questions attacking intent'
        process='Welcomes backing' if choice=='encourage' else 'Concerned about owner pressure' if pid==manager['id'] or p.get('autonomy')!='Advisory' else 'Accepts a request within the manager remit'
        if choice=='attack':
            r['alignment']=min(100,r['alignment']+2) if agreement.startswith('Supports') else max(0,r['alignment']-2)
            if process.startswith('Concerned'):
                if r['concern'] is None:r['trust']=max(0,r['trust']-3);r['respect']=max(0,r['respect']-2)
                r['concern']=dict(event=key,day=s['day'],reason=process)
        if choice=='encourage' and r['concern'] and any(meeting['topic']==r['concern']['event'] and meeting['approach']=='Respect remit' for meeting in r['meetings']):
            r['trust']=min(100,r['trust']+2);r['respect']=min(100,r['respect']+1);r['concern']=None
            process='Welcomes backing after the remit discussion'
        reactions.append(dict(person=pid,name=p['name'],football='Backs the current plan' if choice=='encourage' else agreement,process=process))
    d['events'].append(dict(id=key,day=s['day'],club=cid,kind='bench',person=manager['id'],public=False,
        participants=participants,observers=witnesses,reason=response,reactions=reactions,minute=m['minute']))


def apply(s,action,data):
    if action!='dynamics_followup':return None
    from .simulation import require
    require(s['match'] is None,'Close matchday before arranging a private follow-up.')
    pid=data.get('id');r=s['dynamics']['staff_links'].get('c0|'+str(pid))
    require(pid in staff_people(s,'c0') and r is not None and r['concern'] is not None,'No current staff concern is available for follow-up.')
    topic=r['concern']['event'];approach=data.get('approach')
    require(approach in ('Listen','Respect remit'),'Choose Listen or Respect remit.')
    require(not any(m['topic']==topic for m in r['meetings']),'This concern has already had its follow-up.')
    reply=('The concern has been heard. Judge the response through future conduct.' if approach=='Listen' else
           'The manager retains selection and tactical authority. Future requests will show whether this assurance is kept.')
    r['meetings'].append(dict(topic=topic,day=s['day'],approach=approach,response=reply))
    # A conversation records intent; it cannot erase a breach or farm trust.
    return reply


def concern_rows(s):
    names={p['id']:p['name'] for p in s['players']};rows=[]
    for pid,a in s['playing_time']['agreements'].items():
        if a['club']=='c0' and a['concern'] and any(p['id']==pid for p in roster(s,'c0')):
            rows.append(dict(person=pid,name=names[pid],kind='player',reason='Playing-time commitment below agreement',
                action='Review opportunities; listen privately',day=a['concern']['since']))
    people=staff_people(s,'c0')
    for r in s['dynamics']['staff_links'].values():
        if r['club']=='c0' and r['person'] in people and r['concern']:
            rows.append(dict(person=r['person'],name=people[r['person']]['name'],kind='staff',reason=r['concern']['reason'],
                action='Private follow-up; respect agreed remit',day=r['concern']['day'],
                can_meet=not s['match'] and not any(m['topic']==r['concern']['event'] for m in r['meetings'])))
    return sorted(rows,key=lambda r:(r['day'],r['person']))


def public(s):
    d=s['dynamics'];rows=roster(s,'c0');ids=[p['id'] for p in rows];leaders=influence(s,'c0',ids);summary=group(s,'c0')
    old=next((r for r in d['history'] if r['day']==s['day']-7),None)
    trend='Not comparable'
    if old and old['members']==ids and old['value'] is not None and summary['value'] is not None:
        delta=summary['value']-old['value'];trend='Improving' if delta>=3 else 'Declining' if delta<=-3 else 'Stable'
    summary['trend']=trend
    players=[]
    for p in rows:
        r=d['members'].get(p['id'],{});links=[v for v in d['links'].values() if v['club']=='c0' and v['source']==p['id'] and v['target'] in ids]
        players.append(dict(id=p['id'],name=p['name'],contacts=len(links),sessions=max((v['sessions'] for v in links),default=0),
            settling='Established member' if r.get('settled') else 'Settling in',days=r.get('days',0),
            influence='Trusted connections' if leaders[p['id']]>=.02 else 'Developing connections' if links else 'Not assessed'))
    return dict(summary=summary,players=players,concerns=concern_rows(s),
        events=[deepcopy(e) for e in d['events'] if e['club']=='c0'],summaries=deepcopy(d['summaries']),
        meetings=[dict(name=staff_people(s,'c0')[r['person']]['name'],**deepcopy(m)) for r in d['staff_links'].values()
                  if r['club']=='c0' and r['person'] in staff_people(s,'c0') for m in r['meetings']])


def validate(s):
    from .simulation import require
    d=s['dynamics'];cfg=s['config']['dynamics'];ids={p['id'] for p in s['players']};clubs={c['id'] for c in s['clubs']}
    for k,v in cfg.items():require(type(v) in (int,float) and math.isfinite(v) and 0<v<=100,'Invalid dynamics tuning.')
    require(cfg['maximum_edge']<=3 and cfg['trust_weight']<=1 and cfg['influence_weight']<=1,'Unbounded coordination tuning.')
    require(all(type(cfg[k]) is int for k in ('settling_days','grievance_days','summary_days')),'Invalid dynamics schedule.')
    require(0<=d['last_day']<=s['day'],'Invalid dynamics date.')
    require(len(d['settled'])==len(set(d['settled'])),'Duplicate social match evidence.')
    require(len({e['id'] for e in d['events']})==len(d['events']),'Duplicate dynamics event.')
    for key,r in d['links'].items():
        require(r['source'] in ids and r['target'] in ids and r['source']!=r['target'] and r['club'] in clubs,'Invalid social participants.')
        require(key==pair_key(r['club'],r['source'],r['target']),'Invalid social link identity.')
        require(all(type(r[k]) in (int,float) and math.isfinite(r[k]) and 0<=r[k]<=100 for k in ('familiarity','trust','respect','alignment')),'Invalid social evidence.')
        require(all(type(r[k]) is int and r[k]>=0 for k in ('sessions','minutes','last_day')) and r['last_day']<=s['day'],'Invalid contact dates.')
    for pid,r in d['members'].items():
        require(pid in ids and r['club'] in clubs and type(r['days']) is int and r['days']>=0 and 0<=r['since']<=s['day'],'Invalid settling evidence.')
    for e in d['events']:
        require(e['club'] in clubs and 0<=e['day']<=s['day'],'Invalid dynamics event.')
        if e['kind']=='bench':require(not e['public'] and all(r['person'] in e['participants']+e['observers'] for r in e['reactions']),'Invalid bench audience.')
    for r in d['staff_links'].values():
        require(r['club'] in clubs and all(type(r[k]) is int and 0<=r[k]<=100 for k in ('trust','respect','alignment')),'Invalid staff relationship.')
