"""Read-only planning tools. Inputs are authorised snapshots, never world state."""
from datetime import date, timedelta

ATTRIBUTES = ('passing', 'finishing', 'tackling', 'goalkeeping')
SORTS = ('Name', 'Wage', 'Age', 'Passing', 'Finishing', 'Tackling', 'Goalkeeping')


def dated(v, day):
    return (date.fromisoformat(v['start_date']) + timedelta(days=day)).strftime('%d %b %Y')


def player_rows(v, recruitment, search='', role='All', only_shortlist=False, sort='Name', descending=False, market_scope='Free agents'):
    rows = [p for p in v['players'] if ((p['club']!='c0' and (market_scope=='All' or (p['club'] is None)==(market_scope=='Free agents'))) if recruitment else p['club']=='c0')
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
    targets = [p for p in players if p['club']!='c0' and not p.get('loan')]
    span=v['season_end']-v.get('season_start',0)+v.get('career_settings',{}).get('season_gap',14)
    default_end=v['season_end']+span*(2 if v['season_done'] else 1)
    offers=v.get('career',{}).get('offers',{})
    contracts=[]
    for p in targets:
        o=offers.get(p['id'],{})
        negotiated=o.get('status') in ('counter','agreed','medical','ready')
        deal=v.get('market',{}).get('deals',{}).get(o.get('deal_id'),{})
        transfer=deal.get('fee',p.get('transfer_quote',0)) if p['club'] else 0
        upfront=deal.get('upfront',transfer);deferred=transfer-upfront
        contracts.append(dict(id=p['id'],upfront=upfront,deferred=deferred,defer_days=deal.get('defer_days',28),fee=o['fee'] if negotiated else p['fee'],
                              wage=o['wage'] if negotiated else p['wage'],
                              end=o['end'] if negotiated else default_end))
    selected={p['id'] for p in targets}
    other=[o for pid,o in offers.items() if pid not in selected and o['status'] in ('medical','ready')]
    reserved_cash=v.get('reserved_cash',0);reserved_wages=v.get('reserved_wages',0)
    for c in contracts:
        o=offers.get(c['id'],{})
        if o.get('status') in ('medical','ready'):
            reserved_cash-=o['fee']+c['upfront'];reserved_wages-=o['wage_delta']
    fee=sum(c['fee']+c['upfront'] for c in contracts);wage=sum(c['wage'] for c in contracts)
    future=sum(c['wage']*max(0,c['end']-v['day'])//7 for c in contracts)
    reasons=[]
    if targets:
        if v['day'] > v.get('window_end',28): reasons.append('Signing window closed')
        if v['match']: reasons.append('Recruitment locked during matchday')
        if not v['manager']: reasons.append('Appoint a manager first')
        if v['cash']-fee-reserved_cash<v['terms']['operating_buffer']:reasons.append('Would use the operating reserve')
        if v['payroll']+wage+reserved_wages>v['budget']:reasons.append('Exceeds the weekly wage limit')
    end_dates=sorted({c['end'] for c in contracts})
    return dict(count=len(targets),fee=fee,wage=wage,future=future,deferred=sum(c['deferred'] for c in contracts),total=fee+future+sum(c['deferred'] for c in contracts),
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
    bonus_due=sum(b['amount']-b['paid'] for b in v.get('clauses',{}).get('payables',[]) if b['source']=='c0')
    cash = v['cash']-terms['fee']-bonus_due; low=cash; high=cash
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
        committed=sum(projected_wage(p,day) for p in v['players'])
        sponsor=sum(c['weekly'] for c in v.get('commercial',{}).get('contracts',[]) if c['start']<day<=c['end'] and (day-c['start'])%7==0)
        bills=sum(b['amount']*(1 if b['target']=='c0' else -1) for b in v.get('market',{}).get('obligations',[]) if b['status']=='scheduled' and b['due']==day and 'c0' in (b['source'],b['target']))
        bills-=sum(c['deferred'] for c in terms['contracts'] if v['day']+c['defer_days']==day)
        sponsorship+=sponsor;cash+=sponsor+bills;low+=sponsor+bills;high+=sponsor+bills
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
                bonus_due=bonus_due,reserve=v['terms']['operating_buffer'])


def projected_wage(p,day):
    if p['contract_end'] is not None and day>p['contract_end']:return 0
    loan=p.get('loan')
    if loan:
        if day>loan['end']:return p['wage'] if loan['source']=='c0' else 0
        share=p['wage']*loan['share']//100
        return share if loan['target']=='c0' else p['wage']-share if loan['source']=='c0' else 0
    return p['wage'] if p['club']=='c0' else 0
