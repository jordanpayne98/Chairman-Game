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
    others = [o for o in v['career']['offers'].values()
              if o['id'] != offer['id'] and o['status'] in RESERVED]
    reserved_cash = sum(o['fee'] for o in others)
    reserved_wages = sum(o['wage_delta'] for o in others)
    old_wage = p['wage'] if offer['kind'] == 'renew' else 0
    delta = terms['wage'] - old_wage
    cash_after = v['cash'] - terms['fee']
    headroom = v['budget'] - v['payroll'] - reserved_wages - delta
    available = cash_after - reserved_cash - v['terms']['operating_buffer']
    days = max(0, end - v['day'])
    future = terms['wage'] * days // 7
    old_future = old_wage * max(0, (p['contract_end'] or v['day']) - v['day']) // 7
    due = (offer.get('due', v['day']) if offer['status'] in RESERVED else
           v['day'] + (v['career_settings']['medical_days'] if offer['kind'] == 'sign' else 0))
    cutoff = min(offer['expires'], v['window_end']) if offer['kind'] == 'sign' else min(offer['expires'], p['contract_end'] or offer['expires'])
    reasons = []
    if v['match']: reasons.append('Finish the current match before changing contracts.')
    if not v['manager']: reasons.append('Appoint a manager first.')
    if available < 0: reasons.append('Would use reserved cash or the operating reserve.')
    if headroom < 0: reasons.append('Exceeds unreserved weekly wage capacity.')
    if v['day'] > cutoff: reasons.append('The completion deadline has passed.')
    if offer['kind'] == 'sign' and due > min(v['window_end'], v['season_end']):
        reasons.append('The medical cannot finish before registration closes.')
    if offer['kind'] == 'renew' and end <= (p['contract_end'] or 0):
        reasons.append('Renewal must extend the existing agreement.')
    return dict(end=end, future=future, total=terms['fee'] + future,
                additional=terms['fee'] + future - old_future, wage_delta=delta,
                cash_after=cash_after, available=available, headroom=headroom,
                reserved_cash=reserved_cash, reserved_wages=reserved_wages,
                due=due, cutoff=cutoff, reasons=reasons)


def attention(v):
    """Prioritised current actions, without inventing hidden demands or risks."""
    rows = []
    people = {p['id']: p for p in v['players']}
    for o in v['career']['offers'].values():
        if o['status'] in CLOSED: continue
        p = people[o['player']]
        cutoff = min(o['expires'], v['window_end']) if o['kind'] == 'sign' else min(o['expires'], p['contract_end'] or o['expires'])
        if o['status'] == 'ready' or cutoff - v['day'] <= 1:
            rows.append(dict(player=p['id'], name=p['name'], deadline=cutoff,
                             label='Medical reviewed: ready to sign' if o['status'] == 'ready' else 'Contract discussion expires soon'))
    return sorted(rows, key=lambda row: (row['deadline'], row['player']))
