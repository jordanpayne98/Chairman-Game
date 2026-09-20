"""Contract read models. Only public terms and authorised snapshots are accepted."""

CLOSED = ('completed', 'withdrawn', 'expired', 'rejected')
RESERVED = ('medical', 'ready')


def proposed_end(v, duration):
    span = v['season_end'] - v['season_start'] + v['career_settings']['season_gap']
    return v['season_end'] + span * (duration if v['season_done'] else duration - 1)


def review(v, offer, draft=None):
    """Compare one deal with other reservations, never counting itself twice."""
    p = next(p for p in v['players'] if p['id'] == offer['player'])
    terms = draft if draft is not None else offer
    end = proposed_end(v, terms['duration']) if draft is not None else offer['end']
    deal=v.get('market',{}).get('deals',{}).get(offer.get('deal_id'),{})
    upfront=deal.get('upfront',0);deferred=deal.get('fee',0)-upfront
    reserved_cash=v.get('reserved_cash',0)-(offer['fee']+upfront if offer['status'] in RESERVED else 0)
    reserved_wages=v.get('reserved_wages',0)-(offer['wage_delta'] if offer['status'] in RESERVED else 0)
    old_wage = p['wage'] if offer['kind'] == 'renew' else 0
    delta = terms['wage'] - old_wage
    cash_after = v['cash'] - terms['fee']-upfront
    from .clauses import sell_on_due
    receipt=sum(amount for right,amount in sell_on_due(v,p['id'],deal.get('source'),deal.get('fee',0)) if right['beneficiary']=='c0') if deal else 0
    cash_after+=receipt
    headroom = v['budget'] - v['payroll'] - reserved_wages - delta
    available = cash_after - receipt - reserved_cash - v['terms']['operating_buffer']
    days = max(0, end - v['day'])
    future = terms['wage'] * days // 7
    old_future = old_wage * max(0, (p['contract_end'] or v['day']) - v['day']) // 7
    due = (offer.get('due', v['day']) if offer['status'] in RESERVED else
           v['day'] + (v['career_settings']['medical_days'] if offer['kind'] != 'renew' else 0))
    cutoff = min(offer['expires'], v['window_end']) if offer['kind'] != 'renew' else min(offer['expires'], p['contract_end'] or offer['expires'])
    reasons = []
    if v['match']: reasons.append('Finish the current match before changing contracts.')
    if not v['manager']: reasons.append('Appoint a manager first.')
    if available < 0: reasons.append('Would use reserved cash or the operating reserve.')
    if headroom < 0: reasons.append('Exceeds unreserved weekly wage capacity.')
    if v['day'] > cutoff: reasons.append('The completion deadline has passed.')
    if offer['kind'] != 'renew' and due > min(v['window_end'], v['season_end']):
        reasons.append('The medical cannot finish before registration closes.')
    if offer['kind'] == 'renew' and end <= (p['contract_end'] or 0):
        reasons.append('Renewal must extend the existing agreement.')
    return dict(end=end, future=future, upfront=upfront, deferred=deferred, sell_on_receipt=receipt, total=terms['fee'] + upfront + deferred + future,
                additional=terms['fee'] + upfront + deferred + future - old_future, wage_delta=delta,
                cash_after=cash_after, available=available, headroom=headroom,
                reserved_cash=reserved_cash, reserved_wages=reserved_wages,
                due=due, cutoff=cutoff, reasons=reasons)


def attention(v):
    """Prioritised current actions, without inventing hidden demands or risks."""
    rows = []
    people = {p['id']: p for p in v['players']}
    for o in v['career']['offers'].values():
        if o['status'] in CLOSED: continue
        authority=v.get('delegation',{}).get('responsibilities',{}).get('contracts',{})
        if o.get('delegate') and o['delegate']==authority.get('delegate') and authority.get('mode')=='Autonomous':continue
        p = people[o['player']]
        cutoff = min(o['expires'], v['window_end']) if o['kind'] != 'renew' else min(o['expires'], p['contract_end'] or o['expires'])
        if o['status'] == 'ready' or cutoff - v['day'] <= 1:
            rows.append(dict(player=p['id'], name=p['name'], deadline=cutoff,
                             label='Medical reviewed: ready to sign' if o['status'] == 'ready' else 'Contract discussion expires soon'))
    for d in v.get('market',{}).get('deals',{}).values():
        if d['status'] in CLOSED or d['kind']=='buy':continue
        if d['status']=='ready' or d['expires']-v['day']<=1:
            rows.append(dict(player=d['player'],name=people[d['player']]['name'],deadline=d['expires'],screen='Transfers',deal_id=d['id'],
                             label='Club deal ready for review' if d['status']=='ready' else 'Club deal expires soon'))
    return sorted(rows, key=lambda row: (row['deadline'], row['player']))
