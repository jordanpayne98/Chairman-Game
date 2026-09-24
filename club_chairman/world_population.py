"""Persistent reduced-detail world people with dated lifecycle processing.

The immutable compressed snapshot avoids copying tens of thousands of nested
attribute maps on every match command. Activation moves the SAME identity and
attributes into the detailed simulation. No search generates people.
"""
import base64
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import zlib
from . import identities,people,staff


def pack(data):
    return base64.b64encode(zlib.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),6)).decode('ascii')


@lru_cache(maxsize=2)
def unpack(blob):
    return json.loads(zlib.decompress(base64.b64decode(blob)).decode())


def attributes(r):
    keys=people.ATTRIBUTES if r['kind']=='player' else staff.CAPABILITIES
    return dict(zip(keys,base64.b64decode(r['ratings'])))


def set_attributes(r,values):
    keys=people.ATTRIBUTES if r['kind']=='player' else staff.CAPABILITIES
    r['ratings']=base64.b64encode(bytes(int(values[k]) for k in keys)).decode()


def overall(r):
    a=attributes(r)
    if r['kind']=='player':return max(1,min(100,int(sum(a[k]*v for k,v in people.WEIGHTS[r['role']].items())+.5)))
    return sum(a[k] for k in staff.ROLES[r['role']][1:])//2


def make_person(s,n,cid,kind,group,slot,day,cohort=0,level=50,role_override=None):
    from .simulation import rng_for
    key=f"world:{n['id']}:{cid or 'free'}:{kind}:{group}:{cohort}:{slot}"
    rng=rng_for(s['seed'],'world-traits-v1:'+key)
    age=rng.randint(14,17) if group=='Youth' else rng.randint(18,20) if group=='Reserves' else rng.randint(19,34) if kind=='player' else rng.randint(29,59)
    if cohort and group=='Youth':age=14
    elif cohort and kind=='staff':age=rng.randint(27,35)
    positions=('GK','GK')+('DEF',)*8+('MID',)*9+('FWD',)*6 if group=='Seniors' else ('GK','GK')+('DEF',)*6+('MID',)*6+('FWD',)*4
    if cid is None:positions=('GK','DEF','MID','FWD')
    role=role_override or (positions[slot%len(positions)] if kind=='player' else tuple(staff.ROLES)[slot%len(staff.ROLES)])
    quality=max(10,min(90,level+rng.randint(-12,12)-(22 if group=='Youth' else 12 if group=='Reserves' else 0)))
    keys=people.ATTRIBUTES if kind=='player' else staff.CAPABILITIES
    vals={k:max(1,min(99,quality+rng.randint(-12,12))) for k in keys}
    if kind=='player' and role!='GK':
        for k in people.GROUPS['Goalkeeping']:vals[k]=rng.randint(5,32)
    ident=identities.make(s,key,nationality=n['id'],domestic=n['id'])
    r=dict(id=key,kind=kind,role=role,group=group,club=cid,origin_nation=n['id'],birth_day=day-age*365-rng.randrange(365),
        status='active',created_day=day,contract_start=day if cid else None,contract_end=day+rng.randint(1,4)*365 if cid else None,
        free_since=day if not cid else None,wage=0,expected_wage=max(8000,(quality**3 if kind=='player' else quality**2*10)),
        potential=max(quality,min(99,quality+rng.randint(4,30))),professionalism=rng.randint(25,90),
        fitness=rng.randint(60,100),height=rng.randint(175,201) if role=='GK' else rng.randint(166,195),foot='Left' if rng.random()<.24 else 'Right',
        hidden={k:rng.randint(25,90) for k in people.HIDDEN},risk=rng.choice(('Cautious','Balanced','Ambitious')),condition=100.0,fatigue=0.0,injury_until=0,history=[],**ident)
    set_attributes(r,vals);r['potential']=max(r['potential'],overall(r))
    if group=='Youth':r['expected_wage']=10000
    elif group=='Reserves':r['expected_wage']=18000
    r['professionalism']=r['hidden']['professionalism']
    r['wage']=r['expected_wage'] if cid else 0
    r['history'].append(dict(day=day,event='Career entry' if cohort else 'Database registration',club=cid))
    return r


