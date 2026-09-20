"""Division membership, league schedules and atomic season movement.

The two eight-club Northshire divisions are development content. Wider national
pyramids, feeder replacements and continental qualification remain separate work.
"""
from copy import deepcopy

def definition():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parent.parent/'data/leagues.json').read_text())


def initialise(s,legacy=False):
    if 'leagues' in s:return
    s['leagues']=dict(legacy=legacy,divisions=[dict(id='northshire-1',name='Northshire Premier',
        tier=1,members=[c['id'] for c in s['clubs']],prizes=list(s['config']['prizes']))],
        exchange=3,closed=False,movements=[],final_tables={},draw_order={})
    if legacy:
        s['leagues']['divisions'][0]['name']='Northshire League'
    else:
        expand_world(s)
        prepare_order(s)
        schedule(s)


def expand_world(s):
    """Add known development entities only at creation or a committed boundary."""
    from . import career, market, staff
    from .simulation import rng_for
    cfg=s['config'].setdefault('leagues',definition())
    added=[]
    for i,name in enumerate(cfg['lower_clubs'],8):
        cid=f'c{i}'
        if any(c['id']==cid for c in s['clubs']):continue
        club=dict(id=cid,name=name,played=0,won=0,drawn=0,lost=0,gf=0,ga=0,points=0,form=[])
        s['clubs'].append(club);added.append(club)
        for j,role in enumerate(['GK']*2+['DEF']*6+['MID']*6+['FWD']*4):
            key=f'division-expansion:{cid}:{j}';rng=rng_for(s['seed'],key)
            p=career.new_person(s,role,rng.randint(19,29),rng.randint(*cfg['initial_ability']),key)
            p.update(club=cid,contract_end=s['career']['start']+316);s['players'].append(p)
        s['registration'][cid]=[p['id'] for p in s['players'] if p['club']==cid]
    # Existing accounts and staff remain untouched; only new clubs receive an
    # explicit opening balance and roster, just like the original world setup.
    schema=s['schema'];market.initialise(s);s['schema']=schema
    staff.add_club_staff(s,added)
    data=s['leagues'];data['divisions'][0]['name']='Northshire Premier'
    if len(data['divisions'])==1:
        data['divisions'].append(dict(id='northshire-2',name='Northshire Championship',tier=2,
            members=[f'c{i}' for i in range(8,16)],prizes=[p*cfg['lower_prize_percent']//100 for p in s['config']['prizes']]))
    s['config']['cup']['round_days']=list(cfg['cup_round_days'])
    data['exchange']=cfg['exchange']
    data['legacy']=False


def division_for(s,cid='c0'):
    return next(d for d in s['leagues']['divisions'] if cid in d['members'])


def prepare_order(s):
    from .simulation import rng_for
    data=s['leagues'];data.update(closed=False,movements=[],final_tables={},draw_order={})
    for d in data['divisions']:
        ids=sorted(d['members']);rng_for(s['seed'],f"league-draw:{s['career']['season']}:{d['id']}").shuffle(ids)
        data['draw_order'][d['id']]=ids


def standings(s,division=None):
    data=s['leagues'];d=division or division_for(s)
    clubs=[c for c in s['clubs'] if c['id'] in d['members']]
    basic=lambda c:(-c['points'],-(c['gf']-c['ga']),-c['gf'])
    if data['legacy']:return sorted(clubs,key=lambda c:basic(c)+(c['id'],))
    order={cid:i for i,cid in enumerate(data['draw_order'][d['id']])}
    groups={}
    for c in clubs:groups.setdefault(basic(c),set()).add(c['id'])
    head={c['id']:0 for c in clubs}
    for f in s['fixtures']:
        if f.get('division')!=d['id'] or f['result'] is None:continue
        home=next(c for c in clubs if c['id']==f['home'])
        if f['away'] not in groups[basic(home)]:continue
        a,b=f['result']['score'];head[f['home']]+=3 if a>b else 1 if a==b else 0
        head[f['away']]+=3 if b>a else 1 if a==b else 0
    return sorted(clubs,key=lambda c:basic(c)+(-head[c['id']],order[c['id']]))


def schedule(s):
    """Generate one double round robin per division with stable fixture IDs."""
    s['fixtures']=[];season=s['career']['season'];start=s['career']['start']
    for d in s['leagues']['divisions']:
        ring=list(d['members']);n=len(ring);pairings=[]
        for r in range(n-1):
            pairings.append([(ring[-1-j],ring[j]) if r%2 else (ring[j],ring[-1-j]) for j in range(n//2)])
            ring=[ring[0],ring[-1]]+ring[1:-1]
        for r in range(2*(n-1)):
            for j,(a,b) in enumerate(pairings[r%(n-1)]):
                if r>=n-1:a,b=b,a
                prefix='' if season==1 and d['tier']==1 else f"s{season}-" if d['tier']==1 else f"s{season}-{d['id']}-"
                s['fixtures'].append(dict(id=f'{prefix}f{r}-{j}',day=s['calendar']['league_days'][r] if s.get('calendar') else start+5+r*7,home=a,away=b,result=None,
                    division=d['id'],competition_name=d['name']))
    s['fixtures'].sort(key=lambda f:(f['day'],f['id']))


def close(s):
    """Freeze final tables and changes; apply membership only on next-season commit."""
    from .simulation import require, news
    from .market import post
    data=s['leagues']
    if data['closed']:return
    require(all(f['result'] is not None for f in s['fixtures']),'Outstanding fixtures prevent season closure.')
    data['final_tables']={d['id']:deepcopy(standings(s,d)) for d in data['divisions']}
    if not data['legacy']:
        count=data['exchange']
        for upper,lower in zip(data['divisions'],data['divisions'][1:]):
            for d,target,rows,kind in ((upper,lower,data['final_tables'][upper['id']][-count:],'Relegated'),
                                      (lower,upper,data['final_tables'][lower['id']][:count],'Promoted')):
                for club in rows:data['movements'].append(dict(club=club['id'],source=d['id'],target=target['id'],kind=kind))
        # Owner award retains its historical posting ID; rivals now receive the
        # same explicit position-based league settlement in their own accounts.
        for d in data['divisions']:
            for i,c in enumerate(data['final_tables'][d['id']]):
                if c['id']!='c0':post(s,c['id'],f"season:{s['career']['season']}:{d['id']}:prize:{c['id']}",d['prizes'][i],'League prize')
        names={c['id']:c['name'] for c in s['clubs']}
        news(s,'Promotion and relegation confirmed','; '.join(names[m['club']]+' '+m['kind'].lower() for m in data['movements'])+'. Membership changes when the next season is prepared.')
    data['closed']=True


def rollover(s):
    data=s['leagues']
    if data['legacy']:
        expand_world(s)
    else:
        from .simulation import require
        require(data['closed'],'Close the season before changing division membership.')
        members={d['id']:set(d['members']) for d in data['divisions']}
        for m in data['movements']:
            members[m['source']].remove(m['club']);members[m['target']].add(m['club'])
        for d in data['divisions']:d['members']=sorted(members[d['id']])
    prepare_order(s)


def snapshot(s):
    data=deepcopy(s['leagues'])
    data['tables']={d['id']:deepcopy(standings(s,d)) for d in data['divisions']}
    data['own_division']=division_for(s)['id']
    return data


def validate(s):
    from .simulation import require
    data=s['leagues'];ds=data['divisions'];known={c['id'] for c in s['clubs']}
    ids=[d['id'] for d in ds];members=[cid for d in ds for cid in d['members']]
    require([d['tier'] for d in ds]==list(range(1,len(ds)+1)),'Divisions must be ordered by unique tier.')
    require(len(ids)==len(set(ids)) and len(ds)>0,'Duplicate or missing division identity.')
    require(len(members)==len(set(members)) and set(members)==known,'Every club must belong to exactly one division.')
    require(type(data['exchange']) is int and data['exchange']>0,'Invalid promotion count.')
    for d in ds:
        n=len(d['members'])
        require(n>=4 and n%2==0 and len(d['prizes'])==n,'Invalid division size or prize schedule.')
        require(all(type(p) is int and p>=0 for p in d['prizes']),'Invalid league prize.')
        if data['legacy']:continue
        require(n>data['exchange'],'Not enough clubs for promotion and relegation.')
        require(set(data['draw_order'][d['id']])==set(d['members']) and len(data['draw_order'][d['id']])==n,'Invalid recorded league draw.')
        fs=[f for f in s['fixtures'] if f.get('division')==d['id']]
        pairs=[(f['home'],f['away']) for f in fs]
        expected={(a,b) for a in d['members'] for b in d['members'] if a!=b}
        require(len(pairs)==len(expected) and set(pairs)==expected,'Division fixtures must contain each ordered pairing once.')
        totals={cid:dict(played=0,won=0,drawn=0,lost=0,gf=0,ga=0,points=0) for cid in d['members']}
        for f in fs:
            if f['result'] is None:continue
            for side,cid in enumerate((f['home'],f['away'])):
                row=totals[cid];gf,ga=f['result']['score'][side],f['result']['score'][1-side]
                row['played']+=1;row['gf']+=gf;row['ga']+=ga
                row['won' if gf>ga else 'drawn' if gf==ga else 'lost']+=1
                row['points']+=3 if gf>ga else 1 if gf==ga else 0
        for c in s['clubs']:
            if c['id'] in totals:require(all(c[k]==v for k,v in totals[c['id']].items()),'Division table does not reconcile with played fixtures.')
    if not data['legacy']:
        require(all(f.get('knockout') or f.get('division') in ids for f in s['fixtures']),'Fixture references an unknown division.')
        require(not s['season_done'] or data['closed'],'Season must close its division tables.')
        if data['closed']:
            require(data['final_tables']=={d['id']:standings(s,d) for d in ds},'Frozen tables differ from completed results.')
            expected=[];count=data['exchange']
            for a,b in zip(ds,ds[1:]):
                expected.extend(dict(club=c['id'],source=a['id'],target=b['id'],kind='Relegated') for c in standings(s,a)[-count:])
                expected.extend(dict(club=c['id'],source=b['id'],target=a['id'],kind='Promoted') for c in standings(s,b)[:count])
            require(data['movements']==expected,'Promotion and relegation do not match final standings.')
