"""Club transactions, temporary registration and dated inter-club settlements.

All commands run inside Simulation's copy-on-commit transaction. Public quotes
are persisted; opening a screen never rerolls a counterparty response.
"""
from copy import deepcopy
from . import clauses, registration, contract_terms, loan_clauses, transfer_rights

DEFAULTS = dict(asking_multiple=3,minimum_squad=14,minimum_goalkeepers=1,
                ai_opening_cash=35000000,ai_weekly_income=3000000,ai_weekly_overheads=350000,
                quote_days=7,medical_days=2,loan_fee=150000,minimum_upfront_percent=50,
                max_installment_days=56,minimum_loan_days=14)
TERMINAL = ('completed','withdrawn','expired','rejected')


def initialise(s):
    s['schema']=4
    cfg=s['config'].setdefault('market',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,v)
    s.setdefault('market',dict(deals={},loans=[],obligations=[],accounts={}))
    for c in s['clubs']:
        if c['id']!='c0':s['market']['accounts'].setdefault(c['id'],dict(opening=cfg['ai_opening_cash'],cash=cfg['ai_opening_cash'],ledger=[],accrued=0))


def player(s,pid):
    from .career import person
    return person(s,pid)


def club_cash(s,cid):return s['cash'] if cid=='c0' else s['market']['accounts'][cid]['cash']


def post(s,cid,key,amount,reason):
    from .simulation import posting
    if cid=='c0':posting(s,key,amount,reason);return
    a=s['market']['accounts'][cid]
    if any(e['id']==key for e in a['ledger']):return
    a['cash']+=amount;a['ledger'].append(dict(id=key,day=s['day'],amount=amount,reason=reason,balance=a['cash']))


def transfer_cash(s,key,source,target,amount,reason):
    from .simulation import require
    require(source!=target and type(amount) is int and amount>=0,'Invalid inter-club payment.')
    require(club_cash(s,source)>=amount,'The paying club cannot fund this payment.')
    post(s,source,key,-amount,reason);post(s,target,key,amount,reason)


def active_loan(s,pid):return next((l for l in s['market']['loans'] if l['player']==pid and l['status']=='active'),None)


def wage_for(s,p,cid,day=None):
    day=s['day'] if day is None else day
    loan=active_loan(s,p['id'])
    wage=contract_terms.projected(p['wage'],s['clauses']['employment'].get(p['id'],{}),s['config']['start_date'],day)
    if loan:
        if day<=loan['end']:
            borrower=wage*loan['share']//100
            return borrower if cid==loan['target'] else wage-borrower if cid==loan['source'] else 0
        return wage if cid==loan['source'] and (p['contract_end'] is None or day<=p['contract_end']) else 0
    return wage if p['club']==cid and (p['contract_end'] is None or day<=p['contract_end']) else 0


def club_payroll(s,cid):
    from .staff import payroll
    return sum(wage_for(s,p,cid) for p in s['players'])+(s['manager']['wage'] if cid=='c0' and s['manager'] else 0)+payroll(s,cid)


def can_release(s,p,cid):
    cfg=s['config']['market'];squad=[q for q in s['players'] if q['club']==cid and q['id']!=p['id'] and not q['retired'] and not q['youth']]
    return len(squad)>=cfg['minimum_squad'] and sum(q['role']=='GK' for q in squad)>=cfg['minimum_goalkeepers']


def quote(s,p,buyer=None):
    amount=transfer_rights.enforced_amount(s,p,buyer or ('c0' if p['club']!='c0' else None))
    normal=p['fee']*s['config']['market']['asking_multiple']
    return min(normal,amount) if amount else normal


def active_deal(s,pid):
    return next((d for d in s['market']['deals'].values() if d['player']==pid and d['status'] not in TERMINAL),None)


def transfer_deal(s,pid):
    return next((d for d in s['market']['deals'].values() if d['player']==pid and d['kind']=='buy' and d['status']=='seller_agreed'),None)


def upfront_for_offer(s,o):
    d=s['market']['deals'].get(o.get('deal_id'))
    return d['upfront'] if d and d['kind']=='buy' and d['status']=='seller_agreed' else 0


