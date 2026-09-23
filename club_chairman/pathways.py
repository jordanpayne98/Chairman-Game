"""Separate youth/reserve football, dated advice and employment-safe pathways."""
from copy import deepcopy
from . import career, people, market, club_ai, registration, world_calendar

DEFAULTS=dict(minimum_players=7,squad_size=11,recovery_days=2,youth_exposure=.65,reserve_exposure=.8,review_days=28,opening_youth=9,opening_reserves=9,annual_intake=6)
POSITIONS=('GK','DEF','DEF','DEF','MID','MID','MID','FWD','FWD')


def initialise(s):
    cfg=s['config'].setdefault('pathways',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('pathways',dict(start=s['day'],season=0,fixtures=[],records=[],reviews={},decisions=[],last_review_day=None,population_day=None))
    sync(s)


def sync(s):
    for p in s['players']:
        d=p['development'];d.setdefault('group','Youth' if p['youth'] else 'Seniors')
        d.setdefault('pathway_history',[]);d.setdefault('exposure',float(d['minutes']));d.setdefault('last_played',None)
        if p['youth']:d['group']='Youth' if p['age']<18 else 'Reserves'
        elif d['group']=='Youth':d['group']='Reserves'


def seed_groups(s):
    """New-career content only: actual wages, no cash grant or migration seeding."""
    from .simulation import rng_for
    extra=0
    for c in s['clubs'][:8]:
        for group,key,wage in [('Youth','opening_youth',10000),('Reserves','opening_reserves',18000)]:
            for i in range(s['config']['pathways'][key]):
                rng=rng_for(s['seed'],f"opening:{c['id']}:{group}:{i}")
                p=career.new_person(s,POSITIONS[i%len(POSITIONS)],rng.randint(14,17) if group=='Youth' else rng.randint(18,20),rng.randint(28,43),f"pathway:{c['id']}:{group}:{i}",group=='Youth')
                p.update(club=c['id'],wage=wage,contract_end=career.contractual_end(s,3));p['development']['group']=group;s['players'].append(p)
                if c['id']=='c0':extra+=wage
    s['budget']+=extra;s['config']['weekly_budget']+=extra
    sync(s)


def schedule(s):
    if world_calendar.active(s):return world_calendar.development_schedule(s)
    w=s['pathways'];season=s['career']['season']
    if w['season']==season:return
    known={f['id'] for f in w['fixtures']}
    for f in s['fixtures']:
        if f.get('competition') not in (None,'league'):continue
        day=f['day']+3
        if not s['day']<day<=career.season_end(s):continue
        for group in ('Youth','Reserves'):
            ident=f"dev:{season}:{f['id']}:{group}"
            if ident not in known:w['fixtures'].append(dict(id=ident,season=season,day=day,home=f['home'],away=f['away'],group=group,status='scheduled',result=None,reason=''))
    w['season']=season


def eligible(s,p,cid,group):
    d=p['development'];day=s['day'];cfg=s['config']['pathways']
    if p['club']!=cid or p['retired'] or p['contract_end'] is None or p['contract_end']<day or p['injury_until']>day:return False
    if p['condition']<65 or p['fatigue']>65 or p['discipline']['ban'] or (p['medical'] and p['medical']['stage']!='available'):return False
    if d['last_played'] is not None and day-d['last_played']<cfg['recovery_days']:return False
    if group=='Youth' and not (p['youth'] and world_calendar.age(s,p)<s['config'].get('world_calendar',{}).get('youth_age_limit',18)):return False
    if group=='Reserves' and d['group']!='Reserves':return False
    if not p['youth'] and any(cid in (f['home'],f['away']) and abs(f['day']-day)<cfg['recovery_days'] for f in s['fixtures']):return False
    return True


def select(s,cid,group,opponent):
    rows=[p for p in s['players'] if eligible(s,p,cid,group)]
    def recent(p):return (sum(r['minutes'] for r in s['pathways']['records'] if r['player']==p['id'] and s['day']-r['day']<28),p['id'])
    # Signed parent-club restrictions apply to development football too.
    rows=[p for p in rows if not any(l['player']==p['id'] and l['status']=='active' and l['source']==opponent and not s['config']['competition']['loan_against_parent'] for l in s['market']['loans'])]
    keepers=sorted((p for p in rows if p['role']=='GK'),key=recent)
    if not keepers:return []
    return keepers[:1]+sorted((p for p in rows if p['role']!='GK'),key=recent)[:s['config']['pathways']['squad_size']-1]


def review(s,p):
    day=s['day'];d=p['development']
    minutes=sum(h['minutes'] for h in d['history'] if day-h['day']<28)+d['minutes']
    route='Maintain';load=d['load'];reason='Continue the current programme and review the next month of evidence.'
    loan=market.active_loan(s,p['id'])
    if p['youth'] and p['contract_end'] is not None and 0<=p['contract_end']-day<=28:route='Renewal review';reason='Academy employment is nearing expiry. Review guaranteed wages and available budget.'
    elif p['injury_until']>day or p['fatigue']>60:route='Recovery';load='Light';reason='Prioritise recovery before additional exposure.'
    elif loan:route='Loan review';reason='Review actual receiving-club minutes and the existing recall and playing-role terms.'
    elif p['youth'] and p['age']<16:route='Youth';reason='Continue age-appropriate youth football.'
    elif p['youth'] and p['age']>=18:route='Promotion review';reason='Review senior registration and employment before promotion.'
    elif minutes<90:route='Youth' if p['youth'] else 'Reserves';reason='Recent minutes are limited. Seek suitable development football.'
    authors=[q for q in s['staff']['people'] if q['club']==p['club'] and q['role'] in ('Academy','Coaching') and q['end']>=day]
    return dict(day=day,club=p['club'],author=authors[0]['name'] if authors else 'Development staff',route=route,reason=reason,minutes=minutes,focus=d['focus'],load=load,coaching='Club coaching' if p['club']=='c0' else 'Receiving-club assessment pending')


def renew_ai_academy(s):
    for p in s['players']:
        cid=p['club']
        if not cid or cid=='c0' or not p['youth'] or p['retired'] or p['contract_end'] is None or not 0<=p['contract_end']-s['day']<=28:continue
        b=club_ai.budgets(s,cid);end=career.contractual_end(s,3)
        if end<=p['contract_end'] or market.club_payroll(s,cid)+b['wages']>b['wage_limit'] or market.club_cash(s,cid)<b['reserve']+b['bills']+b['fees']+4*p['wage']:continue
        p['contract_end']=end;p['development']['pathway_history'].append(dict(day=s['day'],action='Academy renewal',end=end,wage=p['wage']))


def population_checkpoint(s):
    day=s['day'];w=s['pathways']
    if day==0 or day%365 or w['population_day']==day:return
    w['population_day']=day
    from .simulation import rng_for
    for c in s['clubs']:
        cid=c['id']
        if cid=='c0':continue
        for p in s['players']:
            if p['club']==cid and p['youth'] and not p['retired'] and p['age']>=18:
                try:registration.check_arrival(s,p,cid)
                except ValueError:continue
                p['youth']=False;p['development']['group']='Reserves'
        count=sum(p['club']==cid and p['youth'] and not p['retired'] for p in s['players'])
        for i in range(min(s['config']['pathways']['annual_intake'],max(0,s['config']['career']['academy_base_capacity']-count))):
            b=club_ai.budgets(s,cid);fee=s['config']['career']['academy_admission_fee'];wage=s['config']['career']['academy_wage']
            if market.club_cash(s,cid)<b['reserve']+b['bills']+b['fees']+fee or market.club_payroll(s,cid)+b['wages']+wage>b['wage_limit']:break
            role='GK' if not any(p['club']==cid and p['youth'] and p['role']=='GK' and not p['retired'] for p in s['players']) else POSITIONS[(i+1)%len(POSITIONS)]
            key=f'intake:{day}:{cid}:{i}';p=career.new_person(s,role,14,rng_for(s['seed'],key).randint(26,43),key,True)
            p.update(club=cid,wage=wage,contract_end=career.contractual_end(s,3));s['players'].append(p)
            market.post(s,cid,key,-fee,'Annual academy admission');w['decisions'].append(dict(day=day,club=cid,player=p['id'],action='Annual admission',fee=fee))
    sync(s)


def process_day(s):
    from .simulation import rng_for,news
    sync(s);renew_ai_academy(s);population_checkpoint(s);schedule(s)
    w=s['pathways'];cfg=s['config']['pathways']
    for f in w['fixtures']:
        if f['status']!='scheduled' or f['day']>s['day']:continue
        sides=[select(s,f[k],f['group'],f['away' if k=='home' else 'home']) for k in ('home','away')]
        if any(len(side)<cfg['minimum_players'] for side in sides):f.update(status='unplayed',reason='Insufficient eligible players including a goalkeeper.');continue
        ratings=[sum(people.overall(p) for p in side)/len(side) for side in sides];rng=rng_for(s['seed'],f['id'])
        f['result']=[sum(rng.random()<max(.06,min(.32,.16+(ratings[i]-ratings[1-i])/220)) for _ in range(10)) for i in range(2)];f['status']='played'
        for i,side in enumerate(sides):
            for p in side:
                d=p['development'];factor=cfg['youth_exposure' if f['group']=='Youth' else 'reserve_exposure']*max(.25,min(1,1-(people.overall(p)-ratings[1-i])/40));exposure=90*factor
                d['minutes']+=90;d['exposure']+=exposure;d['last_played']=s['day'];p['condition']=max(0,p['condition']-13);p['fatigue']=min(100,p['fatigue']+10);p['sharpness']=min(100,p['sharpness']+4)
                w['records'].append(dict(fixture=f['id'],day=s['day'],player=p['id'],club=p['club'],group=f['group'],minutes=90,exposure=exposure))
    if s['day']%cfg['review_days']==0 and w['last_review_day']!=s['day']:
        w['last_review_day']=s['day']
        for p in s['players']:
            if p['club'] and not p['retired'] and (p['age']<=23 or p['development']['group']!='Seniors'):w['reviews'][p['id']]=review(s,p)
        news(s,'Pathway review','Dated staff advice is available in Academy / Pathways, including loan monitoring.')


def record_senior(s,p,minutes):
    p['development']['exposure']=p['development'].get('exposure',0)+minutes
    if minutes:p['development']['last_played']=s['day']


def apply(s,action,data):
    if action not in ('pathway_group','pathway_accept','academy_renew'):return None
    from .simulation import require,payroll,news
    p=career.person(s,data.get('id'));d=p['development']
    require(p['club']=='c0' and not p['retired'] and s['match'] is None,'Review your own active players outside matchday.')
    if action=='academy_renew':
        require(p['youth'] and p['contract_end'] is not None and 0<=p['contract_end']-s['day']<=28,'Review academy renewals within 28 days of expiry.')
        end=career.contractual_end(s,3);require(end>p['contract_end'],'The existing agreement already covers that term.')
        require(payroll(s)+career.reservations(s)[1]<=s['budget'] and career.free_cash(s,4*p['wage']),'Insufficient wage authority or cash cover for renewal.')
        p['contract_end']=end;d['pathway_history'].append(dict(day=s['day'],action='Academy renewal',end=end,wage=p['wage']))
        news(s,'Academy renewal',p['name']+': existing wage retained; employment extended.')
        return 'Academy agreement extended on the existing weekly wage. No signing fee.'
    if action=='pathway_accept':
        r=s['pathways']['reviews'].get(p['id']);require(r and r['club']=='c0' and s['day']-r['day']<=s['config']['pathways']['review_days'],'Request a current review before applying advice.')
        d.update(focus=r['focus'],load=r['load'])
        if r['route']=='Reserves' and not p['youth']:d['group']='Reserves'
        entry=dict(day=s['day'],action='Applied advice',review_day=r['day'])
    else:
        require(not p['youth'] and data.get('group') in ('Seniors','Reserves'),'Choose a senior or reserve training group.')
        d['group']=data['group'];entry=dict(day=s['day'],action='Training group',group=d['group'])
    if not d['pathway_history'] or d['pathway_history'][-1]!=entry:d['pathway_history'].append(entry)
    return 'Development programme updated. Employment and selection commitments remain as agreed.'


def standings(s,group):
    from . import recruitment
    lid=recruitment.league_id(s,'c0');division=next(d for d in s['leagues']['divisions'] if d['id']==lid)
    rows={cid:dict(club=cid,played=0,points=0,gf=0,ga=0) for cid in division['members']}
    for f in s['pathways']['fixtures']:
        if f['season']!=s['career']['season'] or f['group']!=group or f['status']!='played':continue
        a,b=f['result']
        for cid,scored,conceded in ((f['home'],a,b),(f['away'],b,a)):
            if cid in rows:r=rows[cid];r['played']+=1;r['gf']+=scored;r['ga']+=conceded;r['points']+=3 if scored>conceded else 1 if scored==conceded else 0
    return sorted(rows.values(),key=lambda r:(-r['points'],r['ga']-r['gf'],-r['gf'],r['club']))


def public(s):
    rows=[];w=s['pathways']
    for p in s['players']:
        loan=market.active_loan(s,p['id'])
        if p['retired'] or not (p['club']=='c0' or loan and loan['source']=='c0'):continue
        d=p['development'];rows.append(dict(id=p['id'],name=p['name'],age=p['age'],youth=p['youth'],club=p['club'],wage=p['wage'],end=p['contract_end'],group=d['group'],minutes=d['minutes'],review=deepcopy(w['reviews'].get(p['id'])),history=[{k:h[k] for k in ('day','minutes','focus','load')} for h in d['history'][-8:]],decisions=deepcopy(d['pathway_history'][-8:]),loan=deepcopy(loan)))
    return dict(players=rows,fixtures=deepcopy([f for f in w['fixtures'] if 'c0' in (f['home'],f['away'])][-80:]),records=deepcopy([r for r in w['records'] if r['club']=='c0'][-300:]),tables={g:standings(s,g) for g in ('Youth','Reserves')})


def validate(s):
    from .simulation import require
    w=s['pathways'];known={p['id'] for p in s['players']};cfg=s['config']['pathways']
    require(7<=cfg['minimum_players']<=cfg['squad_size']<=11 and cfg['review_days']>0,'Invalid pathway rules.')
    require(len({f['id'] for f in w['fixtures']})==len(w['fixtures']),'Duplicate development fixture.')
    require(len({(r['fixture'],r['player']) for r in w['records']})==len(w['records']),'Duplicate development appearance.')
    require(all(r['player'] in known and 0<=r['exposure']<=r['minutes'] for r in w['records']),'Invalid development appearance.')
    require(all(p['development']['group'] in ('Youth','Reserves','Seniors') for p in s['players']),'Invalid development group.')
