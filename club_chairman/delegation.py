"""Explicit authority, reviewed proposals and bounded operational decisions.

Every automatic action uses the same domain command as the owner. A failed
proposal runs in a discarded copy, so a denied action cannot leave a payment,
reservation or partial agreement behind.
"""
from copy import deepcopy
import json

DEPARTMENTS={
    'recruitment':('Recruitment','ability_assessment',('scout',)),
    'contracts':('Player contracts','negotiation',('enquire','propose_offer','accept_offer','complete_offer','withdraw_offer','registration_submit')),
    'development':('Training','coaching',('development_plan',)),
    'academy':('Academy','youth_development',('academy_intake','academy_admit','academy_promote')),
    'finance':('Finance','financial_control',()),
    'commercial':('Commercial','commercial_judgement',('sponsor_enquire','sponsor_propose','sponsor_accept')),
    'operations':('Facilities','operations',('project_plan','project_approve','project_cancel')),
    'executive':('Club decisions','people_management',('decision',)),
    'medical':('Recovery','operations',('development_plan',)),
}
MODES=('Manual','Approval required','Autonomous')
COMMITMENTS=('scout','complete_offer','academy_intake','academy_admit','project_plan','project_approve','decision')
DEFAULTS=dict(club_limit=30000000,department_limit=8000000,duration_days=365,
              period_days=28,case_lifetime=7,allocation=25)


def initialise(s):
    cfg=s['config'].setdefault('delegation',{})
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    if 'delegation' in s:return
    s['delegation']=dict(club_limit=cfg['club_limit'],responsibilities={key:dict(delegate=None,mode='Manual',
        limit=cfg['department_limit'],days=cfg['duration_days'],allocation=cfg['allocation'],objective='Maintain',
        excluded=[],generation=0) for key in DEPARTMENTS},cases=[],log=[],held={},last_digest=s['day'])


