"""Dated repurchase rights, matching notices and player buy-out compensation.

All mutations run inside the simulation's copy-on-commit transaction. A right
settles club permission only; personal employment still has its own consent.
"""
from copy import deepcopy

TERMS=dict(buy_back_fee=0,buy_back_later=0,rights_seasons=2,first_refusal=False)
PACKAGE=('fee','upfront','defer_days','sell_on_kind','sell_on_percent',
         'appearance_fee','appearance_count','promotion_fee',*TERMS)


def initialise(s):
    for key in ('rights','notices','buyouts'):s['clauses'].setdefault(key,[])
    cfg=s['config']['clauses']
    cfg.setdefault('right_notice_days',3)
    cfg.setdefault('buyback_discount',20)
    cfg.setdefault('refusal_discount',5)
    cfg.setdefault('ai_buyout_multiple',2)
    # Supported game profiles, not a claim that other jurisdictions prohibit
    # all negotiated termination agreements. Northshire is fictional.
    cfg.setdefault('release_profiles',{'northshire':['transfer','buyout'],
                                     'spain':['transfer','buyout'],'default':['transfer']})


def allowed_kinds(s,employer='c0'):
    club=next((c for c in s['clubs'] if c['id']==employer),{})
    nation=club.get('nation',s['config'].get('nation',{}).get('id','northshire'))
    profiles=s['config']['clauses']['release_profiles']
    return profiles.get(nation,profiles['default'])


def dates(s,seasons):
    from .career import season_end,contractual_end
    from .nations import add_year
    span=season_end(s)-s['career']['start']+s['config']['career']['season_gap']
    start=s['calendar']['next_start'] if s.get('calendar') else s['career']['start']+span
    second=add_year(s['config']['start_date'],start) if s.get('calendar') else start+span
    return start,second,contractual_end(s,seasons+1)


def terms(s,data):
    from .simulation import require
    t={k:data.get(k,v) for k,v in TERMS.items()}
    for k in ('buy_back_fee','buy_back_later'):
        require(type(t[k]) is int and 0<=t[k]<=100000000,'Buy-back prices must be £0–£1,000,000.')
    require(type(t['first_refusal']) is bool,'First refusal must be on or off.')
    require(type(t['rights_seasons']) is int and 1<=t['rights_seasons']<=3,'Choose one to three future seasons of rights.')
    require(not t['buy_back_fee'] or not t['buy_back_later'] or t['buy_back_later']>=t['buy_back_fee'],'The later buy-back price cannot be below the first price.')
    if not t['buy_back_fee']:t['buy_back_later']=0
    return t


def description(t):
    rows=[]
    if t.get('buy_back_fee'):
        rows.append(f"Seller buy-back: £{t['buy_back_fee']/100:,.0f} in the next season's window; £{(t.get('buy_back_later') or t['buy_back_fee'])/100:,.0f} in later eligible windows.")
    if t.get('first_refusal'):rows.append('Seller has first refusal on the complete terms of a future voluntary transfer.')
    if rows:rows.append(f"Valid through {t.get('rights_seasons',2)} future seasons; ends on release or next permanent departure. Personal consent remains required. Buy-out termination is excluded from first refusal and sell-on.")
    return ' '.join(rows)


def eligible(s,r,p,beneficiary=None):
    return (r['status']=='active' and r['player']==p['id'] and r['liable']==p['club']
            and (beneficiary is None or beneficiary==r['beneficiary'])
            and s['day']<=r['expiry'] and not p['retired'] and p['contract_end']>=s['day'])


def buy_back(s,p,buyer):
    return next((r for r in s['clauses']['rights'] if r['kind']=='buyback' and eligible(s,r,p,buyer)
                 and s['day']>=r['start']),None)


def price(s,r):return r['later_fee'] if s['day']>=r['second'] else r['fee']


def enforced_amount(s,p,buyer):
    from .contract_terms import release_amount
    amounts=[release_amount(s,p,p['club'])]
    r=buy_back(s,p,buyer) if buyer is not None else None
    if r:amounts.append(price(s,r))
    return min((n for n in amounts if n),default=0)


