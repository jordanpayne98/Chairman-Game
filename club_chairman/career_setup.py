"""New-career choices and shared fictional club-stature generation.

Only called at creation. No reroll on load, selection, scouting or transfer.
"""
from copy import deepcopy
from . import nations, people, staff, career, identities

NATION_LEVELS={'england':78,'scotland':59,'wales':39,'northern-ireland':40,
 'ireland':46,'germany':76,'france':73,'spain':77,'netherlands':66,
 'portugal':65,'italy':75,'brazil':69,'argentina':65,'usa':61,'compact':55}
BACKGROUNDS=('Local business owner','Football supporter','International investor')
DEFAULTS=dict(tier_step=10,spread=7,minimum_level=22,maximum_level=90,
              senior_min=18,senior_max=25,player_spread=9,opening_weeks=24)


def defaults():
    return dict(name='Alex Morgan',nationality='england',age=35,portrait=0,
                background=BACKGROUNDS[0],club_index=0,sandbox=False,
                funding=0,reputation=0,facilities=0,confidence=60)


def validate_options(options,scenario):
    from .simulation import require
    require(isinstance(options,dict),'Career setup must be a record.')
    require(not (set(options)-set(defaults())),'Unknown career setup option.')
    o=dict(defaults(),**options)
    require(isinstance(o['name'],str) and 1<=len(o['name'].strip())<=40 and o['name'].isprintable(),'Enter an owner name of 1–40 printable characters.')
    o['name']=o['name'].strip()
    require(identities.nation({'config':{}},o['nationality']) is not None,'Choose a recognised nationality.')
    require(o['background'] in BACKGROUNDS,'Unknown owner background.')
    for k,lo,hi in [('age',18,90),('portrait',0,7),('club_index',0,len(clubs(scenario))-1),('funding',0,10000000000),('reputation',0,100),('facilities',0,5),('confidence',20,100)]:
        require(type(o[k]) is int and lo<=o[k]<=hi,'Invalid setup value: '+k)
    require(type(o['sandbox']) is bool,'Sandbox must be enabled or disabled.')
    if not o['sandbox']:
        require(all(o[k]==defaults()[k] for k in ('funding','reputation','facilities','confidence')),'Enable sandbox before changing starting conditions.')
    return o


