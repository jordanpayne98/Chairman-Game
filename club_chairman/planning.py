"""Read-only planning tools. Inputs are authorised snapshots, never world state."""
from datetime import date, timedelta

ATTRIBUTES = ('passing', 'finishing', 'tackling', 'goalkeeping')
SORTS = ('Name', 'Wage', 'Age', 'Passing', 'Finishing', 'Tackling', 'Goalkeeping')


def dated(v, day):
    return (date.fromisoformat(v['start_date']) + timedelta(days=day)).strftime('%d %b %Y')


def player_rows(v, recruitment, search='', role='All', only_shortlist=False, sort='Name', descending=False):
    rows = [p for p in v['players'] if (p['club'] is None) == recruitment
            and (not p.get('retired',False) or only_shortlist) and not p.get('youth',False)
            and search.casefold() in p['name'].casefold()
            and (role == 'All' or p['role'] == role)
            and (not only_shortlist or p['id'] in v['planning']['shortlist'])]
    key = sort.lower()
    def value(p):
        if key in ATTRIBUTES:
            return sum(p['report']['ranges'][key]) / 2 if p['report'] else None
        return p.get(key, p['name']).casefold() if key == 'name' else p.get(key, p['name'])
    # Stable identity tie-break; unknown estimates stay last in either direction.
    rows.sort(key=lambda p: (p['name'].casefold(), p['id']))
    assessed = [p for p in rows if value(p) is not None]
    assessed.sort(key=value, reverse=descending)
    return assessed + [p for p in rows if value(p) is None]


def signing_terms(v, players):
    """An illustrative completion-today scenario, using current agent terms when known."""
    targets = [p for p in players if p['club'] is None]
    span=v['season_end']-v.get('season_start',0)+v.get('career_settings',{}).get('season_gap',14)
    default_end=v['season_end']+span*(2 if v['season_done'] else 1)
    offers=v.get('career',{}).get('offers',{})
    contracts=[]
    for p in targets:
        o=offers.get(p['id'],{})
        negotiated=o.get('status') in ('counter','agreed','medical','ready')
        contracts.append(dict(id=p['id'],fee=o['fee'] if negotiated else p['fee'],
                              wage=o['wage'] if negotiated else p['wage'],
                              end=o['end'] if negotiated else default_end))
    selected={p['id'] for p in targets}
    other=[o for pid,o in offers.items() if pid not in selected and o['status'] in ('medical','ready')]
    reserved_cash=sum(o['fee'] for o in other);reserved_wages=sum(o['wage_delta'] for o in other)
    fee=sum(c['fee'] for c in contracts);wage=sum(c['wage'] for c in contracts)
    future=sum(c['wage']*max(0,c['end']-v['day'])//7 for c in contracts)
    reasons=[]
    if targets:
        if v['day'] > v.get('window_end',28): reasons.append('Signing window closed')
        if v['match']: reasons.append('Recruitment locked during matchday')
        if not v['manager']: reasons.append('Appoint a manager first')
        if v['cash']-fee-reserved_cash<v['terms']['operating_buffer']:reasons.append('Would use the operating reserve')
        if v['payroll']+wage+reserved_wages>v['budget']:reasons.append('Exceeds the weekly wage limit')
    end_dates=sorted({c['end'] for c in contracts})
    return dict(count=len(targets),fee=fee,wage=wage,future=future,total=fee+future,
                cash_after=v['cash']-fee,headroom=v['budget']-v['payroll']-wage-reserved_wages,
                end_date=dated(v,end_dates[0] if len(end_dates)==1 else default_end) if len(end_dates)<2 else 'varies by agreement',
                reasons=reasons,contracts=contracts)


def forecast(v, players=(), horizon=28):
    """Daily cash settlement projection using current commitments and labelled gates.

    Gate receipts are estimates at today's supporter mood; +/-15% attendance is a
    planning sensitivity, not a confidence interval. No prizes or unapproved spend.
    """
    terms = signing_terms(v, players)
    end = v['day'] if v['season_done'] else min(v['season_end'], v['day']+horizon)
    cash = v['cash']-terms['fee']; low=cash; high=cash
    accrued = v['accrued_costs']; sponsorship=costs=gates=0
    points = [dict(day=v['day'], cash=cash, low=low, high=high)]
    daily = v['payroll']+terms['wage']+v['terms']['weekly_overheads']
    gate_days = [f['day'] for f in v['fixtures'] if f['home']=='c0' and f['result'] is None]
    def gate(day):
        capacity=v['terms']['capacity']+sum(p['closure']+p['capacity'] for p in v.get('career',{}).get('projects',[]) if p['status']=='construction' and p['due']<=day)
        attendance = min(capacity, max(0,round((3800+v['supporters']*15)*(1800/v['tickets']))))
        return (attendance*v['tickets'], round(attendance*.85)*v['tickets'],
                min(capacity,round(attendance*1.15))*v['tickets'])
    # A paused home match may still settle on the current day.
    if v['day'] in gate_days and v['match'] and not v['match']['settled']:
        income, lo, hi = gate(v['day']);cash+=income;low+=lo;high+=hi;gates+=income
        points.append(dict(day=v['day'],cash=cash,low=low,high=high))
    if v['match'] and not v['match']['settled'] and v['day']==v['season_end']:
        amount=accrued//7;cash-=amount;low-=amount;high-=amount;costs+=amount;accrued=0
        points.append(dict(day=v['day'],cash=cash,low=low,high=high))
    for day in range(v['day']+1,end+1):
        committed=sum(p['wage'] for p in v['players'] if p['club']=='c0' and (p['contract_end'] is None or p['contract_end']>=day))
        manager=v['manager'];committed+=manager['wage'] if manager and manager.get('contract_end',end)>=day else 0
        extra=sum(p['upkeep'] for p in v.get('career',{}).get('projects',[]) if p['status']=='construction' and p['due']<=day)
        accrued += committed+sum(c['wage'] for c in terms['contracts'] if c['end']>=day)+v['terms']['weekly_overheads']+extra
        if day % 7 == 0:
            income=v['terms']['weekly_sponsor'];amount=accrued//7;accrued%=7
            sponsorship+=income;costs+=amount
            cash+=income-amount;low+=income-amount;high+=income-amount
        if day in gate_days:
            income,lo,hi=gate(day);cash+=income;low+=lo;high+=hi;gates+=income
        if day == v['season_end']:
            amount=accrued//7;cash-=amount;low-=amount;high-=amount;costs+=amount;accrued=0
        points.append(dict(day=day,cash=cash,low=low,high=high))
    return dict(points=points, cash=cash, low=low, high=high, end=end,
                minimum=min(p['low'] for p in points), sponsorship=sponsorship,
                costs=costs, gates=gates, accrued=accrued//7, terms=terms,
                reserve=v['terms']['operating_buffer'])
