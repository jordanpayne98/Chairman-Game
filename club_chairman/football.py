"""Saved possession engine: rules, manager changes and one auditable event stream."""
from copy import deepcopy
import math
from . import people, registration, managers as manager_model, manager_selection, preparation

DEFAULTS=dict(actions_per_minute=1, foul_rate=.18, yellow_rate=.19, red_rate=.003,
              injury_rate=.003, penalty_rate=.045, condition_cost=.19,
              home_advantage=3, action_scale=18, substitution_condition=90)


def initialise(s):
    cfg=s['config'].setdefault('football',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)


def finished(m):
    return m.get('finished',m['minute']>=90)


def probability(a,b,scale=18):
    return max(.02,min(.98,1/(1+math.exp(max(-40,min(40,(b-a)/scale))))))


def strength(p,keys):
    value=sum(p['attrs'][k] for k in keys)/len(keys)
    return value*(.78+.22*p['condition']/100)*(1-p['fatigue']/1000)*(.94+.06*p['sharpness']/100)*(.97+.06*p['morale']/100)


def select(s,cid,opponent,with_plan=False):
    if cid=='c0' and s['manager']:
        selected=manager_selection.choose(s,cid,opponent)
        return selected if with_plan else selected[:2]
    pool=[p for p in s['players'] if not registration.reason(s,p,cid,opponent)]
    def score(p):
        return people.overall(p,s['config']['people']['weights'])*(.45+.55*p['condition']/100)-p['fatigue']*.12
    chosen=[]
    for role,n in (('GK',1),('DEF',4),('MID',4),('FWD',2)):
        candidates=sorted((p for p in pool if p['role']==role),key=lambda p:(-score(p),p['id']))
        chosen.extend(candidates[:n])
    ids={p['id'] for p in chosen}
    rest=sorted((p for p in pool if p['id'] not in ids),key=lambda p:(p['role']=='GK',-score(p),p['id']))
    chosen.extend(rest[:max(0,11-len(chosen))]);ids={p['id'] for p in chosen}
    bench=sorted((p for p in pool if p['id'] not in ids),key=lambda p:(p['role']!='GK',-score(p),p['id']))[:s['config']['competition']['bench_limit']]
    selected=([p['id'] for p in chosen],[p['id'] for p in bench])
    return (*selected,None) if with_plan else selected


def start(s,f):
    from .simulation import rng_for
    a,ab,ap=select(s,f['home'],f['away'],True);b,bb,bp=select(s,f['away'],f['home'],True)
    m=dict(engine=2,fixture=f['id'],home=f['home'],away=f['away'],minute=0,clock='0',
           score=[0,0],shots=[0,0],on_target=[0,0],xg=[0.,0.],possession=[0,0],
           fouls=[0,0],corners=[0,0],yellow_cards=[0,0],red_cards=[0,0],
           passes=[0,0],completed_passes=[0,0],risk=[1.,1.],intervened=False,settled=False,
           lineups=[a,b],on_pitch=[list(a),list(b)],bench=[ab,bb],participants=[list(a),list(b)],
           substitutions=[0,0],windows=[0,0],cards={},dismissed=[],stats={},events=[],
           phase='first_half',phase_minute=0,phase_length=45,added=0,added_announced=False,
           finished=False,knockout=bool(f.get('knockout')),winner=None,shootout=[0,0],kicks=[0,0],
           possession_side=0,zone=0,ball=None,pending_injuries=[],
           served_bans=[p['id'] for p in s['players'] if p['club'] in (f['home'],f['away']) and p['discipline']['ban']>0],
           new_bans={},rng=rng_for(s['seed'],'football:'+f['id']).getstate())
    if ap or bp:m['selection_plans']=[ap,bp]
    if s['manager'] and 'c0' in (f['home'],f['away']):
        own=0 if f['home']=='c0' else 1
        m['manager_plan']=manager_model.plan(s)
        m['risk'][own]=m['manager_plan']['baseline']
    preparation.snapshot(s,m)
    for pid in a+b:ensure_stats(m,pid)
    under=[len(ids)<s['config']['competition']['minimum_players'] for ids in (a,b)]
    if any(under):
        m['finished']=True;m['phase']='full_time';m['forfeit']=True
        # A double failure is a recorded 0–0; single failure awards the opponent 3–0.
        if under[0]!=under[1]:
            side=1 if under[0] else 0;m['score'][side]=3
            m['winner']=m['home'] if side==0 else m['away']
            for _ in range(3):event(m,'goal','Administrative goal: opponent could not field seven eligible players.',side=side)
        elif m['knockout']:
            # Both clubs fail the minimum-player rule. A recorded seeded draw
            # advances one club; it is not a played win or a player achievement.
            m['winner']=rng_for(s['seed'],'cup-admin:'+f['id']).choice(sorted((f['home'],f['away'])))
            event(m,'administrative_draw','Both clubs cannot field seven eligible players. A seeded administrative draw advances '+m['winner']+'.')
        event(m,'abandonment','Fixture awarded under the minimum-player rule. No player appearance or performance bonus is earned.')
        m['participants']=[[],[]]
    else:
        event(m,'kickoff','Kick-off. Managers have selected eligible teams and their substitutes.')
        for side,selection in enumerate(m.get('selection_plans',[None,None])):
            if selection:event(m,'selection','Manager selects '+selection['formation']+'. '+selection['reason'],side=side)
    return m