def extra_reservations(s,cid='c0',exclude=None):
    deals=[d for d in s['market']['deals'].values() if d['id']!=exclude and d['status'] in ('medical','ready') and d['target']==cid]
    ai=[d for d in s.get('club_ai',{}).get('decisions',[]) if d['club']==cid and d['status'] in ('medical','rights_wait') and d['id']!=exclude]
    loan_cash,loan_wages=loan_clauses.active_reservations(s,cid)
    return loan_cash+sum(d['fee']+loan_clauses.reserve(d) for d in deals)+sum(d['fee']+d['signing_fee']+d.get('appearance_fee',0)+d.get('promotion_fee',0) for d in ai),loan_wages+sum(max(d['wage_cost'],d.get('purchase_wage',0)) if loan_clauses.reserve(d) else d['wage_cost'] for d in deals)+sum(d['wage'] for d in ai)


def registration_check(s,p,cid):
    from .simulation import require
    from .club_ai import pending_for
    from .career import window_end
    require(s['match'] is None,'Finish matchday before changing registration.')
    require(not s['season_done'] and s['day']<=window_end(s),'The registration window is closed.')
    require(not p['retired'] and not p['youth'],'Only active senior players can use this market.')
    require(active_loan(s,p['id']) is None,'Resolve the existing loan before another registration change.')
    require(pending_for(s,p['id']) is None,'This player has a conditional agreement elsewhere. Wait for its outcome.')
    require(cid in {c['id'] for c in s['clubs']},'Unknown destination club.')
    registration.check_arrival(s,p,cid)


def complete_purchase(s,o):
    """Settle club terms within the same transaction as the new employment."""
    from .simulation import require
    p=player(s,o['player']);d=s['market']['deals'].get(o.get('deal_id'))
    require(d is not None and d['status']=='seller_agreed','The selling-club agreement is no longer available.')
    registration_check(s,p,'c0')
    transfer_rights.check_exit(s,p,d)
    require(p['club']==d['source'] and (can_release(s,p,d['source']) or transfer_rights.exit_met(s,p,d)),'The selling club can no longer release this player.')
    require(s['day']<=d['expires'],'The selling-club agreement expired.')
    transfer_cash(s,d['id']+':upfront','c0',d['source'],d['upfront'],('Player buy-out compensation: ' if d.get('exit_kind')=='buyout' else 'Transfer fee: ')+p['name'])
    d['employment_end']=o['end'];d['player_consent']=o['id']
    clauses.complete_sale(s,d)
    remainder=d['fee']-d['upfront']
    if remainder:
        s['market']['obligations'].append(dict(id=d['id']+':deferred',source='c0',target=d['source'],amount=remainder,
            due=s['day']+d['defer_days'],status='scheduled',player=p['id']))
    s['transfer_spend']+=d['fee'];d.update(status='completed',completed=s['day'])
    d['transcript'].append('Club registration and transfer obligations completed together.')


def close_purchase(s,o,reason):
    d=s['market']['deals'].get(o.get('deal_id'))
    if d and d['status'] not in TERMINAL:
        d['status']='withdrawn';d['transcript'].append(reason);transfer_rights.withdrawn(s,d)