def exit_met(s,p,d):
    if d.get('exit_kind')=='buyout':
        check_exit(s,p,d);return True
    amount=enforced_amount(s,p,d['target'])
    return bool(amount and d['fee']>=amount and d.get('upfront',d['fee'])>=amount)


def check_exit(s,p,d):
    from .simulation import require
    if d.get('notice_id'):
        n=next((n for n in s['clauses']['notices'] if n['id']==d['notice_id']),None)
        require(n is not None and n['status']=='matching' and n['match_id']==d['id']
                and origin(s,n)['status']=='rights_wait' and s['day']<=n['expires']
                and package(d)==n['package'], 'The matched offer is no longer available on these terms.')
    trigger=d.get('exit_kind')
    if trigger=='buyback':
        r=buy_back(s,p,d['target'])
        require(r is not None and r['id']==d['right_id'] and d['fee']==price(s,r),'The buy-back right or dated price changed. Reopen the discussion.')
    elif trigger=='buyout':
        c=s['clauses']['employment'].get(p['id'])
        require(c is not None and c['id']==d['exit_contract'] and c.get('release_kind')=='buyout'
                and c['employer']==p['club'] and c['start']<=s['day']<=c['end'] and c['release_fee']==d['fee'],
                'The buy-out amount or employment agreement changed.')
    elif trigger=='release':
        from .contract_terms import release_amount
        amount=release_amount(s,p,p['club'])
        require(amount>0 and d['fee']>=amount,'The transfer release clause is no longer satisfied.')
    if trigger:require(d.get('upfront',d['fee'])==d['fee'],'A contractual exit must be funded in full.')


def complete(s,d):
    for r in s['clauses']['rights']:
        if r['player']==d['player'] and r['liable']==d['source'] and r['status']=='active':
            r.update(status='exercised' if r['beneficiary']==d['target'] else 'ended',closed=s['day'],sale=d['id'])
    for n in s['clauses']['notices']:
        if n.get('match_id')==d['id']:
            n['status']='completed';original=origin(s,n)
            original.update(status='cancelled' if n['origin_kind']=='ai' else 'withdrawn')
            original.setdefault('transcript',[]).append('First-refusal holder completed on the matched terms.')
    if d.get('exit_kind')=='buyout':return
    start,second,expiry=dates(s,d.get('rights_seasons',2))
    for kind,enabled in (('buyback',d.get('buy_back_fee',0)),('refusal',d.get('first_refusal',False))):
        if enabled:
            s['clauses']['rights'].append(dict(id=d['id']+':'+kind,kind=kind,player=d['player'],beneficiary=d['source'],
                liable=d['target'],start=start if kind=='buyback' else s['day'],second=second,expiry=expiry,
                fee=d.get('buy_back_fee',0),later_fee=d.get('buy_back_later') or d.get('buy_back_fee',0),status='active'))


def release(s,pid,employer):
    for r in s['clauses']['rights']:
        if r['player']==pid and r['liable']==employer and r['status']=='active':r.update(status='ended',closed=s['day'])


def origin(s,n):
    if n['origin_kind']=='club':return s['market']['deals'][n['origin_id']]
    return next(d for d in s['club_ai']['decisions'] if d['id']==n['origin_id'])


def package(d):
    defaults=dict(upfront=d['fee'],defer_days=28,sell_on_kind='none',sell_on_percent=0,
                  appearance_fee=0,appearance_count=10,promotion_fee=0,**TERMS)
    return {k:deepcopy(d.get(k,defaults.get(k))) for k in PACKAGE}


