"""Continuing careers, negotiated contracts, academy and infrastructure commands.

Domain functions operate only on the caller's uncommitted state copy. Simulation
imports are local to keep the existing match engine separate from career policy.
"""
from copy import deepcopy
from . import market, clauses

CAREER_DEFAULTS = dict(season_gap=14, offer_lifetime=7,
                      medical_days=2, manager_notice_weeks=4, academy_trial_fee=200000,
                      academy_admission_fee=50000, academy_wage=10000, academy_base_capacity=12)
PROJECTS = {
    'training':dict(name='Training ground',cost=6000000,days=28,upkeep=30000,capacity=0,closure=0),
    'academy':dict(name='Academy centre',cost=5000000,days=28,upkeep=25000,capacity=0,closure=0),
    'stadium':dict(name='East stand expansion',cost=9000000,days=35,upkeep=40000,capacity=800,closure=800),
}


def initialise(s):
    """Schema upgrade adds no contracts, cash movements or random-stream changes."""
    s['schema']=3
    s.setdefault('career',dict(season=1,start=0,history=[],offers={},projects=[],
                              facilities={'training':1,'academy':1,'stadium':1},intakes=[],next_person=0))
    s['config'].setdefault('career',deepcopy(CAREER_DEFAULTS))
    for k,v in CAREER_DEFAULTS.items():s['config']['career'].setdefault(k,v)
    s['config'].setdefault('projects',deepcopy(PROJECTS))
    for p in s['players']:
        p.setdefault('youth',False);p.setdefault('retired',False)
        p.setdefault('birth_day',s['day']-p['age']*365)
        p.setdefault('injury_until',0);p.setdefault('career_goals',0);p.setdefault('career_appearances',0)
    if s['manager']:
        s['manager'].setdefault('contract_end',season_end(s))
        s['manager'].setdefault('notice_weeks',s['config']['career']['manager_notice_weeks'])


def season_end(s):return max(f['day'] for f in s['fixtures'])
def window_end(s):return s['career']['start']+28


def available_capacity(s):
    closure=sum(p['closure'] for p in s['career']['projects'] if p['status']=='construction')
    return max(0,s['config']['capacity']-closure)


def reservations(s,exclude=None):
    deals=[o for key,o in s['career']['offers'].items() if key!=exclude and o['status'] in ('medical','ready')]
    fees,wages=market.extra_reservations(s) if 'market' in s else (0,0)
    return fees+sum(o['fee']+market.upfront_for_offer(s,o) for o in deals),wages+sum(o['wage_delta'] for o in deals)


def manager_severance(s):
    m=s['manager']
    if not m:return 0
    remaining=max(0,m['contract_end']-s['day'])
    return m['wage']*min(remaining,7*m['notice_weeks'])//7


def contractual_end(s,duration):
    # The compact test league has fourteen weekly rounds and a two-week preseason.
    span=season_end(s)-s['career']['start']+s['config']['career']['season_gap']
    return season_end(s)+span*(duration-1 if not s['season_done'] else duration)


def person(s,pid):
    from .simulation import require
    p=next((p for p in s['players'] if p['id']==pid),None)
    require(p is not None,'This person is unavailable.')
    return p


def news(s,title,body):
    from .simulation import news as post_news
    post_news(s,title,body)


def free_cash(s,amount):
    return s['cash']-reservations(s)[0]-amount >= s['config']['operating_buffer']


def new_person(s,role,age,level,key,youth=False):
    from .simulation import rng_for
    rng=rng_for(s['seed'],key);n=s['career']['next_person'];s['career']['next_person']+=1
    first=['Jude','Toby','Finn','Luca','Kai','Ellis','Rory','Milo','Reuben','Joel','Alfie','Dylan']
    last=['Walsh','Harris','Chapman','Stewart','Edwards','Murray','Grant','Walker','Carter','Wood','Ross','Cole']
    attrs={k:max(1,min(100,level+rng.randint(-7,7))) for k in ('passing','finishing','tackling','goalkeeping')}
    return dict(id=f'n{n}',name=rng.choice(first)+' '+rng.choice(last),club=None,role=role,age=age,
                attrs=attrs,wage=(100 if youth else 450+level*13)*100,fee=(500 if youth else 3000+level*350)*100,
                goals=0,appearances=0,career_goals=0,career_appearances=0,contract_end=None,youth=youth,retired=False,
                birth_day=s['day']-age*365-rng.randrange(365),injury_until=0)


