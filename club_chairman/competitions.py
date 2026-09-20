"""Domestic knockout scheduling and advancement, independent of presentation.

The Northshire development cup shares domestic registration and player bans
across both divisions. Full national and continental calendars remain separate.
"""
from copy import deepcopy

DEFAULTS = dict(id='northshire-cup', name='Northshire Cup', round_days=[22, 50, 78],
                minimum_rest_days=3, winner_prize=0)


def initialise(s, legacy=False):
    cfg=s['config'].setdefault('cup',deepcopy(DEFAULTS))
    for key,value in DEFAULTS.items():cfg.setdefault(key,deepcopy(value))
    if 'competitions' not in s:
        s['competitions']={'cup':None}
        if not legacy:start_season(s)


def start_season(s):
    """Draw only the next known round; all possible dates are reserved up front."""
    from .simulation import require
    cfg=s['config']['cup'];members=sorted(c['id'] for c in s['clubs'])
    require(len(members)>=2,'A cup needs at least two entrants.')
    count=(len(members)-1).bit_length()
    require(s.get('calendar') or len(cfg['round_days'])>=count,'The cup calendar has too few round dates.')
    dates=list(s['calendar']['cup_days']) if s.get('calendar') else [s['career']['start']+d for d in cfg['round_days'][-count:]]
    require(all(type(d) is int for d in dates) and dates==sorted(set(dates)), 'Cup dates must be distinct and increasing.')
    require(all(b-a>=cfg['minimum_rest_days'] for a,b in zip(dates,dates[1:])), 'Cup rounds do not allow enough recovery.')
    require(all(abs(f['day']-day)>=cfg['minimum_rest_days'] for f in s['fixtures'] for day in dates), 'Cup dates conflict with league recovery time.')
    s['competitions']['cup']=dict(id=cfg['id'],name=cfg['name'],season=s['career']['season'],
        entrants=members,dates=dates,rounds=[],winner=None,prize=cfg['winner_prize'],settled=False)
    draw_round(s,members)


def round_label(number,total):
    left=total-number
    return 'Final' if left==1 else 'Semi-finals' if left==2 else 'Quarter-finals' if left==3 else f'Round {number+1}'


def draw_round(s,entrants):
    from .simulation import rng_for, news
    cup=s['competitions']['cup'];number=len(cup['rounds']);ids=sorted(entrants)
    rng_for(s['seed'],f"cup:{cup['id']}:{cup['season']}:{number}").shuffle(ids)
    # Byes reduce a non-power-of-two field to the next smaller power of two.
    byes=(1<<((len(ids)-1).bit_length()))-len(ids)
    exempt=ids[:byes];playing=ids[byes:];fixtures=[]
    label=round_label(number,len(cup['dates']))
    for i in range(0,len(playing),2):
        fid=f"s{cup['season']}-{cup['id']}-r{number+1}-{i//2}"
        s['fixtures'].append(dict(id=fid,day=cup['dates'][number],home=playing[i],away=playing[i+1],
            result=None,competition=cup['id'],competition_name=cup['name'],round=label,knockout=True))
        fixtures.append(fid)
    cup['rounds'].append(dict(label=label,day=cup['dates'][number],entrants=sorted(entrants),
        byes=exempt,fixtures=fixtures,advanced=None))
    s['fixtures'].sort(key=lambda f:(f['day'],f['id']))
    names={c['id']:c['name'] for c in s['clubs']}
    pairings=[names[playing[i]]+' v '+names[playing[i+1]] for i in range(0,len(playing),2)]
    news(s,cup['name']+' draw',label+': '+ '; '.join(pairings)+('. Byes: '+', '.join(names[c] for c in exempt) if exempt else '')+'.')


