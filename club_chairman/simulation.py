"""Deterministic domain logic. Money is integer pence; no presentation imports."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
from . import career, market, commercial, clauses, people, registration, football, staff, delegation, club_ai, competitions, leagues, nations, shortlists, feeders, detail, managers, preparation, contract_terms, loan_clauses, transfer_rights, recruitment, reputation, playing_time, morale, relationships, dynamics, scouting, pathways, world_calendar, world_population, identities
from .football import finished as match_finished


@dataclass(frozen=True)
class Command:
    id: str
    revision: int
    action: str
    payload: dict
    actor: str = 'owner'
    scope: str = 'c0'
    responsibility: str = ''


def definition():
    return json.loads((Path(__file__).resolve().parent.parent / 'data/world.json').read_text())


def rng_for(seed, key):
    number = int.from_bytes(hashlib.sha256(f'{seed}:{key}'.encode()).digest()[:8], 'big')
    return random.Random(number)


def restore_rng(state):
    def tuples(value):
        return tuple(tuples(x) for x in value) if isinstance(value, list) else value
    rng = random.Random()
    rng.setstate(tuples(state))
    return rng


def new_career(seed=42,scenario='compact'):
    if type(seed) is not int or not 0 <= seed <= 999999:
        raise ValueError('Seed must be between 0 and 999999.')
    cfg = definition()
    rng = rng_for(seed, 'world')
    world = dict(schema=2, seed=seed, revision=0, day=0, config=cfg,
                 career_id=hashlib.sha256(f'preview:{seed}'.encode()).hexdigest()[:12],
                 cash=cfg['opening_cash'], owner_cash=cfg['owner_cash'],
                 budget=cfg['weekly_budget'], tickets=cfg['ticket_price'], manager=None,
                 trust=60, morale=55, supporters=60, clubs=[], players=[], reports={},
                 scouting={}, fixtures=[], ledger=[], inbox=[], receipts={},
                 decision=None, match=None, season_done=False, transfer_spend=0, accrued_costs=0,
                 planning=dict(shortlist=[], comparison=[], notes={}, inbox_read=0))
    first = ['Daniel', 'Lewis', 'Oliver', 'Marcus', 'Jamie', 'Callum', 'Ethan', 'Noah', 'Theo', 'Ben', 'Isaac', 'Alex', 'Max', 'Owen', 'Sam', 'Ryan', 'Leon', 'Adam']
    last = ['Mercer', 'Reed', 'Hughes', 'Turner', 'Clarke', 'Shaw', 'Bennett', 'Price', 'Ward', 'Evans', 'Foster', 'Hayes', 'Brooks', 'Baker', 'Palmer', 'Collins', 'Morgan', 'Ellis']
    roles = ['GK'] * 2 + ['DEF'] * 6 + ['MID'] * 6 + ['FWD'] * 4
    for i, name in enumerate(cfg['clubs']):
        world['clubs'].append(dict(id=f'c{i}', name=name, played=0, won=0, drawn=0, lost=0, gf=0, ga=0, points=0, form=[]))
    for i in range(8 * 18 + 12):
        club = f'c{i // 18}' if i < 144 else None
        role = roles[i % 18] if club else ['GK', 'DEF', 'MID', 'FWD'][i % 4]
        level = rng.randint(40, 68) if club else rng.randint(40, 78)
        attrs = {key: max(1, min(100, level + rng.randint(-10, 10))) for key in ['passing', 'finishing', 'tackling', 'goalkeeping']}
        if role == 'GK': attrs['goalkeeping'] = level
        p = dict(id=f'p{i}', name=f'{first[i % 18]} {last[(i // 18 + i) % 18]}', club=club, role=role,
                 age=rng.randint(19, 32), attrs=attrs, wage=(450 + level * 13) * 100,
                 fee=(3000 + level * 350) * 100, goals=0, appearances=0,
                 contract_end=96 if club else None)
        world['players'].append(p)
        if club == 'c0': world['reports'][p['id']] = make_report(world, p, 'Coaching staff', 5)
    ring = list(range(8))
    pairings = []
    for round_no in range(7):
        pairs = [(ring[j], ring[-1-j]) for j in range(4)]
        pairings.append([(b,a) if round_no % 2 else (a,b) for a,b in pairs])
        ring = [ring[0], ring[-1]] + ring[1:-1]
    for rnd in range(14):
        for j, (a,b) in enumerate(pairings[rnd % 7]):
            if rnd >= 7: a,b = b,a
            world['fixtures'].append(dict(id=f'f{rnd}-{j}', day=5+rnd*7, home=f'c{a}', away=f'c{b}', result=None))
    career.initialise(world)
    market.initialise(world)
    commercial.initialise(world)
    clauses.initialise(world)
    people.initialise(world);registration.initialise(world);football.initialise(world)
    pathways.initialise(world);pathways.seed_groups(world)
    staff.initialise(world);delegation.initialise(world);club_ai.initialise(world)
    competitions.initialise(world,legacy=True)
    leagues.initialise(world)
    world['calendar']=None
    if scenario!='compact':nations.configure(world,scenario)
    competitions.start_season(world)
    shortlists.initialise(world)
    detail.initialise(world)
    managers.initialise(world)
    contract_terms.initialise(world)
    transfer_rights.initialise(world)
    preparation.initialise(world)
    recruitment.initialise(world)
    reputation.initialise(world)
    playing_time.initialise(world)
    morale.initialise(world)
    relationships.initialise(world)
    dynamics.initialise(world)
    world_calendar.initialise(world)
    pathways.sync(world);pathways.schedule(world);scouting.initialise(world)
    world['config']['club_ai']['payroll_income_percent']=100
    world_population.initialise(world)
    identities.name_starting_people(world)
    world['schema']=29
    for p in world['players']:
        if p['club']:p['contract_end']=career.contractual_end(world,3)
        if p['club']=='c0':world['reports'][p['id']]=make_report(world,p,'Coaching staff',5)
    if world['calendar']:
        news(world,'National development scenario',f"{world['config']['nation']['name']}: one active national pyramid. Club identities, squads and finances are provisional content; an eight-club feeder pool exchanges clubs with the lowest primary tier. Continental competitions are pending.")
    news(world, 'Welcome to Northbridge', 'Appoint a manager, review your wage budget, and request scouting before the first match. Review your divisions and domestic cup under Competitions.')
    return world


def make_report(s, p, source='Recruitment analyst', radius=9, complete=False):
    if source=='Recruitment analyst' and 'staff' in s:
        radius=max(4,round(radius*(1-(staff.capability(s,'c0','ability_assessment')-50)/150)))
    return people.report(s,p,source,radius,complete=complete)


def news(s, title, body):
    s['inbox'].append(dict(day=s['day'], title=title, body=body))


def posting(s, key, amount, reason):
    if any(x['id'] == key for x in s['ledger']): return
    s['cash'] += amount
    s['ledger'].append(dict(id=key, day=s['day'], amount=amount, reason=reason,
                            debit='cash' if amount > 0 else reason,
                            credit=reason if amount > 0 else 'cash', balance=s['cash']))


def payroll(s):
    return market.club_payroll(s,'c0') if 'market' in s else sum(p['wage'] for p in s['players'] if p['club']=='c0')+(s['manager']['wage'] if s['manager'] else 0)


def table(s):
    return leagues.standings(s)


def calendar_date(s, day=None):
    return (date.fromisoformat(s['config']['start_date']) + timedelta(days=s['day'] if day is None else day)).strftime('%d %b %Y')


MANAGERS = managers.CANDIDATES


def require(condition, message):
    if not condition: raise ValueError(message)


def execute(state, command):
    """Copy-on-commit: invalid commands cannot leave partial state changes."""
    if command.id in state['receipts']:
        prior = state['receipts'][command.id]
        require(prior['action'] == command.action and prior['payload'] == command.payload, 'Command ID reused for different work.')
        return state, prior['message']
    require(command.revision == state['revision'], 'The career changed. Review and try again.')
    require(command.scope=='c0','This action is outside your authority.')
    s = deepcopy(state)
    prior_clubs={p['id']:p['club'] for p in s['players'] if not p['youth']}
    if command.actor=='owner':message=apply(s,command.action,command.payload)
    else:
        rule=s['delegation']['responsibilities'].get(command.responsibility)
        require(rule and rule['delegate']==command.actor,'This action is outside your authority.')
        message=delegation.perform(s,command.responsibility,command.action,command.payload,'Authorised staff command.')
    pathways.sync(s);scouting.record_signings(s,prior_clubs)
    dynamics.sync(s)
    registration.sync(s,prior_clubs)
    delegation.reconcile(s)
    recruitment.sync(s)
    reputation.sync(s)
    playing_time.reconcile(s)
    if not s['match'] or s['match']['settled']:
        reputation.review(s)
        playing_time.review(s)
        relationships.process(s)
        morale.reconcile(s)
    s['revision'] += 1
    s['receipts'][command.id] = dict(action=command.action, payload=deepcopy(command.payload), message=message)
    validate(s)
    return s, message


def apply(s, action, payload):
    for module in (world_population,scouting,pathways):
        result=module.apply(s,action,payload)
        if result is not None:return result
    result=dynamics.apply(s,action,payload)
    if result is not None:return result
    result=relationships.apply(s,action,payload)
    if result is not None:return result
    result=playing_time.apply(s,action,payload)
    if result is not None:return result
    result=transfer_rights.apply(s,action,payload)
    if result is not None:return result
    result=loan_clauses.apply(s,action,payload)
    if result is not None:return result
    cfg = s['config']
    result=managers.apply(s,action,payload)
    if result is not None:return result
    result=staff.apply(s,action,payload)
    if result is not None:return result
    result=delegation.apply(s,action,payload)
    if result is not None:return result
    result=people.apply(s,action,payload)
    if result is not None:return result
    result=registration.apply(s,action,payload)
    if result is not None:return result
    result=clauses.apply(s,action,payload)
    if result is not None:return result
    result=market.apply(s,action,payload)
    if result is not None:return result
    result=commercial.apply(s,action,payload)
    if result is not None:return result
    result=career.apply(s,action,payload)
    if result is not None:return result
    if action == 'shortlist_manage':return shortlists.apply(s,payload)
    if action == 'planning':
        key = payload.get('key'); value = payload.get('value')
        known = {p['id'] for p in s['players']}
        require(key in ('shortlist', 'comparison', 'notes', 'inbox_read', 'shortlists'), 'Unknown planning record.')
        if key=='shortlists':
            shortlists.restore(s,value)
            return 'Shortlist change undone. Time and money are unchanged.'
        if key in ('shortlist', 'comparison'):
            require(isinstance(value, list) and all(isinstance(x, str) for x in value), 'Invalid player selection.')
            require(len(value) == len(set(value)) and set(value) <= known, 'Select known players only.')
            require(len(value) <= (4 if key == 'comparison' else len(known)), 'Compare up to four players.')
        elif key == 'notes':
            require(isinstance(value, dict) and set(value) <= known and all(isinstance(n, str) and len(n) <= 240 for n in value.values()), 'Notes must be 240 characters or fewer.')
        else:
            require(type(value) is int and 0 <= value <= len(s['inbox']), 'Invalid read marker.')
        s['planning'][key] = deepcopy(value)
        if key=='shortlist':shortlists.active(s['planning'])['players']=list(value)
        return 'Planning saved. Time and money are unchanged.'
    if action == 'hire':
        require(not s['season_done'] and s['match'] is None, 'Appointments are unavailable during a match or after season end.')
        require(s['manager'] is None, 'A manager is already appointed for this preview season.')
        m = managers.candidate(s,payload.get('id'))
        require(m is not None, 'Unknown candidate.')
        require(payroll(s) + m['wage'] + career.reservations(s)[1] <= s['budget'], 'Increase the weekly wage budget first.')
        require(career.free_cash(s,m['fee']), 'Insufficient available cash.')
        s['manager'] = dict(deepcopy(m),contract_end=career.contractual_end(s,3),notice_weeks=cfg['career']['manager_notice_weeks'])
        preparation.appoint(s)
        posting(s, f"hire:{m['id']}:{s['revision']}", -m['fee'], 'Manager signing fee')
        news(s, 'Manager appointed', f"{m['name']} takes charge. Weekly salary: £{m['wage']//100:,}. Selection and tactics are delegated to the manager.")
        return 'Manager appointed. Football decisions are delegated.'
    if action == 'budget':
        value = payload.get('value')
        require(type(value) is int and 1500000 <= value <= 4000000, 'Weekly wage budget must be £15,000–£40,000.')
        require(value >= payroll(s)+career.reservations(s)[1], 'Budget cannot be below existing wage commitments.')
        s['budget'] = value
        return 'Wage budget updated. This changes authority, not cash.'
    if action == 'tickets':
        value = payload.get('value')
        require(type(value) is int and 1000 <= value <= 3000, 'Ticket price must be £10–£30.')
        require(s['match'] is None, 'Ticket prices are locked during matchday.')
        s['tickets'] = value
        return 'Ticket price updated for future home fixtures.'
    if action == 'sign':
        raise ValueError('Open Contracts: agree terms, review the medical and confirm completion. Instant signing is no longer available.')
    if action == 'scout':
        require(not s['season_done'] and s['match'] is None, 'Recruitment is closed during matchday or after season end.')
        job=scouting.commission(s,payload.get('id'))
        return f"Scouting commissioned. Report due day {job['due']}."
    if action == 'fund':
        amount = 5000000
        require(s['owner_cash'] >= amount, 'Owner funds are insufficient.')
        s['owner_cash'] -= amount
        posting(s, f"equity:{s['revision']}", amount, 'Owner equity injection')
        clauses.settle_payables(s)
        return '£50,000 moved from owner funds to club equity.'
    if action == 'decision':
        require(s['decision'] is not None, 'No decision is pending.')
        d = s['decision']; choice = payload.get('choice')
        require(choice in ('approve','decline'), 'Choose approve or decline.')
        if choice == 'approve':
            require(career.free_cash(s,d['cost']), 'Insufficient available cash. You may decline or fund the club.')
            posting(s, d['id'], -d['cost'], d['title'])
            s['morale'] = min(100,s['morale']+d['morale'])
            s['supporters'] = min(100,s['supporters']+d['supporters'])
            s['trust'] = min(100,s['trust']+4)
        news(s, d['title'], 'Approved and paid.' if choice == 'approve' else 'Declined. The club retains the cash.')
        s['decision'] = None
        return 'Decision recorded.'
    if action == 'continue':
        require(not s['season_done'], 'Season complete. Open Career to prepare the next season.')
        require(s['manager'] is not None, 'Appoint a manager in Staff before continuing.')
        require(s['decision'] is None, 'Resolve the pending chairman decision first.')
        require(s['match'] is None, 'Finish the current match first.')
        # Advance one committed day at a time. UI offers bounded batching to next fixture.
        tomorrow = s['day'] + 1
        s['day']=tomorrow
        previous_clubs={p['id']:p['club'] for p in s['players'] if not p['youth']}
        commercial.process_day(s)
        if tomorrow % 7 == 0:
            posting(s, f'sponsor:{tomorrow}', cfg['weekly_sponsor'], 'Weekly sponsorship')
        market.process_day(s)
        career.process_day(s)
        world_population.process_day(s)
        staff.process_day(s)
        pathways.process_day(s)
        people.process_day(s)
        preparation.process_day(s)
        dynamics.process_day(s)
        club_ai.process_day(s)
        registration.sync(s,previous_clubs)
        market.accrue_accounts(s)
        if tomorrow % 7 == 0:
            due = (s['accrued_costs'] + payroll(s) + cfg['weekly_overheads']) // 7
            require(s['cash'] >= due, 'Payroll shortfall: inject owner funds before Continue. No unpaid day has advanced.')
        s['day'] = tomorrow
        s['accrued_costs'] += payroll(s) + cfg['weekly_overheads']
        if tomorrow % 7 == 0:
            posting(s, f'payroll:{tomorrow}', -(s['accrued_costs']//7), 'Accrued payroll and operations')
            s['accrued_costs'] %= 7
        clauses.settle_payables(s)
        scouting.process_day(s)
        season_day=tomorrow-s['career']['start']
        if season_day in (3,24,45,66):
            s['decision'] = dict(id=f'decision:{tomorrow}', title='Community open day' if season_day in (3,45) else 'Manager preparation camp',
                cost=150000 if season_day in (3,45) else 350000, morale=2 if season_day in (3,45) else 7,
                supporters=7 if season_day in (3,45) else 1)
            news(s, 'Chairman decision required', s['decision']['title'])
        delegation.process_day(s)
        playing_time.reconcile(s)
        playing_time.review(s)
        relationships.process(s)
        morale.reconcile(s)
        fixtures = [f for f in s['fixtures'] if f['day']==tomorrow]
        if fixtures:
            require(s['manager'] is not None,'Appoint a manager before the fixture.')
            own = next((f for f in fixtures if 'c0' in (f['home'],f['away'])),None)
            if own is None:
                settle_background(s)
                competitions.progress(s)
                close_season(s)
                return 'Other clubs’ fixtures completed. Results are available in Competitions.'
            s['match'] = start_match(s, own)
            if match_finished(s['match']):settle_matchday(s)
            return 'Matchday ready. Open Matchday to watch or skip.'
        return f"Advanced to {calendar_date(s)}."
    if action in ('match_step','match_skip'):
        require(s['match'] is not None and not match_finished(s['match']), 'No active match.')
        count=300 if action=='match_skip' else payload.get('minutes',1)
        require(type(count) is int and 1<=count<=300, 'Invalid match step.')
        for _ in range(count):
            if match_finished(s['match']): break
            step_match(s, s['match'])
        if match_finished(s['match']): settle_matchday(s)
        return 'Full time. Review the match.' if match_finished(s['match']) else 'Match progressed.'
    if action == 'intervene':
        m=s['match']
        require(m is not None and not match_finished(m), 'No live match.')
        require(not m['intervened'], 'The manager has already received your message this match.')
        require(payload.get('choice') in ('encourage','attack'), 'Unknown bench message.')
        m['intervened']=True
        rng=restore_rng(m['rng'])
        own=0 if m['home']=='c0' else 1
        if payload['choice']=='encourage':
            s['trust']=min(100,s['trust']+3)
            s['morale']=min(100,s['morale']+2)
            response='Manager: Thank you for the backing. We will keep to our plan.'
        else:
            accept=rng.random() < max(.15,min(.85,.65-s['manager']['autonomy']*.3+(s['trust']-50)/200))
            if accept:
                m['risk'][own]=1.3
                if 'manager_plan' in m:m['owner_instruction']='attack'
                response='Manager: We will push higher. That will leave space behind us.'
            else:
                response='Manager: I disagree. We are sticking to our approach.'
            s['trust']=max(0,s['trust']-4)
        dynamics.bench_event(s,m,payload['choice'],response)
        m['events'].append(dict(minute=m['minute'],text=response,kind='bench'))
        m['rng']=rng.getstate()
        return response
    if action == 'match_close':
        require(s['match'] is not None and match_finished(s['match']), 'Finish the match first.')
        s['match']=None
        return 'Match review closed.'
    raise ValueError('Unknown command.')


def select_lineup(s, club):
    pool=[p for p in s['players'] if p['club']==club and not p['youth'] and not p['retired']]
    chosen=[]
    for role,n in [('GK',1),('DEF',4),('MID',4),('FWD',2)]:
        key={'GK':'goalkeeping','DEF':'tackling','MID':'passing','FWD':'finishing'}[role]
        chosen += sorted((p for p in pool if p['role']==role),key=lambda p:(p['injury_until']>s['day'],-p['attrs'][key],p['id']))[:n]
    selected={p['id'] for p in chosen}
    chosen+=sorted((p for p in pool if p['id'] not in selected),key=lambda p:(p['injury_until']>s['day'],-p['attrs']['passing'],p['id']))[:max(0,11-len(chosen))]
    return [p['id'] for p in chosen]


def start_match(s,f):
    return football.start(s,f)


def legacy_start_match(s,f):
    return dict(fixture=f['id'],home=f['home'],away=f['away'],minute=0,score=[0,0],shots=[0,0],on_target=[0,0],xg=[0.,0.],
                possession=[0,0],risk=[(1.12 if s['manager']['style']=='Attacking' else .92 if s['manager']['style']=='Cautious' else 1.) if cid=='c0' and s['manager'] else 1. for cid in (f['home'],f['away'])],intervened=False,settled=False,
                lineups=[select_lineup(s,f['home']),select_lineup(s,f['away'])],events=[],
                rng=rng_for(s['seed'],f['id']).getstate())


def step_match(s,m):
    if m.get('engine')==2:return football.step(s,m)
    rng=restore_rng(m['rng']); m['minute']+=1
    people={p['id']:p for p in s['players']}
    teams=[[people[pid] for pid in lineup] for lineup in m['lineups']]
    strengths=[]
    for i,players in enumerate(teams):
        club=m['home'] if i==0 else m['away']
        skill=s['manager']['skill'] if club=='c0' else 62
        strengths.append(sum(p['attrs']['passing'] for p in players)/11+(skill-60)*.2+(s['morale']-50)*.08*(club=='c0'))
    edge=strengths[0]-strengths[1]+s['config']['home_advantage']
    side=0 if rng.random()<1/(1+math.exp(-edge/s['config']['action_scale'])) else 1
    other=1-side
    m['possession'][side]+=1
    if rng.random()<s['config']['shot_rate'] * m['risk'][side] * m['risk'][other]:
        attackers=[p for p in teams[side] if p['role'] in ('MID','FWD')] or teams[side][1:]
        shooter=rng.choice(attackers)
        keeper=next((p for p in teams[other] if p['role']=='GK'),teams[other][0])
        xg=rng.uniform(.04,.26)
        chance=max(.02,min(.98,xg+(shooter['attrs']['finishing']-keeper['attrs']['goalkeeping'])/600))
        m['shots'][side]+=1; m['xg'][side]+=xg
        goal=rng.random()<chance
        target=goal or rng.random()<.35
        if target:m['on_target'][side]+=1
        if goal:
            m['score'][side]+=1;shooter['goals']+=1
            text=f"GOAL — {shooter['name']} finishes for {s['clubs'][int((m['home'] if side==0 else m['away'])[1:])]['name']}."
        else: text=f"{shooter['name']}: {'saved by the goalkeeper' if target else 'shot off target'}."
        m['events'].append(dict(minute=m['minute'],text=text,kind='goal' if goal else 'shot',player=shooter['id']))
    if m['minute'] in (45,90):m['events'].append(dict(minute=m['minute'],text='Half time' if m['minute']==45 else 'Full time',kind='period'))
    m['rng']=rng.getstate()


def record_result(s,m):
    f=next(f for f in s['fixtures'] if f['id']==m['fixture'])
    if f['result'] is not None:return
    reputation.collect(s,m)
    playing_time.collect(s,m)
    morale.collect(s,m)
    loan_clauses.record_match(s,m)
    clauses.record_match(s,m)
    if m.get('engine')==2:
        football.settle_players(s,m)
        preparation.settle(s,m)
        dynamics.settle(s,m)
    f['result']=football.public_match(m) if m.get('engine')==2 else deepcopy({k:m[k] for k in ('score','events','shots','on_target','xg','possession','lineups')})
    for side,cid in enumerate([m['home'],m['away']]):
        c=next(c for c in s['clubs'] if c['id']==cid);gf,ga=m['score'][side],m['score'][1-side]
        if not f.get('knockout'):
            c['played']+=1;c['gf']+=gf;c['ga']+=ga
            key='won' if gf>ga else 'drawn' if gf==ga else 'lost'
            c[key]+=1;c['points']+=3 if gf>ga else 1 if gf==ga else 0
            c['form'].append('W' if gf>ga else 'D' if gf==ga else 'L')
        for pid in m.get('participants',m['lineups'])[side]:next(p for p in s['players'] if p['id']==pid)['appearances']+=1


def settle_matchday(s):
    m=s['match']
    if m['settled']:return
    record_result(s,m)
    settle_background(s,legacy=m.get('engine')!=2)
    own=0 if m['home']=='c0' else 1
    difference=m['score'][own]-m['score'][1-own]
    s['morale']=max(10,min(95,s['morale']+(4 if difference>0 else -3 if difference<0 else 0)))
    s['supporters']=max(5,min(95,s['supporters']+(3 if difference>0 else -2 if difference<0 else 0)))
    if own==0:
        attendance=min(career.available_capacity(s),max(0,round((3800+s['supporters']*15)*(1800/s['tickets']))))
        posting(s,f"gate:{m['fixture']}",attendance*s['tickets'],'Match tickets')
        news(s,'Home attendance',f'{attendance:,} supporters paid £{s["tickets"]/100:.2f}.')
    news(s,'Match result',f"{s['clubs'][int(m['home'][1:])]['name']} {m['score'][0]}–{m['score'][1]} {s['clubs'][int(m['away'][1:])]['name']}")
    m['settled']=True
    competitions.progress(s)
    close_season(s)
    clauses.settle_payables(s)


def settle_background(s,legacy=False):
    for f in list(s['fixtures']):
        if f['day']==s['day'] and f['result'] is None:
            other=legacy_start_match(s,f) if legacy else start_match(s,f)
            while not match_finished(other):step_match(s,other)
            record_result(s,other)


def close_season(s):
    if not s['season_done'] and competitions.complete(s) and all(f['result'] is not None for f in s['fixtures']):
        leagues.close(s)
        reputation.close_season(s)
        position=next(i for i,c in enumerate(table(s)) if c['id']=='c0')
        prefix='season' if s['career']['season']==1 else f"season:{s['career']['season']}"
        posting(s,prefix+':prize',leagues.division_for(s)['prizes'][position],'League prize')
        # Settle the final part-week of wages and overheads through the last match.
        posting(s,prefix+':final-payroll',-(s['accrued_costs']//7),'Final pro-rata payroll and operations')
        s['accrued_costs']=0
        s['season_done']=True
        news(s,'Season complete',f'Northbridge finished {position+1} of {len(table(s))} in {leagues.division_for(s)['name']}. Review the table and finances. Open Career to review contracts, preserve this season’s history and prepare the next campaign.')
    clauses.settle_payables(s)


def validate(s):
    require(s.get('schema')==29,'Unsupported save schema. This build supports schema 29.')
    scouting.validate(s);pathways.validate(s);world_calendar.validate(s);world_population.validate(s)
    recruitment.validate(s)
    reputation.validate(s)
    playing_time.validate(s)
    morale.validate(s)
    relationships.validate(s)
    dynamics.validate(s)
    leagues.validate(s)
    feeders.validate(s)
    detail.validate(s)
    nations.validate(s)
    competitions.validate(s)
    managers.validate(s)
    preparation.validate(s)
    staff.validate(s);delegation.validate(s);club_ai.validate(s)
    people.validate(s);registration.validate(s)
    clauses.validate(s)
    market.validate(s)
    commercial.validate(s)
    require(type(s['cash']) is int and type(s['owner_cash']) is int,'Invalid cash data.')
    require(s['cash']==s['config']['opening_cash']+sum(x['amount'] for x in s['ledger']),'Cash does not reconcile with the ledger.')
    require(len({x['id'] for x in s['ledger']})==len(s['ledger']),'Duplicate financial posting.')
    require(s['owner_cash']>=0,'Owner funds cannot be negative.')
    require(len({p['id'] for p in s['players']})==len(s['players']),'Duplicate player identity.')
    require(all(c['played']==c['won']+c['drawn']+c['lost'] for c in s['clubs']),'League results do not reconcile.')
    require(all(c['points']==3*c['won']+c['drawn'] for c in s['clubs']),'League points do not reconcile.')
    require(type(s['career']['season']) is int and s['career']['season']>=1,'Invalid season number.')
    require(len({f['id'] for f in s['fixtures']})==len(s['fixtures']),'Duplicate fixture identity.')
    require(all(p['wage']>=0 and type(p['wage']) is int for p in s['players']),'Invalid wages.')
    require(all(p['status'] in ('feasibility','quoted','construction','operational','cancelled') for p in s['career']['projects']),'Invalid project status.')
    known = {p['id'] for p in s['players']}
    plan = s['planning']
    shortlists.validate(s)
    for key, limit in (('shortlist', len(known)), ('comparison', 4)):
        require(isinstance(plan[key], list) and all(isinstance(x, str) for x in plan[key]), 'Invalid saved planning selection.')
        require(len(plan[key]) <= limit and len(plan[key]) == len(set(plan[key])) and set(plan[key]) <= known, 'Invalid saved planning selection.')
    require(isinstance(plan['notes'], dict) and set(plan['notes']) <= known and all(isinstance(n, str) and len(n) <= 240 for n in plan['notes'].values()), 'Invalid saved notes.')
    require(type(plan['inbox_read']) is int and 0 <= plan['inbox_read'] <= len(s['inbox']), 'Invalid saved read marker.')


def view(s):
    """Authorised UI snapshot. Hidden traits, true potential and RNG stay private."""
    players=[]
    for p in s['players']:
        row={k:p[k] for k in ('id','name','club','role','age','wage','fee','goals','appearances','contract_end','youth','retired','career_goals','career_appearances')}
        row['report']=people.observed_report(s,p)
        row['retirement']=deepcopy(p.get('retirement'))
        row.update({k:deepcopy(p[k]) for k in ('height','foot','nationality','homegrown','condition','fatigue','sharpness','morale','medical','discipline')})
        if p['club']!='c0':
            for key in ('condition','fatigue','sharpness','morale','medical'):row[key]=None
        upcoming=next((f for f in s['fixtures'] if 'c0' in (f['home'],f['away']) and f['result'] is None),None)
        opponent=(upcoming['away'] if upcoming['home']=='c0' else upcoming['home']) if upcoming else None
        row['availability']='Retired' if p['retired'] else registration.reason(s,p,'c0',opponent) if p['club']=='c0' else 'Free agent' if p['club'] is None else 'Not assessed by your staff'
        row['development']={k:deepcopy(p['development'][k]) for k in ('focus','load','last_day')} if p['club']=='c0' else None
        row['scout_due']=s['scouting'].get(p['id'])
        row['scout_quote']=scouting.quote(s,p) if p['club']!='c0' and not p['youth'] and not p['retired'] else None
        employment=s['clauses']['employment'].get(p['id'],{})
        row['buyout_amount']=employment.get('release_fee',0) if employment.get('release_kind')=='buyout' and employment['employer']==p['club'] and s['day']<=employment['end'] else 0
        row['transfer_quote']=market.quote(s,p) if p['club'] not in (None,'c0') else 0
        row['loan']=deepcopy(market.active_loan(s,p['id']))
        players.append(row)
    m=None if s['match'] is None else football.public_match(s['match'])
    snapshot = dict(revision=s['revision'],date=calendar_date(s),day=s['day'],start_date=s['config']['start_date'],cash=s['cash'],owner_cash=s['owner_cash'],budget=s['budget'],
                payroll=payroll(s),tickets=s['tickets'],manager=managers.view(s,s['manager']) if s['manager'] else None,manager_candidates=[managers.view(s,p) for p in s['managers']['people']],trust=s['trust'],morale=s['morale'],supporters=s['supporters'],
                players=players,table=deepcopy(table(s)),clubs=deepcopy(s['clubs']),fixtures=deepcopy(s['fixtures']),
                ledger=deepcopy(s['ledger']),inbox=deepcopy(s['inbox']),decision=deepcopy(s['decision']),match=m,
                season_done=s['season_done'],seed=s['seed'],transfer_spend=s['transfer_spend'],planning=deepcopy(s['planning']),
                terms={k:s['config'][k] for k in ('scout_fee','scout_days','operating_buffer','weekly_overheads','weekly_sponsor','capacity')},
                accrued_costs=s['accrued_costs'],season_end=career.season_end(s),
                public_players={p['id']:{k:p[k] for k in ('name','role')} for p in s['players']},
                season=s['career']['season'],season_start=s['career']['start'],window_end=career.window_end(s),
                career=deepcopy(s['career']),reserved_cash=career.reservations(s)[0],reserved_wages=career.reservations(s)[1],
                preparation=preparation.view(s),severance=career.manager_severance(s),career_settings=deepcopy(s['config']['career']),project_specs=deepcopy(s['config']['projects']))
    snapshot['scouting_work']=scouting.public(s)
    snapshot['pathways']=pathways.public(s)
    snapshot['world_calendar']=world_calendar.public(s)
    snapshot['world_population']=world_population.public_summary(s)
    snapshot['playing_time']=playing_time.public(s)
    snapshot['mood']=morale.public(s)
    snapshot['relationships']=relationships.public(s)
    snapshot['dynamics']=dynamics.public(s)
    snapshot['reputation']=reputation.public(s)
    snapshot['reputation_coverage']=dict(start=s['reputation_progress']['start'],next_review=s['reputation_progress']['next_review'])
    snapshot['detail']=detail.snapshot(s)
    snapshot['calendar']=deepcopy(s.get('calendar'))
    snapshot['nation']=deepcopy(s['config'].get('nation'))
    snapshot['contract_ends']={str(n):career.contractual_end(s,n) for n in (1,2,3)}
    snapshot['leagues']=leagues.snapshot(s)
    snapshot['competitions']=deepcopy(s['competitions'])
    snapshot['market']={k:deepcopy(s['market'][k]) for k in ('deals','loans','obligations')}
    snapshot['registration']=registration.snapshot(s)
    snapshot['staff']=staff.snapshot(s)
    snapshot['delegation']=delegation.snapshot(s)
    snapshot['club_ai']=club_ai.snapshot(s)
    snapshot['commercial']=deepcopy(s['commercial'])
    snapshot['clauses']=clauses.snapshot(s)
    snapshot['clause_settings']=deepcopy(s['config']['clauses'])
    snapshot['clause_settings']['allowed_release_kinds']=transfer_rights.allowed_kinds(s)
    snapshot['market_settings']=deepcopy(s['config']['market'])
    snapshot['commercial_settings']=deepcopy(s['config']['commercial'])
    snapshot['terms']['capacity']=career.available_capacity(s)
    snapshot['terms']['physical_capacity']=s['config']['capacity']
    return snapshot
