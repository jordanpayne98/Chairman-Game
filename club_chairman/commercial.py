"""Fictional sponsorship rights with consent, exclusivity and dated payments."""
from copy import deepcopy

DEFAULTS=dict(quote_days=7,min_weeks=4,max_weeks=16,naming_sentiment=-5,
              rights={'training':{'name':'Training partner','weekly':120000,'sponsor':'Northshire Tools'},
                      'digital':{'name':'Digital partner','weekly':80000,'sponsor':'Beacon Broadband'},
                      'stadium':{'name':'Stadium naming rights','weekly':200000,'sponsor':'Hartwell Energy'}})


def initialise(s):
    s.setdefault('commercial',dict(offers={},contracts=[]))
    cfg=s['config'].setdefault('commercial',{})
    for k,v in DEFAULTS.items():cfg.setdefault(k,deepcopy(v))


def weekly_on(c,day):
    return c['weekly'] if c['start']<day<=c['end'] and (day-c['start'])%7==0 else 0


def process_day(s):
    from .simulation import posting,news
    day=s['day']
    for o in s['commercial']['offers'].values():
        if o['status'] in ('quote','counter','agreed') and day>o['expires']:
            o['status']='expired';news(s,'Sponsor proposal expired',o['sponsor']+': no agreement was signed.')
    for c in s['commercial']['contracts']:
        amount=weekly_on(c,day)
        key=c['id']+f':payment:{day}'
        if amount and not any(e['id']==key for e in s['ledger']):
            posting(s,key,amount,'Sponsorship: '+c['sponsor'])
            c['paid']+=amount
        if c['status']=='active' and day>=c['end']:
            c['status']='expired';news(s,'Sponsorship completed',c['sponsor']+': exclusive rights are available again.')


def conflict(s,right,start,end):
    return any(c['right']==right and max(start,c['start'])<min(end,c['end']) for c in s['commercial']['contracts'])


def apply(s,action,data):
    from .simulation import require,news
    if action not in ('sponsor_enquire','sponsor_propose','sponsor_accept','sponsor_withdraw'):return None
    require(s['match'] is None,'Review commercial agreements outside matchday.')
    cfg=s['config']['commercial'];right=data.get('right');require(right in cfg['rights'],'Unknown sponsorship inventory.')
    offers=s['commercial']['offers']
    if action=='sponsor_enquire':
        prior=offers.get(right)
        require(not prior or prior['status'] in ('signed','expired','withdrawn','rejected'),'A discussion already exists for these rights.')
        require(not conflict(s,right,s['day'],s['day']+1),'These exclusive rights are already contracted.')
        spec=cfg['rights'][right]
        offers[right]=dict(id=f"sponsor:{right}:{s['revision']}",right=right,sponsor=spec['sponsor'],weekly=spec['weekly'],weeks=8,
            expires=s['day']+cfg['quote_days'],status='quote',rounds=0,transcript=['Sponsor: We propose weekly payments for exclusive rights. No money is paid before services begin.'])
        return 'Sponsorship proposal opened. No rights granted or income booked.'
    o=offers.get(right);require(o is not None and o['status'] in ('quote','counter','agreed'),'No open sponsor discussion.')
    if action=='sponsor_withdraw':o['status']='withdrawn';return 'Sponsor proposal withdrawn. No contract was signed.'
    require(s['day']<=o['expires'],'The sponsor proposal expired.')
    if action=='sponsor_propose':
        weekly=data.get('weekly');weeks=data.get('weeks')
        require(type(weekly) is int and 10000<=weekly<=1000000,'Weekly sponsorship must be £100–£10,000.')
        require(type(weeks) is int and cfg['min_weeks']<=weeks<=cfg['max_weeks'],'Choose 4–16 weeks of rights.')
        terms=[weekly,weeks];require(terms!=o.get('last_proposal'),'These terms have already been considered.')
        o['last_proposal']=terms;o['rounds']+=1
        ceiling=cfg['rights'][right]['weekly']*(100+min(10,max(0,s['supporters']-50)//2))//100
        o.update(weekly=min(weekly,ceiling),weeks=weeks,status='agreed' if weekly<=ceiling else 'counter')
        if weekly>ceiling and o['rounds']>=3:o['status']='rejected'
        o['transcript'].append('Sponsor: We accept the proposed terms.' if o['status']=='agreed' else 'Sponsor: Our revised weekly payment is shown.' if o['status']=='counter' else 'Sponsor: We are ending these discussions.')
        return 'Sponsor response recorded. Review the actual counteroffer before signing.'
    require(o['status'] in ('counter','agreed'),'Send a proposal before accepting.')
    start=s['day'];end=start+o['weeks']*7
    require(not conflict(s,right,start,end),'An overlapping exclusive-rights agreement already exists.')
    c=dict(id=o['id'],right=right,sponsor=o['sponsor'],weekly=o['weekly'],start=start,end=end,status='active',paid=0)
    s['commercial']['contracts'].append(c);o['status']='signed'
    if right=='stadium':s['supporters']=max(5,s['supporters']+cfg['naming_sentiment'])
    news(s,'Sponsorship signed',o['sponsor']+': weekly payments start in seven days. Rights and payment dates are now binding.')
    return 'Rights committed. Income will settle on the scheduled dates.'


def validate(s):
    from .simulation import require
    contracts=s['commercial']['contracts']
    require(len({c['id'] for c in contracts})==len(contracts),'Duplicate sponsor contract.')
    for i,c in enumerate(contracts):
        require(c['end']>c['start'] and type(c['weekly']) is int and c['weekly']>0,'Invalid sponsorship terms.')
        for other in contracts[:i]:
            require(c['right']!=other['right'] or max(c['start'],other['start'])>=min(c['end'],other['end']),'Overlapping exclusive sponsor rights.')
        paid=sum(e['amount'] for e in s['ledger'] if e['id'].startswith(c['id']+':payment:'))
        require(paid==c['paid'],'Sponsor income does not reconcile.')


def venue_name(v):
    contract=next((c for c in v.get('commercial',{}).get('contracts',[]) if c['right']=='stadium' and c['start']<=v['day']<c['end']),None)
    club=next((c['name'] for c in v.get('clubs',[]) if c['id']=='c0'),'Northbridge Athletic')
    return contract['sponsor']+' Stadium' if contract else 'Northbridge ground' if club=='Northbridge Athletic' else club+' ground'
