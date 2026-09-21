"""Dated employment changes and conditional club payments; all amounts in pence."""
from copy import deepcopy
from . import nations

EMPLOYMENT=dict(player_option=False,release_fee=0,annual_raise=0,relegation_cut=0,promotion_bonus=0)
TRANSFER=dict(appearance_fee=0,appearance_count=10,promotion_fee=0)


def initialise(s):
    s['clauses'].setdefault('conditional',[])
    s['config']['clauses'].setdefault('allowed_employment',list(EMPLOYMENT))
    s['config']['clauses'].setdefault('player_option_notice',14)


def terms(data):return {k:data.get(k,v) for k,v in EMPLOYMENT.items()}


def validate_terms(s,data):
    from .simulation import require
    t=terms(data)
    require(type(t['player_option']) is bool,'Player option must be on or off.')
    require(not(t['player_option'] and data.get('club_option')),'Club and player options cannot coexist.')
    for k,limit in (('release_fee',100000000),('promotion_bonus',10000000),('annual_raise',25),('relegation_cut',50)):
        require(type(t[k]) is int and 0<=t[k]<=limit,'Invalid '+k.replace('_',' ')+'.')
    for k,v in t.items():require(not v or k in s['config']['clauses']['allowed_employment'],'This ruleset does not permit '+k.replace('_',' ')+'.')
    return t


def transfer_terms(s,data):
    from .simulation import require
    t={k:data.get(k,v) for k,v in TRANSFER.items()}
    for k in ('appearance_fee','promotion_fee'):
        require(type(t[k]) is int and 0<=t[k]<=100000000,'Conditional club payments must be £0–£1,000,000.')
    require(type(t['appearance_count']) is int and 1<=t['appearance_count']<=100,'Appearance threshold must be 1–100 matches.')
    return t


def description(t):
    rows=[]
    if t.get('player_option'):rows.append('Player option: one additional season; the player decides near expiry.')
    if t.get('release_fee'):rows.append(f"Fixed release amount £{t['release_fee']/100:,.0f}, paid in full; personal consent and registration still required.")
    if t.get('annual_raise'):rows.append(f"Annual wage increase {t['annual_raise']}% on each signing anniversary.")
    if t.get('relegation_cut'):rows.append(f"Relegation wage reduction {t['relegation_cut']}% at division rollover.")
    if t.get('promotion_bonus'):rows.append(f"One promotion bonus £{t['promotion_bonus']/100:,.0f} during this employment agreement.")
    return ' '.join(rows)


def transfer_description(t):
    return (f"After {t.get('appearance_count',10)} appearances: £{t.get('appearance_fee',0)/100:,.0f}; "
            f"first promotion: £{t.get('promotion_fee',0)/100:,.0f}. Each once, before the new employment end date.")


def projected(wage,c,origin,day):
    due=c.get('next_raise');rate=c.get('annual_raise',0)
    while rate and due is not None and due<=min(day,c['end']):
        wage=wage*(100+rate)//100;due=nations.add_year(origin,due)
    return wage


def guaranteed(wage,start,end,rate,origin):
    due=nations.add_year(origin,start);total=0;cursor=start
    while due<=end and rate:
        total+=wage*(due-cursor);cursor=due;wage=wage*(100+rate)//100;due=nations.add_year(origin,due)
    return (total+wage*max(0,end-cursor))//7


def remaining(wage,c,start,end,origin):
    due=c.get('next_raise');rate=c.get('annual_raise',0);cursor=start;total=0
    while rate and due is not None and due<=end:
        if due>cursor:total+=wage*(due-cursor);cursor=due
        wage=wage*(100+rate)//100;due=nations.add_year(origin,due)
    return (total+wage*max(0,end-cursor))//7


def process_day(s):
    from .simulation import news
    from .career import person
    from .market import active_loan
    for pid,c in s['clauses']['employment'].items():
        p=person(s,pid);loan=active_loan(s,pid);employer=loan['source'] if loan else p['club']
        if employer!=c['employer'] or p['retired']:continue
        if c.get('player_option') and c['option_status']=='available' and c['end']-s['day']<=s['config']['clauses']['player_option_notice']:
            if s['day']>c['end']:c['option_status']='expired';continue
            # A first transparent choice: retain security when settled, or when
            # existing pay meets the player's current domestic wage benchmark.
            from .people import overall
            benchmark=(450+overall(p,s['config']['people']['weights'])*13)*100
            take=p['morale']>=40 or p['wage']>=benchmark
            c['option_status']='exercised' if take else 'declined';c['option_decided']=s['day']
            if take:p['contract_end']=c['end']=c['option_end']
            news(s,'Player option decision',p['name']+(' exercised the signed extension for continued security.' if take else ' declined the extension and will seek different terms.'))
        wage=projected(p['wage'],c,s['config']['start_date'],s['day'])
        if wage!=p['wage']:
            p['wage']=wage
            while c['next_raise']<=min(s['day'],c['end']):c['next_raise']=nations.add_year(s['config']['start_date'],c['next_raise'])
            news(s,'Contracted wage increase',p['name']+f": annual salary clause now pays £{wage/100:,.0f} per week.")
    for c in s['clauses']['conditional']:
        if c['status']=='pending' and s['day']>c['expiry']:c['status']='expired'