def notify(s,d,origin_kind='club'):
    """Hold a voluntary sale until the exact package has been considered."""
    from .simulation import news,require
    from .career import person,window_end
    p=person(s,d['player']);buyer=d.get('target',d.get('club'))
    if d.get('exit_kind') in ('buyout','buyback') or d.get('notice_id'):return False
    r=next((r for r in s['clauses']['rights'] if r['kind']=='refusal' and eligible(s,r,p)
            and buyer!=r['beneficiary']),None)
    if not r:return False
    terms_=package(d)
    old=next((n for n in reversed(s['clauses']['notices']) if n['origin_id']==d['id'] and n['package']==terms_),None)
    if old:return old['status'] in ('pending','matching')
    medical=s['config']['market']['medical_days']
    expiry=min(d.get('expires',window_end(s)),window_end(s))
    require(expiry-s['day']>=medical+2,'The offer leaves no time for first refusal and medical. Reopen it earlier in a window.')
    n=dict(id=d['id']+':notice:'+str(len(s['clauses']['notices'])),right=r['id'],player=p['id'],source=p['club'],
           beneficiary=r['beneficiary'],other_buyer=buyer,origin_kind=origin_kind,origin_id=d['id'],
           resume=d['status'],package=terms_,created=s['day'],deadline=min(s['day']+s['config']['clauses']['right_notice_days'],expiry-medical-1,r['expiry']),
           expires=expiry,status='pending',match_id=None)
    s['clauses']['notices'].append(n);d['status']='rights_wait'
    news(s,'First-refusal notice',p['name']+': the rights holder can match the complete package before the response deadline. Registration is paused.')
    return True


def resume(s,n,status):
    n['status']=status;d=origin(s,n)
    if d['status']!='rights_wait':return
    d['status']=n['resume']
    if n['origin_kind']=='ai':d['due']=s['day']+s['config']['club_ai']['medical_days']


def cancel_notice(s,n):
    """Unwind both consent and reservations when the underlying sale disappears."""
    from . import market
    n['status']='cancelled'
    if not n.get('match_id'):return
    if n['beneficiary']=='c0':
        d=s['market']['deals'][n['match_id']]
        if d['status'] not in market.TERMINAL:
            d['status']='withdrawn';d['transcript'].append('The underlying sale was withdrawn or expired; matched consent is cancelled.')
        o=s['career']['offers'].get(n['player'])
        if o and o.get('deal_id')==d['id'] and o['status'] not in market.TERMINAL:
            o['status']='withdrawn';o['transcript'].append('Matched club consent ended. Reservations released.')
    else:
        d=next(d for d in s['club_ai']['decisions'] if d['id']==n['match_id'])
        if d['status']!='completed':d.update(status='cancelled',outcome='Underlying first-refusal sale ended.')


def withdrawn(s,d):
    for n in s['clauses']['notices']:
        if n['status'] not in ('pending','matching'):continue
        if n['origin_id']==d['id']:cancel_notice(s,n)
        elif n.get('match_id')==d['id']:resume(s,n,'failed')


def cancel_match(s,n):
    """Withdraw related consent too when the original sale disappears."""
    if not n.get('match_id'):return
    if n['beneficiary']=='c0':
        d=s['market']['deals'][n['match_id']]
        if d['status']!='completed':d['status']='withdrawn'
        o=s['career']['offers'].get(n['player'])
        if o and o.get('deal_id')==d['id'] and o['status']!='completed':
            o['status']='withdrawn';o['transcript'].append('The original sale or matching deadline ended.')
    else:
        d=next(d for d in s['club_ai']['decisions'] if d['id']==n['match_id'])
        if d['status']!='completed':d.update(status='cancelled',outcome='The original sale or matching deadline ended.')


def personal_accepts(p,wage,end,day):
    # A player can reject an automated clause move for insufficient incentive.
    # Human buyers use the normal negotiable agent/medical workflow instead.
    minimum=p['wage']*(120 if p['morale']>=85 else 105)//100
    return wage>=minimum and end>max(day,p['contract_end'])


def ai_employment(s,p,cid,wage,end,ident):
    """New AI employment can agree an exit price; migration invents none."""
    if 'buyout' not in allowed_kinds(s,cid) or 'release_fee' not in s['config']['clauses']['allowed_employment']:return
    from . import clauses
    amount=min(100000000,p['fee']*s['config']['market']['asking_multiple']*s['config']['clauses']['ai_buyout_multiple'])
    clauses.sign(s,p,dict(id=ident,end=end,release_kind='buyout',release_fee=amount),employer=cid)