def exposure(s,action,data):
    from . import career,market
    cost=0;days=0;hold=None
    if action=='scout':cost=s['config']['scout_fee']
    elif action in ('propose_offer','accept_offer','complete_offer'):
        p=career.person(s,data.get('id'));o=s['career']['offers'].get(p['id'])
        if not o:raise ValueError('No player discussion exists.')
        terms=data if action=='propose_offer' else o
        end=career.contractual_end(s,terms['duration']) if action=='propose_offer' else o['end']
        days=max(0,end-s['day']);cost=terms['fee']+terms['wage']*days//7
        if o['kind']=='renew':cost=max(0,cost-p['wage']*max(0,p['contract_end']-s['day'])//7)
        deal=s['market']['deals'].get(o.get('deal_id'))
        if deal:cost+=deal['fee']
        if any(terms.get(k,0) for k in ('appearance_bonus','goal_bonus','club_option')):
            raise ValueError('Performance bonuses and extension options need an owner review; their full exposure is not delegated.')
        hold='contract:'+p['id']
    elif action=='academy_intake':cost=s['config']['career']['academy_trial_fee']
    elif action=='academy_admit':
        p=career.person(s,data.get('id'));days=max(0,career.contractual_end(s,3)-s['day']);cost=s['config']['career']['academy_admission_fee']+p['wage']*days//7
    elif action=='project_plan':cost=50000
    elif action=='project_approve':
        p=next((p for p in s['career']['projects'] if p['id']==data.get('id')),None)
        if not p:raise ValueError('The facility proposal no longer exists.')
        days=365;cost=p['cost']+p['upkeep']*days//7
    elif action=='decision':cost=s['decision']['cost'] if s['decision'] and data.get('choice')=='approve' else 0
    elif action in ('sponsor_propose','sponsor_accept'):
        o=s['commercial']['offers'].get(data.get('right'))
        days=(data['weeks'] if action=='sponsor_propose' else o['weeks'])*7
    return dict(cost=cost,days=days,hold=hold)


def spent(s,key=None,exclude=None):
    day=s['day'];period=s['config']['delegation']['period_days'];d=s['delegation']
    committed=sum(e['committed'] for e in d['log'] if day-e['day']<period and (key is None or e['responsibility']==key))
    held=sum(h['cost'] for ident,h in d['held'].items() if ident!=exclude and (key is None or h['responsibility']==key))
    return committed+held


def authorize(s,actor,scope,key,action,data,override=False):
    from .simulation import require
    from .staff import person
    require(scope=='c0' and key in DEPARTMENTS,'This delegated action has no authority in that club or department.')
    p=person(s,actor);rule=s['delegation']['responsibilities'][key]
    require(p['club']=='c0' and p['start']<=s['day']<=p['end'] and rule['delegate']==actor,'This delegate is no longer appointed to that responsibility.')
    require(action in DEPARTMENTS[key][2] and action not in rule['excluded'],'This action is excluded from the delegate’s authority.')
    if key=='medical':require(data.get('load')=='Light','Medical authority only permits lighter recovery work.')
    require(override or rule['mode']=='Autonomous','This responsibility requires owner approval.')
    require(override or p['autonomy']!='Approval required','The staff contract requires owner approval.')
    e=exposure(s,action,data)
    if not override:
        require(e['days']<=rule['days'],'The proposed contract exceeds delegated duration authority.')
        require(spent(s,key,e['hold'])+e['cost']<=rule['limit'],'The department’s rolling commitment limit would be exceeded.')
        require(spent(s,None,e['hold'])+e['cost']<=s['delegation']['club_limit'],'The club’s rolling delegated commitment limit would be exceeded.')
    return e


def cancel_uncommitted(s,key,actor):
    from . import career
    d=s['delegation']
    for c in d['cases']:
        if c['responsibility']==key and c['status'] in ('pending','blocked'):
            c['status']='cancelled';c['outcome']='Responsibility changed; proposal returned to owner control.'
    for o in s['career']['offers'].values():
        if o.get('delegate')==actor and key=='contracts' and o['status'] not in ('completed','withdrawn','expired','rejected'):
            career.apply(s,'withdraw_offer',dict(id=o['player']))
    for ident,h in list(d['held'].items()):
        if h['responsibility']==key:del d['held'][ident]
    if key=='commercial':
        for o in s['commercial']['offers'].values():
            if o.get('delegate')==actor and o['status'] in ('quote','counter','agreed'):o['status']='withdrawn'


def reconcile(s):
    if 'delegation' not in s:return
    from .simulation import news
    people={p['id']:p for p in s['staff']['people']}
    for key in DEPARTMENTS:
        rule=s['delegation']['responsibilities'][key]
        p=people.get(rule['delegate'])
        if rule['delegate'] and (not p or p['club']!='c0' or p['end']<s['day']):
            cancel_uncommitted(s,key,rule['delegate']);rule.update(delegate=None,mode='Manual',generation=rule['generation']+1)
            news(s,'Responsibility returned to owner',DEPARTMENTS[key][0]+': the delegate left. Existing contracts still apply; new commitments require your review.')
    for ident,h in list(s['delegation']['held'].items()):
        o=s['career']['offers'].get(h['player'])
        if not o or o['status'] not in ('medical','ready'):del s['delegation']['held'][ident]


def perform(s,key,action,data,reason,override=False,approved=None):
    from .simulation import apply as domain_apply,validate
    from . import registration
    actor=s['delegation']['responsibilities'][key]['delegate']
    e=authorize(s,actor,'c0',key,action,data,override)
    if approved and (e['cost']>approved['cost'] or e['days']>approved['days']):raise ValueError('Terms changed. Decline this proposal and review a fresh one.')
    trial=deepcopy(s);prior={p['id']:p['club'] for p in trial['players'] if not p['youth']}
    result=domain_apply(trial,action,deepcopy(data));registration.sync(trial,prior)
    reconcile(trial)
    if action=='enquire':trial['career']['offers'][data['id']]['delegate']=actor
    if action=='sponsor_enquire':trial['commercial']['offers'][data['right']]['delegate']=actor
    if action=='accept_offer':trial['delegation']['held'][e['hold']]=dict(cost=e['cost'],responsibility=key,player=data['id'])
    if action in ('complete_offer','withdraw_offer') and e['hold']:trial['delegation']['held'].pop(e['hold'],None)
    trial['delegation']['log'].append(dict(day=s['day'],actor=actor,scope='c0',responsibility=key,
        action=action,data=deepcopy(data),reason=reason,outcome=result,committed=e['cost'] if action in COMMITMENTS else 0))
    validate(trial);s.clear();s.update(trial)
    return result


def propose(s,key,action,data,reason):
    d=s['delegation'];rule=d['responsibilities'][key]
    signature=json.dumps([key,action,data],sort_keys=True)
    if any(c['signature']==signature and c['status'] in ('pending','blocked') for c in d['cases']):return
    try:e=exposure(s,action,data)
    except ValueError as exc:e=dict(cost=0,days=0,hold=None);reason+=' '+str(exc)
    error='Owner approval requested.'
    if rule['mode']=='Autonomous':
        try:perform(s,key,action,data,reason);return
        except ValueError as exc:error=str(exc)
    d=s['delegation']
    ident=f"delegation:{s['day']}:{key}:{len(d['cases'])}"
    d['cases'].append(dict(id=ident,signature=signature,day=s['day'],expires=s['day']+s['config']['delegation']['case_lifetime'],
        responsibility=key,actor=rule['delegate'],generation=rule['generation'],action=action,data=deepcopy(data),
        exposure=e,status='pending',reason=reason,issue=error,outcome=None))
    from .simulation import news
    news(s,'Staff approval requested',DEPARTMENTS[key][0]+': '+reason+' '+error)


def recommendation(s,key):
    from . import career,commercial,registration
    own=[p for p in s['players'] if p['club']=='c0' and not p['retired']]
    if key=='executive' and s['decision']:
        return 'decision',dict(choice='approve'),'Deliver the scheduled club activity within approved resources.'
    if key=='contracts':
        for o in sorted(s['career']['offers'].values(),key=lambda o:o['id']):
            if o.get('delegate')!=s['delegation']['responsibilities'][key]['delegate']:continue
            pid=o['player'];p=career.person(s,pid)
            if o['status']=='draft':return 'propose_offer',dict(id=pid,wage=p['wage'],fee=0 if o['kind']=='renew' else p['fee'],duration=2),'Offer continuity on the current base salary, without performance clauses.'
            if o['status'] in ('counter','agreed'):return 'accept_offer',dict(id=pid),'Reserve the negotiated cash and payroll after the player response.'
            if o['status']=='ready':return 'complete_offer',dict(id=pid),'Complete the agreed contract after medical review and current affordability checks.'
        for p in sorted(own,key=lambda p:(p['contract_end'] or 9999,p['id'])):
            o=s['career']['offers'].get(p['id'])
            if not p['youth'] and not p.get('retired') and p['contract_end']-s['day']<=28 and (not o or o['status'] in ('completed','withdrawn','expired')):
                return 'enquire',dict(id=p['id']),'Review approaching employment expiry and protect squad continuity.'
        seniors=[p for p in own if not p['youth']]
        if s['day']<=career.window_end(s) and len(seniors)<19:
            from . import club_ai,people
            from .simulation import payroll
            choices=[]
            for p in s['players']:
                o=s['career']['offers'].get(p['id'])
                if p['club'] is not None or p['youth'] or p['retired'] or club_ai.pending_for(s,p['id']):continue
                if o and o['status'] not in ('completed','expired','withdrawn'):continue
                report=people.observed_report(s,p)
                if not report or 'overall' not in report:continue
                if not career.free_cash(s,p['fee']) or payroll(s)+career.reservations(s)[1]+p['wage']>s['budget']:continue
                try:registration.check_arrival(s,p,'c0')
                except ValueError:continue
                cover=sum(q['role']==p['role'] for q in seniors)
                choices.append((cover,-sum(report['overall'])/2,p['wage'],p['id']))
            if choices:
                pid=min(choices)[-1]
                return 'enquire',dict(id=pid),'Use a completed scouting assessment to discuss affordable squad cover.'
    if key=='recruitment' and s['day']%7==1 and s['day']<=career.window_end(s):
        pool=[p for p in s['players'] if p['club'] is None and not p['youth'] and not p['retired'] and p['id'] not in s['scouting'] and p['id'] not in s['reports']]
        if pool:
            # Salary/age/role are public; latent attributes never rank targets.
            p=min(pool,key=lambda p:(sum(q['role']==p['role'] for q in own),p['wage'],p['age'],p['id']))
            return 'scout',dict(id=p['id']),'Assess affordable cover for a position with fewer squad options.'
    if key in ('development','medical') and s['day']%7==1:
        for p in own:
            focus='Goalkeeping' if p['role']=='GK' else 'Technical'
            load='Light' if p['injury_until']>s['day'] or p['condition']<80 else 'Normal'
            if key=='medical' and load!='Light':continue
            if p['development']['load']!=load or key=='development' and p['development']['focus']!=focus:
                return 'development_plan',dict(id=p['id'],focus=focus,load=load),'Match training load to observed fitness and the player’s role.'
    if key=='academy' and s['day']%7==2:
        if s['day']//365 not in s['career']['intakes']:return 'academy_intake',{},'Review this year’s persistent academy cohort.'
        trials=[p for p in s['players'] if p['youth'] and p['club'] is None and not p['retired'] and p.get('candidate_season')==s['career']['season']]
        if trials and len([p for p in own if p['youth']])<s['config']['career']['academy_base_capacity']+(s['career']['facilities']['academy']-1)*6:
            p=min(trials,key=lambda p:(p['wage'],p['id']))
            return 'academy_admit',dict(id=p['id']),'Offer an available academy place within the approved wage budget.'
    if key=='commercial':
        for right in sorted(s['config']['commercial']['rights']):
            if any(c['right']==right and c['status']=='active' for c in s['commercial']['contracts']):continue
            o=s['commercial']['offers'].get(right)
            if o and not o.get('delegate'):continue
            if (not o or o['status'] in ('signed','expired','withdrawn','rejected')) and s['day']%7==3:
                return 'sponsor_enquire',dict(right=right),'Seek a sponsor for uncommitted inventory.'
            if not o:continue
            if o['status']=='quote':return 'sponsor_propose',dict(right=right,weekly=o['weekly'],weeks=o['weeks']),'Submit the quoted sponsor terms for unused inventory.'
            if o['status'] in ('agreed','counter'):return 'sponsor_accept',dict(right=right),'Sign dated sponsorship after checking exclusivity and contract duration.'
    if key=='operations' and s['day']%7==4:
        quoted=next((p for p in s['career']['projects'] if p['status']=='quoted'),None)
        if quoted:return 'project_approve',dict(id=quoted['id']),'Review the requested facility proposal, including a year of additional running costs.'
        rule=s['delegation']['responsibilities'][key]
        if rule['objective']=='Develop' and not any(p['status'] in ('feasibility','quoted','construction') for p in s['career']['projects']) and s['career']['facilities']['training']<3:
            return 'project_plan',dict(kind='training'),'Investigate the training improvement objective before approving construction.'
    return None


def process_day(s):
    from .simulation import news
    for c in s['delegation']['cases']:
        if c['status'] in ('pending','blocked') and s['day']>c['expires']:c['status']='expired';c['outcome']='Unsigned proposal lapsed.'
    reconcile(s)
    for key in DEPARTMENTS:
        rule=s['delegation']['responsibilities'][key]
        if not rule['delegate'] or rule['mode']=='Manual':continue
        rec=recommendation(s,key)
        if rec:
            action,data,reason=rec;propose(s,key,action,data,reason)
    d=s['delegation']
    if s['day']-d['last_digest']>=28:
        entries=[e for e in d['log'] if e['day']>d['last_digest']]
        pending=sum(c['status'] in ('pending','blocked') for c in d['cases'])
        news(s,'Executive monthly digest',f"{len(entries)} delegated actions recorded; {pending} proposals need review. Guaranteed commitments authorised: £{sum(e['committed'] for e in entries)/100:,.0f}. Club cash: £{s['cash']/100:,.0f}. Staff > Reports explains each action.")
        d['last_digest']=s['day']
    if s['day']%7==0 and d['responsibilities']['finance']['delegate']:
        from .simulation import view,payroll
        from .planning import forecast
        f=forecast(view(s));news(s,'Finance briefing',f"Committed payroll is £{payroll(s)/100:,.0f}/week. The current forecast closes at £{f['cash']/100:,.0f}; it includes signed obligations and excludes unsigned staff proposals. No budget or owner funding was changed.")


def cover_plan(v):
    rules=v['delegation']['responsibilities'];own=[p for p in v['staff']['people'] if p['club']=='c0']
    used={p['id']:sum(r['allocation'] for r in rules.values() if r['delegate']==p['id']) for p in own};result={}
    for key in DEPARTMENTS:
        rule=rules[key]
        if rule['delegate']:continue
        options=[p for p in own if used[p['id']]+rule['allocation']<=p['availability']]
        if not options:continue
        cap=DEPARTMENTS[key][1]
        def score(p):
            report=p.get('assessment') or v['staff'].get('assessments',{}).get(p['id'])
            return sum(report['ranges'][cap])/2 if report else 50
        p=max(options,key=lambda p:(score(p),-used[p['id']],p['id']))
        result[key]=p['id'];used[p['id']]+=rule['allocation']
    return result


def apply(s,action,data):
    if action not in ('delegation_set','delegation_preset','delegation_case','delegation_club_limit','delegation_cover'):return None
    from .simulation import require
    from .staff import person
    require(s['match'] is None,'Responsibilities and approvals pause during matchday.')
    d=s['delegation']
    if action=='delegation_cover':
        plan=cover_plan(s);require(plan,'No unallocated staff capacity is available for uncovered departments.')
        for key,actor in plan.items():
            r=d['responsibilities'][key];r.update(delegate=actor,mode='Manual',generation=r['generation']+1)
        return f'{len(plan)} departments assigned advisory cover. Review a preset to change approval authority.'
    if action=='delegation_club_limit':
        value=data.get('value');require(type(value) is int and 0<=value<=100000000,'Choose a valid club commitment limit.')
        d['club_limit']=value;return 'Club delegated commitment limit updated. Signed agreements remain binding.'
    if action=='delegation_case':
        c=next((c for c in d['cases'] if c['id']==data.get('id')),None)
        require(c is not None and c['status'] in ('pending','blocked') and s['day']<=c['expires'],'This proposal is no longer awaiting review.')
        choice=data.get('choice');require(choice in ('approve','decline'),'Choose approve or decline.')
        if choice=='decline':c['status']='declined';c['outcome']='Owner declined.';return 'Proposal declined; no commitment was made.'
        rule=d['responsibilities'][c['responsibility']]
        require(c['actor']==rule['delegate'] and c['generation']==rule['generation'],'Authority changed. Review a fresh proposal.')
        result=perform(s,c['responsibility'],c['action'],c['data'],c['reason']+' Owner approved this proposal.',override=True,approved=c['exposure'])
        target=next(x for x in s['delegation']['cases'] if x['id']==c['id']);target['status']='approved';target['outcome']=result
        return result
    if action=='delegation_preset':
        preset=data.get('preset');require(preset in ('Hands-on','Balanced','Executive'),'Unknown responsibility preset.')
        for key,rule in d['responsibilities'].items():
            mode='Manual' if preset=='Hands-on' or not rule['delegate'] else 'Approval required' if preset=='Balanced' else 'Autonomous'
            if rule['delegate'] and person(s,rule['delegate'])['autonomy']=='Approval required' and mode=='Autonomous':mode='Approval required'
            if rule['mode']!=mode:cancel_uncommitted(s,key,rule['delegate']);rule['generation']+=1;rule['mode']=mode
        return 'Responsibility preset applied to appointed delegates. Vacancies remain under owner control.'
    key=data.get('key');require(key in DEPARTMENTS,'Unknown responsibility.')
    rule=d['responsibilities'][key];actor=data.get('delegate');mode=data.get('mode');limit=data.get('limit');days=data.get('days');objective=data.get('objective','Maintain')
    require(mode in MODES and type(limit) is int and 0<=limit<=100000000 and type(days) is int and 0<=days<=1095,'Invalid authority limits.')
    require(objective in ('Maintain','Develop'),'Choose a supported department objective.')
    require(objective=='Maintain' or key=='operations','The Develop objective is currently available for Facilities.')
    if actor:
        p=person(s,actor);require(p['club']=='c0' and p['end']>=s['day'],'Appoint a current member of your staff.')
        allocated=sum(r['allocation'] for k,r in d['responsibilities'].items() if k!=key and r['delegate']==actor)
        require(allocated+rule['allocation']<=p['availability'],'This assignment exceeds the staff member’s available capacity.')
        require(mode!='Autonomous' or p['autonomy']!='Approval required','The staff contract requires approval for commitments.')
    else:require(mode=='Manual','Unstaffed responsibilities must remain with the owner.')
    cancel_uncommitted(s,key,rule['delegate'])
    rule.update(delegate=actor,mode=mode,limit=limit,days=days,objective=objective,generation=rule['generation']+1)
    return 'Responsibility saved. New authority applies to future actions; signed agreements are unchanged.'


def snapshot(s):
    d=deepcopy(s['delegation'])
    for key,rule in d['responsibilities'].items():rule['used']=spent(s,key)
    d['used']=spent(s);return d


def validate(s):
    from .simulation import require
    d=s['delegation'];people={p['id']:p for p in s['staff']['people']}
    require(set(d['responsibilities'])==set(DEPARTMENTS),'Missing responsibility coverage.')
    for key,r in d['responsibilities'].items():
        require(r['mode'] in MODES and r['limit']>=0 and r['days']>=0,'Invalid responsibility limits.')
        if r['delegate']:require(r['delegate'] in people and people[r['delegate']]['club']=='c0','A departed staff member retained authority.')
        else:require(r['mode']=='Manual','A vacancy cannot commit autonomously.')
    for pid,p in people.items():require(sum(r['allocation'] for r in d['responsibilities'].values() if r['delegate']==pid)<=p['availability'],'Staff allocation exceeds available capacity.')
    require(len({c['id'] for c in d['cases']})==len(d['cases']),'Duplicate staff approval identity.')