def process_day(s):
    from .simulation import news,require
    day=s['day']
    transfer_rights.process_day(s)
    # Income then dated liabilities; Continue is atomic if a player-owned bill is unaffordable.
    for cid,a in s['market']['accounts'].items():
        if day%7==0:post(s,cid,f'ai-income:{day}',s['config']['market']['ai_weekly_income'],'Operating income')
    for bill in s['market']['obligations']:
        if bill['status']=='scheduled' and bill['due']<=day:
            transfer_cash(s,bill['id'],bill['source'],bill['target'],bill['amount'],'Transfer instalment')
            bill['status']='paid';bill['paid']=day
            news(s,'Transfer instalment settled',f"{player(s,bill['player'])['name']}: £{bill['amount']/100:,.0f} paid on schedule.")
    for loan in s['market']['loans']:
        if loan['status']=='active' and day==loan['end'] and loan.get('purchase_kind')=='option':
            loan_clauses.process_end(s,loan)
        if loan['status']=='active' and day>loan['end']:
            if loan_clauses.process_end(s,loan):continue
            p=player(s,loan['player']);p['club']=loan['source'];loan['status']='returned';loan['returned']=day
            news(s,'Loan completed',p['name']+' returned to the parent club. Full wages revert to the employer.')
    for d in s['market']['deals'].values():
        if d['status'] in TERMINAL:continue
        if day>d['expires']:
            d['status']='expired';d['transcript'].append('Deadline passed. No registration changed; reservations released.')
            o=s['career']['offers'].get(d['player'])
            if o and o.get('deal_id')==d['id'] and o['status'] not in TERMINAL:
                o['status']='expired';o['transcript'].append('Selling-club consent expired. No contract was signed.')
            news(s,'Club deal expired',player(s,d['player'])['name']+': '+d['kind']+' discussion expired.')
        elif d['status']=='medical' and day>=d['due']:
            d['status']='ready';d['transcript'].append('Medical and consent checks complete. Final registration review is required.')
            news(s,'Club deal ready',player(s,d['player'])['name']+': review final '+d['kind']+' completion in Transfers.')


def accrue_accounts(s):
    day=s['day']
    for cid,a in s['market']['accounts'].items():
        a['accrued']+=club_payroll(s,cid)+s['config']['market']['ai_weekly_overheads']
        if day%7==0:
            amount=a['accrued']//7
            # No invented overdraft: retained arrears stay visible in the account.
            paid=min(amount,a['cash']);post(s,cid,f'ai-payroll:{day}',-paid,'Payroll and operations')
            a['accrued']-=paid*7


def validate(s):
    from .simulation import require
    loan_clauses.validate(s)
    for a in s['market']['accounts'].values():
        require(a['cash']==a['opening']+sum(e['amount'] for e in a['ledger']),'Counterparty cash does not reconcile.')
        require(a['cash']>=0 and len({e['id'] for e in a['ledger']})==len(a['ledger']),'Invalid counterparty ledger.')
    loans=[l for l in s['market']['loans'] if l['status']=='active']
    require(len({l['player'] for l in loans})==len(loans),'Duplicate active loan.')
    for l in loans:require(player(s,l['player'])['club']==l['target'],'Loan registration does not match the borrower.')
    require(len({b['id'] for b in s['market']['obligations']})==len(s['market']['obligations']),'Duplicate dated obligation.')
    for b in s['market']['obligations']:
        require(type(b['amount']) is int and b['amount']>=0 and b['source']!=b['target'],'Invalid dated obligation.')


