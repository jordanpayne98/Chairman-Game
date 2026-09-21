"""Persistent supporting pools beneath the national development pyramids.

Clubs use the existing detailed simulation at this milestone. They are excluded
from primary-cup entry while in the pool, but retain people, accounts and history.
"""
from copy import deepcopy
import json
from pathlib import Path


def definition(nation):
    from .simulation import require
    data=json.loads((Path(__file__).resolve().parent.parent/'data/feeders.json').read_text(encoding='utf-8'))
    require(nation in data['pools'],'No validated feeder pool is defined for this nation.')
    return dict(deepcopy(data['pools'][nation]),nation=nation,version=data['version'],
                initial_ability=data['initial_ability'],prize_percent=data['prize_percent'],
                content_status=data['content_status'])


def validate_definition(cfg,exchange):
    from .simulation import require
    clubs=cfg.get('clubs');ability=cfg.get('initial_ability')
    require(isinstance(clubs,list) and len(clubs)>=2*exchange and len(clubs)>=4 and len(clubs)%2==0,'Feeder pool needs an even, sufficient number of clubs.')
    require(all(isinstance(c,dict) and isinstance(c.get('name'),str) and c['name'].strip() and isinstance(c.get('city'),str) and c['city'].strip() for c in clubs),'Feeder club names and cities are required.')
    require(len({c['name'].casefold() for c in clubs})==len(clubs),'Feeder club names must be unique.')
    require(isinstance(ability,list) and len(ability)==2 and all(type(x) is int for x in ability) and 1<=ability[0]<=ability[1]<=100,'Invalid feeder ability bounds.')
    require(type(cfg.get('prize_percent')) is int and 0<=cfg['prize_percent']<=100,'Invalid feeder prize percentage.')
    require(isinstance(cfg.get('name'),str) and cfg['name'].strip(),'Feeder pool name is required.')


def initialise(s):
    """New careers only: resolve all entrants and their detail before scheduling."""
    from . import career,market,staff
    from .simulation import rng_for,require
    n=s['config']['nation'];cfg=definition(n['id']);validate_definition(cfg,n['exchange'])
    names={c['name'].casefold() for c in s['clubs']}
    require(not names & {c['name'].casefold() for c in cfg['clubs']},'Feeder names conflict with existing clubs.')
    require(not any(d.get('supporting') for d in s['leagues']['divisions']),'A feeder pool already exists.')
    offset=len(s['clubs']);members=[];added=[]
    for index,record in enumerate(cfg['clubs']):
        cid=f'c{offset+index}';record['id']=cid;members.append(cid)
        club=dict(id=cid,name=record['name'],city=record['city'],nation=n['id'],
                  played=0,won=0,drawn=0,lost=0,gf=0,ga=0,points=0,form=[])
        s['clubs'].append(club);added.append(club)
        for j,role in enumerate(['GK']*2+['DEF']*6+['MID']*6+['FWD']*4):
            key=f"feeder:{n['id']}:{cid}:{j}";rng=rng_for(s['seed'],key)
            p=career.new_person(s,role,rng.randint(19,29),rng.randint(*cfg['initial_ability']),key)
            p.update(club=cid,nationality=n['name'],homegrown=True);s['players'].append(p)
        s['registration'][cid]=[p['id'] for p in s['players'] if p['club']==cid]
    schema=s['schema'];market.initialise(s);s['schema']=schema;staff.add_club_staff(s,added)
    bottom=s['leagues']['divisions'][-1];size=len(members)
    # Interpolate the current lowest tier's prize curve, then apply the declared
    # supporting-tier percentage. Values remain development economy tuning.
    prizes=[bottom['prizes'][round(i*(len(bottom['prizes'])-1)/(size-1))]*cfg['prize_percent']//100 for i in range(size)]
    cfg['division']=n['id']+'-regional';cfg['parent']=bottom['id'];s['config']['feeder']=cfg
    s['leagues']['divisions'].append(dict(id=cfg['division'],name=cfg['name'],tier=bottom['tier']+1,
                                         members=members,prizes=prizes,supporting=True))


def validate(s):
    from .simulation import require
    ds=s['leagues']['divisions'];pools=[d for d in ds if d.get('supporting')];cfg=s['config'].get('feeder')
    require(all(type(d.get('supporting',False)) is bool for d in ds),'Invalid supporting-division flag.')
    if cfg is None:
        require(not pools,'Supporting division has no feeder definition.')
        return
    validate_definition(cfg,s['leagues']['exchange'])
    require(s.get('calendar') and cfg['nation']==s['config']['nation']['id'],'Feeder pool nation differs from the career.')
    require(len(pools)==1 and pools[0] is ds[-1] and pools[0]['id']==cfg['division'] and ds[-2]['id']==cfg['parent'],'Invalid feeder link to the lowest primary division.')
    require(pools[0]['name']==cfg['name'] and len(pools[0]['members'])==len(cfg['clubs']),'Feeder membership count or identity changed.')
    ids=[c.get('id') for c in cfg['clubs']];known={c['id']:c for c in s['clubs']}
    require(all(isinstance(cid,str) for cid in ids) and len(ids)==len(set(ids)) and set(ids)<=set(known),'Feeder entrants need unique persistent club identities.')
    require(all(known[c['id']]['name']==c['name'] and known[c['id']]['city']==c['city'] for c in cfg['clubs']),'Feeder club identity differs from the saved definition.')
    require(all(cid=='c0' or cid in s['market']['accounts'] for cid in known),'A club is missing its financial account.')