def ensure_stats(m,pid):
    m['stats'].setdefault(pid,dict(minutes=0,goals=0,shots=0,on_target=0,passes=0,completed=0,
                                 tackles=0,saves=0,errors=0,fouls=0,rating=6.0))


def event(m,kind,text,**data):
    m['events'].append(dict(minute=m['minute'],clock=m['clock'],kind=kind,text=text,**data))


def role_candidate(pool,rng,roles=None):
    options=[p for p in pool if not roles or p['role'] in roles]
    return rng.choice(options or pool)


def substitute(s,m,side,out,rng,forced=False,halftime=False):
    cfg=s['config']['competition'];by_id={p['id']:p for p in s['players']}
    if out not in m['on_pitch'][side]:return False
    room=m['substitutions'][side]<cfg['substitutions'] and (halftime or m['windows'][side]<cfg['substitution_windows'])
    options=[by_id[pid] for pid in m['bench'][side] if by_id[pid]['injury_until']<=s['day']]
    if not room or not options:
        if forced:
            m['on_pitch'][side].remove(out)
            event(m,'injury_exit',by_id[out]['name']+' must leave; no permitted substitute is available.',side=side,player=out)
        return False
    options.sort(key=lambda p:(p['role']!=by_id[out]['role'],-people.overall(p,s['config']['people']['weights'])*p['condition']/100,p['id']))
    incoming=options[0]['id'];m['on_pitch'][side].remove(out);m['on_pitch'][side].append(incoming)
    m['bench'][side].remove(incoming);m['participants'][side].append(incoming);ensure_stats(m,incoming)
    m['substitutions'][side]+=1
    if not halftime:m['windows'][side]+=1
    event(m,'substitution',by_id[out]['name']+' off; '+by_id[incoming]['name']+' on. '+('Injury replacement.' if forced else 'Manager responds to condition and match demands.'),side=side,off=out,on=incoming)
    return True


def managers(s,m,rng,halftime=False):
    by_id={p['id']:p for p in s['players']}
    for side in (0,1):
        if not m['on_pitch'][side]:continue
        # One window per scheduled change; no automatic override of an accepted
        # owner request for the same team.
        own=(m['home'] if side==0 else m['away'])=='c0'
        if own and 'manager_plan' in m:
            change=manager_model.adjustment(m,side) if not m.get('owner_instruction') else None
            if change:
                desired,reason=change;m['risk'][side]=desired
                event(m,'tactic','Manager '+reason+'; adjusts attacking risk.',side=side,risk=desired,reason=reason,manager=m['manager_plan']['manager'])
        elif m['minute']>=65:
            desired=1.22 if m['score'][side]<m['score'][1-side] else .9 if m['score'][side]>m['score'][1-side] else 1
            own=(m['home'] if side==0 else m['away'])=='c0'
            if not (own and m['intervened']) and desired!=m['risk'][side]:
                m['risk'][side]=desired
                event(m,'tactic','Manager '+('pushes forward to chase the score.' if desired>1 else 'protects the lead.' if desired<1 else 'restores a balanced approach.'),side=side)
        candidates=[by_id[pid] for pid in m['on_pitch'][side] if by_id[pid]['role']!='GK']
        if not candidates:continue
        out=min(candidates,key=lambda p:(p['condition'],-p['fatigue'],p['id']))
        if out['condition']<s['config']['football']['substitution_condition']:
            substitute(s,m,side,out['id'],rng,halftime=halftime)


