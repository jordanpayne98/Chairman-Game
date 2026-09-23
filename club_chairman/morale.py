"""Source-based morale. Explanations and summaries never add match modifiers."""
from copy import deepcopy
from math import isfinite

DEFAULTS = dict(concern_base=8, concern_ambition=8, playing_time_cap=20,
                result_cap=10, result_days=7, result_strength=4,
                legacy_days=14, history_days=35, trend_threshold=3)


def band(value):
    if value is None:return 'No squad data'
    return ('Very unhappy' if value<=20 else 'Unhappy' if value<=40 else
            'Content' if value<=60 else 'Happy' if value<=80 else 'Delighted')


def initialise(s,legacy=False):
    cfg=s['config'].setdefault('morale',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('mood',dict(players={},seen=[]))
    sync(s,legacy)


def sync(s,legacy=False):
    for p in s['players']:
        if p['id'] in s['mood']['players']:continue
        row=dict(sources={},snapshots=[],started=s['day'])
        s['mood']['players'][p['id']]=row
        if legacy:
            # Preserve old saves, including active match inputs. This transparent
            # transition is not an invented historical cause or dispute.
            row['sources']['legacy']=dict(id='legacy',group='legacy',club=None,start=s['day'],
                end=s['day']+s['config']['morale']['legacy_days'],amount=p['morale']-50,
                reason='Imported mood; earlier causes were not recorded',resolved=None)
        else:p['morale']=50.0
        snapshot(s,p)


def add(s,p,source,group,amount,reason,club=None,start=None,end=None):
    rows=s['mood']['players'][p['id']]['sources']
    if source in rows:return
    rows[source]=dict(id=source,group=group,amount=amount,reason=reason,club=club,
        start=s['day'] if start is None else start,end=end,resolved=None)


def strength(s,p,item):
    day=s['day']
    if item['resolved'] is not None or day<item['start']:return 0.0
    if item['club'] is not None and p['club']!=item['club']:return 0.0
    if item['end'] is None:return item['amount']
    return item['amount']*max(0,(item['end']-day)/(item['end']-item['start']))


def snapshot(s,p):
    rows=s['mood']['players'][p['id']]['snapshots']
    item=dict(day=s['day'],value=p['morale'],club=p['club'],senior=not p['youth'] and not p['retired'])
    if rows and rows[-1]['day']==s['day']:rows[-1]=item
    else:rows.append(item)
    rows[:]=[r for r in rows if r['day']>=s['day']-s['config']['morale']['history_days']]


def reconcile(s):
    sync(s)
    cfg=s['config']['morale']
    for p in s['players']:
        row=s['mood']['players'][p['id']];sources=row['sources']
        agreement=s['playing_time']['agreements'].get(p['id'])
        concern=agreement and agreement['concern']
        # Include the onset in the identity: a later recurrence is a new episode.
        key=(concern['id']+':'+str(concern['since'])) if concern else None
        for item in sources.values():
            if item['group']=='playing_time' and item['id']!=key and item['end'] is None and item['resolved'] is None:
                item['resolved']=s['day']
        if concern:
            amount=-(cfg['concern_base']+cfg['concern_ambition']*p['hidden']['ambition']/100)
            add(s,p,key,'playing_time',amount,'Playing-time agreement remains below its recorded target',
                club=agreement['club'],start=concern['since'])
        totals={}
        for item in sources.values():
            totals[item['group']]=totals.get(item['group'],0)+strength(s,p,item)
        caps={'playing_time':cfg['playing_time_cap'],'result':cfg['result_cap'],'support':5,'legacy':50}
        p['morale']=max(1,min(100,50+sum(max(-caps[g],min(caps[g],v)) for g,v in totals.items())))
        snapshot(s,p)


def kickoff(s,m):
    # Freeze public expectations; migrations cannot invent pre-match evidence.
    m['mood_expectations']={cid:s['recruitment']['clubs'][cid]['value'] for cid in (m['home'],m['away'])}


def collect(s,m):
    if m.get('forfeit') or m.get('abandoned') or 'mood_expectations' not in m:return
    if m['fixture'] in s['mood']['seen']:return
    s['mood']['seen'].append(m['fixture'])
    cfg=s['config']['morale'];players={p['id']:p for p in s['players']}
    for side,cid in enumerate((m['home'],m['away'])):
        other=(m['away'],m['home'])[side]
        gap=m['mood_expectations'][cid]-m['mood_expectations'][other]
        expected=max(.15,min(.85,.5+gap/100))
        gf,ga=m['score'][side],m['score'][1-side]
        actual=1 if gf>ga else 0 if gf<ga else .5
        for pid in m.get('participants',m['lineups'])[side]:
            if m.get('stats',{}).get(pid,{}).get('minutes',0)<=0:continue
            p=players[pid]
            amount=cfg['result_strength']*(actual-expected)*2
            add(s,p,'result:'+m['fixture'],'result',amount,
                f'Match {m["fixture"]}: {gf}–{ga}, relative to pre-match club standing',
                club=cid,end=s['day']+cfg['result_days'])


def trend(s,now,previous):
    if previous is None:return 'Collecting history'
    delta=now-previous;threshold=s['config']['morale']['trend_threshold']
    return 'Rising' if delta>=threshold else 'Falling' if delta<=-threshold else 'Stable'


def public(s):
    own=[p for p in s['players'] if p['club']=='c0' and not p['retired']]
    profiles={}
    for p in own:
        row=s['mood']['players'][p['id']]
        past=next((r for r in row['snapshots'] if r['day']==s['day']-7),None)
        reasons=[]
        for item in row['sources'].values():
            value=strength(s,p,item)
            if value:
                # Explain direction, not hidden personality coefficients.
                reasons.append(dict(id=item['id'],reason=item['reason'],start=item['start'],end=item['end'],
                    direction='Positive' if value>0 else 'Negative',ongoing=item['end'] is None))
        profiles[p['id']]=dict(value=p['morale'],band=band(p['morale']),
            trend=trend(s,p['morale'],past['value'] if past else None),reasons=reasons)
    squad=[p for p in own if not p['youth']]
    prior={pid:r for pid,row in s['mood']['players'].items() for r in row['snapshots']
           if r['day']==s['day']-7 and r['club']=='c0' and r['senior']}
    current={p['id']:p for p in squad};shared=current.keys() & prior.keys()
    average=sum(p['morale'] for p in squad)/len(squad) if squad else None
    delta=sum(current[pid]['morale']-prior[pid]['value'] for pid in shared)/len(shared) if shared else None
    counts=dict(unhappy=sum(p['morale']<=40 for p in squad),content=sum(40<p['morale']<=60 for p in squad),
                happy=sum(p['morale']>60 for p in squad))
    comparable=any(r['day']==s['day']-7 for row in s['mood']['players'].values() for r in row['snapshots'])
    return dict(players=profiles,squad=dict(name='Current first team',day=s['day'],value=average,band=band(average),
        counts=counts,trend=trend(s,delta,0) if delta is not None else 'Not comparable',compared=len(shared),
        arrivals=len(current.keys()-prior.keys()) if comparable else None,
        departures=len(prior.keys()-current.keys()) if comparable else None,
        concerns=sum(any(r['ongoing'] and r['direction']=='Negative' for r in profiles[p['id']]['reasons']) for p in squad)))


def validate(s):
    from .simulation import require
    cfg=s['config']['morale']
    require(all(isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) and v>0 for v in cfg.values()),'Invalid morale tuning.')
    require(cfg['history_days']>=7,'Morale history must cover its trend window.')
    require(len(set(s['mood']['seen']))==len(s['mood']['seen']),'Duplicate morale fixture.')
    known={p['id'] for p in s['players']}
    require(set(s['mood']['players'])==known,'Missing morale records.')
    for row in s['mood']['players'].values():
        for key,item in row['sources'].items():
            require(key==item['id'] and item['group'] in ('legacy','playing_time','result','support'),'Invalid morale source.')
            require(isfinite(item['amount']) and abs(item['amount'])<=100,'Invalid morale contribution.')
            require(item['end'] is None or item['end']>item['start'],'Invalid morale duration.')
        require(len({r['day'] for r in row['snapshots']})==len(row['snapshots']),'Duplicate morale snapshot.')
        require(all(isfinite(r['value']) and 0<=r['value']<=100 for r in row['snapshots']),'Invalid morale snapshot.')
