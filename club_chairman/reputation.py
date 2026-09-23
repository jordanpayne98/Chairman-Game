"""Dated domestic career evidence. No private ability, match RNG or cash inputs.

Reviews share a frozen prior-period reference. Changes are slow, season-budgeted
and based only on newly observed events; migration never invents past evidence.
"""
from copy import deepcopy
from math import isfinite

DEFAULTS = dict(version=1,review_days=28,minimum_minutes=90,minimum_matches=2,
    player_rate=.06,club_rate=.08,competition_rate=.08,period_cap=1,
    player_season_cap=5,club_season_cap=6,competition_season_cap=2,
    performance_centre=6.5,performance_scale=5,result_scale=12,
    title_bonus=1,cup_bonus=1,promotion_bonus=1,relegation_penalty=1)
KINDS=('clubs','leagues','players','cups')


def initialise(s):
    cfg=s['config'].setdefault('reputation',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    r=s['recruitment'];r.setdefault('cups',{})
    fresh='reputation_progress' not in s
    if fresh:
        s['reputation_progress']=dict(start=s['day'],season=s['career']['season'],
            next_review=s['day']+cfg['review_days'],seen=[],period=dict(clubs={},players={}),
            contributions={},closed=[],excluded_awards=[],budgets={},carry={},reference={})
    sync(s)
    if fresh:
        # Completed fixtures are explicitly outside this evidence coverage.
        s['reputation_progress']['seen']=[f['id'] for f in s['fixtures'] if f['result'] is not None]
        if s['season_done']:s['reputation_progress']['closed'].append(s['career']['season'])
        cup=s['competitions']['cup']
        if cup and cup['settled']:s['reputation_progress']['excluded_awards'].append(f"season:{s['career']['season']}:cup")


def sync(s):
    r=s['recruitment'];state=s['reputation_progress']
    cup=s['competitions']['cup']
    if cup and cup['id'] not in r['cups']:
        from .recruitment import record
        base=round(sum(r['clubs'][cid]['value'] for cid in cup['entrants'])/len(cup['entrants']))
        r['cups'][cup['id']]=record(base,s['day'],'Provisional domestic cup baseline; no past honours inferred.')
    for kind in KINDS:
        refs=state['reference'].setdefault(kind,{})
        for key,rec in r[kind].items():
            rec.setdefault('baseline',dict(value=rec['value'],day=rec['day'],source=rec['source']))
            rec.setdefault('reviews',[])
            refs.setdefault(key,rec['value'])
    if state['season']!=s['career']['season']:
        # Flush happens at closure. Old season budgets cannot spill into the next.
        state.update(season=s['career']['season'],seen=[],period=dict(clubs={},players={}),
                     contributions={},budgets={},carry={})


def collect(s,m):
    """Called only by authoritative result settlement, including background clubs."""
    state=s['reputation_progress'];fid=m['fixture']
    if fid in state['seen']:return
    state['seen'].append(fid)
    if m.get('forfeit') or m.get('abandoned') or m.get('engine')!=2:return
    f=next(f for f in s['fixtures'] if f['id']==fid)
    ref=state['reference'];cfg=s['config']['reputation']
    comp=f.get('competition') if f.get('knockout') else f.get('division')
    kind='cups' if f.get('knockout') else 'leagues'
    level=ref[kind].get(comp,50)
    for side,cid in enumerate((m['home'],m['away'])):
        gf,ga=m['score'][side],m['score'][1-side]
        # Draws after extra time remain sporting draws, regardless of shootout.
        outcome=1 if gf>ga else .5 if gf==ga else 0
        c=state['period']['clubs'].setdefault(cid,dict(matches=0,level=0,outcome=0))
        c['matches']+=1;c['level']+=level;c['outcome']+=outcome
        for pid in m['participants'][side]:
            st=m.get('stats',{}).get(pid,{})
            minutes=st.get('minutes',0)
            if minutes<=0:continue
            p=state['period']['players'].setdefault(pid,dict(matches=0,minutes=0,level=0,rating=0,goals=0))
            p['matches']+=1;p['minutes']+=minutes;p['level']+=minutes*level
            p['rating']+=minutes*st.get('rating',cfg['performance_centre']);p['goals']+=st.get('goals',0)
            key=f'{kind}:{comp}:{cid}'
            credit=state['contributions'].setdefault(key,{})
            credit[pid]=credit.get(pid,0)+minutes


def change(s,kind,key,event,amount,summary,evidence):
    rec=s['recruitment'][kind][key]
    if any(row['id']==event for row in rec['reviews']):return
    cfg=s['config']['reputation'];state=s['reputation_progress'];token=kind+':'+key
    cap=cfg['player_season_cap'] if kind=='players' else cfg['club_season_cap'] if kind=='clubs' else cfg['competition_season_cap']
    left=max(0,cap-state['budgets'].get(token,0))
    # Carry fractions across reviews, but never carry blocked changes over a cap.
    amount=max(-left,min(left,amount+state['carry'].get(token,0)))
    delta=int(amount)
    previous=rec['value'];value=max(1,min(100,previous+delta));delta=value-previous
    state['carry'][token]=amount-int(amount) if 1<value<100 and abs(amount)<left else 0
    state['budgets'][token]=state['budgets'].get(token,0)+abs(delta)
    rec.update(value=value,day=s['day'],trend=delta,source=summary)
    rec['reviews'].append(dict(id=event,day=s['day'],season=s['career']['season'],
        before=previous,after=value,change=delta,summary=summary,evidence=deepcopy(evidence)))


def review(s,force=False):
    state=s['reputation_progress'];cfg=s['config']['reputation']
    if not force and s['day']<state['next_review']:return
    period=state['period'];ref=state['reference'];end=state['next_review']
    event=f"review:{state['season']}:{end}:{s['day']}"
    for cid,c in sorted(period['clubs'].items()):
        if c['matches']<cfg['minimum_matches'] and not force:continue
        target=c['level']/c['matches']+(c['outcome']/c['matches']-.5)*cfg['result_scale']
        amount=max(-cfg['period_cap'],min(cfg['period_cap'],(target-ref['clubs'][cid])*cfg['club_rate']))
        change(s,'clubs',cid,event,amount,f"Results review: {c['matches']} played matches.",c)
    for pid,p in sorted(period['players'].items()):
        if p['minutes']<cfg['minimum_minutes'] or p['matches']<cfg['minimum_matches']:continue
        rating=p['rating']/p['minutes']
        target=p['level']/p['minutes']+(rating-cfg['performance_centre'])*cfg['performance_scale']
        amount=max(-cfg['period_cap'],min(cfg['period_cap'],(target-ref['players'][pid])*cfg['player_rate']))
        evidence=dict(matches=p['matches'],minutes=p['minutes'],goals=p['goals'],rating=round(rating,2))
        change(s,'players',pid,event,amount,f"Performance review: {p['minutes']} minutes; average rating {rating:.2f}.",evidence)
    state['period']=dict(clubs={},players={})
    state['reference']={kind:{key:r['value'] for key,r in s['recruitment'][kind].items()} for kind in KINDS}
    # Real due timestamp, no repeated backdated reviews after a gap.
    while state['next_review']<=s['day']:state['next_review']+=cfg['review_days']


def honour(s,kind,comp,cid,event,label,bonus):
    if event in s['reputation_progress']['excluded_awards']:return
    change(s,'clubs',cid,event,bonus,label,dict(competition=comp,club=cid))
    contributions=s['reputation_progress']['contributions'].get(f'{kind}:{comp}:{cid}',{})
    for pid,minutes in sorted(contributions.items()):
        if minutes<s['config']['reputation']['minimum_minutes']:continue
        change(s,'players',pid,event,bonus,label+' / recorded contributor.',dict(competition=comp,club=cid,minutes=minutes))


def close_season(s):
    state=s['reputation_progress'];season=s['career']['season'];cfg=s['config']['reputation']
    if season in state['closed']:return
    # Freeze all linked values BEFORE any season award or competition change.
    prior=deepcopy(state['reference']);event=f'season:{season}'
    review(s,force=True)
    for d in s['leagues']['divisions']:
        rows=s['leagues']['final_tables'][d['id']]
        honour(s,'leagues',d['id'],rows[0]['id'],event+':title:'+d['id'],d['name']+' champions',cfg['title_bonus'])
        level=sum(prior['clubs'][cid] for cid in d['members'])/len(d['members'])
        amount=max(-1,min(1,(level-prior['leagues'][d['id']])*cfg['competition_rate']))
        change(s,'leagues',d['id'],event,amount,'Season review of prior-period participating club standing.',dict(clubs=len(d['members']),prior_mean=round(level,2)))
    for m in s['leagues']['movements']:
        positive=m['kind']=='Promoted'
        change(s,'clubs',m['club'],event+':movement',cfg['promotion_bonus'] if positive else -cfg['relegation_penalty'],m['kind']+' at season closure.',dict(source=m['source'],target=m['target']))
    cup=s['competitions']['cup']
    if cup and cup['winner']:
        honour(s,'cups',cup['id'],cup['winner'],event+':cup',cup['name']+' winners',cfg['cup_bonus'])
        level=sum(prior['clubs'][cid] for cid in cup['entrants'])/len(cup['entrants'])
        amount=max(-1,min(1,(level-prior['cups'][cup['id']])*cfg['competition_rate']))
        change(s,'cups',cup['id'],event,amount,'Season review of prior-period cup entrants.',dict(clubs=len(cup['entrants']),prior_mean=round(level,2)))
    state['closed'].append(season)
    state['reference']={kind:{key:r['value'] for key,r in s['recruitment'][kind].items()} for kind in KINDS}
    from .simulation import news
    news(s,'Reputation season review','Dated results, titles and division movement have been reviewed. Open Career > Reputation for club and competition evidence; player profiles show individual contributions. Standing does not change football ability.')


def public(s):
    return {kind:deepcopy(s['recruitment'][kind]) for kind in KINDS}


def validate(s):
    from .simulation import require
    state=s['reputation_progress'];cfg=s['config']['reputation']
    require(type(state['next_review']) is int and state['next_review']>=state['start'],'Invalid reputation review schedule.')
    require(len(state['seen'])==len(set(state['seen'])) and len(state['closed'])==len(set(state['closed'])),'Duplicate reputation evidence.')
    for k in ('review_days','minimum_minutes','minimum_matches','player_season_cap','club_season_cap','competition_season_cap'):
        require(type(cfg[k]) is int and cfg[k]>0,'Invalid reputation tuning.')
    require(cfg['version']==1,'Unsupported reputation policy.')
    for key in ('player_rate','club_rate','competition_rate','period_cap','performance_centre','performance_scale','result_scale','title_bonus','cup_bonus','promotion_bonus','relegation_penalty'):
        require(type(cfg[key]) in (int,float) and isfinite(cfg[key]) and cfg[key]>=0,'Invalid reputation tuning.')
    for kind in ('clubs','players'):
        for key,entry in state['period'][kind].items():
            require(key in s['recruitment'][kind] and type(entry['matches']) is int and entry['matches']>0,'Invalid reputation evidence identity.')
            require(all(type(v) in (int,float) and isfinite(v) and v>=0 for v in entry.values()),'Invalid reputation evidence totals.')
            if kind=='players':require(entry['minutes']>0,'Invalid reputation minutes.')
    for kind in KINDS:
        for rec in s['recruitment'][kind].values():
            require(type(rec['value']) is int and 1<=rec['value']<=100,'Invalid reputation standing.')
            rows=rec['reviews'];require(len({r['id'] for r in rows})==len(rows),'Duplicate reputation review.')
            last=rec['baseline']['value']
            for row in rows:
                require(row['before']==last and row['after']-row['before']==row['change'] and 1<=row['after']<=100,'Reputation evidence does not reconcile.')
                last=row['after']
            # Legacy/dev scenarios may author a new public value before evidence exists.
            if rows:require(last==rec['value'],'Reputation history does not match standing.')
    require(all(isfinite(v) and abs(v)<1 for v in state['carry'].values()),'Invalid reputation fractional progress.')
