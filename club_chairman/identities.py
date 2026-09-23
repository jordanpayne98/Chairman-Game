"""Seeded, persisted names and nationality, independent of ability RNG streams."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((Path(__file__).resolve().parent.parent/'data/world_population.json').read_text(encoding='utf-8'))


def definition(s):
    return s['config'].get('world_population',catalogue())


def nation(s,key):
    data=definition(s)
    aliases={'Ireland':'ireland','United States':'usa','United States of America':'usa','Turkey':'turkiye'}
    key=aliases.get(key,key)
    return next((n for n in data['nations'] if key in (n['id'],n['name'])),None)


def make(s,key,nationality=None,domestic=None):
    from .simulation import rng_for
    data=definition(s);home=nation(s,domestic or s['config'].get('nation',{}).get('id','england'))
    rng=rng_for(s['seed'],'identity-v1:'+key)
    country=nation(s,nationality) if nationality else None
    if country is None:
        country=home if rng.random()<.88 else rng.choice(data['nations'])
    locale=rng.choices(country['locales'],weights=[x['weight'] for x in country['locales']])[0]['pool']
    pool=data['names'][locale];given=rng.choice(pool['given']);family=rng.choice(pool['family'])
    if pool['style']=='double_family':family+=' '+rng.choice(pool['family'])
    elif pool['style']=='given_family' and rng.random()<.3:
        middle=rng.choice(pool['given'])
        if middle!=given:given+=' '+middle
    name=family+' '+given if pool['style']=='family_given' else given+' '+family
    # Birthplace and citizenship are distinct. These are fictional content shares.
    born=home if home and rng.random()<.15 else country
    secondary=[born['id']] if born and born['id']!=country['id'] else []
    return dict(name=name,given_name=given,family_name=family,name_locale=locale,
                nationality=country['name'],nation_id=country['id'],nationalities=[country['id']]+secondary,
                birth_nation=born['id'] if born else country['id'],name_algorithm=data['name_algorithm'])


def stamp(s,p,domestic=None):
    p.update(make(s,p['id'],domestic=domestic))


def initialise(s):
    s['config'].setdefault('world_population',deepcopy(catalogue()))


def name_starting_people(s):
    home=s['config'].get('nation',{}).get('id','england')
    for p in s['players']:
        stamp(s,p,home)
        # Training eligibility is separate from a passport. Opening youth were
        # developed locally; foreign-born seniors may also be locally trained.
        if not p['youth'] and p['birth_nation']!=home:p['homegrown']=False
    for p in s['staff']['people']+s['managers']['people']:
        stamp(s,p,home)
        from .simulation import rng_for
        age=rng_for(s['seed'],'staff-age:'+p['id']).randint(30,59)
        p.update(age=age,birth_day=s['day']-age*365,lifecycle_year=s['day']//365,retired=False)
