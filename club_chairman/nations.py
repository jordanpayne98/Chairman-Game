"""Approved national formats and isolated development scenarios.

Calendar reservations are persisted and validated before fixtures are exposed.
This is not the connected full world or a release-ready club/history database.
"""
from copy import deepcopy
from datetime import date, timedelta
import calendar as month_calendar
import json
from pathlib import Path


def catalogue():
    data=json.loads((Path(__file__).resolve().parent.parent/'data/nations.json').read_text(encoding='utf-8'))
    validate_catalogue(data)
    return data


def validate_catalogue(data):
    from .simulation import require
    ns=data['nations'];ids=[n['id'] for n in ns]
    require(len(ns)==14 and len(ids)==len(set(ids)),'National catalogue needs fourteen unique nations.')
    require(sum(len(n['division_sizes']) for n in ns)==data['expected_divisions']==38,'National division inventory must total 38.')
    require(sum(sum(n['division_sizes']) for n in ns)==data['expected_clubs']==636,'National club inventory must total 636.')
    for n in ns:validate_profile(n)


def validate_profile(n):
    from .simulation import require
    sizes=n['division_sizes']
    require(bool(sizes) and len(set(sizes))==1 and all(type(x) is int and x>=4 and x%2==0 for x in sizes),'National divisions need equal, even membership sizes.')
    require(type(n['exchange']) is int and 0<=n['exchange']<=min(sizes)//2,'Invalid national exchange count.')
    require((n['exchange']==0)==n['closed'],'Closed leagues cannot automatically exchange clubs.')
    require(n['start_month'] in range(1,13) and n['end_month'] in range(1,13),'Invalid national calendar months.')
    require(type(n['minimum_rest_days']) is int and n['minimum_rest_days']>=3,'Calendar requires at least three recovery days.')
    require(type(n['first_fixture_day']) is int and n['first_fixture_day']>=1,'Invalid opening fixture offset.')
    require(type(n['registration_days']) is int and n['registration_days']>=1,'Invalid registration window.')
    require(all(type(n[k]) is int and n[k]>=0 for k in ('top_prize','bottom_prize','tier_prize_percent')) and n['top_prize']>=n['bottom_prize'] and n['tier_prize_percent']<=100,'Invalid national prize tuning.')
    for r in n['blackout_ranges']:require(len(r)==2 and all(type(d) is int for d in r) and 0<=r[0]<=r[1],'Invalid calendar blackout range.')
    if n['playable']:
        require(not n['closed'] and not n['playoff_top'],'This scenario requires unsupported playoff rules.')
        require(bool(n['cities']) and len(n['cities'])*len(n['club_suffixes'])>=sum(sizes),'Scenario has too few distinct club identities.')
        names=[city+' '+suffix for suffix in n['club_suffixes'] for city in n['cities']]
        require(len(names)==len(set(names)),'Scenario club names must be unique.')


def scenario(id):
    from .simulation import require
    n=next((n for n in catalogue()['nations'] if n['id']==id),None)
    require(n is not None and n['playable'],'That national scenario is not yet playable.')
    return deepcopy(n)


def bounds(profile,year):
    start=date(year,profile['start_month'],1)
    end_year=year+(profile['end_month']<profile['start_month'])
    end=date(end_year,profile['end_month'],month_calendar.monthrange(end_year,profile['end_month'])[1])
    return start,end,date(year+1,profile['start_month'],1)


def plan(profile,year,origin):
    """Reserve cup slots first, then spread league rounds across valid Saturdays."""
    from .simulation import require
    validate_profile(profile)
    origin=date.fromisoformat(origin);start,end,next_start=bounds(profile,year)
    first=(start-origin).days;last=(end-origin).days;rest=profile['minimum_rest_days']
    blocked={first+d for a,b in profile['blackout_ranges'] for d in range(a,b+1)}
    require(last not in blocked,'Calendar conflict: the reserved cup final is in a blackout.')
    cup_count=(sum(profile['division_sizes'])-1).bit_length();cup=[]
    for i in range(cup_count-1):
        target=first+round((last-first)*(i+1)/cup_count)
        choices=[d for d in range(max(first+profile['first_fixture_day'],target-14),min(last-rest,target+15))
                 if (origin+timedelta(days=d)).weekday()==2 and d not in blocked
                 and all(abs(d-c)>=rest for c in cup+[last])]
        require(bool(choices),'Calendar conflict: no recovery-safe domestic cup slot.')
        cup.append(min(choices,key=lambda d:(abs(d-target),d)))
    cup=sorted(cup+[last])
    candidates=[d for d in range(first+profile['first_fixture_day'],last+1)
                if (origin+timedelta(days=d)).weekday()==5 and d not in blocked
                and all(abs(d-c)>=rest for c in cup)]
    rounds=2*(profile['division_sizes'][0]-1)
    require(len(candidates)>=rounds,'Calendar conflict: not enough recovery-safe league dates. Review blackouts, cup slots or season length.')
    league=[candidates[round(i*(len(candidates)-1)/(rounds-1))] for i in range(rounds)]
    all_dates=sorted(league+cup)
    require(all(b-a>=rest for a,b in zip(all_dates,all_dates[1:])),'Calendar conflict: minimum recovery cannot be satisfied.')
    return dict(nation=profile['id'],year=year,start=first,end=last,next_start=(next_start-origin).days,
                league_days=league,cup_days=cup,blocked_days=sorted(blocked))


def prepare(s,year):
    s['calendar']=plan(s['config']['nation'],year,s['config']['start_date'])
    s['career']['start']=s['calendar']['start']


def contract_end(profile,origin,year,duration,closed=False):
    _,end,_=bounds(profile,year+duration-1+int(closed))
    return (end-date.fromisoformat(origin)).days


def add_year(origin,day):
    origin=date.fromisoformat(origin);d=origin+timedelta(days=day)
    d=d.replace(year=d.year+1,day=min(d.day,month_calendar.monthrange(d.year+1,d.month)[1]))
    return (d-origin).days


def configure(s,id):
    """Called only for a new career; never reshapes a loaded world."""
    from . import career, leagues, market, staff
    from .simulation import rng_for
    n=scenario(id);s['config']['nation']=n
    s['config']['start_date']=date(2026,n['start_month'],1).isoformat();prepare(s,2026)
    s['career_id']+='-'+id
    names=[city+' '+suffix for suffix in n['club_suffixes'] for city in n['cities']]
    added=[];total=sum(n['division_sizes'])
    for i in range(total):
        if i>=len(s['clubs']):
            c=dict(id=f'c{i}',name=names[i],played=0,won=0,drawn=0,lost=0,gf=0,ga=0,points=0,form=[])
            s['clubs'].append(c);added.append(c)
            for j,role in enumerate(['GK']*2+['DEF']*6+['MID']*6+['FWD']*4):
                key=f"national:{id}:{c['id']}:{j}";rng=rng_for(s['seed'],key)
                p=career.new_person(s,role,rng.randint(19,29),rng.randint(*n['initial_ability']),key)
                p.update(club=c['id']);s['players'].append(p)
            s['registration'][c['id']]=[p['id'] for p in s['players'] if p['club']==c['id']]
        c=s['clubs'][i];c.update(name='Northbridge Athletic' if i==0 else names[i],nation=id,city=n['cities'][i%len(n['cities'])])
    schema=s['schema'];market.initialise(s);s['schema']=schema;staff.add_club_staff(s,added)
    for p in s['players']:p['nationality']=n['name'];p['homegrown']=True
    ds=[];offset=0
    for i,size in enumerate(n['division_sizes']):
        prizes=[(n['top_prize']-(n['top_prize']-n['bottom_prize'])*rank//(size-1))*n['tier_prize_percent']**i//100**i for rank in range(size)]
        ds.append(dict(id=f'{id}-{i+1}',name=n['name']+(' Premier' if i==0 else f' Division {i+1}'),tier=i+1,members=[f'c{j}' for j in range(offset,offset+size)],prizes=prizes));offset+=size
    s['leagues'].update(divisions=ds,exchange=n['exchange'],legacy=False)
    s['config']['cup'].update(id=id+'-cup',name=n['name']+' Cup',minimum_rest_days=n['minimum_rest_days'])
    s['config']['competition']['name']=n['name']+' domestic registration'
    leagues.prepare_order(s);leagues.schedule(s)


def validate(s):
    from .simulation import require
    require('calendar' in s,'Career calendar metadata is missing.')
    cal=s.get('calendar')
    if cal is None:
        require('nation' not in s['config'],'National career has no calendar.')
        return
    n=s['config']['nation'];expected=plan(n,cal['year'],s['config']['start_date'])
    require(cal['year']==date.fromisoformat(s['config']['start_date']).year+s['career']['season']-1,'National calendar year does not match the career season.')
    require(cal==expected and s['career']['start']==cal['start'],'Saved national calendar does not reconcile with its rules.')
    ds=s['leagues']['divisions']
    require([len(d['members']) for d in ds]==n['division_sizes'] and s['leagues']['exchange']==n['exchange'],'National membership/rules differ from the selected format.')
    require(all(c.get('nation')==n['id'] for c in s['clubs']),'Club national identity is inconsistent.')
    for d in ds:
        for day in cal['league_days']:
            fs=[f for f in s['fixtures'] if f.get('division')==d['id'] and f['day']==day]
            require(len(fs)==len(d['members'])//2,'National league date has missing fixtures.')
    require(all(f['day'] in cal['cup_days' if f.get('knockout') else 'league_days'] for f in s['fixtures']),'Fixture violates reserved national dates.')
    cup=s['competitions']['cup']
    require(cup is not None and cup['dates']==cal['cup_days'],'National cup does not use its reserved dates.')