def progress(s):
    from .simulation import news, require
    from .market import post
    cup=s['competitions']['cup']
    if not cup or cup['settled']:return
    current=cup['rounds'][-1];by_id={f['id']:f for f in s['fixtures']}
    fixtures=[by_id[fid] for fid in current['fixtures']]
    if any(f['result'] is None for f in fixtures):return
    winners=[f['result'].get('winner') for f in fixtures]
    require(all(w in (f['home'],f['away']) for f,w in zip(fixtures,winners)), 'A knockout tie has no valid advancing club.')
    advanced=current['byes']+winners;current['advanced']=advanced
    if len(advanced)==1:
        cup['winner']=advanced[0]
        if cup['prize']:post(s,cup['winner'],f"cup:{cup['id']}:{cup['season']}:prize",cup['prize'],'Cup winner prize')
        cup['settled']=True
        name=next(c['name'] for c in s['clubs'] if c['id']==cup['winner'])
        news(s,cup['name']+' complete',name+' lift the trophy. The full draw and results remain in Competitions and season history.')
    else:draw_round(s,advanced)


def complete(s):
    cup=s['competitions']['cup']
    return cup is None or cup['settled']


def label(f):
    return f.get('competition_name','Northshire League')+(' / '+f['round'] if f.get('round') else '')


def result_text(f):
    r=f['result']
    if not r:return 'Scheduled'
    value='–'.join(map(str,r['score']))
    if any(r.get('kicks',[0,0])):value+=' (pens '+ '–'.join(map(str,r['shootout']))+')'
    elif r.get('knockout') and r.get('minute',0)>100:value+=' aet'
    if r.get('forfeit'):value+=' awarded'
    return value


def validate(s):
    from .simulation import require
    cup=s['competitions']['cup']
    known={c['id'] for c in s['clubs']};slots=set()
    for f in s['fixtures']:
        require(f['home'] in known and f['away'] in known and f['home']!=f['away'],'Invalid fixture participants.')
        for cid in (f['home'],f['away']):
            slot=(f['day'],cid)
            require(slot not in slots,'A club has overlapping fixtures.');slots.add(slot)
    if cup is None:return
    require(cup['season']==s['career']['season'],'Cup season does not match the career.')
    require(set(cup['entrants'])==known and len(cup['entrants'])==len(known),'Cup entrant membership is invalid.')
    require(type(cup['prize']) is int and cup['prize']>=0,'Invalid cup prize.')
    by_id={f['id']:f for f in s['fixtures']};previous=set(cup['entrants']);listed=[]
    require(1<=len(cup['rounds'])<=len(cup['dates']),'Invalid cup round count.')
    for index,r in enumerate(cup['rounds']):
        require(set(r['entrants'])==previous and len(r['entrants'])==len(previous),'Cup round entrants do not match qualifiers.')
        participants=list(r['byes']);advanced=list(r['byes'])
        for fid in r['fixtures']:
            require(fid in by_id,'Cup fixture is missing.');f=by_id[fid];listed.append(fid)
            require(f.get('competition')==cup['id'] and f.get('knockout') and f['day']==r['day']==cup['dates'][index],'Cup fixture has invalid rules or date.')
            participants.extend((f['home'],f['away']))
            if f['result'] is not None:
                winner=f['result'].get('winner');require(winner in (f['home'],f['away']),'Invalid knockout winner.');advanced.append(winner)
        require(len(participants)==len(set(participants)) and set(participants)==previous,'Duplicate or missing cup participant.')
        if r['advanced'] is not None:
            require(len(advanced)==len(r['byes'])+len(r['fixtures']) and r['advanced']==advanced,'Cup advancement does not reconcile.')
            previous=set(advanced)
        else:require(index==len(cup['rounds'])-1,'An unfinished round has successors.')
    require(len(listed)==len(set(listed)) and set(listed)=={f['id'] for f in s['fixtures'] if f.get('competition')==cup['id']},'Cup fixture graph is inconsistent.')
    if cup['settled']:
        require(cup['rounds'][-1]['advanced']==[cup['winner']],'Cup champion does not match the final.')
    else:require(cup['winner'] is None and cup['rounds'][-1]['advanced'] is None,'Unsettled cup has completed advancement.')
    require(not s['season_done'] or complete(s),'Season ended before the cup finished.')
