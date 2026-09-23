"""Sparse, directed player-to-chairman evidence from private meaningful contact.

No inferred observers, teammate contagion, selection orders or duplicate concern
penalties. Fulfilment repairs trust; support is a bounded temporary reaction.
"""
from copy import deepcopy
from . import morale

DEFAULTS=dict(cooldown_days=14,support_days=7,support_max=3,breach_trust=6,
              repair_trust=2,minor_grievance_days=28,trust_floor=35)


def initialise(s):
    cfg=s['config'].setdefault('relationships',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    s.setdefault('relationships',dict(links={},events=[],seen=[],meetings=[]))


def link(s,pid,cid):
    key=pid+'>'+cid+':chairman'
    return s['relationships']['links'].setdefault(key,dict(player=pid,club=cid,
        target=cid+':chairman',trust=50,respect=50,alignment=50,grievance=None))


def event(s,key,pid,cid,kind,reason,day,expiry=None):
    if key in s['relationships']['seen']:return False
    s['relationships']['seen'].append(key)
    s['relationships']['events'].append(dict(id=key,player=pid,club=cid,kind=kind,reason=reason,
        day=day,expiry=expiry,participants=[pid,cid+':chairman'],observers=[],public=False))
    return True


def process(s):
    data=s['relationships'];cfg=s['config']['relationships'];players={p['id']:p for p in s['players']}
    for agreement in s['playing_time']['agreements'].values():
        pid=agreement['player'];cid=agreement['club'];p=players[pid]
        # Review entries are historical facts; a load must not invent contact.
        for review in agreement['reviews']:
            key=agreement['id']+':review:'+str(review['day'])
            if key in data['seen']:continue
            if review['outcome']=='Insufficient opportunities':
                data['seen'].append(key);continue
            kind='shortfall' if review['outcome']=='Below agreement' else 'fulfilled'
            if not event(s,key,pid,cid,kind,review['outcome']+' / '+review['role'],review['day']):continue
            r=link(s,pid,cid)
            if kind=='shortfall':
                # Repeated windows of the same unresolved breach do not stack.
                if r['grievance'] is None or r['grievance']['agreement']!=agreement['id']:
                    r['trust']=max(0,r['trust']-cfg['breach_trust'])
                    r['respect']=max(0,r['respect']-2)
                    r['grievance']=dict(agreement=agreement['id'],since=review['day'],resolved=None)
            else:
                r['trust']=min(100,r['trust']+cfg['repair_trust'])
                r['respect']=min(100,r['respect']+1)
                if r['grievance'] is not None:r['grievance']=None
        # Other clubs use the same response/cooldown/source policy.
        if cid!='c0' and agreement['concern'] and p['club']==cid and not p['retired']:
            topic=meeting_topic(s,p,cid)
            if available(s,p,cid,topic):meet(s,p,cid,'Listen')
    for r in data['links'].values():
        grievance=r['grievance']
        agreement=s['playing_time']['agreements'].get(r['player'])
        if grievance and (not agreement or agreement['id']!=grievance['agreement']):
            if grievance['resolved'] is None:grievance['resolved']=s['day']
            if s['day']>=grievance['resolved']+cfg['minor_grievance_days']:r['grievance']=None


def meeting_topic(s,p,cid):
    a=s['playing_time']['agreements'].get(p['id'])
    if a and a['club']==cid and a['concern']:
        return a['concern']['id']+':'+str(a['concern']['since'])
    return 'wellbeing:'+str(s['day']//s['config']['relationships']['cooldown_days'])


def available(s,p,cid,topic):
    rows=[r for r in s['relationships']['meetings'] if r['player']==p['id'] and r['club']==cid]
    return (not rows or s['day']>=rows[-1]['day']+s['config']['relationships']['cooldown_days']) and not any(r['topic']==topic for r in rows)


def meet(s,p,cid,approach):
    from .simulation import require
    topic=meeting_topic(s,p,cid);cfg=s['config']['relationships']
    require(available(s,p,cid,topic),'Allow the support cooldown and new circumstances before another meeting. This concern has already been heard.')
    r=link(s,p['id'],cid)
    concern=topic.startswith('wellbeing:') is False
    # Existing stable traits condition this response; no new random personality
    # score, hidden threshold disclosure or repeatable acceptance reroll.
    receptive=r['trust']>=cfg['trust_floor'] and (not concern or approach=='Listen' and p['hidden']['ambition']<=65)
    value=cfg['support_max'] if receptive and not concern else 1 if receptive else 0
    reply=('Thank you for listening. I still need the agreed opportunities.' if receptive and concern else
           'I appreciate the support.' if receptive else
           'I need to see things change; encouragement alone does not resolve this.')
    identity=f"meeting:{p['id']}:{cid}:{len(s['relationships']['meetings'])}"
    event(s,identity,p['id'],cid,'support',approach+': '+reply,s['day'],s['day']+cfg['support_days'])
    data=dict(id=identity,player=p['id'],club=cid,day=s['day'],topic=topic,approach=approach,response=reply,
              outcome='Reassured' if receptive else 'Needs evidence',next_day=s['day']+cfg['cooldown_days'])
    s['relationships']['meetings'].append(data)
    if value:
        morale.add(s,p,identity,'support',value,'Private support conversation: '+reply,
                   club=cid,end=s['day']+cfg['support_days'])
    # Listening is evidence of process, not fulfilment. Never erase a concern
    # or award trust just for repeatedly clicking a dialogue.
    return reply+' The role agreement and manager selection authority remain unchanged.'


def apply(s,action,data):
    if action!='support_player':return None
    from .simulation import require
    require(s['match'] is None,'Hold private support meetings outside matchday.')
    p=next((p for p in s['players'] if p['id']==data.get('id')),None)
    require(p is not None and p['club']=='c0' and not p['youth'] and not p['retired'],'Meet an active member of your first team.')
    approach=data.get('approach');require(approach in ('Listen','Encourage'),'Choose Listen or Encourage.')
    return meet(s,p,'c0',approach)


def public(s):
    own={p['id'] for p in s['players'] if p['club']=='c0' and not p['retired']}
    data=s['relationships'];result={}
    for pid in own:
        r=data['links'].get(pid+'>c0:chairman');p=next(p for p in s['players'] if p['id']==pid)
        history=[deepcopy(e) for e in data['events'] if e['player']==pid and e['club']=='c0']
        meetings=[deepcopy(e) for e in data['meetings'] if e['player']==pid and e['club']=='c0']
        result[pid]=dict(assessment='Not assessed' if not r else 'Strained' if r['trust']<45 else 'Building trust' if r['trust']<60 else 'Established trust',
            grievance=bool(r and r['grievance']),events=history,meetings=meetings,
            can_meet=not p['youth'] and not s['match'] and available(s,p,'c0',meeting_topic(s,p,'c0')),
            next_day=meetings[-1]['next_day'] if meetings else s['day'])
    return result


def validate(s):
    from .simulation import require
    cfg=s['config']['relationships'];data=s['relationships'];known={p['id'] for p in s['players']};clubs={c['id'] for c in s['clubs']}
    require(all(type(v) is int and 0<v<=100 for v in cfg.values()),'Invalid relationship tuning.')
    require(len(data['seen'])==len(set(data['seen'])),'Duplicate relationship evidence.')
    require(len({e['id'] for e in data['events']})==len(data['events']),'Duplicate relationship event.')
    for r in data['links'].values():
        require(r['player'] in known and r['club'] in clubs,'Invalid relationship participants.')
        require(all(type(r[k]) is int and 0<=r[k]<=100 for k in ('trust','respect','alignment')),'Invalid relationship state.')
    for e in data['events']:
        require(e['id'] in data['seen'] and e['player'] in known and e['club'] in clubs,'Invalid relationship evidence.')
        require(not e['public'] and e['observers']==[] and e['participants']==[e['player'],e['club']+':chairman'],'Invalid private meeting audience.')
