"""Football attributes, uncertain observations and dated player development.

The four legacy keys remain intact for old match saves. `goalkeeping` is a
compatibility field, not a 38th displayed attribute. All new random draws use
their own identity stream; scouting never changes potential or match RNG.
"""
from copy import deepcopy
import math

GROUPS = {
    'Technical': ('passing', 'first_touch', 'technique', 'dribbling', 'finishing',
                  'long_shots', 'crossing', 'heading', 'tackling', 'marking', 'set_pieces'),
    'Mental': ('decisions', 'anticipation', 'vision', 'composure', 'concentration',
               'positioning', 'off_the_ball', 'teamwork', 'work_rate', 'determination', 'bravery'),
    'Physical': ('acceleration', 'pace', 'agility', 'balance', 'strength',
                 'jumping_reach', 'stamina', 'natural_fitness'),
    'Goalkeeping': ('reflexes', 'handling', 'aerial_command', 'one_on_ones',
                    'communication', 'distribution', 'rushing_out'),
}
ATTRIBUTES = tuple(k for keys in GROUPS.values() for k in keys)
BANDS = {-6: (60, 75), -7: (70, 85), -8: (80, 90), -9: (85, 95), -10: (90, 99)}
# Striker weights are from GDD 9. Other positional tables are explicit compact
# league calibration data, exposed for review in FORMULAS.md.
WEIGHTS = {
    'FWD': dict(finishing=.20, off_the_ball=.15, composure=.10, anticipation=.10,
                acceleration=.10, first_touch=.10, heading=.08, pace=.07, strength=.05, decisions=.05),
    'DEF': dict(tackling=.20, marking=.18, positioning=.15, anticipation=.10,
                heading=.10, strength=.08, concentration=.07, pace=.05, passing=.04, decisions=.03),
    'MID': dict(passing=.22, vision=.15, decisions=.13, first_touch=.12, technique=.10,
                teamwork=.08, stamina=.07, positioning=.05, tackling=.04, work_rate=.04),
    'GK': dict(reflexes=.23, handling=.20, one_on_ones=.15, aerial_command=.12,
               positioning=.10, communication=.07, distribution=.05, agility=.05, rushing_out=.03),
}
DEFAULTS = dict(recovery_base=4.0, recovery_fitness_factor=.05, weekly_growth=.30,
                intense_load=1.25, light_load=.6, decline_age=30, report_age_days=28,
                potential_review_days=91, potential_annual_limit=3)
HIDDEN = ('professionalism', 'adaptability', 'consistency', 'ambition', 'injury_susceptibility')


def overall(p, weights=None):
    weights = (weights or WEIGHTS)[p['role']]
    order=tuple(WEIGHTS[p['role']])+tuple(k for k in ATTRIBUTES if k not in WEIGHTS[p['role']])
    return max(1, min(100, int(sum(p['attrs'][k]*weights[k] for k in order if k in weights)+.5)))


def enrich(s, p):
    from .simulation import rng_for
    rng = rng_for(s['seed'], 'person-depth:' + p['id'])
    base = p['attrs'][{'GK': 'goalkeeping', 'DEF': 'tackling', 'MID': 'passing', 'FWD': 'finishing'}[p['role']]]
    for k in ATTRIBUTES:
        anchor = p['attrs']['goalkeeping'] if k in GROUPS['Goalkeeping'] else base
        if k in GROUPS['Goalkeeping'] and p['role'] != 'GK': anchor = 20
        p['attrs'].setdefault(k, float(max(1, min(100, anchor + rng.randint(-12, 12)))))
    p.setdefault('height', rng.randint(174, 199) if p['role'] == 'GK' else rng.randint(166, 196))
    p.setdefault('foot', 'Left' if rng.random() < .24 else 'Right')
    p.setdefault('nationality', 'England')
    p.setdefault('homegrown', True)  # Existing fictional league domestic background.
    p.setdefault('familiarity', {p['role']: 100})
    p.setdefault('condition', 100.0); p.setdefault('fatigue', 0.0)
    p.setdefault('sharpness', 70.0); p.setdefault('morale', 55.0)
    p.setdefault('hidden', {k: rng.randint(25, 85) for k in HIDDEN})
    rating = overall(p, s['config'].get('people', {}).get('weights'))
    p.setdefault('potential_code', -7 if p['youth'] else -6 if p['age']<24 else None)
    band = BANDS.get(p['potential_code'], (rating, min(100,rating+max(0,29-p['age']))))
    sampled = rng.randint(*band)
    p.setdefault('potential', max(rating, sampled))
    p.setdefault('peak_overall', rating)
    p.setdefault('development', dict(focus='Balanced', load='Normal', last_day=s['day'],
                                     minutes=0, last_review=s['day'], reviews=[], history=[]))
    p.setdefault('medical', None)
    p.setdefault('discipline', dict(yellows=0, ban=0))
    return p