def shot(s,m,side,shooter,defenders,rng,penalty=False,cross=False):
    other=1-side
    keeper=next((p for p in defenders if p['role']=='GK'),defenders[0])
    quality=.76 if penalty else (.05+rng.random()*.12 if cross else .03+rng.random()*.18)
    if not penalty:quality+=(m['risk'][other]-1)*.04
    quality=max(.02,min(.9,quality+(shooter['attrs']['off_the_ball']-sum(p['attrs']['positioning'] for p in defenders)/len(defenders))*.001))
    m['shots'][side]+=1;m['xg'][side]=round(m['xg'][side]+quality,6)
    stat=m['stats'][shooter['id']];stat['shots']+=1
    finishing=strength(shooter,('heading','bravery') if cross else ('finishing','composure'))
    keeping=strength(keeper,('reflexes','one_on_ones'))
    logit=math.log(quality/(1-quality))+(finishing-keeping)/75
    goal=rng.random()<max(.02,min(.98,1/(1+math.exp(-logit))))
    target=goal or rng.random()<.36
    if target:m['on_target'][side]+=1;stat['on_target']+=1
    if goal:
        m['score'][side]+=1;shooter['goals']+=1;stat['goals']+=1
        event(m,'goal','GOAL — '+shooter['name']+(' converts the penalty.' if penalty else ' heads in the cross.' if cross else ' finishes the move.'),side=side,player=shooter['id'],xg=quality)
    else:
        if target:m['stats'][keeper['id']]['saves']+=1
        event(m,'shot',shooter['name']+(': penalty saved.' if penalty and target else ': penalty off target.' if penalty else ': saved by the goalkeeper.' if target else ': shot off target.'),side=side,player=shooter['id'],xg=quality,on_target=target)
        if not target and rng.random()<.22:
            m['corners'][side]+=1;event(m,'corner','Deflected behind for a corner.',side=side)
    m['possession_side']=other;m['zone']=0;m['ball']=None


def injure(s,m,side,p,rng):
    days=rng.choice((4,7,10,14,21,28))
    p['injury_until']=s['day']+days;p['condition']=min(p['condition'],65)
    p['medical']=dict(type=rng.choice(('Muscle strain','Ankle sprain','Impact injury')),onset=s['day'],
                       estimate=[s['day']+max(2,days-3),s['day']+days+5],stage='rehabilitation',severity='Moderate' if days>10 else 'Minor')
    event(m,'injury',p['name']+' needs treatment and cannot continue.',side=side,player=p['id'])
    substitute(s,m,side,p['id'],rng,forced=True)


