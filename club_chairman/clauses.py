"""Binding employment clauses, earned bonus payables and next-sale rights.

No new terms are invented for an old save. Money uses integer pence; sporting
events create one liability each, independent of live playback or skipped games.
"""
from copy import deepcopy
from . import contract_terms

DEFAULTS = dict(max_bonus=100000, max_sell_on_percent=50, option_wage_premium=5)
EMPTY_TERMS = dict(appearance_bonus=0, goal_bonus=0, club_option=False)


def initialise(s):
    s['schema'] = 5
    s.setdefault('clauses', dict(employment={}, history=[], payables=[], sell_on=[]))
    settings = s['config'].setdefault('clauses', {})
    for key, value in DEFAULTS.items(): settings.setdefault(key, value)


def terms(data):
    return {**{key: data.get(key, default) for key, default in EMPTY_TERMS.items()},**contract_terms.terms(data)}


def validate_terms(s, data):
    from .simulation import require
    result = terms(data)
    for key in ('appearance_bonus', 'goal_bonus'):
        require(type(result[key]) is int and 0 <= result[key] <= s['config']['clauses']['max_bonus'],
                'Bonuses must be whole pence between £0 and £1,000 per event.')
    require(type(result['club_option']) is bool, 'Choose whether the club has an extension option.')
    contract_terms.validate_terms(s,data)
    return result


def description(data):
    t = terms(data)
    return (f"£{t['appearance_bonus']/100:,.0f} per appearance; £{t['goal_bonus']/100:,.0f} per goal. "
            + ('Club option: one additional season continuing the signed pay conditions.' if t['club_option'] else 'No club extension option.')+' '+contract_terms.description(t))


def sign(s, p, offer, employer="c0"):
    previous = s['clauses']['employment'].pop(p['id'], None)
    if previous: s['clauses']['history'].append(dict(previous, closed=s['day']))
    if not any(v for k,v in terms(offer).items() if k!='release_kind'): return
    from .career import season_end
    span = season_end(s) - s['career']['start'] + s['config']['career']['season_gap']
    from .nations import add_year
    option_end=add_year(s['config']['start_date'],offer['end']) if s.get('calendar') else offer['end']+span
    s['clauses']['employment'][p['id']] = dict(
        id=offer['id'] + ':clauses', player=p['id'], employer=employer, start=s['day'],
        end=offer['end'], **terms(offer), option_end=option_end,
        option_status='available' if offer.get('club_option') or offer.get('player_option') else 'none', cap=None,
        next_raise=add_year(s['config']['start_date'],s['day']))


def end_employment(s, pid):
    previous = s['clauses']['employment'].pop(pid, None)
    if previous: s['clauses']['history'].append(dict(previous, closed=s['day']))


def record_match(s, match):
    from .simulation import news
    contract_terms.record_match(s,match)
    existing = {b['id'] for b in s['clauses']['payables']}
    for side, lineup in enumerate(match.get('participants',match['lineups'])):
        cid = match['home'] if side == 0 else match['away']
        for pid in lineup:
            contract = s['clauses']['employment'].get(pid)
            if not contract or not contract['start'] <= s['day'] <= contract['end']: continue
            # A loan changes registration, not the employer's bonus obligation.
            goals = sum(e.get('player') == pid and e['kind'] == 'goal' for e in match['events'])
            for trigger, units in (('appearance', 1), ('goal', goals)):
                amount = contract[trigger + '_bonus'] * units
                key = f"{contract['id']}:{match['fixture']}:{trigger}"
                if not amount or key in existing: continue
                s['clauses']['payables'].append(dict(id=key, player=pid, source=contract['employer'],
                    fixture=match['fixture'], representing=cid, trigger=trigger, units=units,
                    amount=amount, paid=0, due=s['day'], status='due'))
                existing.add(key)


def settle_payables(s):
    contract_terms.settle(s)
    from .market import club_cash, post
    from .simulation import news
    for bill in s['clauses']['payables']:
        if bill['paid'] == bill['amount']: continue
        remaining = bill['amount'] - bill['paid']
        amount = min(remaining, max(0, club_cash(s, bill['source'])))
        if amount:
            post(s, bill['source'], bill['id'] + f":payment:{bill['paid']}", -amount,
                 'Player ' + bill['trigger'] + ' bonus')
            bill['paid'] += amount
        bill['status'] = 'paid' if bill['paid'] == bill['amount'] else 'arrears'
        if bill['status'] == 'arrears' and not bill.get('notified'):
            bill['notified'] = True
            news(s, 'Player bonus unpaid', 'Earned bonuses exceed available cash. The balance remains due in Contracts > Clauses. Add funding to settle it.')


def validate_sell_on(s, data):
    from .simulation import require
    kind = data.get('sell_on_kind', 'none'); percent = data.get('sell_on_percent', 0)
    require(kind in ('none', 'gross', 'profit'), 'Choose gross proceeds, profit or no sell-on right.')
    require(type(percent) is int and 0 <= percent <= s['config']['clauses']['max_sell_on_percent'], 'Sell-on percentage must be 0–50%.')
    require((kind == 'none') == (percent == 0), 'A sell-on right needs a positive percentage; None needs zero.')
    return dict(sell_on_kind=kind, sell_on_percent=percent)


