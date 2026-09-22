"""Consented loan purchase rights and appearance-conditioned obligations."""
from datetime import date,timedelta


def terms(s,d,data):
    from .simulation import require
    from .market import quote,player
    from .career import contractual_end,window_end
    kind=data.get('purchase_kind',d.get('purchase_kind','none'))
    require(kind in ('none','option','obligation'),'Choose no purchase, option or appearance obligation.')
    if kind=='none':return dict(purchase_kind='none',purchase_fee=0,purchase_count=0)
    count=data.get('purchase_count',d.get('purchase_count') or 2)
    require(type(count) is int and 1<=count<=30,'Purchase appearance threshold must be 1–30 matches.')
    p=player(s,d['player'])
    require(not any(r['player']==p['id'] and r['liable']==d['source'] and r['kind']=='refusal'
                    and r['beneficiary']!=d['target'] and r['status']=='active' and s['day']<=r['expiry']
                    for r in s['clauses']['rights']),
            'An existing first-refusal right prevents pre-agreeing this loan purchase. Use a permanent transfer with a matching notice, or a loan without purchase terms.')
    fee=d.get('purchase_fee') or quote(s,p,d['target'])
    require(type(fee) is int and fee>0,'Invalid purchase price.')
    end=contractual_end(s,2)
    require(end>d['end'],'The permanent agreement must outlast the loan.')
    if kind=='obligation':require(d['end']+1<=window_end(s),'A binding purchase must settle after the loan within this registration window. Shorten the loan first.')
    return dict(purchase_kind=kind,purchase_fee=fee,purchase_count=count,purchase_wage=p['wage'],purchase_end=end)


def description(d,origin=None):
    kind=d.get('purchase_kind','none')
    if kind=='none':return 'No purchase clause.'
    condition='Optional purchase during the loan and registration window.' if kind=='option' else f"Binding purchase after loan expiry if {d['purchase_count']} appearances are reached."
    ending=(' Employment to '+(date.fromisoformat(origin)+timedelta(days=d['purchase_end'])).strftime('%d %b %Y')+'.') if origin else ''
    return condition+f" Price £{d['purchase_fee']/100:,.0f}; permanent wages £{d['purchase_wage']/100:,.0f}/week. Consent includes these employment terms."+ending


def reserve(d):return d.get('purchase_fee',0) if d.get('purchase_kind')=='obligation' else 0


def active_reservations(s,cid):
    from .market import player,wage_for
    rows=[l for l in s['market']['loans'] if l['status']=='active' and l['target']==cid and l.get('purchase_kind')=='obligation']
    return sum(l['purchase_fee'] for l in rows),sum(max(0,l['purchase_wage']-wage_for(s,player(s,l['player']),cid)) for l in rows)


def record_match(s,m):
    if m.get('forfeit'):return
    for l in s['market']['loans']:
        if l['status']!='active' or l.get('purchase_kind','none')=='none' or l['target'] not in (m['home'],m['away']):continue
        side=0 if l['target']==m['home'] else 1
        if l['player'] in m.get('participants',m['lineups'])[side] and m['fixture'] not in l['purchase_fixtures']:
            l['purchase_fixtures'].append(m['fixture'])


def purchase(s,l,automatic=False):
    from .simulation import require,news
    from . import market,registration,clauses,career,club_ai
    p=market.player(s,l['player']);day=s['day'];target=l['target']
    require(l['status']=='active' and not s['match'] and day<=career.window_end(s) and not s['season_done'],'Loan purchase requires an active loan and an open registration window outside matchday.')
    require(p['club']==target and not p['retired'] and day<=p['contract_end'] and l['purchase_end']>day,'Employment or player availability changed.')
    require(automatic or l.get('purchase_kind')=='option' and target=='c0' and day<=l['end'],'Only the borrower can exercise an unused purchase option.')
    registration.check_arrival(s,p,target)
    # Remove this loan's own reserved capacity in the uncommitted transaction.
    # Any failed recheck rolls this change back with the whole command/day.
    l['status']='purchasing'
    fees,wages=career.reservations(s) if target=='c0' else market.extra_reservations(s,target)
    limit=s['budget'] if target=='c0' else club_ai.budgets(s,target)['wage_limit']
    require(market.club_cash(s,target)-fees-l['purchase_fee']>=s['config']['operating_buffer'],'Fund the contracted loan purchase before continuing.')
    require(market.club_payroll(s,target)-p['wage']+l['purchase_wage']+wages<=limit,'Permanent purchase wages exceed available capacity.')
    deal=dict(id=l['id']+':purchase',player=l['player'],source=l['source'],target=target,fee=l['purchase_fee'],employment_end=l['purchase_end'])
    market.transfer_cash(s,deal['id'],target,l['source'],l['purchase_fee'],'Loan purchase')
    clauses.complete_sale(s,deal)
    p.update(wage=l['purchase_wage'],contract_end=l['purchase_end'])
    if target!='c0':
        from . import transfer_rights
        transfer_rights.ai_employment(s,p,target,p['wage'],p['contract_end'],deal['id'])
    l.update(status='purchased',purchased=day)
    if target=='c0':s['transfer_spend']+=l['purchase_fee']
    news(s,'Loan purchase completed',p['name']+': pre-agreed purchase and employment terms settled; loan restrictions ended.')


def process_end(s,l):
    if l.get('purchase_kind')=='obligation' and s['day']>l['end'] and len(l['purchase_fixtures'])>=l['purchase_count']:
        purchase(s,l,automatic=True);return True
    if l.get('purchase_kind')=='option' and l['target']!='c0' and s['day']<=l['end'] and len(l['purchase_fixtures'])>=l['purchase_count']:
        from . import market,career,club_ai
        p=market.player(s,l['player']);fees,wages=market.extra_reservations(s,l['target']);b=club_ai.budgets(s,l['target'])
        if (s['day']<=career.window_end(s) and not s['season_done'] and s['day']<=p['contract_end'] and l['purchase_end']>s['day']
            and market.club_cash(s,l['target'])-fees-l['purchase_fee']>=b['reserve']+b['bills']
            and market.club_payroll(s,l['target'])-market.wage_for(s,p,l['target'])+l['purchase_wage']+wages<=b['wage_limit']):
            from .registration import check_arrival
            try:check_arrival(s,p,l['target'])
            except ValueError:return False
            purchase(s,l,automatic=True);return True
    return False


def apply(s,action,data):
    if action!='loan_purchase':return None
    from .simulation import require
    l=next((l for l in s['market']['loans'] if l['id']==data.get('id')),None)
    require(l is not None and l.get('purchase_kind')=='option','No purchase option exists.')
    purchase(s,l)
    return 'Permanent purchase completed on the signed terms.'


def validate(s):
    from .simulation import require
    for l in s['market']['loans']:
        kind=l.get('purchase_kind','none')
        require(kind in ('none','option','obligation'),'Invalid loan purchase type.')
        if kind=='none':continue
        require(all(type(l[k]) is int and l[k]>0 for k in ('purchase_fee','purchase_wage','purchase_end','purchase_count')),'Invalid loan purchase terms.')
        require(len(l['purchase_fixtures'])==len(set(l['purchase_fixtures'])),'Duplicate loan purchase exposure.')