def clubs(scenario):
    if scenario=='compact':
        from .simulation import definition
        from .leagues import definition as league_definition
        names=definition()['clubs']+league_definition()['lower_clubs']
        return [dict(index=i,name=name,tier=i//8+1) for i,name in enumerate(names)]
    n=nations.scenario(scenario);names=[city+' '+suffix for suffix in n['club_suffixes'] for city in n['cities']]
    names[0]='Northbridge Athletic';out=[];i=0
    for tier,size in enumerate(n['division_sizes'],1):
        for _ in range(size):out.append(dict(index=i,name=names[i],tier=tier));i+=1
    return out


def select_club(s,o):
    """Resolve ownership before competition draws and stature generation.

    c0 is the engine's controlled-club slot. Swap its opening identity and
    membership with the selected slot; no played results or histories exist.
    """
    from . import leagues
    for c in s['clubs']:c['opening_identity']=c['id']
    target='c'+str(o['club_index'])
    if target=='c0':return
    a=next(c for c in s['clubs'] if c['id']=='c0');b=next(c for c in s['clubs'] if c['id']==target)
    for key in ('name','city','opening_identity'):
        av=a.get(key);bv=b.get(key)
        if bv is not None:a[key]=bv
        if av is not None:b[key]=av
    for d in s['leagues']['divisions']:
        d['members']=[target if cid=='c0' else 'c0' if cid==target else cid for cid in d['members']]
    leagues.prepare_order(s);leagues.schedule(s)


def positions(size):
    return (['GK']*2+['DEF']*6+['MID']*6+['FWD']*4+['MID','DEF','FWD','MID','DEF','FWD','MID'])[:size]


def profile(seed,nation,key,tier=1,config=None):
    from .simulation import rng_for
    cfg=dict(DEFAULTS,**(config or {}));rng=rng_for(seed,'stature:'+key)
    reputation=max(cfg['minimum_level'],min(cfg['maximum_level'],NATION_LEVELS.get(nation,46)-(tier-1)*cfg['tier_step']+rng.randint(-cfg['spread'],cfg['spread'])))
    wealth=rng.randint(75,125) # Independent of standing; richer does not mean prestigious.
    facilities=max(1,min(5,round(reputation/20)+rng.choice((-1,0,0,1))))
    level=max(15,min(90,round(reputation*.8+facilities*4)))
    size=max(cfg['senior_min'],min(cfg['senior_max'],18+(reputation-30)//10))
    roles=['Executive','Coaching','Medical']
    if reputation>=40:roles+=['Recruitment','Finance']
    if reputation>=55:roles+=['Football director','Academy']
    if reputation>=70:roles+=['Commercial','Operations']
    return dict(reputation=reputation,wealth=wealth,facilities=facilities,level=level,squad_size=size,roles=roles,tier=tier)


def tune_player(s,p,pr):
    from .simulation import rng_for
    rng=rng_for(s['seed'],'starting-person:'+p['id']);youth=p['youth'];reserve=p['development'].get('group')=='Reserves'
    age=rng.randint(14,17) if youth else rng.randint(18,20) if reserve else rng.choice((rng.randint(18,22),rng.randint(23,29),rng.randint(30,35)))
    level=max(10,min(94,pr['level']+rng.randint(-s['config']['starting_stature']['player_spread'],s['config']['starting_stature']['player_spread'])-(20 if youth else 12 if reserve else 0)))
    if rng.random()<.06:level=min(96,level+8) # Uncommon standout, not guaranteed superstar.
    p.update(age=age,birth_day=s['day']-age*365-rng.randrange(365))
    p['attrs']={k:max(1,min(99,level+rng.randint(-10,10))) for k in people.ATTRIBUTES}
    if p['role']!='GK':
        for k in people.GROUPS['Goalkeeping']:p['attrs'][k]=rng.randint(5,30)
    p['attrs']['goalkeeping']=p['attrs']['handling'];rating=people.overall(p)
    p['potential']=min(100,rating+rng.randint(10,25) if age<23 else rating+rng.randint(0,4))
    p['potential_code']=None;p['peak_overall']=rating
    p['wage']=10000 if youth else 18000 if reserve else max(12000,round(level**3*pr['wealth']/100))
    p['fee']=max(50000,p['wage']*rng.randint(20,70))


def apply(s,o,scenario):
    from .simulation import rng_for,make_report,posting,news
    from . import recruitment,reputation,preparation,market
    cfg=s['config'].setdefault('starting_stature',deepcopy(DEFAULTS))
    s['career_setup']=dict(version=1,scenario=scenario,options=deepcopy(o),customised=o['sandbox'],route='Existing club appointment')
    s['owner']={k:deepcopy(o[k]) for k in ('name','nationality','age','portrait','background')}
    profiles={}
    for c in s['clubs']:
        cid=c['id'];tier=next((d['tier'] for d in s['leagues']['divisions'] if cid in d['members']),6)
        pr=profile(s['seed'],scenario,c.get('opening_identity',cid),tier,cfg)
        if cid=='c0' and o['sandbox']:
            if o['reputation']:pr['reputation']=o['reputation']
            if o['facilities']:pr['facilities']=o['facilities']
            pr['level']=max(15,min(90,round(pr['reputation']*.8+pr['facilities']*4)))
            pr['squad_size']=max(18,min(25,18+(pr['reputation']-30)//10))
            pr['roles']=['Executive','Coaching','Medical']+(['Recruitment','Finance'] if pr['reputation']>=40 else [])+(['Football director','Academy'] if pr['reputation']>=55 else [])+(['Commercial','Operations'] if pr['reputation']>=70 else [])
        c['stature']=pr;profiles[cid]=pr
        roster=[p for p in s['players'] if p['club']==cid and not p['youth'] and p['development'].get('group','Seniors')=='Seniors']
        for i in range(len(roster),pr['squad_size']):
            p=career.new_person(s,('DEF','MID','FWD','GK')[i%4],22,pr['level'],'starting-depth:'+cid+':'+str(i));p['club']=cid;p['development']['group']='Seniors';s['players'].append(p)
        for p in s['players']:
            if p['club']==cid:tune_player(s,p,pr)
        s['registration'][cid]=[p['id'] for p in s['players'] if p['club']==cid and not p['youth'] and p['development'].get('group','Seniors')=='Seniors']
    # Retain identities when adjusting initial departments; release surplus slots.
    template=deepcopy(s['staff']['people'][0])
    for cid,pr in profiles.items():
        for p in s['staff']['people']:
            if p['club']==cid and p['role'] not in pr['roles']:p.update(club=None,wage=0,start=None,end=None)
        for role in pr['roles']:
            p=next((p for p in s['staff']['people'] if p['club']==cid and p['role']==role),None)
            if p is None:
                p=deepcopy(template);p.update(id='opening-staff:'+cid+':'+role,club=cid,role=role,history=[],objectives=[],pending=None)
                identities.stamp(s,p,s['config'].get('nation',{}).get('id','england'));s['staff']['people'].append(p)
            rng=rng_for(s['seed'],'opening-staff-skills:'+p['id'])
            p['capabilities']={k:max(1,min(99,pr['level']+rng.randint(-14,12))) for k in staff.CAPABILITIES}
            wage=max(12000,pr['level']**2*10*pr['wealth']//100)
            p.update(wage=wage,expected_wage=wage,reputation=pr['reputation'],start=0,end=career.contractual_end(s,3))
    s['config']['recruitment']['max_wage']=max(s['config']['recruitment']['max_wage'],max(p['wage'] for p in s['players'])*3)
    pr=profiles['c0'];m=s['managers']['people'][0]
    m.update(skill=pr['level'],wage=max(30000,pr['level']**2*20),fee=max(90000,pr['level']**2*60))
    m['capabilities']={k:max(1,min(99,pr['level']+rng_for(s['seed'],'opening-manager:'+k).randint(-10,10))) for k in staff.CAPABILITIES}
    s['manager']=dict(deepcopy(m),contract_end=career.contractual_end(s,3),notice_weeks=4);preparation.appoint(s)
    for cid,pr in profiles.items():
        wages=market.club_payroll(s,cid);opening=wages*cfg['opening_weeks'];overheads=max(30000,wages//8)
        if cid=='c0':
            s['cash']=opening;s['config']['opening_cash']=opening;s['budget']=wages*125//100
            s['config'].update(budget_min=wages//2,budget_max=wages*3,weekly_sponsor=wages//2,capacity=max(2000,pr['reputation']**2*5))
            s['career']['facilities']={k:pr['facilities'] for k in s['career']['facilities']}
        else:s['market']['accounts'][cid].update(opening=opening,cash=opening,income_weekly=(wages+overheads)*115//100,overheads_weekly=overheads)
        s['recruitment']['clubs'][cid]=recruitment.record(pr['reputation'],0,'Opening stature; no past honours inferred.')
    recruitment.sync(s)
    for d in s['leagues']['divisions']:
        value=round(sum(profiles[cid]['reputation'] for cid in d['members'])/len(d['members']))
        s['recruitment']['leagues'][d['id']]=recruitment.record(value,0,'Opening member stature; no prior results.')
    for p in s['players']:
        if p['club']:
            base=profiles[p['club']]['reputation']
            s['recruitment']['players'][p['id']]=recruitment.record(base+rng_for(s['seed'],'opening-reputation:'+p['id']).randint(-5,5),0,'Opening club context; no past achievements inferred.')
    s['reputation_progress']['reference']={};reputation.sync(s)
    for p in s['players']:
        if p['club']:p['contract_end']=career.contractual_end(s,3)
        if p['club']=='c0':s['reports'][p['id']]=make_report(s,p,'Coaching staff',5)
    if o['sandbox']:
        s['trust']=o['confidence']
        if o['funding']:posting(s,'sandbox:opening-funding',o['funding'],'Sandbox opening funding grant')
    news(s,'Career setup confirmed',o['name']+' takes charge. Starting employment and operating cash are inherited. '+('Sandbox settings enabled.' if o['sandbox'] else 'Standard starting conditions.'))