def sell_on_due(s, pid, seller, fee):
    rows = []
    for right in s['clauses']['sell_on']:
        if right['player'] != pid or right['liable'] != seller or right['status'] != 'active': continue
        basis = fee if right['kind'] == 'gross' else max(0, fee - right['basis'])
        rows.append((right, basis * right['percent'] // 100))
    return rows


def complete_sale(s, deal):
    """Called after receipt of the fee, before registration changes, atomically."""
    from .market import transfer_cash
    from . import transfer_rights
    if deal.get('exit_kind')=='buyout':
        release(s,deal['player'],deal['source'])
        s['clauses']['buyouts'].append(dict(id=deal['id']+':compensation',player=deal['player'],sponsor=deal['target'],employer=deal['source'],amount=deal['fee'],day=s['day'],player_consent=deal['player_consent']))
        transfer_rights.complete(s,deal)
        return
    for right, amount in sell_on_due(s, deal['player'], deal['source'], deal['fee']):
        transfer_cash(s, right['id'] + ':settlement', deal['source'], right['beneficiary'], amount, 'Sell-on clause')
        right.update(status='settled', settled=s['day'], amount=amount, sale=deal['id'])
    transfer_rights.complete(s,deal)
    contract_terms.signed_sale(s,deal)
    end_employment(s, deal['player'])
    if deal.get('sell_on_percent', 0):
        s['clauses']['sell_on'].append(dict(id=deal['id'] + ':sell-on', player=deal['player'],
            liable=deal['target'], beneficiary=deal['source'], kind=deal['sell_on_kind'],
            percent=deal['sell_on_percent'], basis=deal['fee'], status='active',
            cap=None, expiry='Next permanent transfer or release'))


def release(s, pid, employer):
    from . import transfer_rights
    transfer_rights.release(s,pid,employer)
    end_employment(s, pid)
    for right in s['clauses']['sell_on']:
        if right['player'] == pid and right['liable'] == employer and right['status'] == 'active':
            right.update(status='expired', expired=s['day'])


def apply(s, action, data):
    if action != 'exercise_option': return None
    from .simulation import require, news
    from .career import person
    from .market import active_loan, TERMINAL
    pid = data.get('id'); p = person(s, pid)
    c = s['clauses']['employment'].get(pid)
    require(s['match'] is None, 'Exercise options outside matchday.')
    require(c is not None and c['employer'] == 'c0' and c['option_status'] == 'available' and c.get('club_option'), 'No unused club option exists.')
    loan = active_loan(s, pid)
    require((loan['source'] if loan else p['club']) == 'c0' and s['day'] <= c['end'], 'The option expired or employment changed.')
    offer = s['career']['offers'].get(pid)
    require(not offer or offer['status'] in TERMINAL, 'Resolve the open renewal discussion before exercising this option.')
    p['contract_end'] = c['option_end']; c['end'] = c['option_end']; c['option_status'] = 'exercised'
    news(s, 'Club option exercised', p['name'] + ': employment extended for one additional season; signed wage clauses and bonuses continue.')
    return 'Extension signed. Guaranteed future wages increased; no immediate fee.'


def snapshot(s):
    # Only clauses our club signed or is entitled to see; no hidden player data.
    c=deepcopy(s['clauses'])
    c['employment']={pid:r for pid,r in c['employment'].items() if r['employer']=='c0'}
    c['history']=[r for r in c['history'] if r['employer']=='c0']
    for key,parties in (('rights',('beneficiary','liable')),('notices',('source','beneficiary','other_buyer')),
                        ('buyouts',('sponsor','employer')),('conditional',('source','target')),('sell_on',('beneficiary','liable'))):
        c[key]=[r for r in c[key] if any(r[k]=='c0' for k in parties)]
    c['payables']=[r for r in c['payables'] if r['source']=='c0']
    return c


def validate(s):
    from .simulation import require
    from . import transfer_rights
    transfer_rights.validate(s)
    contract_terms.validate(s)
    ids = {p['id'] for p in s['players']}
    for pid, c in s['clauses']['employment'].items():
        require(pid in ids and c['player'] == pid and c['start'] <= c['end'], 'Invalid employment clause.')
        validate_terms(s, c)
        require(c['option_status'] in ('none', 'available', 'exercised','declined','expired'), 'Invalid extension state.')
    bills = s['clauses']['payables']; rights = s['clauses']['sell_on']
    require(len({b['id'] for b in bills}) == len(bills), 'Duplicate earned bonus.')
    for b in bills:
        require(b['player'] in ids and type(b['amount']) is int and type(b['paid']) is int and 0 <= b['paid'] <= b['amount'], 'Invalid bonus payable.')
    require(len({r['id'] for r in rights}) == len(rights), 'Duplicate sell-on right.')
    active = [(r['player'], r['liable']) for r in rights if r['status'] == 'active']
    require(len(set(active)) == len(active), 'Conflicting sell-on rights.')
    for r in rights:
        validate_sell_on(s, dict(sell_on_kind=r['kind'], sell_on_percent=r['percent']))
        require(r['beneficiary'] != r['liable'] and r['player'] in ids, 'Invalid sell-on beneficiary.')