def process_day(s):
    """Opening expiries, dated projects, medicals, then periodic development."""
    from .simulation import make_report,rng_for
    day=s['day'];career=s['career']
    for o in career['offers'].values():
        if o['status'] in ('completed','withdrawn','expired','rejected'):continue
        p=person(s,o['player'])
        if day>o['expires'] or (o['kind']!='renew' and day>window_end(s)):
            o['status']='expired';market.close_purchase(s,o,'Personal terms expired.');o['transcript'].append('Offer or registration deadline passed: no contract was signed and reserved capacity was released.')
            news(s,'Offer expired',p['name']+': no contract was signed. Reserved capacity was released.');continue
        if o['status']=='medical' and day>=o['due']:
            rng=rng_for(s['seed'],'medical:'+o['id'])
            o['medical_days']=14 if rng.random()<.08 else 0
            o['status']='ready'
            o['medical']='Restricted training for 14 days after completion is advised.' if o['medical_days'] else 'No immediate registration concern was found. Future fitness is not guaranteed.'
            news(s,'Contract ready for final review',p['name']+': '+o['medical'])
    for p in s['players']:
        p['age']=max(0,(day-p['birth_day'])//365)
        if p['club'] and p['contract_end'] is not None and day>p['contract_end']:
            if p['club']=='c0':
                clauses.release(s,p['id'],'c0')
                p['club']=None;p['youth']=False;news(s,'Player contract expired',p['name']+' is now a free agent. No renewal was signed.')
            else:p['contract_end']=season_end(s)  # Existing AI preview-club retention policy.
    if s['manager'] and day>s['manager']['contract_end']:
        name=s['manager']['name'];s['manager']=None
        news(s,'Manager contract expired',name+' has left. Appoint a manager before advancing again.')
    for o in career['offers'].values():
        p=person(s,o['player'])
        if o['status'] in ('draft','counter','agreed','medical','ready') and o['kind']=='renew' and p['club']!='c0':
            o['status']='expired';o['transcript'].append('Employment expired before renewal completion. Reserved capacity was released.')
            news(s,'Renewal lapsed',p['name']+': the old employment agreement expired before completion. Any reservations were released.')
    for p in career['projects']:
        if p['status']=='feasibility' and day>=p['due']:
            p['status']='quoted';news(s,'Project proposal ready',p['name']+': review the fixed price, closure and weekly upkeep before approval.')
        elif p['status']=='construction' and day>=p['due']:
            p['status']='operational';career['facilities'][p['kind']]+=1
            s['config']['capacity']+=p['capacity'];s['config']['weekly_overheads']+=p['upkeep']
            news(s,'Facility opened',p['name']+' is operational. Capacity and running costs have been updated.')
    if day%28==0:
        names=[]
        for p in s['players']:
            if p['club']!='c0' or p['retired'] or p['age']>23:continue
            rng=rng_for(s['seed'],f"development:{p['id']}:{day}")
            training=career['facilities']['training'];ceiling=85 if p['age']<21 else 78
            key={'GK':'goalkeeping','DEF':'tackling','MID':'passing','FWD':'finishing'}[p['role']]
            if rng.random()<min(.8,.25+.08*training) and p['injury_until']<=day:
                p['attrs'][key]=max(p['attrs'][key],min(ceiling,p['attrs'][key]+1))
                names.append(p['name'])
            s['reports'][p['id']]=make_report(s,p,'Academy coaches' if p['youth'] else 'Coaching staff',9 if p['youth'] else 5)
        if names:news(s,'Development review',', '.join(names[:5])+': staff have refreshed their estimates. Development remains uncertain.')


def apply(s,action,data):
    from .simulation import require,payroll,posting,make_report,rng_for,table,MANAGERS
    c=s['career'];cfg=s['config'];settings=cfg['career']
    if action=='manager_replace':
        require(s['match'] is None,'Staff changes are unavailable during matchday.')
        candidate=next((m for m in MANAGERS if m['id']==data.get('id')),None)
        require(candidate is not None,'Unknown candidate.')
        require(not s['manager'] or candidate['id']!=s['manager']['id'],'This manager is already appointed. Use Renew contract.')
        wage=data.get('wage',candidate['wage']);duration=data.get('duration',2)
        require(type(wage) is int and candidate['wage']<=wage<=candidate['wage']*2,'This candidate requires at least the displayed salary.')
        require(type(duration) is int and 1<=duration<=3,'Choose one to three seasons.')
        cost=manager_severance(s)+candidate['fee'];old=s['manager']['wage'] if s['manager'] else 0
        require(free_cash(s,cost),'Insufficient unreserved cash for notice and the signing fee.')
        require(payroll(s)-old+wage+reservations(s)[1]<=s['budget'],'Appointment exceeds the wage limit including reserved offers.')
        if s['manager']:posting(s,f"manager-exit:{s['revision']}",-manager_severance(s),'Manager termination payment')
        posting(s,f"manager-hire:{s['revision']}",-candidate['fee'],'Manager signing fee')
        s['manager']=dict(deepcopy(candidate),wage=wage,contract_end=contractual_end(s,duration),notice_weeks=settings['manager_notice_weeks'])
        s['trust']=55;news(s,'Manager appointed',candidate['name']+' takes charge. Selection and tactics remain delegated.')
        return 'Manager appointed. Notice and signing costs are recorded in the ledger.'
    if action=='manager_renew':
        require(s['manager'] is not None and s['match'] is None,'Renewal is unavailable during a match or without a manager.')
        end=contractual_end(s,1 if s['season_done'] else 2)
        require(end>s['manager']['contract_end'],'This manager already has a contract covering next season.')
        s['manager']['contract_end']=end;news(s,'Manager contract renewed',s['manager']['name']+' stays on the same salary and notice terms.')
        return 'Manager renewed through next season. No signing fee.'
    if action=='enquire':
        require(s['match'] is None,'Contract discussions pause during matchday.')
        p=person(s,data.get('id'));require(not p['retired'] and not p['youth'],'Only active senior players can negotiate here.')
        require(market.active_loan(s,p['id']) is None,'Resolve the loan before negotiating a permanent contract.')
        deal=market.transfer_deal(s,p['id'])
        require(p['club'] in (None,'c0') or deal is not None,'Agree selling-club terms in Transfers first.')
        old=c['offers'].get(p['id'])
        require(not old or old['status'] in ('completed','withdrawn','expired','rejected'),'A discussion is already open for this player.')
        require(not old or s['day']>=old.get('cooldown',0),'The player needs time after the previous breakdown.')
        require(p['club']=='c0' or s['day']<=window_end(s),'The registration window has closed.')
        if old:c.setdefault('offer_history',[]).append(deepcopy(old))
        kind='renew' if p['club']=='c0' else 'transfer' if p['club'] else 'sign'
        c['offers'][p['id']]=dict(id=f"offer:{p['id']}:{s['revision']}",player=p['id'],kind=kind,status='draft',
            wage=p['wage'],fee=0 if kind=='renew' else p['fee'],duration=2,end=contractual_end(s,2),
            deal_id=deal['id'] if deal else None,source=p['club'],
            rounds=0,expires=min(s['day']+settings['offer_lifetime'],deal['expires']) if deal else s['day']+settings['offer_lifetime'],transcript=['Agent: We will consider pay, security and the signing fee.'],wage_delta=0)
        return 'Discussion opened. No funds are committed.'
    if action in ('propose_offer','accept_offer','complete_offer','withdraw_offer'):
        require(s['match'] is None,'Contracts cannot change during matchday.')
        o=c['offers'].get(data.get('id'));require(o is not None,'No discussion exists.')
        p=person(s,o['player']);require(o['status'] not in ('completed','withdrawn','expired','rejected'),'This discussion has closed.')
        require(s['day']<=o['expires'],'This offer has expired.')
        if action=='withdraw_offer':
            market.close_purchase(s,o,'Personal terms withdrawn.')
            o['status']='withdrawn';o['transcript'].append('Chairman: We are withdrawing. No contract was signed.')
            return 'Offer withdrawn. Reserved cash and payroll capacity released.'
        require(not p['retired'] and ((o['kind']=='sign' and p['club'] is None) or (o['kind']=='renew' and p['club']=='c0') or (o['kind']=='transfer' and p['club']==o.get('source'))),'The player’s registration has changed.')
        require(o['kind']=='renew' or s['day']<=window_end(s),'Registration window closed. Withdraw this offer.')
        if action=='propose_offer':
            require(o['status'] in ('draft','counter','agreed'),'Withdraw conditional acceptance before changing terms.')
            wage=data.get('wage');fee=data.get('fee');duration=data.get('duration')
            require(type(wage) is int and 10000<=wage<=500000,'Weekly wage must be £100–£5,000.')
            require(type(fee) is int and 0<=fee<=10000000,'Signing fee must be £0–£100,000.')
            require(type(duration) is int and 1<=duration<=3,'Choose one to three seasons.')
            end=contractual_end(s,duration);require(end>s['day'] and (o['kind']!='renew' or end>p['contract_end']),'Renewal must extend beyond the existing agreement.')
            extra=clauses.validate_terms(s,data)
            proposal=(wage,fee,duration,*extra.values())
            require(proposal!=tuple(o.get('last_proposal',[])),'These exact terms were already considered; change the offer or accept the counter.')
            o['last_proposal']=list(proposal);o['rounds']+=1
            rng=rng_for(s['seed'],'contract-priority:'+p['id']);discount=rng.randint(90,103)
            security=1-(duration-1)*.025
            required_wage=round(p['wage']*discount/100*security)
            if extra['club_option']:required_wage=required_wage*(100+cfg['clauses']['option_wage_premium'])//100
            required_fee=0 if o['kind']=='renew' else p['fee']*.9
            acceptable=wage>=required_wage and fee>=required_fee
            o.update(wage=wage,fee=fee,duration=duration,end=end,expires=s['day']+settings['offer_lifetime'])
            o.update(extra)
            if o.get('deal_id'):o['expires']=min(o['expires'],s['market']['deals'][o['deal_id']]['expires'])
            o['transcript'].append(f"Chairman: £{wage/100:,.0f}/week, £{fee/100:,.0f} fee, {duration} seasons.")
            if any(extra.values()):o['transcript'].append('Clauses: '+clauses.description(extra))
            if acceptable:
                o['status']='agreed';o['transcript'].append('Agent: Those terms work. We can proceed to the medical and registration review.')
            elif o['rounds']>=3:
                o['status']='rejected';o['cooldown']=s['day']+14;market.close_purchase(s,o,'Player rejected personal terms.');o['transcript'].append('Agent: We are ending these discussions. Try again after the cooling-off period.')
            else:
                o['status']='counter';o['wage']=max(wage,p['wage'],required_wage);o['fee']=max(fee,0 if o['kind']=='renew' else p['fee'])
                o['transcript'].append('Agent: The package is too low. Our revised terms are shown above.')
            return 'Response received. Review the revised terms and expiry.'
        if action=='accept_offer':
            require(o['status'] in ('agreed','counter'),'Send an offer before conditional acceptance.')
            due=s['day']+(settings['medical_days'] if o['kind']!='renew' else 0)
            if o['kind']!='renew':
                require(due<=min(window_end(s),season_end(s)), 'The medical cannot finish before registration closes. No capacity was reserved.')
            fee,wages=reservations(s,exclude=p['id']);delta=o['wage']-(p['wage'] if o['kind']=='renew' else 0)
            require(s['manager'] is not None,'Appoint a manager before agreeing contracts.')
            require(s['cash']-fee-o['fee']-market.upfront_for_offer(s,o)>=cfg['operating_buffer'],'Insufficient unreserved cash.')
            require(payroll(s)+wages+delta<=s['budget'],'Conditional acceptance exceeds unreserved wage capacity.')
            o.update(status='medical',due=due,wage_delta=max(0,delta),expires=s['day']+settings['offer_lifetime'])
            if o.get('deal_id'):
                deal=s['market']['deals'][o['deal_id']]
                require(deal['status']=='seller_agreed' and due<=deal['expires'],'Selling-club consent expires before the medical completes.')
                o['expires']=min(o['expires'],deal['expires'])
            if o['kind']=='renew':o.update(status='ready',medical_days=0,medical='Existing employment renewal: no new medical restriction.')
            o['transcript'].append('Conditional acceptance recorded. Cash and payroll capacity are reserved; employment has not changed.')
            return 'Medical arranged. Capacity reserved until completion, expiry or withdrawal.'
        require(o['status']=='ready','The medical and registration review are not ready.')
        require(o['kind']!='renew' or o['end']>p['contract_end'],'Renewal no longer extends the current agreement.')
        require(s['manager'] is not None,'Appoint a manager before completing this contract.')
        fees,wages=reservations(s,exclude=p['id']);delta=o['wage']-(p['wage'] if o['kind']=='renew' else 0)
        require(s['cash']-fees-o['fee']-market.upfront_for_offer(s,o)>=cfg['operating_buffer'],'Insufficient unreserved cash at completion.')
        require(payroll(s)+wages+delta<=s['budget'],'Wage capacity changed; revise the budget or withdraw.')
        if o['kind']=='transfer':market.complete_purchase(s,o)
        posting(s,o['id'],-o['fee'],'Contract signing fee' if o['kind']!='renew' else 'Contract renewal fee')
        if o['kind']!='renew':s['transfer_spend']+=o['fee']
        p.update(club='c0',wage=o['wage'],contract_end=o['end'],injury_until=max(p['injury_until'],s['day']+o['medical_days']))
        clauses.sign(s,p,o)
        s['scouting'].pop(p['id'],None)
        if p['id'] not in s['reports']:s['reports'][p['id']]=make_report(s,p,'Coaching staff',5)
        o['status']='completed';o['transcript'].append('Registration complete. The signed terms are now binding.')
        news(s,'Contract completed',p['name']+': employment, registration and cash have been updated together.')
        return 'Contract completed. The manager decides selection and minutes.'
    if action=='academy_intake':
        require(s['match'] is None,'Arrange trials outside matchday.')
        cycle=s['day']//365
        require(cycle not in c['intakes'],'This year’s regional candidates have already been assessed.')
        require(free_cash(s,settings['academy_trial_fee']),'Insufficient available cash for trials.')
        posting(s,f"intake:{cycle}",-settings['academy_trial_fee'],'Academy trial programme');c['intakes'].append(cycle)
        rng=rng_for(s['seed'],f"intake:{c['season']}")
        for i,role in enumerate(('GK','DEF','DEF','MID','MID','FWD')):
            p=new_person(s,role,rng.randint(14,17),rng.randint(26,48)+c['facilities']['academy'],f"youth:{c['season']}:{i}",True)
            p['candidate_season']=c['season'];s['players'].append(p);s['reports'][p['id']]=make_report(s,p,'Academy trial staff',12)
        news(s,'Academy trials complete','Six regional candidates are available for this season’s trial period. Reopening trials will not generate different players.')
        return 'Annual trial cohort assessed. Review each admission in Academy.'
    if action in ('academy_admit','academy_promote'):
        require(s['match'] is None,'Academy registration is locked during matchday.')
        p=person(s,data.get('id'));require(p['youth'] and not p['retired'],'Not an active academy player.')
        if action=='academy_admit':
            require(p['club'] is None and p.get('candidate_season')==c['season'],'This candidate is no longer available for admission.')
            capacity=settings['academy_base_capacity']+(c['facilities']['academy']-1)*6
            require(sum(x['youth'] and x['club']=='c0' for x in s['players'])<capacity,'Academy is full. Promote eligible players or expand facilities.')
            require(free_cash(s,settings['academy_admission_fee']),'Insufficient available cash.')
            require(payroll(s)+p['wage']+reservations(s)[1]<=s['budget'],'Admission exceeds the wage budget.')
            posting(s,'admit:'+p['id'],-settings['academy_admission_fee'],'Academy admission')
            p.update(club='c0',contract_end=contractual_end(s,3));message='Academy place agreed. Development is uncertain.'
        else:
            require(p['club']=='c0' and p['age']>=16,'Promotion requires an owned academy player aged at least 16.')
            p['youth']=False;message='Promoted to the senior squad on existing contract terms. Minutes are not guaranteed.'
        news(s,'Academy pathway',p['name']+': '+message);return message
    if action=='project_plan':
        kind=data.get('kind');require(kind in cfg['projects'],'Unknown project.')
        require(not any(p['kind']==kind and p['status'] in ('feasibility','quoted','construction') for p in c['projects']),'A project already occupies this site.')
        require(c['facilities'][kind]<5,'This facility has reached the current build limit.')
        require(free_cash(s,50000),'Insufficient cash for the £500 feasibility study.')
        spec=deepcopy(cfg['projects'][kind]);level=c['facilities'][kind]
        spec.update(id=f"project:{kind}:{s['revision']}",kind=kind,status='feasibility',due=s['day']+3,cost=spec['cost']*level)
        posting(s,spec['id']+':study',-50000,'Facility feasibility');c['projects'].append(spec)
        return 'Feasibility commissioned. A fixed-price proposal arrives in three days.'
    if action=='project_approve':
        p=next((p for p in c['projects'] if p['id']==data.get('id')),None)
        require(p is not None and p['status']=='quoted','No ready proposal exists.')
        require(s['match'] is None,'Construction approval is unavailable during matchday.')
        require(free_cash(s,p['cost']),'Insufficient unreserved cash for the full fixed price.')
        posting(s,p['id']+':build',-p['cost'],'Facility construction');p.update(status='construction',started=s['day'],due=s['day']+p['days'])
        return 'Construction approved and fully paid. Closures apply until the opening milestone.'
    if action=='project_cancel':
        p=next((p for p in c['projects'] if p['id']==data.get('id')),None)
        require(p is not None and p['status'] in ('feasibility','quoted'),'Only an uncommitted proposal can be cancelled. Construction has a fixed binding contract.')
        p['status']='cancelled';return 'Proposal cancelled. The feasibility fee is not refundable.'
    if action=='next_season':
        require(s['season_done'] and s['match'] is None,'Finish and close the season’s final match before continuing.')
        require(s['decision'] is None,'Resolve the outstanding chairman decision.')
        if not any(h['season']==c['season'] for h in c['history']):
            c['history'].append(dict(season=c['season'],table=deepcopy(table(s)),fixtures=deepcopy(s['fixtures']),cash=s['cash'],day=s['day']))
        for o in c['offers'].values():
            if o['status'] not in ('completed','withdrawn','expired','rejected'):
                o['status']='expired';market.close_purchase(s,o,'Season closed before registration.');o['transcript'].append('Season closed: unfinished discussion expired and reserved capacity released.')
        old_end=season_end(s);c['season']+=1;c['start']=old_end+settings['season_gap'];s['season_done']=False
        for club in s['clubs']:
            for key in ('played','won','drawn','lost','gf','ga','points'):club[key]=0
            club['form']=[]
        for p in s['players']:
            p['career_goals']+=p['goals'];p['career_appearances']+=p['appearances'];p['goals']=0;p['appearances']=0
            loan=market.active_loan(s,p['id'])
            if p['club'] not in (None,'c0') and not loan:p['contract_end']=c['start']+96
            if p['age']>=36 and p['club']!='c0' and not loan:p['retired']=True;p['club']=None
            if p['youth'] and p['club'] is None:p['retired']=True
        # Keep opponents playable. Scheduled background entrants have new identities.
        for club in s['clubs'][1:]:
            for role,count in (('GK',2),('DEF',6),('MID',6),('FWD',4)):
                pool=[p for p in s['players'] if p['club']==club['id'] and p['role']==role and not p['retired']]
                for i in range(max(0,count-len(pool))):
                    p=new_person(s,role,19,48+int(club['id'][1:]),f"background:{c['season']}:{club['id']}:{role}:{i}")
                    p.update(club=club['id'],contract_end=c['start']+96);s['players'].append(p)
        active_free=[p for p in s['players'] if p['club'] is None and not p['youth'] and not p['retired']]
        for i in range(max(0,12-len(active_free))):s['players'].append(new_person(s,('GK','DEF','MID','FWD')[i%4],21,45+i%20,f"market:{c['season']}:{i}"))
        ring=list(range(8));pairs=[]
        for r in range(7):
            pairs.append([(ring[-1-j],ring[j]) if r%2 else (ring[j],ring[-1-j]) for j in range(4)])
            ring=[ring[0],ring[-1]]+ring[1:-1]
        s['fixtures']=[]
        for r in range(14):
            for j,(a,b) in enumerate(pairs[r%7]):
                if r>=7:a,b=b,a
                s['fixtures'].append(dict(id=f"s{c['season']}-f{r}-{j}",day=c['start']+5+r*7,home=f'c{a}',away=f'c{b}',result=None))
        news(s,'New season prepared',f"Season {c['season']} is ready. The two-week preseason advances normally with wages and deadlines. Review expiring contracts before Continue.")
        return 'New fixtures created. History retained. No days or recurring payments have been skipped.'
    return None