def release_amount(s,p,source):
    c=s['clauses']['employment'].get(p['id'])
    return c.get('release_fee',0) if c and c['employer']==source and c['start']<=s['day']<=c['end'] else 0


def release_met(s,p,d):
    amount=release_amount(s,p,d['source'])
    return bool(amount and d['fee']>=amount and d.get('upfront',d['fee'])>=amount)


def signed_sale(s,d):
    for trigger,amount in (('appearances',d.get('appearance_fee',0)),('promotion',d.get('promotion_fee',0))):
        if not amount:continue
        s['clauses']['conditional'].append(dict(id=d['id']+':'+trigger,player=d['player'],source=d['target'],target=d['source'],
            trigger=trigger,amount=amount,threshold=d.get('appearance_count',10),count=0,fixtures=[],paid=0,status='pending',
            start=s['day'],expiry=d['employment_end']))


def record_match(s,m):
    if m.get('forfeit'):return
    for c in s['clauses']['conditional']:
        if c['status']!='pending' or c['trigger']!='appearances' or not c['start']<=s['day']<=c['expiry']:continue
        if c['source'] not in (m['home'],m['away']) or m['fixture'] in c['fixtures']:continue
        side=0 if m['home']==c['source'] else 1
        if c['player'] not in m.get('participants',m['lineups'])[side]:continue
        c['fixtures'].append(m['fixture']);c['count']+=1
        if c['count']>=c['threshold']:c.update(status='due',due=s['day'])


def movements(s,rollover=False):
    from .career import person
    from .simulation import news
    promoted={m['club'] for m in s['leagues']['movements'] if m['kind']=='Promoted'}
    relegated={m['club'] for m in s['leagues']['movements'] if m['kind']=='Relegated'}
    for pid,c in s['clauses']['employment'].items():
        if not c['start']<=s['day']<=c['end']:continue
        if rollover and c['employer'] in relegated and c.get('relegation_cut') and c.get('last_relegation')!=s['career']['season']:
            p=person(s,pid);p['wage']=p['wage']*(100-c['relegation_cut'])//100;c['last_relegation']=s['career']['season']
            news(s,'Relegation wage clause',p['name']+f": agreed reduction applied; £{p['wage']/100:,.0f} per week.")
        if not rollover and c['employer'] in promoted and c.get('promotion_bonus') and not c.get('promotion_paid'):
            c['promotion_paid']=True
            s['clauses']['payables'].append(dict(id=c['id']+':promotion',player=pid,source=c['employer'],trigger='promotion',units=1,
                amount=c['promotion_bonus'],paid=0,due=s['day'],status='due'))
    if not rollover:
        for c in s['clauses']['conditional']:
            if c['status']=='pending' and c['trigger']=='promotion' and c['source'] in promoted and c['start']<=s['day']<=c['expiry']:
                c.update(status='due',due=s['day'])


def settle(s):
    from .market import transfer_cash,club_cash
    for c in s['clauses']['conditional']:
        if c['status'] not in ('due','arrears'):continue
        amount=min(c['amount']-c['paid'],max(0,club_cash(s,c['source'])))
        if amount:transfer_cash(s,c['id']+':'+str(c['paid']),c['source'],c['target'],amount,'Conditional transfer payment')
        c['paid']+=amount;c['status']='paid' if c['paid']==c['amount'] else 'arrears'


def validate(s):
    from .simulation import require
    cfg=s['config']['clauses']
    require(type(cfg['player_option_notice']) is int and 0<=cfg['player_option_notice']<=60,'Invalid player option notice.')
    require(isinstance(cfg['allowed_employment'],list) and set(cfg['allowed_employment'])<=set(EMPLOYMENT),'Invalid employment ruleset.')
    for c in s['clauses']['employment'].values():
        if c.get('annual_raise'):require(type(c.get('next_raise')) is int and c['next_raise']>c['start'],'Invalid annual wage date.')
    rows=s['clauses']['conditional'];ids={p['id'] for p in s['players']};clubs={c['id'] for c in s['clubs']}
    require(len({c['id'] for c in rows})==len(rows),'Duplicate conditional transfer clause.')
    for c in rows:
        require(c['player'] in ids and c['source'] in clubs and c['target'] in clubs and c['source']!=c['target'],'Invalid conditional transfer parties.')
        require(c['trigger'] in ('appearances','promotion') and c['status'] in ('pending','due','arrears','paid','expired'),'Invalid conditional trigger state.')
        require(type(c['amount']) is int and type(c['paid']) is int and 0<=c['paid']<=c['amount'] and c['start']<=c['expiry'],'Invalid conditional payment.')
        require(len(c['fixtures'])==len(set(c['fixtures'])) and c['count']==len(c['fixtures']),'Duplicate conditional appearance.')