def initialise(s):
    cfg = s['config'].setdefault('people', {})
    for k, v in DEFAULTS.items(): cfg.setdefault(k, v)
    cfg.setdefault('weights', deepcopy(WEIGHTS))
    for p in s['players']: enrich(s, p)


def report(s, p, source, radius):
    from .simulation import rng_for
    rng = rng_for(s['seed'], f"report:{p['id']}:{s['day']}")
    ranges = {}
    ordered=('passing','finishing','tackling','goalkeeping')
    ordered=ordered+tuple(k for k in ATTRIBUTES if k not in ordered)
    for k in ordered:
        if k not in p['attrs']:continue
        value=p['attrs'][k]
        estimate = max(1, min(100, round(value + rng.randint(-7, 7))))
        ranges[k] = [max(1, estimate-radius), min(100, estimate+radius)]
    result = dict(day=s['day'], source=source,
                  confidence='Moderate' if radius < 9 else 'Low', ranges=ranges)
    if 'potential' in p:
        weights = s['config']['people']['weights'][p['role']]
        result['overall'] = [max(1, min(100, round(math.fsum(ranges[k][i]*w for k,w in weights.items())))) for i in (0,1)]
        estimate = p['potential'] + rng.randint(-8, 8)
        uncertainty = radius + (9 if p['age'] < 21 else 4)
        result['potential'] = [max(1,min(100,estimate-uncertainty)), max(1,min(100,estimate+uncertainty))]
        result['role'] = p['role']
    return result


def observed_report(s, p):
    """Widen stored evidence with time, using public age only. No truth refresh."""
    r = deepcopy(s['reports'].get(p['id']))
    if not r: return None
    months = max(0, s['day']-r['day']) // s['config']['people']['report_age_days']
    width = min(20, months*(2 if p['age'] < 24 else 1))
    if width:
        for key, pair in r['ranges'].items(): r['ranges'][key] = [max(1,pair[0]-width), min(100,pair[1]+width)]
        for key in ('overall','potential'):
            if key in r: r[key] = [max(1,r[key][0]-width), min(100,r[key][1]+width)]
        r['confidence'] = 'Low'
    r['stale'] = bool(months)
    return r