def apply(s,action,data):
    from .simulation import require,news
    from .career import window_end,reservations,person
    if action not in ('club_enquire','club_propose','club_accept','market_withdraw','sale_enquire','sale_terms','loan_enquire','market_accept','market_complete','loan_recall','loan_terms'):return None
    require(s['match'] is None,'Finish matchday before changing club agreements.')
    cfg=s['config']['market'];day=s['day']
    if action in ('club_enquire','sale_enquire','loan_enquire'):
        p=person(s,data.get('id'))
        require(active_deal(s,p['id']) is None,'A club discussion is already open for this person.')
        o=s['career']['offers'].get(p['id']);require(not o or o['status'] in TERMINAL,'Resolve the existing personal contract discussion first.')
        require(p['club'] is not None,'Free agents negotiate directly in Contracts.')
        buying=p['club']!='c0';source=p['club'];target='c0' if buying else data.get('club')
        require(target in s['market']['accounts'] or target=='c0','Select a receiving club.')
        require(target!=source,'Choose a different club.')
        registration_check(s,p,target)
        require(can_release(s,p,source) or action!='loan_enquire' and transfer_rights.enforced_amount(s,p,target)>0,'The current club must retain its minimum senior squad and goalkeeper cover.')
        kind='buy' if action=='club_enquire' else 'sale' if action=='sale_enquire' else 'loan'
        require((kind!='buy' or buying) and (kind!='sale' or not buying),'Use the correct transaction for this registration.')
        price=quote(s,p,target) if kind!='loan' else cfg['loan_fee']
        key=f"club:{p['id']}:{s['revision']}"
        days=min(56,p['contract_end']-day-cfg['medical_days']) if kind=='loan' else None
        end=day+cfg['medical_days']+days if kind=='loan' else None
        if kind=='loan':require(days>=cfg['minimum_loan_days'],'Employment expires too soon for this loan.')
        s['market']['deals'][key]=dict(id=key,player=p['id'],kind=kind,source=source,target=target,status='quote',fee=price,
            upfront=price,defer_days=28,share=100,end=end,days=days,wage_cost=p['wage'],rounds=0,expires=min(day+cfg['quote_days'],window_end(s)),
            transcript=[f"Club: Proposed {kind}. Fee £{price/100:,.0f}. The player will review employment or temporary placement separately."])
        return 'Club discussion opened. No money, employment or registration has changed.'
    if action=='loan_recall':
        l=next((l for l in s['market']['loans'] if l['id']==data.get('id') and l['status']=='active'),None)
        require(l is not None and l['source']=='c0','Only your own active outgoing loan can be recalled.')
        require(l.get('purchase_kind')!='obligation','A binding purchase loan cannot be recalled to cancel its condition.')
        require(day<=window_end(s),'Recall is permitted only during a registration window.')
        p=player(s,l['player']);cash,wages=reservations(s)
        require(club_payroll(s,'c0')+p['wage']*l['share']//100+wages<=s['budget'],'Recall would exceed the wage limit.')
        refund=l.get('fee',0)*max(0,l['end']-day)//max(1,l['end']-l['start'])
        require(s['cash']-cash-refund>=s['config']['operating_buffer'],'Recall refund would consume reserved cash or the operating reserve.')
        transfer_cash(s,l['id']+':recall-refund','c0',l['target'],refund,'Unserved loan fee refund')
        p['club']='c0';l.update(status='recalled',returned=day,refund=refund)
        news(s,'Player recalled',p['name']+' returns. The unserved loan fee was refunded and full wages resume.')
        return 'Recall completed. Registration and payroll updated together.'
    d=s['market']['deals'].get(data.get('id'));require(d is not None,'Unknown club discussion.')
    require(d['status'] not in TERMINAL,'This club discussion is closed.')
    p=person(s,d['player'])
    if action=='market_withdraw':
        d['status']='withdrawn';d['transcript'].append('Chairman withdrew. No registration changed.')
        o=s['career']['offers'].get(p['id'])
        if o and o.get('deal_id')==d['id'] and o['status'] not in TERMINAL:o['status']='withdrawn';o['transcript'].append('Club agreement withdrawn. Reservations released.')
        transfer_rights.withdrawn(s,d)
        return 'Discussion withdrawn; reservations released.'
    registration_check(s,p,d['target'])
    require(p['club']==d['source'] and (can_release(s,p,d['source']) or d['kind']!='loan' and transfer_rights.exit_met(s,p,d)),'Registration or selling-club squad cover changed.')
    require(day<=d['expires'],'The club offer expired.')
    if action=='club_propose':
        require(d['kind']=='buy' and d['status'] in ('quote','counter'),'Club terms cannot be revised at this stage.')
        fee=data.get('fee');percent=data.get('upfront_percent');defer=data.get('defer_days')
        require(type(fee) is int and 0<=fee<=100000000,'Choose a transfer fee between £0 and £1,000,000.')
        require(type(percent) is int and cfg['minimum_upfront_percent']<=percent<=100,'At least half of the transfer fee is payable immediately.')
        require(type(defer) is int and 7<=defer<=cfg['max_installment_days'],'Deferred payment must be due within 7–56 days.')
        sell_on=clauses.validate_sell_on(s,data)
        addons=contract_terms.transfer_terms(s,{**d,**data})
        release=transfer_rights.enforced_amount(s,p,d['target'])
        if release and fee>=release:
            require(percent==100 and not sell_on['sell_on_percent'] and not addons['appearance_fee'] and not addons['promotion_fee'] and not addons['buy_back_fee'] and not addons['first_refusal'],'Release amount must be paid in full without conditional club terms.')
        proposal=[fee,percent,defer,*sell_on.values(),*addons.values()];require(proposal!=d.get('last_proposal'),'The club has already considered these terms.')
        d['last_proposal']=proposal;d['rounds']+=1
        minimum=quote(s,p,d['target']);accepted=fee>=minimum
        d.update(fee=fee if accepted else minimum,upfront=(fee if accepted else minimum)*percent//100,defer_days=defer,status='agreed' if accepted else 'counter')
        d.update(sell_on,**addons)
        if not accepted and d['rounds']>=3:d['status']='rejected'
        d['transcript'].append('Club: Accepted. Personal terms remain outstanding.' if accepted else 'Club: The minimum fee is our quoted valuation.' if d['status']=='counter' else 'Club: Negotiations ended after three unsuccessful proposals.')
        return 'Club response recorded. No fee has been paid.'
    if action=='club_accept':
        require(d['kind']=='buy' and d['status'] in ('agreed','counter'),'Submit a club offer first.')
        if transfer_rights.notify(s,d):return 'First refusal notified. Wait for the holder’s response in Transfers > Rights.'
        d['status']='seller_agreed';d['transcript'].append('Club terms agreed subject to personal terms, medical and registration.')
        return 'Selling-club consent recorded. Open personal terms to continue.'
    if action=='sale_terms':
        require(d['kind']=='sale' and d['status']=='quote','Only an unaccepted sale quote can change.')
        sell_on=clauses.validate_sell_on(s,data)
        addons=contract_terms.transfer_terms(s,{**d,**data})
        # Transparent preview valuation: retained upside reduces today's bid.
        discount=sell_on['sell_on_percent'] if sell_on['sell_on_kind']=='gross' else sell_on['sell_on_percent']//2
        discount+=s['config']['clauses']['buyback_discount'] if addons['buy_back_fee'] else 0
        discount+=s['config']['clauses']['refusal_discount'] if addons['first_refusal'] else 0
        fee=quote(s,p,d['target'])*(100-discount)//100
        require(not addons['buy_back_fee'] or addons['buy_back_fee']>=fee,'The buyer requires a buy-back price at least equal to its transfer valuation.')
        # Until risk-based AI valuation lands, a buyer caps the entire possible
        # package at its valuation; adding a bonus cannot create a free claim.
        contingent=addons['appearance_fee']+addons['promotion_fee']
        require(contingent<=fee,'Conditional payments exceed the buyer’s total valuation. Reduce the bonuses.')
        fee-=contingent
        d.update(sell_on,**addons,fee=fee,upfront=fee)
        d['transcript'].append(f"Buyer: £{fee/100:,.0f} guaranteed plus up to £{contingent/100:,.0f} conditional; {sell_on['sell_on_percent']}% {sell_on['sell_on_kind']} sell-on terms.")
        return 'Buyer quote revised. No funds or registration changed.'
    if action=='loan_terms':
        require(d['kind']=='loan' and d['status']=='quote','Only an unaccepted loan quote can change.')
        share=data.get('share');days=data.get('days')
        require(type(share) is int and 50<=share<=100,'The borrower must cover 50–100% of wages.')
        require(type(days) is int and cfg['minimum_loan_days']<=days<=84,'Choose a loan of 14–84 days.')
        require(day+cfg['medical_days']+days<=p['contract_end'],'The loan and medical must fit before employment expires.')
        fee=cfg['loan_fee']+p['wage']*(100-share)*days//700
        d.update(share=share,days=days,end=day+cfg['medical_days']+days,fee=fee,upfront=fee,wage_cost=p['wage']*share//100)
        d.update(loan_clauses.terms(s,d,data))
        d['transcript'].append('Revised loan quote: reduced recurring wage cover is offset by a larger fee.')
        return 'Loan quote revised. No payment or registration change.'
    require(d['kind'] in ('loan','sale'),'Complete purchases through the personal contract workflow.')
    if d['kind']=='loan':registration.check_arrival(s,p,d['target'],is_loan=True)
    if action=='market_accept':
        require(d['status']=='quote','This deal has already been accepted.')
        if d['kind']=='sale' and transfer_rights.notify(s,d):return 'First refusal notified. Wait for the holder’s response in Transfers > Rights.'
        require(day+cfg['medical_days']<=d['expires'],'Medical checks cannot finish before this offer expires.')
        require(s['manager'] is not None,'Appoint a manager first.')
        if d['kind']=='loan' and d.get('days') is not None:
            require(day+cfg['medical_days']+d['days']<=p['contract_end'],'The full loan term no longer fits before employment expires.')
            d['end']=day+cfg['medical_days']+d['days']
            if d.get('purchase_kind')=='obligation':require(d['end']+1<=window_end(s),'Purchase settlement no longer fits the registration window.')
        fees,wages=reservations(s) if d['target']=='c0' else extra_reservations(s,d['target'])
        require(club_cash(s,d['target'])-fees-d['fee']-loan_clauses.reserve(d)>=s['config']['operating_buffer'],'The receiving club has insufficient unreserved cash.')
        if d['target']=='c0':require(club_payroll(s,'c0')+wages+max(d['wage_cost'],d.get('purchase_wage',0) if loan_clauses.reserve(d) else 0)<=s['budget'],'Incoming loan exceeds wage capacity.')
        elif 'club_ai' in s:
            from .club_ai import budgets
            b=budgets(s,d['target'])
            require(club_payroll(s,d['target'])+wages+max(d['wage_cost'],d.get('purchase_wage',0) if loan_clauses.reserve(d) else 0)<=b['wage_limit'],'The receiving club cannot authorise these wages.')
            require(club_cash(s,d['target'])-fees-d['fee']-loan_clauses.reserve(d)-b['bills']>=b['reserve']+d['wage_cost']*s['config']['club_ai']['reserve_weeks'],'The receiving club must retain cover for its existing bills and running costs.')
        d.update(status='medical',due=day+cfg['medical_days'])
        d['transcript'].append('Player: Temporary placement agreed.' if d['kind']=='loan' else 'Player: The receiving club employment terms are accepted.')
        return 'Consent recorded and medical booked. Receiving-club capacity reserved.'
    require(action=='market_complete' and d['status']=='ready','Wait for medical and final review.')
    fees,wages=reservations(s) if d['target']=='c0' else extra_reservations(s,d['target'])
    require(club_cash(s,d['target'])-fees>=s['config']['operating_buffer'],'Receiving-club cash changed; revise funding first.')
    if d['target']=='c0':require(club_payroll(s,'c0')+wages<=s['budget'] and s['manager'] is not None,'Incoming loan lacks manager or wage capacity.')
    elif 'club_ai' in s:
        from .club_ai import budgets
        b=budgets(s,d['target'])
        require(club_payroll(s,d['target'])+wages<=b['wage_limit'],'The receiving club’s payroll authority changed.')
        require(club_cash(s,d['target'])-fees-b['bills']>=b['reserve'],'The receiving club must retain its committed cash cover.')
    transfer_cash(s,d['id']+':fee',d['target'],d['source'],d['fee'],'Loan fee' if d['kind']=='loan' else 'Player transfer')
    if d['kind']=='loan':
        if d.get('days') is not None:d['end']=day+d['days']
        require(p['contract_end']>=d['end'] and day<d['end'],'Loan dates no longer fit employment.')
        if d.get('purchase_kind')=='obligation':require(d['end']+1<=window_end(s),'Purchase settlement no longer fits the registration window.')
        s['market']['loans'].append(dict(id=d['id'],player=p['id'],source=d['source'],target=d['target'],start=day,end=d['end'],share=d['share'],fee=d['fee'],status='active',**{k:v for k,v in d.items() if k.startswith('purchase_')},purchase_fixtures=[]))
    else:
        from .career import contractual_end
        d['employment_end']=contractual_end(s,2)
        clauses.complete_sale(s,d)
        p['contract_end']=d['employment_end']
    p['club']=d['target'];d.update(status='completed',completed=day)
    if d['kind']=='sale':transfer_rights.ai_employment(s,p,d['target'],p['wage'],p['contract_end'],d['id'])
    d['transcript'].append('Fee settled and registration completed atomically.')
    news(s,'Loan registered' if d['kind']=='loan' else 'Player sold',p['name']+': fees, payroll responsibility and registration updated together.')
    return 'Club transaction completed. Existing statistics and identity retained.'
