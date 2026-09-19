"""Read-only planning tools. Inputs are authorised snapshots, never world state."""
from datetime import date, timedelta

ATTRIBUTES = ('passing', 'finishing', 'tackling', 'goalkeeping')
SORTS = ('Name', 'Wage', 'Age', 'Passing', 'Finishing', 'Tackling', 'Goalkeeping')


def dated(v, day):
    return (date.fromisoformat(v['start_date']) + timedelta(days=day)).strftime('%d %b %Y')


def player_rows(v, recruitment, search='', role='All', only_shortlist=False, sort='Name', descending=False):
    rows = [p for p in v['players'] if (p['club'] is None) == recruitment
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
    """Guaranteed future wages exclude already accrued costs and existing contracts."""
    targets = [p for p in players if p['club'] is None]
    days = max(0, v['season_end'] - v['day'])
    fee = sum(p['fee'] for p in targets)
    wage = sum(p['wage'] for p in targets)
    future = wage * days // 7
    reasons = []
    if targets:
        if v['season_done'] or v['day'] > 28: reasons.append('Signing window closed')
        if v['match']: reasons.append('Recruitment locked during matchday')
        if not v['manager']: reasons.append('Appoint a manager first')
        if v['cash'] - fee < v['terms']['operating_buffer']: reasons.append('Would use the operating reserve')
        if v['payroll'] + wage > v['budget']: reasons.append('Exceeds the weekly wage limit')
    return dict(count=len(targets), fee=fee, wage=wage, future=future, total=fee+future,
                cash_after=v['cash']-fee, headroom=v['budget']-v['payroll']-wage,
                end_date=dated(v, v['season_end']), reasons=reasons)


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
    def gate():
        attendance = min(v['terms']['capacity'], max(0,round((3800+v['supporters']*15)*(1800/v['tickets']))))
        return (attendance*v['tickets'], round(attendance*.85)*v['tickets'],
                min(v['terms']['capacity'],round(attendance*1.15))*v['tickets'])
    # A paused home match may still settle on the current day.
    if v['day'] in gate_days and v['match'] and not v['match']['settled']:
        income, lo, hi = gate();cash+=income;low+=lo;high+=hi;gates+=income
        if v['day'] == v['season_end']:
            amount=accrued//7;cash-=amount;low-=amount;high-=amount;costs+=amount;accrued=0
        points.append(dict(day=v['day'],cash=cash,low=low,high=high))
    for day in range(v['day']+1,end+1):
        accrued += daily
        if day % 7 == 0:
            income=v['terms']['weekly_sponsor'];amount=accrued//7;accrued%=7
            sponsorship+=income;costs+=amount
            cash+=income-amount;low+=income-amount;high+=income-amount
        if day in gate_days:
            income,lo,hi=gate();cash+=income;low+=lo;high+=hi;gates+=income
        if day == v['season_end']:
            amount=accrued//7;cash-=amount;low-=amount;high-=amount;costs+=amount;accrued=0
        points.append(dict(day=day,cash=cash,low=low,high=high))
    return dict(points=points, cash=cash, low=low, high=high, end=end,
                minimum=min(p['low'] for p in points), sponsorship=sponsorship,
                costs=costs, gates=gates, accrued=accrued//7, terms=terms,
                reserve=v['terms']['operating_buffer'])