def ai_affordable(s,p,cid,pack,wage):
    from . import market,club_ai,registration
    b=club_ai.budgets(s,cid)
    maximum=pack['fee']+pack.get('appearance_fee',0)+pack.get('promotion_fee',0)+p['fee']
    if (market.club_cash(s,cid)-b['fees']-b['bills']-maximum<b['reserve']+wage*s['config']['club_ai']['reserve_weeks']
        or market.club_payroll(s,cid)+b['wages']+wage>b['wage_limit']):return False
    try:registration.check_arrival(s,p,cid)
    except ValueError:return False
    return True


def match(s,n):
    from . import career,market
    from .simulation import require,news
    p=career.person(s,n['player']);cid=n['beneficiary']
    require(n['status']=='pending' and s['day']<=n['deadline'],'The matching deadline has passed.')
    require(p['club']==n['source'] and not market.active_loan(s,p['id']),'The player is no longer available for this sale.')
    key=n['id']+':match';d=dict(deepcopy(n['package']),id=key,player=p['id'],source=p['club'],target=cid,
        notice_id=n['id'],expires=n['expires'],transcript=['First-refusal holder matched the entire club package. Personal consent remains outstanding.'])
    if cid=='c0':
        fees,_=career.reservations(s)
        require(s['cash']-fees-d['upfront']>=s['config']['operating_buffer'],'Insufficient unreserved cash for the matched upfront fee.')
        d.update(kind='buy',status='seller_agreed',wage_cost=p['wage'],rounds=0,share=100,days=None,end=None)
        s['market']['deals'][key]=d
    else:
        wage=p['wage']*110//100;end=max(career.contractual_end(s,2),p['contract_end']+1)
        require(ai_affordable(s,p,cid,d,wage),'The matching club cannot fund the complete package.')
        from . import recruitment
        recruitment.check(s,p,cid,wage,end)
        d['interest_policy']=1
        d.update(club=cid,day=s['day'],due=s['day']+s['config']['club_ai']['medical_days'],status='medical',
                 signing_fee=p['fee'],wage=wage,end=end,reason='Exercise first refusal on matched terms after player consent.',outcome=None)
        s['club_ai']['decisions'].append(d)
    n.update(status='matching',match_id=key)
    news(s,'First refusal matched',p['name']+': the matching club must complete the separate employment and registration checks before the original deadline.')


def process_day(s):
    from . import market,career
    for r in s['clauses']['rights']:
        if r['status']=='active' and s['day']>r['expiry']:r.update(status='expired',closed=s['day'])
    for n in s['clauses']['notices']:
        if n['status'] not in ('pending','matching'):continue
        p=career.person(s,n['player']);original=origin(s,n)
        if (p['club']!=n['source'] or s['day']>n['expires']
            or original['status'] in market.TERMINAL or original['status']=='cancelled'):
            cancel_notice(s,n)
            if original['status']=='rights_wait':
                original.update(status='cancelled' if n['origin_kind']=='ai' else 'expired')
            continue
        if n['status']=='matching':
            matched=s['market']['deals'].get(n['match_id']) if n['beneficiary']=='c0' else next(d for d in s['club_ai']['decisions'] if d['id']==n['match_id'])
            if matched['status'] in market.TERMINAL or matched['status']=='cancelled':resume(s,n,'failed')
        elif s['day']>n['deadline']:resume(s,n,'expired')
        elif n['beneficiary']!='c0' and s['day']>n['created']:
            total=n['package']['fee']+n['package']['appearance_fee']+n['package']['promotion_fee']
            if total>p['fee']*s['config']['market']['asking_multiple']:resume(s,n,'declined');continue
            try:match(s,n)
            except ValueError:resume(s,n,'declined')


