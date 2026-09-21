"""Compact-club decisions constrained by observed ability and real accounts."""
from copy import deepcopy
from . import market,registration,staff,people,clauses,detail

DEFAULTS=dict(review_days=7,medical_days=2,target_squad=19,max_squad=20,
              reserve_weeks=3,payroll_income_percent=90,upgrade_margin=5)


def initialise(s):
    cfg=s['config'].setdefault('club_ai',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('club_ai',dict(enabled=True,decisions=[],observations={},last_review={},finance=[]))


def pending_for(s,pid):
    return next((d for d in s.get('club_ai',{}).get('decisions',[]) if d.get('player')==pid and d['status']=='medical'),None)


def budgets(s,cid):
    cfg=s['config']['club_ai'];income=s['config']['market']['ai_weekly_income']
    wage_limit=income*cfg['payroll_income_percent']//100-s['config']['market']['ai_weekly_overheads']
    reserve=(market.club_payroll(s,cid)+s['config']['market']['ai_weekly_overheads'])*cfg['reserve_weeks']
    bills=sum(b['amount'] for b in s['market']['obligations'] if b['source']==cid and b['status']=='scheduled')
    fees,wages=market.extra_reservations(s,cid)
    reserve+=wages*cfg['reserve_weeks']
    return dict(wage_limit=wage_limit,reserve=reserve,bills=bills,
        fees=fees,wages=wages)


def observation(s,cid,p):
    from .simulation import rng_for
    by_club=s['club_ai']['observations'].setdefault(cid,{})
    r=by_club.get(p['id'])
    if r and s['day']-r['day']<28:return r
    competence=staff.capability(s,cid,'ability_assessment');radius=max(4,round((100-competence)/5))
    rng=rng_for(s['seed'],f"ai-observer:{cid}:{p['id']}:{s['day']//28}")
    # Latent truth enters only this persisted observation; policy sees estimates.
    estimate=max(1,min(100,people.overall(p)+rng.randint(-radius,radius)))
    r=dict(day=s['day'],estimate=estimate,range=[max(1,estimate-radius),min(100,estimate+radius)],observer=cid)
    by_club[p['id']]=r;return r


def log(s,cid,kind,reason,**data):
    s['club_ai']['finance'].append(dict(day=s['day'],club=cid,kind=kind,reason=reason,**data))


def process_day(s):
    from .simulation import rng_for,news
    from .career import contractual_end,window_end
    if not s['club_ai']['enabled']:return
    cfg=s['config']['club_ai'];day=s['day']
    for d in s['club_ai']['decisions']:
        if d['status']!='medical' or day<d['due']:continue
        p=market.player(s,d['player']);cid=d['club'];b=budgets(s,cid)
        try:
            if p['club']!=d['source'] or p['retired'] or p['youth'] or market.active_loan(s,p['id']):raise ValueError('Player availability changed.')
            if day>window_end(s):raise ValueError('Registration window closed.')
            if market.active_deal(s,p['id']):raise ValueError('A competing club agreement now requires priority review.')
            o=s['career']['offers'].get(p['id'])
            if o and o['status'] not in market.TERMINAL:raise ValueError('A competing personal discussion is active.')
            if market.club_cash(s,cid)-b['fees']-b['bills']<b['reserve']:raise ValueError('Cash reserve no longer covers existing commitments.')
            if market.club_payroll(s,cid)+b['wages']>b['wage_limit']:raise ValueError('Payroll headroom changed.')
            if d['source'] and not market.can_release(s,p,d['source']):raise ValueError('Selling club needs its squad cover.')
            registration.check_arrival(s,p,cid)
        except ValueError as exc:d.update(status='cancelled',outcome=str(exc));continue
        if rng_for(s['seed'],'ai-medical:'+d['id']).random()<.08:
            d.update(status='cancelled',outcome='Medical advice led the club to withdraw before committing.');continue
        if d['source']:
            market.transfer_cash(s,d['id']+':fee',cid,d['source'],d['fee'],'AI transfer: '+p['name'])
            clauses.complete_sale(s,dict(d,target=cid))
        market.post(s,cid,d['id']+':signing',-d['signing_fee'],'Player signing fee: '+p['name'])
        previous={p['id']:p['club']};p.update(club=cid,wage=d['wage'],contract_end=d['end'])
        registration.sync(s,{q['id']:previous.get(q['id'],q['club']) for q in s['players']})
        d.update(status='completed',completed=day,outcome='Consents, medical, cash, payroll and registration rechecked; employment and fee settled.')
        log(s,cid,'registration',d['reason'],player=p['id'],fee=d['fee']+d['signing_fee'])
        news(s,'League recruitment',next(c['name'] for c in s['clubs'] if c['id']==cid)+' signed '+p['name']+'.')
    if day%cfg['review_days']:return
    # Employment does not change inside the review phase. Cache release cover
    # once; pending bids still get their normal per-player checks below.
    cover={}
    for p in s['players']:
        if p['club'] and not p['retired'] and not p['youth']:
            row=cover.setdefault(p['club'],[0,0]);row[0]+=1;row[1]+=int(p['role']=='GK')
    market_cfg=s['config']['market']
    releasable={p['id'] for p in s['players'] if p['club'] in cover
                and cover[p['club']][0]-1>=market_cfg['minimum_squad']
                and cover[p['club']][1]-int(p['role']=='GK')>=market_cfg['minimum_goalkeepers']}
    for club in s['clubs'][1:]:
        cid=club['id']
        squad=[p for p in s['players'] if p['club']==cid and not p['retired'] and not p['youth']]
        if not detail.review_due(s,cid,squad):continue
        s['club_ai']['last_review'][cid]=day;b=budgets(s,cid)
        for role in ('Executive','Football director','Coaching'):
            if any(p['club']==cid and p['role']==role for p in s['staff']['people']):continue
            candidates=[p for p in s['staff']['people'] if p['club'] is None and not p['pending'] and p['role']==role and (p['id'] not in s['staff']['offers'] or s['staff']['offers'][p['id']]['status'] in staff.CLOSED)]
            if not candidates:continue
            candidate=min(candidates,key=lambda p:(p['expected_wage'],-p['reputation'],p['id']));wage=candidate['expected_wage']*11//10
            if market.club_payroll(s,cid)+b['wages']+wage>b['wage_limit'] or market.club_cash(s,cid)-b['bills']-b['fees']<b['reserve']+wage*cfg['reserve_weeks']:continue
            candidate.update(club=cid,wage=wage,start=day,end=day+330,autonomy='Advisory')
            log(s,cid,'staff appointment','Fill a departmental vacancy using public role, reputation and salary demands within budget.',staff=candidate['id'])
            b=budgets(s,cid)
        for employee in s['staff']['people']:
            if employee['club']==cid and not employee['pending'] and employee['end']-day<=28:
                if market.club_payroll(s,cid)+b['wages']<=b['wage_limit'] and market.club_cash(s,cid)-b['fees']-b['bills']>=b['reserve']:
                    employee['end']=day+330;log(s,cid,'staff renewal','Maintain departmental cover within the existing salary budget.',staff=employee['id'])
        for p in squad:
            if p['contract_end']-day>28 or market.active_loan(s,p['id']):continue
            if market.club_payroll(s,cid)+b['wages']<=b['wage_limit'] and market.club_cash(s,cid)-b['fees']-b['bills']>=b['reserve']:
                p['contract_end']=contractual_end(s,3);log(s,cid,'player renewal','Retain existing squad cover at affordable current terms.',player=p['id'])
        log(s,cid,'finance','Checked current payroll, all dated transfer bills and three weeks of running-cost cover.',cash=market.club_cash(s,cid),payroll=market.club_payroll(s,cid),reserve=b['reserve'])
        if day>=window_end(s)-cfg['medical_days'] or len(squad)>=cfg['max_squad'] or any(d['club']==cid and d['status']=='medical' for d in s['club_ai']['decisions']):continue
        candidates=[];current_cash=market.club_cash(s,cid);current_payroll=market.club_payroll(s,cid)
        arrival_cache={}
        for p in s['players']:
            if p['club'] in ('c0',cid) or p['youth'] or p['retired'] or market.active_loan(s,p['id']) or pending_for(s,p['id']) or market.active_deal(s,p['id']):continue
            o=s['career']['offers'].get(p['id'])
            if o and o['status'] not in market.TERMINAL:continue
            if p['club'] and p['id'] not in releasable:continue
            fee=market.quote(s,p) if p['club'] else 0;signing=p['fee']
            if current_cash-fee-signing-b['fees']-b['bills']<b['reserve']+p['wage']*cfg['reserve_weeks']:continue
            if current_payroll+p['wage']+b['wages']>b['wage_limit']:continue
            # Candidates have no active deal, bid or target-club employment.
            # Eligibility here varies only by these three registration traits.
            rules=s['config']['competition']
            signature=(p['age']>=rules['exempt_under'],p['age']<rules['minimum_age'],p['homegrown'])
            if signature not in arrival_cache:
                try:registration.check_arrival(s,p,cid);arrival_cache[signature]=True
                except ValueError:arrival_cache[signature]=False
            if not arrival_cache[signature]:continue
            current=[q for q in squad if q['role']==p['role']]
            worst=min((observation(s,cid,q)['estimate'] for q in current),default=0)
            estimate=observation(s,cid,p)['estimate'];need=max(0,{'GK':2,'DEF':6,'MID':6,'FWD':4}[p['role']]-len(current))
            if not need and (len(squad)>=cfg['target_squad'] or estimate<worst+cfg['upgrade_margin']):continue
            score=need*30+estimate-worst-(fee+signing)/1000000-p['wage']/100000
            candidates.append((score,p,fee,signing,estimate))
        if not candidates:continue
        candidates.sort(key=lambda x:(-x[0],x[1]['id']));best=candidates[0][0]
        options=[x for x in candidates[:3] if best-x[0]<=3]
        _,p,fee,signing,estimate=rng_for(s['seed'],f'ai-choice:{cid}:{day}').choice(options)
        ident=f"ai:{cid}:{day}:{p['id']}"
        s['club_ai']['decisions'].append(dict(id=ident,club=cid,player=p['id'],source=p['club'],day=day,due=day+cfg['medical_days'],status='medical',
            fee=fee,signing_fee=signing,wage=p['wage'],end=contractual_end(s,2),
            reason=f"Observed role fit ({estimate}/100 estimate), squad cover and affordable guaranteed costs. Conditional player/club consent; medical and final checks pending.",outcome=None))


def snapshot(s):
    # Opponents' private estimates, internal targets and reserved bids are not
    # available to the owner. Only completed public registrations are exported.
    return dict(transfers=[{k:deepcopy(d[k]) for k in ('club','player','completed','fee','status')} for d in s['club_ai']['decisions'] if d['status']=='completed'])


def validate(s):
    from .simulation import require
    decisions=s['club_ai']['decisions']
    require(len({d['id'] for d in decisions})==len(decisions),'Duplicate AI agreement identity.')
    pending=[d['player'] for d in decisions if d['status']=='medical']
    require(len(pending)==len(set(pending)),'A player has competing binding AI reservations.')