def action(s,m,rng):
    cfg=s['config']['football'];by_id={p['id']:p for p in s['players']}
    teams=[[by_id[pid] for pid in ids] for ids in m['on_pitch']]
    side=m['possession_side'];other=1-side
    if not teams[side] or not teams[other]:return
    m['possession'][side]+=1
    attacker=role_candidate(teams[side],rng,('MID','FWD') if m['zone']>0 else ('DEF','MID'))
    defender=role_candidate(teams[other],rng,('DEF','MID'))
    if rng.random()<cfg['foul_rate']:
        m['fouls'][other]+=1;m['stats'][defender['id']]['fouls']+=1
        event(m,'foul',defender['name']+' fouls '+attacker['name']+'.',side=other,player=defender['id'],against=attacker['id'])
        yellow=rng.random()<cfg['yellow_rate'];red=rng.random()<cfg['red_rate']
        if yellow:
            count=m['cards'].get(defender['id'],0)+1;m['cards'][defender['id']]=count
            m['yellow_cards'][other]+=1
            event(m,'yellow',defender['name']+' is cautioned.',side=other,player=defender['id'])
            red=red or count>=2
        if red:
            second=m['cards'].get(defender['id'],0)>=2
            m['red_cards'][other]+=1;m['dismissed'].append(defender['id']);m['on_pitch'][other].remove(defender['id'])
            m['new_bans'][defender['id']]=s['config']['competition']['second_yellow_ban' if second else 'red_ban']
            event(m,'red',defender['name']+(' is sent off for a second caution.' if second else ' is shown a straight red card.'),side=other,player=defender['id'])
            teams[other]=[p for p in teams[other] if p['id']!=defender['id']]
        if m['zone']==2 and rng.random()<cfg['penalty_rate'] and teams[other]:
            event(m,'penalty','Penalty awarded following the foul.',side=side)
            taker=max(teams[side],key=lambda p:strength(p,('finishing','composure')))
            shot(s,m,side,taker,teams[other],rng,penalty=True)
        return
    if rng.random()<cfg['injury_rate']*(1+attacker['fatigue']/80):
        injure(s,m,side,attacker,rng);return
    if m['zone']>=2 and rng.random()<.62*m['risk'][side]:
        shooter=role_candidate(teams[side],rng,('FWD','MID'))
        shot(s,m,side,shooter,teams[other],rng,cross=rng.random()<.23);return
    m['passes'][side]+=1;m['stats'][attacker['id']]['passes']+=1
    attack=strength(attacker,('passing','first_touch','decisions','vision'))
    defence=strength(defender,('tackling','positioning','anticipation'))
    edge=cfg['home_advantage'] if side==0 else 0
    # Numerical advantage, condition and tactical risk affect the next action.
    advantage=(len(teams[side])-len(teams[other]))*3+(m['risk'][other]-1)*15
    if (m['home'] if side==0 else m['away'])=='c0' and s['manager'] and 'manager_plan' not in m:
        advantage+=(s['manager']['skill']-62)*.12
    advantage+=preparation.edge(m,side)-preparation.edge(m,other)
    if rng.random()<probability(attack+edge+advantage+10,defence,cfg['action_scale']):
        m['completed_passes'][side]+=1;m['stats'][attacker['id']]['completed']+=1;m['zone']=min(2,m['zone']+1)
        if m['zone']==2:event(m,'progression',attacker['name']+' finds space in the attacking third.',side=side,player=attacker['id'])
    else:
        m['stats'][defender['id']]['tackles']+=1;m['stats'][attacker['id']]['errors']+=1
        m['possession_side']=other;m['zone']=max(0,2-m['zone']);m['ball']=None
        event(m,'turnover',defender['name']+' wins possession.',side=other,player=defender['id'])


def end_phase(s,m,rng):
    if m['phase']=='first_half':
        event(m,'period','Half time.');managers(s,m,rng,halftime=True)
        for p in s['players']:
            if p['id'] in sum(m['on_pitch'],[]):p['condition']=min(100,p['condition']+3)
        m.update(phase='second_half',phase_minute=0,phase_length=45,added=0,added_announced=False,possession_side=1)
    elif m['phase']=='second_half' and m['knockout'] and m['score'][0]==m['score'][1]:
        event(m,'period','Level after regulation. Extra time follows.')
        m.update(phase='extra_first',phase_minute=0,phase_length=15,added=0,added_announced=False)
    elif m['phase']=='extra_first':
        event(m,'period','Extra-time interval.')
        m.update(phase='extra_second',phase_minute=0,phase_length=15,added=0,added_announced=False)
    elif m['phase']=='extra_second' and m['score'][0]==m['score'][1]:
        event(m,'period','The tie will be decided by a penalty shootout.')
        m.update(phase='shootout',phase_minute=0)
    else:
        m.update(finished=True,phase='full_time')
        m['winner']=m['home'] if m['score'][0]>m['score'][1] else m['away'] if m['score'][1]>m['score'][0] else None
        event(m,'period','Full time.')


def shootout_step(s,m,rng):
    by_id={p['id']:p for p in s['players']};side=sum(m['kicks'])%2;other=1-side
    # Equal eligible numbers; removed players cannot take a kick or keep goal.
    count=min(map(len,m['on_pitch']))
    ids=sorted(m['on_pitch'][side],key=lambda pid:(-by_id[pid]['attrs']['composure'],pid))[:count]
    pid=ids[m['kicks'][side]%count];p=by_id[pid]
    goal=rng.random()<max(.55,min(.9,.72+(p['attrs']['composure']-50)/300))
    m['kicks'][side]+=1;m['shootout'][side]+=int(goal)
    event(m,'shootout',p['name']+(' scores.' if goal else ' misses.'),side=side,player=pid,converted=goal)
    done=any(m['shootout'][i]>m['shootout'][1-i]+max(0,5-m['kicks'][1-i]) for i in (0,1)) if max(m['kicks'])<=5 else m['kicks'][0]==m['kicks'][1] and m['shootout'][0]!=m['shootout'][1]
    if done:
        m['finished']=True;m['phase']='full_time';m['winner']=m['home'] if m['shootout'][0]>m['shootout'][1] else m['away']
        event(m,'period',f"Full time. Shootout {m['shootout'][0]}–{m['shootout'][1]}.")