def apply(s,action,data):
    if action not in ('right_enquire','buyout_enquire','refusal_match','refusal_decline'):return None
    from . import market,career
    from .simulation import require
    require(s['match'] is None,'Finish matchday before exercising transfer rights.')
    if action in ('refusal_match','refusal_decline'):
        n=next((n for n in s['clauses']['notices'] if n['id']==data.get('id')),None)
        require(n is not None and n['beneficiary']=='c0' and n['status']=='pending' and s['day']<=n['deadline'],'No pending first-refusal response is available.')
        if action=='refusal_match':match(s,n);return 'Complete personal terms for the matched transfer in Transfers.'
        resume(s,n,'declined');return 'First refusal declined for this exact offer; the original transaction can proceed.'
    p=career.person(s,data.get('id'));require(p['club'] not in (None,'c0'),'Select a player employed by another club.')
    require(market.active_deal(s,p['id']) is None,'Resolve the existing club discussion first.')
    o=s['career']['offers'].get(p['id']);require(not o or o['status'] in market.TERMINAL,'Resolve the existing personal discussion first.')
    market.registration_check(s,p,'c0')
    if action=='right_enquire':
        r=buy_back(s,p,'c0');require(r is not None,'No active buy-back right is available in this season.')
        fee=price(s,r);extra=dict(exit_kind='buyback',right_id=r['id']);expiry=r['expiry']
    else:
        c=s['clauses']['employment'].get(p['id'])
        require(c and c['employer']==p['club'] and c.get('release_kind')=='buyout' and c.get('release_fee')
                and c['start']<=s['day']<=c['end'],'No agreed player buy-out is available.')
        fee=c['release_fee'];extra=dict(exit_kind='buyout',exit_contract=c['id']);expiry=c['end']
    key=f"exit:{p['id']}:{s['revision']}"
    s['market']['deals'][key]=dict(id=key,player=p['id'],kind='buy',source=p['club'],target='c0',status='seller_agreed',
        fee=fee,upfront=fee,defer_days=28,share=100,days=None,end=None,wage_cost=p['wage'],rounds=0,
        expires=min(expiry,career.window_end(s),s['day']+s['config']['market']['quote_days']),
        transcript=['Contractual exit opened. Full funding and fresh player employment consent are required; no money or registration changed.'],**extra)
    return 'Contractual club condition recorded. Negotiate personal terms before committing any payment.'


def validate(s):
    from .simulation import require
    cfg=s['config']['clauses'];ids={p['id'] for p in s['players']};clubs={c['id'] for c in s['clubs']}
    require(type(cfg['right_notice_days']) is int and 1<=cfg['right_notice_days']<=14,'Invalid first-refusal notice period.')
    for k in ('buyback_discount','refusal_discount'):
        require(type(cfg[k]) is int and 0<=cfg[k]<=20,'Invalid retained-right valuation discount.')
    require(type(cfg['ai_buyout_multiple']) is int and 1<=cfg['ai_buyout_multiple']<=10,'Invalid AI buy-out pricing.')
    require('default' in cfg['release_profiles'] and all(isinstance(v,list) and v and set(v)<={'transfer','buyout'} for v in cfg['release_profiles'].values()),'Invalid release-clause country profiles.')
    for key in ('rights','notices','buyouts'):
        rows=s['clauses'][key];require(len({r['id'] for r in rows})==len(rows),'Duplicate transfer-right record.')
    for r in s['clauses']['rights']:
        require(r['player'] in ids and r['beneficiary'] in clubs and r['liable'] in clubs and r['beneficiary']!=r['liable'],'Invalid transfer-right parties.')
        require(r['kind'] in ('buyback','refusal') and r['status'] in ('active','exercised','ended','expired'),'Invalid transfer-right state.')
        require(all(type(r[k]) is int for k in ('start','second','expiry','fee','later_fee')) and r['start']<=r['expiry'] and 0<=r['fee']<=r['later_fee']<=100000000,'Invalid dated transfer right.')
    for n in s['clauses']['notices']:
        require(n['player'] in ids and n['beneficiary'] in clubs and n['source'] in clubs and n['other_buyer'] in clubs,'Invalid matching parties.')
        require(n['created']<=n['deadline']<=n['expires'] and n['status'] in ('pending','matching','declined','expired','failed','cancelled','completed'),'Invalid matching notice state.')
        require(n['package']['fee']>=n['package']['upfront']>=0,'Invalid matched payment schedule.')
        origin(s,n)
    for b in s['clauses']['buyouts']:
        require(b['player'] in ids and b['sponsor'] in clubs and b['employer'] in clubs and b['amount']>0 and b['player_consent'],'Invalid buy-out compensation receipt.')