def _build(seed,origin_day,cfg_text,active_nation,active_clubs):
    from .simulation import rng_for
    cfg=json.loads(cfg_text);s=dict(seed=seed,config={'world_population':cfg})
    settings=cfg['settings'];clubs={};persons={}
    from .career_setup import profile,positions
    from .nations import catalogue
    depths={n['id']:n['division_sizes'] for n in catalogue()['nations']}
    prefixes=('Northstar','Harbour','Union','Riverside','Valley','Olympic','Central','Crescent','Royal','Dynamo','Atlas','Phoenix','Sporting','Racing','Vista','Falcon')
    suffixes=('Athletic','United','Sport Club','FC','Rovers','City','Club','Association')
    for n in cfg['nations']:
        # Existing domestic clubs own their detailed rosters. The remaining
        # clubs fill the worldwide inventory; they are not inserted into a
        # domestic schedule merely to make them visible in a search.
        start=active_clubs if n['id']==active_nation else 0
        for i in range(start,n['clubs']):
            cid=f"world-club:{n['id']}:{i}";rng=rng_for(seed,cid)
            sizes=depths.get(n['id'],[n['clubs']]);tier=next((j+1 for j in range(len(sizes)) if i<sum(sizes[:j+1])),len(sizes)+1)
            stature=profile(seed,n['id'],cid,tier);level=stature['level']
            city=n['cities'][i%len(n['cities'])] if n['cities'] else None
            name=(city+' ' if city else prefixes[i%len(prefixes)]+' ')+suffixes[(i//max(1,len(n['cities'])))%len(suffixes)]
            if not city:name+=f" ({n['name']})"
            c=dict(id=cid,name=name,nation=n['id'],city=city,level=level,stature=stature,opening_cash=0,cash=0,income_weekly=0,ledger=[],payroll_limit=0)
            clubs[cid]=c;payroll=0
            for group,count in [('Seniors',stature['squad_size']),('Youth',settings['youth_target']),('Reserves',settings['reserve_target'])]:
                for j in range(count):
                    # Group participates in identity key, preserving individuality.
                    r=make_person(s,n,cid,'player',group,j,origin_day,level=level,role_override=positions(stature['squad_size'])[j] if group=='Seniors' else None)
                    # Identity includes group from its first generation.
                    if group=='Seniors':r['wage']=r['expected_wage']=max(12000,r['expected_wage']*stature['wealth']//100)
                    persons[r['id']]=r;payroll+=r['wage']
            for j,role in enumerate(stature['roles']):
                r=make_person(s,n,cid,'staff','Staff',j,origin_day,level=level,role_override=role)
                r['wage']=r['expected_wage']=max(12000,r['expected_wage']*stature['wealth']//100)
                persons[r['id']]=r;payroll+=r['wage']
            c.update(opening_cash=payroll*16,cash=payroll*16,income_weekly=payroll*115//100,payroll_limit=payroll*120//100)
        for kind,count in [('player',settings['free_players_per_nation']),('staff',settings['free_staff_per_nation'])]:
            for i in range(count):
                r=make_person(s,n,None,kind,'Seniors' if kind=='player' else 'Staff',i,origin_day,level=40+i%25);persons[r['id']]=r
    return pack(dict(version=1,last_day=origin_day,clubs=clubs,people=persons,cycles=[],next_serial=0))


@lru_cache(maxsize=3)
def build(seed,origin_day,cfg_text,active_nation,active_clubs):
    return _build(seed,origin_day,cfg_text,active_nation,active_clubs)


def initialise(s,legacy=False):
    identities.initialise(s)
    if 'world_population' in s:return
    s['world_population']=dict(blob=None,claimed=[],enabled_day=None,last_day=s['day'],legacy=legacy,manifest={})
    if not legacy:enable(s)


def enable(s):
    from .simulation import require
    w=s['world_population'];require(w['blob'] is None,'The world database already exists.')
    home=s['config'].get('nation',{}).get('id','england')
    # Compact clubs are an isolated development world, not substitutes for
    # England's approved 100-club inventory.
    count=sum(not d.get('supporting') and len(d['members']) or 0 for d in s['leagues']['divisions']) if s.get('calendar') else 0
    w['blob']=build(s['seed'],s['day'],json.dumps(s['config']['world_population'],sort_keys=True),home,count)
    w.update(enabled_day=s['day'],last_day=s['day']);manifest(s)


def manifest(s):
    w=s['world_population'];db=unpack(w['blob']);counts={n['id']:dict(players=0,staff=0,retired=0,free=0) for n in identities.definition(s)['nations']};claimed=set(w['claimed'])
    for r in db['people'].values():
        if r['id'] in claimed:continue
        c=counts[r['nation_id']]
        if r['status']!='active':c['retired']+=1;continue
        c['players' if r['kind']=='player' else 'staff']+=1
        if r['club'] is None:c['free']+=1
    w['manifest']=dict(version=1,clubs=len(db['clubs']),people=len(db['people']),counts=counts,recent_cycles=deepcopy(db['cycles'][-3:]),
        sha256=hashlib.sha256(w['blob'].encode()).hexdigest(),last_day=db['last_day'])


def _employed_moves(s,db,roster,day,events):
    """Fill senior vacancies through consented, funded background club purchases.

    Both sides use the same persistent person. Payments are recorded on both
    club ledgers before any later free-agent hiring; a seller keeps viable
    senior and goalkeeper cover. The world stream is independent of UI RNG.
    """
    from .simulation import rng_for
    from .career_setup import positions
    from collections import Counter
    club_targets={cid:Counter(positions(c.get('stature',{}).get('squad_size',25))) for cid,c in db['clubs'].items()}
    targets={'GK':2,'DEF':8,'MID':9,'FWD':6}
    supply={role:[] for role in targets}
    for seller_id in sorted(db['clubs']):
        senior=[p for p in roster[seller_id] if p['kind']=='player' and p['group']=='Seniors']
        if len(senior)<=14:continue
        for role in targets:
            players=[p for p in senior if p['role']==role]
            if len(players)>club_targets[seller_id][role]:
                supply[role].extend((seller_id,p['id']) for p in players)
    for buyer_id in sorted(db['clubs']):
        buyer=db['clubs'][buyer_id];team=roster[buyer_id]
        payroll=sum(p['wage'] for p in team)
        for role,target in club_targets[buyer_id].items():
            if sum(p['kind']=='player' and p['group']=='Seniors' and p['role']==role for p in team)>=target:
                continue
            rng=rng_for(s['seed'],f'world-employed:{buyer_id}:{role}:{day}')
            if rng.randrange(4):continue  # Routine vacancy recruitment still favours free agents.
            candidates=[]
            for seller_id,pid in supply[role]:
                if seller_id==buyer_id:continue
                seller_team=roster[seller_id]
                senior=[p for p in seller_team if p['kind']=='player' and p['group']=='Seniors']
                if len(senior)<=14:continue
                if sum(p['role']==role for p in senior)<=club_targets[seller_id][role]:continue
                p=db['people'][pid]
                if p['club']!=seller_id or p['contract_start']==day or p['contract_end']<=day+30 or p['injury_until']>day:continue
                fee=p['wage']*6
                wage=max(p['wage'],p['expected_wage'])
                if payroll+wage>buyer['payroll_limit'] or buyer['cash']<fee+4*(payroll+wage):continue
                # National and regional routes are preferred, but neither
                # nationality nor distance makes a person ineligible.
                distance=0 if buyer['nation']==db['clubs'][seller_id]['nation'] else 1
                candidates.append((distance,abs(overall(p)-buyer['level']),p['id'],seller_id,fee,wage))
            if not candidates:continue
            candidates.sort();distance,_,pid,seller_id,fee,wage=candidates[0]
            p=db['people'][pid];seller=db['clubs'][seller_id]
            if rng.randrange(100)>=max(10,min(90,65+(buyer['level']-seller['level'])//2-15*distance)):
                continue
            # Same-cycle destinations cannot sell a recently acquired person.
            if p not in roster[seller_id]:continue
            buyer['cash']-=fee;seller['cash']+=fee
            buyer['ledger'].append(dict(day=day,income=0,payroll=0,transfer=-fee,balance=buyer['cash'],person=pid))
            seller['ledger'].append(dict(day=day,income=0,payroll=0,transfer=fee,balance=seller['cash'],person=pid))
            roster[seller_id].remove(p);team.append(p);payroll+=wage
            p.update(club=buyer_id,group='Seniors',wage=wage,contract_start=day,contract_end=day+730,free_since=None)
            p['history'].append(dict(day=day,event='Transferred',club=buyer_id,from_club=seller_id,fee=fee))
            events['transfers']+=1


def process_day(s):
    w=s['world_population']
    if w['blob'] is None:return
    # A monthly committed cycle handles all elapsed periods in stable order.
    cfg=identities.definition(s);settings=cfg['settings'];period=settings['cycle_days'];year=settings['annual_days']
    if s['day']-w['last_day']<period:return
    db=deepcopy(unpack(w['blob']));claimed=set(w['claimed']);by_nation={n['id']:n for n in cfg['nations']}
    from .simulation import rng_for
    while s['day']-db['last_day']>=period:
        previous=db['last_day'];day=previous+period;annual=day//year>previous//year;events=dict(day=day,retirements=0,inactive_exits=0,intakes=0,staff_entries=0,signings=0,expiries=0,transfers=0)
        roster={cid:[] for cid in db['clubs']};available=[];dues={cid:0 for cid in db['clubs']}
        for pid in sorted(db['people']):
            if pid in claimed:continue
            r=db['people'][pid]
            if r['status']!='active':continue
            age=max(0,(day-r['birth_day'])//365);rng=rng_for(s['seed'],f"world-life:{pid}:{day}")
            cid=r['club']
            if cid:
                paid_days=max(0,min(day,r['contract_end'])-max(previous,r['contract_start']))
                dues[cid]+=r['wage']*paid_days//7
            threshold=38 if r['role']=='GK' else 35 if r['kind']=='player' else 64
            retired=annual and age>=threshold and (age>=threshold+6 or rng.random()<.2+(age-threshold)*.12)
            inactive=not cid and day-r['free_since']>=settings['inactive_free_years']*year
            if retired or inactive:
                r.update(status='retired' if retired else 'inactive',club=None,wage=0,contract_start=None,contract_end=None)
                r['history'].append(dict(day=day,event='Retired' if retired else 'Left active football',club=cid));events['retirements' if retired else 'inactive_exits']+=1;continue
            if cid and r['contract_end']<day:
                r['history'].append(dict(day=r['contract_end']+1,event='Contract expired',club=cid));r.update(club=None,wage=0,contract_start=None,contract_end=None,free_since=day);cid=None;events['expiries']+=1
            if r['kind']=='player':
                if cid and rng.random()<r['hidden']['injury_susceptibility']/3000:
                    r['injury_until']=day+rng.randint(5,45);r['history'].append(dict(day=day,event='Training injury',club=cid))
                r['condition']=max(45.0,r['condition']-12) if r['injury_until']>day else min(100.0,r['condition']+15)
                if r['group']=='Youth' and age>=18:r['group']='Reserves';r['history'].append(dict(day=day,event='Reserve pathway',club=cid))
                if r['group']=='Reserves' and age>=21:r['group']='Seniors';r['history'].append(dict(day=day,event='Senior pathway',club=cid))
                if day//settings['development_days']>previous//settings['development_days']:
                    vals=attributes(r);before=overall(r);growth=0
                    if age<24 and before<r['potential'] and cid and r['injury_until']<=day and rng.random()<.25+r['professionalism']/200:growth=1
                    elif age>=30 and rng.random()<min(.85,(age-28)/14):growth=-1
                    # Physical decline and training growth use existing attributes.
                    keys=people.GROUPS['Physical'] if growth<0 else tuple(people.WEIGHTS[r['role']])
                    for k in keys:vals[k]=max(1,min(99,vals[k]+growth))
                    set_attributes(r,vals)
                    if growth>0 and overall(r)>r['potential']:
                        for k in keys:vals[k]=max(1,vals[k]-1)
                        set_attributes(r,vals);growth=0
                    if growth:r['history'].append(dict(day=day,event='Training development' if growth>0 else 'Age-related decline',club=cid))
            elif annual:
                vals=attributes(r)
                if age<55 and cid and rng.random()<.55:
                    k=rng.choice(staff.CAPABILITIES);vals[k]=min(99,vals[k]+1)
                elif age>=64 and rng.random()<.5:
                    k=rng.choice(staff.CAPABILITIES);vals[k]=max(1,vals[k]-1)
                if vals!=attributes(r):r['history'].append(dict(day=day,event='Professional development' if age<55 else 'Age-related decline',club=cid))
                set_attributes(r,vals)
            if cid:roster[cid].append(r)
            else:available.append(r)
        if annual:
            # Scheduled entrants fill regional workforce shortages. They are
            # independent adults, never copies or renamed retired employees.
            vacancies={nid:{role:0 for role in staff.ROLES} for nid in by_nation}
            for cid,c in db['clubs'].items():
                occupied={r['role'] for r in roster[cid] if r['kind']=='staff'}
                for role in c.get('stature',{}).get('roles',list(staff.ROLES)):
                    if role not in occupied:vacancies[c['nation']][role]+=1
            for nid in sorted(by_nation):
                for index,role in enumerate(staff.ROLES):
                    free=sum(r['kind']=='staff' and r['nation_id']==nid and r['role']==role for r in available)
                    target=settings['free_staff_per_nation']//len(staff.ROLES)+(index<settings['free_staff_per_nation']%len(staff.ROLES))+vacancies[nid][role]
                    for _ in range(max(0,target-free)):
                        serial=db['next_serial'];db['next_serial']+=1
                        r=make_person(s,by_nation[nid],None,'staff','Staff',serial,day,cohort=day//year,level=45,role_override=role)
                        r['history'][0]['event']='Regional staff entry';db['people'][r['id']]=r;available.append(r);events['staff_entries']+=1
        _employed_moves(s,db,roster,day,events)
        for cid in sorted(db['clubs']):
            c=db['clubs'][cid];income=c['income_weekly']*(day-previous)//7;c['cash']+=income-dues[cid]
            c['ledger'].append(dict(day=day,income=income,payroll=dues[cid],balance=c['cash']))
            employed=roster[cid];payroll=sum(r['wage'] for r in employed)
            # Renew before expiry where the existing budget permits; otherwise
            # the person becomes available naturally on the next processing date.
            retained=set()
            for group,target in [('Seniors',c.get('stature',{}).get('squad_size',settings['senior_target'])),('Youth',settings['youth_target']),('Reserves',settings['reserve_target'])]:
                pool=sorted([r for r in employed if r['kind']=='player' and r['group']==group],key=lambda r:(-overall(r),r['id']))
                keep=[r for r in pool if r['role']=='GK'][:2]
                keep+= [r for r in pool if r not in keep][:max(0,target-len(keep))]
                retained.update(r['id'] for r in keep)
            retained.update(r['id'] for r in employed if r['kind']=='staff')
            for r in sorted(employed,key=lambda r:r['id']):
                if r['id'] in retained and 0<=r['contract_end']-day<=period and c['cash']>=payroll*4 and payroll<=c['payroll_limit']:
                    r['contract_end']=day+year*2;r['history'].append(dict(day=day,event='Contract renewed',club=cid))
            from .career_setup import positions
            from collections import Counter
            needs=[('player',role,n) for role,n in Counter(positions(c.get('stature',{}).get('squad_size',25))).items()]+ [('staff',role,1) for role in c.get('stature',{}).get('roles',list(staff.ROLES))]
            for kind,role,target in needs:
                have=sum(r['kind']==kind and r['role']==role and (kind=='staff' or r['group']=='Seniors') for r in employed)
                if have>=target:continue
                candidates=[r for r in available if r['club'] is None and r['kind']==kind and r['role']==role and (kind=='staff' or r['group']=='Seniors') and r['expected_wage']+payroll<=c['payroll_limit'] and c['cash']>=4*(payroll+r['expected_wage'])]
                candidates.sort(key=lambda r:(r['nation_id']!=c['nation'],abs(overall(r)-c['level']),r['id']))
                for r in candidates[:target-have]:
                    if payroll+r['expected_wage']>c['payroll_limit'] or c['cash']<4*(payroll+r['expected_wage']):break
                    r.update(club=cid,wage=r['expected_wage'],contract_start=day,contract_end=day+730,free_since=None);r['history'].append(dict(day=day,event='Signed contract',club=cid));employed.append(r);payroll+=r['wage'];events['signings']+=1
            if annual:
                count=sum(r['kind']=='player' and r['group']=='Youth' for r in employed)
                for i in range(min(settings['intake_limit'],max(0,settings['youth_target']-count))):
                    if payroll+10000>c['payroll_limit'] or c['cash']<4*(payroll+10000):break
                    serial=db['next_serial'];db['next_serial']+=1
                    keeper_needed=sum(p['kind']=='player' and p['group']=='Youth' and p['role']=='GK' for p in employed)<2
                    r=make_person(s,by_nation[c['nation']],cid,'player','Youth',serial,day,cohort=day//year,level=c['level'],role_override='GK' if keeper_needed else None)
                    db['people'][r['id']]=r;employed.append(r);payroll+=r['wage'];events['intakes']+=1
        db['last_day']=day;db['cycles'].append(events)
    w['blob']=pack(db);w['last_day']=db['last_day'];manifest(s)


def activate(s,pid):
    from .simulation import require
    from . import career,pathways
    w=s['world_population'];require(w['blob'] is not None,'Create the world database first.')
    require(pid not in w['claimed'],'This person is already in detailed simulation.')
    db=unpack(w['blob']);r=db['people'].get(pid)
    require(r and r['status']=='active' and r['club'] is None,'Only available unattached people can enter the current recruitment market.')
    r=deepcopy(r);age=max(0,(s['day']-r['birth_day'])//365);a=attributes(r)
    last_club=next((db['clubs'][e['club']] for e in reversed(r['history']) if e.get('club') in db['clubs']),None)
    location_nation=last_club['nation'] if last_club else r['origin_nation']
    if r['kind']=='player':
        require(age>=16,'This player is too young for the senior recruitment market.')
        a['goalkeeping']=a['handling']
        p=dict(id=pid,name=r['name'],club=None,role=r['role'],age=age,attrs=a,wage=r['expected_wage'],fee=50000,
            goals=0,appearances=0,career_goals=0,career_appearances=0,contract_end=None,youth=False,retired=False,
            birth_day=r['birth_day'],injury_until=r['injury_until'],condition=r['condition'],fatigue=r['fatigue'],potential=r['potential'],height=r['height'],foot=r['foot'],nationality=r['nationality'],homegrown=False,
            hidden=deepcopy(r['hidden']),background_history=r['history'])
        for k in ('nation_id','nationalities','birth_nation','given_name','family_name','name_locale','name_algorithm'):p[k]=r[k]
        people.enrich(s,p);s['players'].append(p);pathways.sync(s)
    else:
        p=dict(id=pid,name=r['name'],role=r['role'],club=None,capabilities=a,expected_wage=r['expected_wage'],wage=0,start=None,end=None,
            notice_weeks=4,availability=100,reputation=overall(r),autonomy='Advisory',pending=None,workload=0,morale=60,objectives=[],history=[],risk=r['risk'],
            age=age,birth_day=r['birth_day'],background_history=r['history'],lifecycle_year=s['day']//365,retired=False)
        for k in ('nationality','nation_id','nationalities','birth_nation','given_name','family_name','name_locale','name_algorithm'):p[k]=r[k]
        s['staff']['people'].append(p)
    p['location_nation']=location_nation
    w['claimed'].append(pid);manifest(s)
    return r['kind']


def apply(s,action,data):
    if action not in ('world_population_enable','world_person_activate'):return None
    from .simulation import require
    require(s['match'] is None,'Review the world database outside matchday.')
    if action=='world_population_enable':enable(s);return 'World population created. Existing people and contracts retain their identities.'
    kind=activate(s,data.get('id'));return 'Persistent '+kind+' added to recruitment. Assessment and employment terms still require review.'


def public_summary(s):
    w=s['world_population']
    return dict(enabled=w['blob'] is not None,last_day=w['last_day'],manifest=deepcopy(w['manifest']),
        recent_cycles=deepcopy(w['manifest'].get('recent_cycles',[])),
        nations=[{k:n[k] for k in ('id','name','region','playable')} for n in identities.definition(s)['nations']])


def search(s,nation_id,kind='player',query='',page=0,available_only=False):
    w=s['world_population']
    if not w['blob']:return dict(rows=[],total=0)
    db=unpack(w['blob']);claimed=set(w['claimed']);query=query.casefold()
    rows=[r for r in db['people'].values() if r['nation_id']==nation_id and r['kind']==kind and r['status']=='active' and r['id'] not in claimed and (not available_only or r['club'] is None) and (not query or query in r['name'].casefold())]
    rows.sort(key=lambda r:(r['name'],r['id']))
    result=[]
    for r in rows[page*8:page*8+8]:
        c=db['clubs'].get(r['club']);history=deepcopy(r['history'][-6:])
        for event in history:
            if event['event']=='Transferred':
                source=db['clubs'].get(event.get('from_club'));target=db['clubs'].get(event.get('club'))
                event['summary']=f"Transferred: {source['name'] if source else 'Unknown'} to {target['name'] if target else 'Unknown'} (£{event['fee']/100:,.0f})"
        result.append(dict(id=r['id'],kind=r['kind'],name=r['name'],nationality=r['nationality'],role=r['role'],group=r['group'],age=max(0,(s['day']-r['birth_day'])//365),club=c['name'] if c else None,history=history,contract_end=r['contract_end'],available=r['club'] is None and (r['kind']=='staff' or s['day']-r['birth_day']>=16*365)))
    return dict(rows=result,total=len(rows))


def validate(s):
    from .simulation import require
    w=s['world_population'];cfg=identities.definition(s);ids=[n['id'] for n in cfg['nations']]
    require(len(ids)==len(set(ids)) and len(ids)>=211,'World nationality catalogue is incomplete or duplicated.')
    require(all(n['locales'] and all(x['pool'] in cfg['names'] and x['weight']>0 for x in n['locales']) for n in cfg['nations']),'Unknown national naming pool.')
    require(all(type(v) is int and v>0 for v in cfg['settings'].values()),'Invalid world population setting.')
    require(len(w['claimed'])==len(set(w['claimed'])),'Duplicate detailed-world activation.')
    if w['blob'] is None:return
    require(w['manifest']['last_day']==w['last_day']<=s['day'],'World population clock is inconsistent.')
    # Explicit database audits inspect every record; ordinary match commands
    # verify the immutable snapshot checksum without decompressing the world.
    require(w['manifest']['sha256']==hashlib.sha256(w['blob'].encode()).hexdigest(),'World database snapshot checksum mismatch.')


def validate_database(s):
    from .simulation import require
    w=s['world_population'];db=unpack(w['blob']);known=set(db['clubs']);nations={n['id'] for n in identities.definition(s)['nations']}
    for pid,r in db['people'].items():
        require(pid==r['id'] and r['nation_id'] in nations,'Invalid world person identity.')
        require(r['club'] is None or r['club'] in known,'Missing background employer.')
        a=attributes(r);require(len(a)==(37 if r['kind']=='player' else 11) and all(1<=x<=100 for x in a.values()),'Invalid world attributes.')
        require(r['status'] in ('active','retired','inactive'),'Invalid lifecycle status.')
        if r['club']:require(r['contract_start'] is not None and r['contract_end']>=r['contract_start'] and r['wage']>0,'Invalid background contract.')
    for c in db['clubs'].values():
        require(c['cash']==c['opening_cash']+sum(e['income']-e['payroll']+e.get('transfer',0) for e in c['ledger']),'Background club ledger does not reconcile.')
    transfers={}
    for c in db['clubs'].values():
        for entry in c['ledger']:
            if entry.get('transfer'):
                transfers.setdefault((entry['day'],entry['person']),[]).append(entry['transfer'])
    require(all(len(amounts)==2 and sum(amounts)==0 for amounts in transfers.values()),'Background transfer money does not balance.')