def step(s,m):
    from .simulation import restore_rng
    if finished(m):return
    rng=restore_rng(m['rng'])
    if m['phase']=='shootout':
        shootout_step(s,m,rng);m['rng']=rng.getstate();return
    m['minute']+=1;m['phase_minute']+=1
    offset={'first_half':0,'second_half':45,'extra_first':90,'extra_second':105}[m['phase']]
    reg=offset+m['phase_length'];local=m['phase_minute']
    m['clock']=str(offset+local) if local<=m['phase_length'] else f"{reg}+{local-m['phase_length']}"
    by_id={p['id']:p for p in s['players']}
    for pid in sum(m['on_pitch'],[]):
        p=by_id[pid];ensure_stats(m,pid);m['stats'][pid]['minutes']+=1
        cost=s['config']['football']['condition_cost']*(1.25-p['attrs']['stamina']/200)
        p['condition']=round(max(0,p['condition']-cost),4);p['fatigue']=round(min(100,p['fatigue']+.09),4)
    if local in (20,30,38) and m['phase']=='second_half':managers(s,m,rng)
    for _ in range(s['config']['football']['actions_per_minute']):
        if min(map(len,m['on_pitch']))<s['config']['competition']['minimum_players']:break
        action(s,m,rng)
    if min(map(len,m['on_pitch']))<s['config']['competition']['minimum_players']:
        m.update(finished=True,phase='full_time',abandoned=True)
        side=0 if len(m['on_pitch'][1])<s['config']['competition']['minimum_players'] else 1
        m['winner']=m['home'] if side==0 else m['away']
        # Retain real goals and append only the additional administrative goals.
        target=max(3,m['score'][1-side]+3)
        for _ in range(max(0,target-m['score'][side])):
            m['score'][side]+=1;event(m,'goal','Administrative goal after abandonment.',side=side)
        event(m,'abandonment','Match abandoned: fewer than seven players remain. Result awarded under competition rules.')
    elif local==m['phase_length'] and not m['added_announced']:
        m['added']=rng.randint(1,3) if m['phase']=='first_half' else rng.randint(2,5) if m['phase']=='second_half' else 1
        m['added_announced']=True;event(m,'period',f"{m['added']} minute(s) of added time.")
    elif local>=m['phase_length']+m['added'] and m['added_announced']:end_phase(s,m,rng)
    for stat in m['stats'].values():
        involvement=stat['completed']*.014+stat['tackles']*.08+stat['saves']*.12+stat['goals']*.9-stat['errors']*.035-stat['fouls']*.055
        stat['rating']=round(max(1,min(10,6+involvement)),1)
    m['rng']=rng.getstate()


def settle_players(s,m):
    """Called exactly once by fixture settlement, never by rendering."""
    by_id={p['id']:p for p in s['players']}
    for pid in m['served_bans']:by_id[pid]['discipline']['ban']=max(0,by_id[pid]['discipline']['ban']-1)
    for pid,stat in m['stats'].items():
        p=by_id[pid];p['development']['minutes']+=stat['minutes']
        if stat['minutes']:p['sharpness']=min(100,p['sharpness']+stat['minutes']*.06)
    for pid,number in m['cards'].items():
        p=by_id[pid];p['discipline']['yellows']+=number
        threshold=s['config']['competition']['yellow_limit']
        if p['discipline']['yellows']>=threshold:
            p['discipline']['yellows']%=threshold
            m['new_bans'][pid]=max(1,m['new_bans'].get(pid,0))
    for pid,ban in m['new_bans'].items():by_id[pid]['discipline']['ban']+=ban


def public_match(m):
    return {k:deepcopy(v) for k,v in m.items() if k not in ('rng','served_bans','new_bans','manager_plan')}
