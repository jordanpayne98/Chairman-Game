"""Staff employment, assessed capabilities and dated departmental coverage."""
from copy import deepcopy
import math

CAPABILITIES=('tactical_judgement','coaching','youth_development','ability_assessment',
              'potential_assessment','negotiation','financial_control','commercial_judgement',
              'operations','people_management','adaptability')
ROLES={
    'Executive':('Chief executive','people_management','financial_control'),
    'Football director':('Director of football','negotiation','ability_assessment'),
    'Recruitment':('Recruitment lead','ability_assessment','potential_assessment'),
    'Academy':('Academy director','youth_development','potential_assessment'),
    'Finance':('Finance lead','financial_control','operations'),
    'Commercial':('Commercial lead','commercial_judgement','negotiation'),
    'Operations':('Operations lead','operations','people_management'),
    'Coaching':('Head coach','coaching','tactical_judgement'),
    'Medical':('Medical services lead','operations','people_management'),
}
DEFAULTS=dict(notice_weeks=4,start_delay=2,poach_notice=7,interview_days=1,
              offer_days=7,report_radius=12,interview_radius=6,full_coverage_days=28)
CLOSED=('active','withdrawn','rejected','expired','ended')


def initialise(s):
    from .simulation import rng_for
    cfg=s['config'].setdefault('staff',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    cfg.setdefault('weights',{role:{key:.5 for key in spec[1:]} for role,spec in ROLES.items()})
    if 'staff' in s:
        for p in s['staff']['people']:enrich(s,p)
        return
    data=dict(people=[],offers={},assessments={},shortlist=[],history=[])
    first=('Ellis','Morgan','Taylor','Robin','Casey','Harper','Alex','Sam','Drew')
    last=('Bennett','Ward','Mason','Reed','Clarke','Morgan','Hayes','Brooks','Shaw')
    # An explicit opening staff roster for the compact AI clubs. These salaries
    # are paid from their existing accounts; no extra money is created.
    for i,role in enumerate(ROLES):
        for j in range(3):
            pid=f'staff:{i}:{j}';rng=rng_for(s['seed'],pid)
            skills={k:rng.randint(30,65) for k in CAPABILITIES[:-1]}
            for key in ROLES[role][1:]:skills[key]=rng.randint(50,82)
            level=sum(skills[k] for k in ROLES[role][1:])//2
            p=dict(id=pid,name=first[(i+j)%9]+' '+last[(i*2+j)%9],role=role,club=None,
                   capabilities=skills,expected_wage=(180+level*5)*100,wage=0,
                   start=None,end=None,notice_weeks=cfg['notice_weeks'],availability=100,
                   reputation=level,autonomy='Advisory',pending=None,workload=0,
                   morale=60,objectives=[],history=[],risk=rng.choice(('Cautious','Balanced','Ambitious')))
            enrich(s,p)
            data['people'].append(p)
    s['staff']=data
    add_club_staff(s,s['clubs'][1:])


def add_club_staff(s,clubs):
    from .simulation import rng_for
    first=('Ellis','Morgan','Taylor','Robin','Casey','Harper','Alex','Sam','Drew')
    last=('Bennett','Ward','Mason','Reed','Clarke','Morgan','Hayes','Brooks','Shaw')
    for c in clubs:
        i=next(i for i,candidate in enumerate(s['clubs'][1:]) if candidate['id']==c['id'])
        for role in ('Executive','Football director','Coaching'):
            pid=f"staff:{c['id']}:{role}";rng=rng_for(s['seed'],pid)
            skills={k:rng.randint(42,75) for k in CAPABILITIES[:-1]}
            s['staff']['people'].append(dict(id=pid,name=first[i%9]+' '+last[(i+3)%9],role=role,club=c['id'],
                capabilities=skills,expected_wage=60000,wage=60000,start=s['day'],end=s['day']+330,
                notice_weeks=4,availability=100,reputation=60,autonomy='Advisory',pending=None,
                workload=0,morale=60,objectives=[],history=[],risk=rng.choice(('Cautious','Balanced','Ambitious'))))
            enrich(s,s['staff']['people'][-1])



def enrich(s,p):
    """Independent identity stream preserves the ten legacy skills and behaviour."""
    from .simulation import rng_for
    if 'adaptability' not in p['capabilities']:
        p['capabilities']['adaptability']=rng_for(s['seed'],'staff-adaptability:'+p['id']).randint(25,85)


def rating(s,p):
    weights=s['config']['staff']['weights'][p['role']]
    return int(math.fsum(p['capabilities'][key]*weight for key,weight in weights.items())+.5)


def current_ratings(s,p):
    return dict(ranges={key:[int(p['capabilities'][key]+.5)]*2 for key in CAPABILITIES},
                overall=[rating(s,p)]*2,role=p['role'])


def observed_assessment(s,p):
    """Current access is separate from the stored interview snapshot."""
    r=deepcopy(s['staff']['assessments'].get(p['id']))
    own=p['club']=='c0'
    if not r:
        if not own:return None
        r=dict(day=s['day'],source='Club access',ranges={})
    full=r.get('knowledge')=='Fully assessed'
    covered=full and s['day']<r['coverage_until']
    months=max(0,s['day']-r['day'])//s['config']['staff']['full_coverage_days']
    stale=not own and not covered and (full or bool(months))
    if stale:
        width=min(20,max(1,months))
        r['ranges']={key:[max(1,a-width),min(100,b+width)] for key,(a,b) in r['ranges'].items()}
    weights=s['config']['staff']['weights'][p['role']]
    if all(key in r['ranges'] for key in weights):
        r['overall']=[int(math.fsum(r['ranges'][key][i]*w for key,w in weights.items())+.5) for i in (0,1)]
    r.update(role=p['role'],exact_current=own or covered,stale=stale,
             knowledge='Club access' if own else 'Fully assessed' if covered else 'Stale' if stale else 'Partial')
    if own or covered:r.update(current_ratings(s,p),rating_day=s['day'])
    return r


def person(s,pid):
    from .simulation import require
    p=next((p for p in s['staff']['people'] if p['id']==pid),None)
    require(p is not None,'Unknown staff member.')
    return p


def payroll(s,cid,day=None):
    if 'staff' not in s:return 0
    day=s['day'] if day is None else day
    return sum(p['wage'] for p in s['staff']['people'] if p['club']==cid and p['start']<=day<=p['end'])


def reservations(s):
    if 'staff' not in s:return 0
    return sum(p['pending']['wage'] for p in s['staff']['people'] if p['pending'] and p['pending']['club']=='c0')


def assess(s,p,radius,complete=False):
    from .simulation import rng_for
    rng=rng_for(s['seed'],f"staff-report:{p['id']}:{radius}")
    ranges={}
    for key in CAPABILITIES:
        value=p['capabilities'][key]
        estimate=max(1,min(100,value+rng.randint(-5,5)))
        ranges[key]=[max(1,estimate-radius),min(100,estimate+radius)]
    s['staff']['assessments'][p['id']]=dict(day=s['day'],ranges=ranges,
        source='Working observations' if p['club']=='c0' else 'Interview and references' if radius<=6 else 'Initial references',
        knowledge='Fully assessed' if complete else 'Partial')
    if complete:
        s['staff']['assessments'][p['id']].update(current_ratings(s,p),coverage_until=s['day']+s['config']['staff']['full_coverage_days'])


def severance(s,p):
    pending=p['pending']
    wage=pending['wage'] if pending else p['wage'];end=pending['end'] if pending else p['end']
    return min(wage*p['notice_weeks'],wage*max(0,(end or s['day'])-s['day'])//7)


def capability(s,cid,key,default=50):
    available=[p for p in s.get('staff',{}).get('people',[]) if p['club']==cid and p['end']>=s['day'] and key in ROLES[p['role']][1:]]
    return max((p['capabilities'][key]*max(.7,1-p['workload']/400) for p in available),default=default)


def process_day(s):
    from .simulation import news
    from . import delegation
    day=s['day']
    for p in s['staff']['people']:
        pending=p['pending']
        if pending and pending['start']<=day:
            old=p['club'];p.update(club=pending['club'],wage=pending['wage'],start=day,end=pending['end'],autonomy=pending['autonomy'],pending=None)
            s['staff']['offers'][p['id']]['status']='active';assess(s,p,3)
            s['staff']['history'].append(dict(day=day,person=p['id'],kind='started',club=p['club'],previous=old))
            if p['club']=='c0':news(s,'Staff member started',p['name']+' is available. Review Responsibilities to allocate work and authority.')
        if p['club'] and p['end']<day:
            old=p['club'];p['club']=None;p['wage']=0
            s['staff']['history'].append(dict(day=day,person=p['id'],kind='expired',club=old))
            if old=='c0':news(s,'Staff contract expired',p['name']+' has left. Uncovered responsibilities return to the owner.')
        if p['club']=='c0' and day%7==0:
            allocated=sum(r['allocation'] for r in s['delegation']['responsibilities'].values() if r['delegate']==p['id'])
            p['workload']=max(0,min(100,p['workload']+(2 if allocated>=100 else -3)))
            p['history'].append(dict(day=day,allocated=allocated,workload=p['workload']));p['history']=p['history'][-52:]
    for offer in s['staff']['offers'].values():
        if offer['status'] not in (*CLOSED,'starting') and day>offer['expires']:offer['status']='expired'
    delegation.reconcile(s)


def apply(s,action,data):
    if not action.startswith('staff_'):return None
    from .simulation import require,posting,news,payroll as total_payroll
    from .career import free_cash,reservations as all_reservations,contractual_end
    from . import market,delegation
    require(s['match'] is None,'Staff employment changes pause during matchday.')
    p=person(s,data.get('id'));cfg=s['config']['staff'];store=s['staff'];day=s['day']
    if action=='staff_shortlist':
        if p['id'] in store['shortlist']:store['shortlist'].remove(p['id'])
        else:store['shortlist'].append(p['id'])
        return 'Staff shortlist saved.'
    if action=='staff_contact':
        require(p['club']!='c0' and not p['pending'],'This person is employed here or has already accepted a move.')
        old=store['offers'].get(p['id'])
        require(not old or old['status'] in CLOSED,'A discussion is already open.')
        assess(s,p,cfg['report_radius'])
        store['offers'][p['id']]=dict(id=f"staff-offer:{p['id']}:{s['revision']}",person=p['id'],status='contact',
            expires=day+cfg['offer_days'],interview_due=day+cfg['interview_days'],wage=p['expected_wage'],duration=2,
            autonomy='Advisory',rounds=0,transcript=['Contact made. References received; an interview becomes available tomorrow.'])
        return 'Contact made. Continue to the interview date.'
    if action=='staff_renew':
        require(p['club']=='c0' and not p['pending'],'Only your current staff can renew here.')
        duration=data.get('duration',3);require(type(duration) is int and 1<=duration<=3,'Choose one to three compact seasons.')
        end=contractual_end(s,duration)
        require(end>p['end'],'The existing contract already covers that date.')
        p['end']=end;store['history'].append(dict(day=day,person=p['id'],kind='renewed',end=end))
        return 'Staff contract renewed at the existing salary and notice terms.'
    if action=='staff_dismiss':
        require(p['club']=='c0' or p['pending'] and p['pending']['club']=='c0','Only your own staff agreement can be ended.')
        cost=severance(s,p);require(free_cash(s,cost),'Insufficient available cash for notice.')
        posting(s,f"staff-exit:{p['id']}:{s['revision']}",-cost,'Staff notice: '+p['name'])
        if p['club']=='c0':p['club']=None;p['wage']=0
        p['pending']=None
        if p['id'] in store['offers']:store['offers'][p['id']]['status']='ended'
        store['history'].append(dict(day=day,person=p['id'],kind='dismissed',cost=cost))
        delegation.reconcile(s)
        news(s,'Staff agreement ended',p['name']+' leaves the role. Notice was paid and uncovered work returned to the owner.')
        return 'Notice paid. Existing signed commitments remain binding.'
    o=store['offers'].get(p['id']);require(o is not None,'Contact the candidate first.')
    require(o['status'] not in CLOSED and o['status']!='starting' and day<=o['expires'],'This discussion is closed or the appointment is already binding.')
    if action=='staff_withdraw':o['status']='withdrawn';return 'Unsigned staff discussion withdrawn.'
    if action=='staff_interview':
        require(o['status']=='contact' and day>=o['interview_due'],'Wait for the interview date.')
        assess(s,p,cfg['interview_radius'],complete=True);o['status']='interviewed'
        o['transcript'].append('Interview complete. Candidate expects '+('a protected advisory role.' if p['risk']=='Cautious' else 'clear objectives and available resources.'))
        return 'Assessment complete: current capabilities and role ability are exact. Fit and future performance remain uncertain.'
    if action=='staff_propose':
        require(o['status'] in ('interviewed','counter','agreed'),'Complete the interview before proposing terms.')
        wage=data.get('wage');duration=data.get('duration');autonomy=data.get('autonomy','Advisory')
        require(type(wage) is int and 10000<=wage<=1000000,'Choose a salary between £100 and £10,000 per week.')
        require(type(duration) is int and 1<=duration<=3,'Choose one to three compact seasons.')
        require(autonomy in ('Advisory','Approval required'),'Choose advisory or protected approval terms.')
        terms=[wage,duration,autonomy];require(o.get('last')!=terms,'These terms have already been considered.')
        o.update(last=terms,rounds=o['rounds']+1,wage=wage,duration=duration,autonomy=autonomy)
        minimum=p['expected_wage']+(p['expected_wage']//10 if autonomy=='Advisory' and p['risk']=='Ambitious' else 0)
        o['status']='agreed' if wage>=minimum else 'rejected' if o['rounds']>=3 else 'counter'
        if o['status']=='counter':o['wage']=minimum
        o['transcript'].append('Candidate: '+('Terms agreed, subject to your appointment review.' if o['status']=='agreed' else 'Counter: requested salary £'+str(minimum//100)+'/week.' if o['status']=='counter' else 'Discussion ended after repeated unsuitable terms.'))
        return 'Staff response received. Review salary, compensation, start date and notice.'
    require(action=='staff_accept','Unknown staff action.')
    require(o['status'] in ('agreed','counter') and not p['pending'] and p['club']!='c0','No available agreed candidate.')
    compensation=p['wage']*p['notice_weeks'] if p['club'] else 0
    require(free_cash(s,compensation),'Insufficient available cash for employer compensation.')
    require(total_payroll(s)+all_reservations(s)[1]+o['wage']<=s['budget'],'Appointment exceeds available wage authority.')
    end=contractual_end(s,o['duration']);start=day+(cfg['poach_notice'] if p['club'] else cfg['start_delay'])
    require(start<end,'The start date must precede contract expiry.')
    if compensation:market.transfer_cash(s,o['id']+':compensation','c0',p['club'],compensation,'Staff compensation: '+p['name'])
    p['pending']=dict(club='c0',wage=o['wage'],start=start,end=end,autonomy=o['autonomy'])
    o.update(status='starting',start=start,end=end,compensation=compensation)
    o['transcript'].append('Binding appointment signed; compensation paid and future payroll reserved. Authority starts only after joining and assignment.')
    return 'Appointment signed. The joining date and future salary are recorded.'


def snapshot(s):
    d=s['staff'];people=[]
    for p in d['people']:
        row={k:deepcopy(v) for k,v in p.items() if k not in ('capabilities','risk')}
        row['assessment']=observed_assessment(s,p);row['notice_cost']=severance(s,p) if p['club']=='c0' or p['pending'] else 0
        row['compensation']=p['wage']*p['notice_weeks'] if p['club'] not in (None,'c0') else 0
        people.append(row)
    return dict(people=people,offers=deepcopy(d['offers']),shortlist=list(d['shortlist']),history=deepcopy(d['history']))


def validate(s):
    from .simulation import require
    cfg=s['config']['staff'];weights=cfg['weights']
    require(type(cfg['full_coverage_days']) is int and cfg['full_coverage_days']>0,'Invalid staff assessment coverage.')
    require(set(weights)==set(ROLES),'Invalid staff rating roles.')
    for role,table in weights.items():
        require(bool(table) and all(key in CAPABILITIES and type(w) in (int,float) and math.isfinite(w) and w>=0 for key,w in table.items()) and abs(sum(table.values())-1)<1e-8,'Invalid staff role weights.')
    for r in s['staff']['assessments'].values():
        require(r.get('knowledge','Partial') in ('Partial','Fully assessed'),'Invalid staff knowledge state.')
        if r.get('knowledge')=='Fully assessed':require(type(r.get('coverage_until')) is int and r['coverage_until']>r['day'],'Invalid staff assessment coverage date.')
    known={c['id'] for c in s['clubs']};ids=set()
    for p in s['staff']['people']:
        require(p['id'] not in ids and p['role'] in ROLES,'Invalid staff identity or role.');ids.add(p['id'])
        require(p['club'] is None or p['club'] in known,'Unknown staff employer.')
        require(type(p['wage']) is int and p['wage']>=0 and 0<p['availability']<=100,'Invalid staff contract.')
        require(set(p['capabilities'])==set(CAPABILITIES) and all(type(v) in (int,float) and math.isfinite(v) and 1<=v<=100 for v in p['capabilities'].values()),'Invalid staff capabilities.')
        if p['pending']:require(p['pending']['start']<p['pending']['end'] and p['pending']['wage']>0,'Invalid pending staff appointment.')