def process_day(s):
    from .simulation import news
    cfg = s['config']['people']; day = s['day']; developed = []
    for p in s['players']:
        if p['retired']: continue
        d = p['development']; injured = p['injury_until'] > day
        medical = p['medical']
        if medical and not injured and medical['stage'] != 'available':
            medical['stage'] = 'conditioning' if p['condition'] < 85 else 'available'
            if medical['stage'] == 'available' and p['club'] == 'c0':
                news(s, 'Medical clearance', p['name'] + ' is available after rehabilitation and conditioning.')
        recovery = cfg['recovery_base'] + cfg['recovery_fitness_factor']*p['attrs']['natural_fitness']
        if 'staff' in s and p['club']:
            medical=[q for q in s['staff']['people'] if q['club']==p['club'] and q['role']=='Medical']
            if medical:recovery+=max(q['capabilities']['operations'] for q in medical)/100
        if d['load'] == 'Light': recovery += 2
        if d['load'] == 'Intense': recovery -= 2
        p['condition'] = round(min(100, p['condition']+recovery*(.45 if injured else 1)), 3)
        p['fatigue'] = round(max(0, p['fatigue']-recovery*.6), 3)
        if day % 7: continue
        rating = overall(p, cfg['weights']); before = rating
        if p['club'] and not injured:
            load = cfg['intense_load'] if d['load']=='Intense' else cfg['light_load'] if d['load']=='Light' else 1
            age = max(0, min(1.4, (29-p['age'])/10))
            coaching = s['career']['facilities']['training'] if p['club']=='c0' else 1
            minutes = min(1, d['minutes']/90)
            headroom = max(0, (p['potential']-rating)/20)
            growth = cfg['weekly_growth']*age*min(1,headroom)*load*(.5+p['hidden']['professionalism']/100)*(.65+minutes*.35)*(1+.06*coaching)
            if 'staff' in s:
                from .staff import capability
                growth*=1+(capability(s,p['club'],'coaching')-50)/250
            keys = GROUPS.get(d['focus'], ATTRIBUTES)
            for key in keys:
                p['attrs'][key] = round(min(100, p['attrs'][key]+growth), 4)
            if d['load']=='Intense': p['fatigue'] = min(100,p['fatigue']+3)
        if p['age'] > cfg['decline_age']:
            for key in GROUPS['Physical']:
                p['attrs'][key] = round(max(1, p['attrs'][key]-.012*(p['age']-cfg['decline_age'])), 4)
        rating = overall(p, cfg['weights'])
        p['potential'] = max(rating, p['potential']); p['peak_overall'] = max(rating,p['peak_overall'])
        d['history'].append(dict(day=day, overall=rating, minutes=d['minutes'], focus=d['focus'], load=d['load']))
        d['history'] = d['history'][-52:]
        if day-d['last_review'] >= cfg['potential_review_days']:
            recent = [h for h in d['history'] if day-h['day']<=91]
            annual = sum(abs(r['change']) for r in d['reviews'] if day-r['day']<365)
            change = 0
            if p['age']<24 and len(recent)>=10 and sum(h['minutes'] for h in recent)>=450 and recent[-1]['overall']>recent[0]['overall'] and p['hidden']['professionalism']>=65 and annual<cfg['potential_annual_limit']:
                change = min(1, 100-p['potential']); p['potential'] += change
            d['reviews'].append(dict(day=day,change=change)); d['reviews']=d['reviews'][-8:]; d['last_review']=day
        d['last_day']=day; d['minutes']=0
        if p['club']=='c0' and day%28==0:
            s['reports'][p['id']]=report(s,p,'Academy coaches' if p['youth'] else 'Coaching staff',9 if p['youth'] else 5)
            if rating>before: developed.append(p['name'])
    if day%28==0:
        news(s,'Player development review','Coaches refreshed squad estimates after the monthly review. Training load, minutes and recovery shape progress; potential remains uncertain.')


def apply(s, action, data):
    if action != 'development_plan': return None
    from .simulation import require
    from .career import person
    p=person(s,data.get('id'))
    require(p['club']=='c0' and not p['retired'] and s['match'] is None,'Set development plans for your players outside matchday.')
    focus=data.get('focus'); load=data.get('load')
    require(focus in ('Balanced',*GROUPS) and load in ('Light','Normal','Intense'),'Choose a valid focus and load.')
    p['development'].update(focus=focus,load=load)
    return 'Development plan saved. Progress is assessed weekly; extra load increases fatigue.'


def validate(s):
    from .simulation import require
    for role, weights in s['config']['people']['weights'].items():
        require(role in WEIGHTS and all(k in ATTRIBUTES and v>=0 for k,v in weights.items()) and abs(sum(weights.values())-1)<1e-8,'Invalid position weights.')
    for p in s['players']:
        require(all(k in p['attrs'] and math.isfinite(p['attrs'][k]) and 1<=p['attrs'][k]<=100 for k in ATTRIBUTES),'Invalid football attributes.')
        require(overall(p,s['config']['people']['weights'])<=p['potential']<=100,'Potential must cover current overall.')
        require(all(0<=p[k]<=100 for k in ('condition','fatigue','sharpness','morale')),'Invalid player condition.')
        require(p['discipline']['ban']>=0 and p['discipline']['yellows']>=0,'Invalid disciplinary record.')
