"""Manager-owned starting selections and public reasons; no extra match bonus."""
from . import people, registration

FORMATIONS={'4-4-2':(4,4,2),'4-3-3':(4,3,3),'4-5-1':(4,5,1),'3-5-2':(3,5,2)}
ROTATION=('Balanced','Fresh legs','Continuity')
YOUTH=('Readiness first','Develop prospects')
DEFAULTS=dict(adaptation_threshold=50,fresh_fatigue_penalty=.15,continuity_bonus=2.,
              continuity_days=14,youth_bonus=3.,readiness_gap=5.,youth_age=21)


def recent_starters(s,cid,days):
    fixtures=[f for f in s['fixtures'] if f['result'] and not f['result'].get('forfeit') and cid in (f['home'],f['away']) and 0<=s['day']-f['day']<=days]
    if not fixtures:return set()
    last=max(fixtures,key=lambda f:(f['day'],f['id']))
    return set(last['result'].get('lineups',[[],[]])[0 if last['home']==cid else 1])


def choose(s,cid,opponent):
    manager=s['manager'];prefs=manager['preferences'];cfg=s['config']['managers']['selection']
    eligible=[p for p in s['players'] if not registration.reason(s,p,cid,opponent)]
    ability={p['id']:people.overall(p,s['config']['people']['weights']) for p in eligible}
    best={role:max((ability[p['id']] for p in eligible if p['role']==role),default=0) for role in ('GK','DEF','MID','FWD')}
    previous=recent_starters(s,cid,cfg['continuity_days'])
    scores={};reasons={}
    for p in eligible:
        pid=p['id'];score=ability[pid]*(.45+.55*p['condition']/100)-p['fatigue']*.12
        factors=[]
        if prefs['rotation']=='Fresh legs':
            score-=p['fatigue']*cfg['fresh_fatigue_penalty'];factors.append('freshness priority')
        elif prefs['rotation']=='Continuity' and pid in previous:
            score+=cfg['continuity_bonus'];factors.append('recent starter')
        if prefs['youth']=='Develop prospects' and p['age']<=cfg['youth_age'] and ability[pid]>=best[p['role']]-cfg['readiness_gap']:
            score+=cfg['youth_bonus']*manager['capabilities']['youth_development']/100
            factors.append('ready prospect')
        scores[pid]=score;reasons[pid]=', '.join(factors) if factors else 'readiness and positional cover'
    counts={role:sum(p['role']==role for p in eligible) for role in ('DEF','MID','FWD')}
    def shortage(formation):
        return sum(max(0,n-counts[role]) for role,n in zip(('DEF','MID','FWD'),FORMATIONS[formation]))
    preferred=prefs['formation'];formation=preferred
    reason='Preferred shape retained; eligible outfield cover is available.'
    if shortage(preferred):
        reason='Preferred shape retained; limited positional cover requires compromise.'
        capable=manager['capabilities']['tactical_judgement']>=s['config']['managers']['judgement_threshold'] and manager['capabilities']['adaptability']>=cfg['adaptation_threshold']
        alternative=min(FORMATIONS,key=lambda shape:(shortage(shape),shape!=preferred,list(FORMATIONS).index(shape)))
        if capable and shortage(alternative)<shortage(preferred):
            formation=alternative;reason='Adjusted from '+preferred+' to reduce gaps in eligible positional cover.'
    chosen=[]
    for role,n in [('GK',1),*zip(('DEF','MID','FWD'),FORMATIONS[formation])]:
        pool=sorted((p for p in eligible if p['role']==role),key=lambda p:(-scores[p['id']],p['id']))
        chosen.extend(pool[:n])
    ids={p['id'] for p in chosen}
    rest=sorted((p for p in eligible if p['id'] not in ids),key=lambda p:(p['role']=='GK',-scores[p['id']],p['id']))
    chosen.extend(rest[:max(0,11-len(chosen))]);ids={p['id'] for p in chosen}
    bench=sorted((p for p in eligible if p['id'] not in ids),key=lambda p:(p['role']!='GK',-scores[p['id']],p['id']))[:s['config']['competition']['bench_limit']]
    starters=[p['id'] for p in chosen];substitutes=[p['id'] for p in bench]
    selected={role:sum(p['role']==role for p in chosen) for role in ('GK','DEF','MID','FWD')}
    if len(chosen)<11:reason+=' Fewer than eleven eligible players are available.'
    if not selected['GK']:reason+=' No eligible goalkeeper; outfield cover is required.'
    plan=dict(manager=manager['id'],day=s['day'],preferred=preferred,formation=formation,
              rotation=prefs['rotation'],youth=prefs['youth'],reason=reason,selected_roles=selected,
              starters=list(starters),bench=list(substitutes),reasons={pid:reasons[pid] for pid in starters+substitutes})
    return starters,substitutes,plan
