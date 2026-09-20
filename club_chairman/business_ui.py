"""Transfer and commercial departments; commands own all state mutations."""
from .planning import dated
from .market import TERMINAL

TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161);RED=(246,150,142)
def money(n):return f'£{n/100:,.0f}'

class BusinessScreens:
    def market_open(self,action,pid,club=None):
        existing=next((d for d in self.v['market']['deals'].values() if d['player']==pid and d['status'] not in TERMINAL),None)
        if not existing:
            if not self.command(action,id=pid,club=club):return
            existing=next(reversed(self.v['market']['deals'].values()))
        self.nav('Transfers');self.market_id=existing['id'];self.market_draft=None;self.outgoing_player=None

    def outgoing_open(self,pid,kind):
        self.nav('Transfers');self.market_id=None;self.outgoing_player=pid;self.outgoing_kind=kind;self.page=0

    def business_attention(self,item):
        if item.get('screen')=='Transfers':
            self.nav('Transfers');self.market_id=item['deal_id'];self.market_draft=None;self.outgoing_player=None
        else:self.contract_open(item['player'])

    def market_section(self,name):
        self.market_tab=name;self.market_id=None;self.outgoing_player=None;self.market_draft=None;self.page=0;self.save_preferences()

    def draw_transfers(self,x):
        if self.outgoing_player:
            p=next(p for p in self.v['players'] if p['id']==self.outgoing_player)
            self.text(p['name']+' / select a receiving club',x,204,27,GREEN)
            self.button('Back to desk',(1200,190,200,42),lambda:setattr(self,'outgoing_player',None))
            clubs=[c for c in self.v['clubs'] if c['id']!='c0']
            for i,c in enumerate(clubs[self.page*5:self.page*5+5]):
                y=265+i*92;self.panel(x,y,1400-x,78);self.text(c['name'],x+20,y+25,28)
                self.button('Request club quote',(1170,y+18,210,42),lambda cid=c['id']:self.market_open('sale_enquire' if self.outgoing_kind=='sale' else 'loan_enquire',p['id'],cid))
            self.pager(x,760,len(clubs),5);return
        deals=self.v['market']['deals']
        if self.market_id in deals:self.draw_club_deal(x,deals[self.market_id]);return
        for i,name in enumerate(('Deals','Loans','Payments')):
            self.button(('• ' if self.market_tab==name else '')+name,(x+190*i,190,180,42),lambda name=name:self.market_section(name))
        if self.market_tab=='Loans':
            rows=list(reversed(self.v['market']['loans']))
            for i,l in enumerate(rows[self.page*4:self.page*4+4]):
                p=next(p for p in self.v['players'] if p['id']==l['player']);y=265+i*117
                self.panel(x,y,1400-x,104);self.text(p['name']+' / '+l['status'].upper(),x+20,y+16,27)
                self.text(self.club(l['source'])+' to '+self.club(l['target']),x+20,y+49,22,MUTED)
                self.text(f"To {dated(self.v,l['end'])} / borrower pays {l['share']}% wages",x+20,y+78,21,MUTED)
                if l['source']=='c0' and l['status']=='active':
                    self.button('Review recall',(1180,y+28,200,44),lambda loan=l,name=p['name']:self.confirm('Recall '+name,f"Return registration immediately and refund {money(loan.get('fee',0)*max(0,loan['end']-self.v['day'])//max(1,loan['end']-loan['start']))} for the unserved loan period. Full wages resume. Recall is legal only inside the window. The game rechecks cash and wage capacity.",lambda:self.command('loan_recall',id=loan['id'])),not self.v['match'] and self.v['day']<=self.v['window_end'])
            if not rows:self.wrap('No loan registrations yet. Open a club player in Recruitment to discuss an incoming loan, or use Review loan in Squad to arrange a temporary move.',x+20,295,1050,28,TEXT)
            self.pager(x,770,len(rows),4);return
        if self.market_tab=='Payments':
            rows=sorted(self.v['market']['obligations'],key=lambda b:(b['status']!='scheduled',b['due']))
            total=sum(b['amount'] for b in rows if b['status']=='scheduled' and b['source']=='c0')
            self.text('Outstanding transfer payments: '+money(total),x,251,27,GREEN)
            for i,b in enumerate(rows[self.page*5:self.page*5+5]):
                y=305+i*87;self.panel(x,y,1400-x,75)
                self.text(money(b['amount'])+' / '+dated(self.v,b['due'])+' / '+b['status'].upper(),x+20,y+14,26)
                self.text(self.club(b['source'])+' to '+self.club(b['target']),x+20,y+46,22,MUTED)
            if not rows:self.wrap('Agreed deferred transfer fees appear here after registration. They survive season changes and save/load. Forecasts include their exact payment dates.',x+20,330,1060,28,TEXT)
            self.pager(x,780,len(rows),5);return
        rows=list(reversed(list(deals.values())))
        self.text('Permanent and temporary moves / no registration without final review',x,253,23,MUTED)
        for i,d in enumerate(rows[self.page*5:self.page*5+5]):
            p=next(p for p in self.v['players'] if p['id']==d['player']);y=292+i*90
            self.panel(x,y,1400-x,78);self.text(p['name']+' / '+d['kind'].upper()+' / '+d['status'].upper(),x+20,y+13,26)
            self.text(self.club(d['source'])+' to '+self.club(d['target'])+' / '+money(d['fee']),x+20,y+47,21,MUTED)
            self.button('Review deal',(1190,y+18,190,42),lambda key=d['id']:(setattr(self,'market_id',key),setattr(self,'market_draft',None)))
        if not rows:self.wrap('Recruitment now includes contracted players. Use Club enquiry to negotiate a permanent transfer, or Discuss loan for temporary registration. Selling and outgoing loans begin from Squad profiles.',x+20,320,1070,28,TEXT)
        self.pager(x,780,len(rows),5)

    def market_edit(self,key,delta):
        d=dict(self.market_draft);limits={'fee':(0,100000000),'upfront_percent':(50,100),'defer_days':(7,56),'share':(50,100),'days':(14,84)}
        d[key]=max(limits[key][0],min(limits[key][1],d[key]+delta));self.market_draft=d;self.save_preferences()

    def market_send(self,d):
        payload=self.market_draft
        if self.command('club_propose',id=d['id'],**payload):self.market_draft=None

    def draw_club_deal(self,x,d):
        p=next(p for p in self.v['players'] if p['id']==d['player'])
        self.button('Back to desk',(x,190,180,42),lambda:(setattr(self,'market_id',None),setattr(self,'market_draft',None)))
        self.text(p['name']+' / '+d['kind'].upper()+' / '+d['status'].upper(),x+205,202,27,GREEN)
        self.text(self.club(d['source'])+' to '+self.club(d['target']),x,250,26)
        self.panel(x,295,565,381,'Club terms')
        right=x+585;self.panel(right,295,1400-right,381,'Conditions and adviser briefing')
        if d['kind']=='buy':
            if self.market_draft is None:self.market_draft=dict(fee=d['fee'],upfront_percent=round(d['upfront']*100/max(1,d['fee'])),defer_days=d['defer_days'])
            editable=d['status'] in ('quote','counter');draft=self.market_draft if editable else dict(fee=d['fee'],upfront_percent=round(d['upfront']*100/max(1,d['fee'])),defer_days=d['defer_days'])
            fields=[('fee','Transfer fee',money(draft['fee']),500000),('upfront_percent','Pay now',str(draft['upfront_percent'])+'%',25),('defer_days','Deferred days',str(draft['defer_days']),7)]
            for i,(key,label,value,step) in enumerate(fields):
                y=355+i*63;self.text(label,x+20,y,25,MUTED);self.text(value,x+235,y,26)
                self.button('−',(x+420,y-8,50,40),lambda k=key,n=step:self.market_edit(k,-n),editable)
                self.button('+',(x+480,y-8,50,40),lambda k=key,n=step:self.market_edit(k,n),editable)
            self.text('Current club quote: '+money(d['fee']),x+20,556,24)
            self.text('Now '+money(d['upfront'])+' / later '+money(d['fee']-d['upfront']),x+20,596,23)
            y=self.wrap('The transfer fee is separate from the player signing fee and wages. Agreed club terms alone do not sign the player or reserve cash.',right+20,352,1360-right,24,TEXT)
            self.wrap('A deferred fee becomes a dated obligation only when registration completes. It remains due after a sale or season change.',right+20,y+20,1360-right,23,MUTED)
            if editable:self.button('Send club offer',(x,773,205,46),lambda:self.market_send(d),not self.v['match'])
            if d['status'] in ('agreed','counter'):
                self.button('Review club consent',(x+225,773,240,46),lambda:self.confirm('Agree selling-club terms',f"Fee {money(d['fee'])}: {money(d['upfront'])} at registration and {money(d['fee']-d['upfront'])} after {d['defer_days']} days. Personal terms and medical remain outstanding; no money is paid now.",lambda:self.command('club_accept',id=d['id'])),not self.v['match'])
            if d['status']=='seller_agreed':self.button('Personal terms',(x,773,230,46),lambda:self.contract_open(p['id']),not self.v['match'])
        else:
            self.text('Club fee '+money(d['fee']),x+20,351,30,GREEN)
            self.text('Weekly wage '+money(d['wage_cost']),x+20,402,25)
            if d['kind']=='loan':
                self.text('Borrower wage share '+str(d['share'])+'%',x+20,448,23)
                self.text('Return after '+dated(self.v,d['end']),x+20,488,24)
                self.button('Wage share -25%',(x+20,541,220,40),lambda:self.command('loan_terms',id=d['id'],share=d['share']-25,days=d['end']-self.v['day']),d['status']=='quote' and d['share']>50)
                self.button('Wage share +25%',(x+260,541,230,40),lambda:self.command('loan_terms',id=d['id'],share=d['share']+25,days=d['end']-self.v['day']),d['status']=='quote' and d['share']<100)
                self.wrap('Lower wage cover increases the upfront fee. Full employer wages resume on return. Early recall refunds the unserved share of the fee. The loan cannot outlast employment.',right+20,354,1360-right,24,TEXT)
            else:self.wrap('The receiving club must fund the fee and retain player consent. The player keeps their identity and history; employment and registration change together at final completion.',right+20,354,1360-right,24,TEXT)
            if d['status']=='quote':self.button('Review conditional deal',(x,773,275,46),lambda:self.confirm('Accept conditional '+d['kind'],f"Receiving club {self.club(d['target'])} pays {money(d['fee'])} on completion and carries {money(d['wage_cost'])}/week. Medical and consent checks take {self.v['market_settings']['medical_days']} days. Registration remains unchanged until final review.",lambda:self.command('market_accept',id=d['id'])),not self.v['match'])
            elif d['status']=='ready':self.button('Review registration',(x,773,260,46),lambda:self.confirm('Complete '+d['kind']+' of '+p['name'],f"Settle {money(d['fee'])} from {self.club(d['target'])} to {self.club(d['source'])}. Move registration and wage responsibility now. This cannot be undone. "+('Early recall refunds the unserved share of the fee. The original employment survives and the player returns after '+dated(self.v,d['end'])+'.' if d['kind']=='loan' else 'The receiving club starts a new employment agreement.'),lambda:self.command('market_complete',id=d['id'])),not self.v['match'])
            elif d['status']=='medical':self.text('Medical due '+dated(self.v,d['due'])+'. Continue to the review.',x,791,24,GREEN)
        self.wrap(d['transcript'][-1],x+20,700,1340-x,22,MUTED)
        if d['status'] not in TERMINAL:
            self.text('Consent expires '+dated(self.v,d['expires']),right+20,617,22,MUTED)
            self.button('Withdraw deal',(1200,773,200,46),lambda:self.confirm('Withdraw club discussion','Release associated reservations and personal discussions. Completed payments and signed contracts are not affected.',lambda:self.command('market_withdraw',id=d['id'])),not self.v['match'])

    def sponsor_open(self,right):
        o=self.v['commercial']['offers'].get(right)
        if not o or o['status'] in ('signed','expired','withdrawn','rejected'):
            if not self.command('sponsor_enquire',right=right):return
        self.sponsor_right=right;self.sponsor_draft=None

    def sponsor_edit(self,key,delta):
        draft=dict(self.sponsor_draft);lo,hi=(10000,1000000) if key=='weekly' else (4,16)
        draft[key]=max(lo,min(hi,draft[key]+delta));self.sponsor_draft=draft;self.save_preferences()

    def sponsor_send(self,o):
        if self.command('sponsor_propose',right=o['right'],**self.sponsor_draft):self.sponsor_draft=None

    def draw_commercial(self,x):
        rights=self.v['commercial_settings']['rights'];offers=self.v['commercial']['offers'];contracts=self.v['commercial']['contracts']
        if self.sponsor_right in offers:
            o=offers[self.sponsor_right];editable=o['status'] in ('quote','counter','agreed')
            if self.sponsor_draft is None:self.sponsor_draft={k:o[k] for k in ('weekly','weeks')}
            draft=self.sponsor_draft if editable else {k:o[k] for k in ('weekly','weeks')}
            self.button('Back to inventory',(x,190,210,42),lambda:(setattr(self,'sponsor_right',None),setattr(self,'sponsor_draft',None)))
            self.text(rights[o['right']]['name']+' / '+o['status'].upper(),x+230,202,27,GREEN)
            self.panel(x,269,570,366,'Proposal / '+o['sponsor'])
            for i,(key,label,value,step) in enumerate([('weekly','Weekly income',money(draft['weekly']),25000),('weeks','Weeks',str(draft['weeks']),4)]):
                y=335+i*95;self.text(label,x+20,y,25,MUTED);self.text(value,x+240,y,28)
                self.button('−',(x+420,y-8,50,42),lambda k=key,n=step:self.sponsor_edit(k,-n),editable)
                self.button('+',(x+485,y-8,50,42),lambda k=key,n=step:self.sponsor_edit(k,n),editable)
            self.wrap('Latest sponsor terms: '+money(o['weekly'])+' per week for '+str(o['weeks'])+' weeks. Total '+money(o['weekly']*o['weeks'])+'.',x+20,530,520,25,TEXT)
            right=x+590;self.panel(right,269,1400-right,366,'Rights and obligations')
            y=self.wrap('Exclusive '+rights[o['right']]['name'].lower()+'. No upfront payment. The first instalment falls seven days after signing; payments repeat weekly until expiry.',right+20,330,1360-right,25,TEXT)
            self.wrap('Stadium naming changes club identity and reduces current supporter sentiment by '+str(abs(self.v['commercial_settings']['naming_sentiment']))+' points.' if o['right']=='stadium' else 'The existing core sponsor is separate. These rights cannot overlap another agreement for the same inventory.',right+20,y+24,1360-right,24,MUTED)
            self.wrap(o['transcript'][-1],x+20,672,1340-x,26,TEXT)
            if editable:
                self.button('Send sponsor proposal',(x,772,260,46),lambda:self.sponsor_send(o),not self.v['match'])
                self.button('Review sponsor agreement',(x+280,772,300,46),lambda:self.confirm('Sign '+o['sponsor'],f"Grant exclusive {rights[o['right']]['name'].lower()} for {o['weeks']} weeks at {money(o['weekly'])}/week. First payment in seven days; total {money(o['weekly']*o['weeks'])}. Unsent draft edits are excluded. "+('Supporter sentiment falls by five points for naming rights.' if o['right']=='stadium' else '')+' The agreed term is binding.',lambda:self.command('sponsor_accept',right=o['right'])),o['status'] in ('agreed','counter') and not self.v['match'])
                self.button('Withdraw sponsor',(1180,772,220,46),lambda:self.confirm('Withdraw sponsor proposal','No rights or income will be created.',lambda:self.command('sponsor_withdraw',right=o['right'])),not self.v['match'])
            return
        self.text('Exclusive inventory / payments follow the signed calendar',x,205,25,GREEN)
        self.text('Core sponsor: '+money(self.v['terms']['weekly_sponsor'])+' weekly / existing agreement',x,247,23,MUTED)
        for i,(key,spec) in enumerate(rights.items()):
            y=300+i*155;self.panel(x,y,1400-x,138)
            active=next((c for c in contracts if c['right']==key and self.v['day']<c['end']),None)
            self.text(spec['name'],x+20,y+19,29)
            self.text((active['sponsor']+' / '+money(active['weekly'])+' per week') if active else 'Available / indicative '+money(spec['weekly'])+' per week',x+20,y+61,24,GREEN)
            self.text(('Committed to '+dated(self.v,active['end'])+' / received '+money(active['paid'])) if active else 'Negotiate income and duration before committing rights.',x+20,y+102,22,MUTED)
            self.button('Contract details' if active else 'Discuss sponsorship',(1150,y+41,230,44),lambda right=key,c=active:self.confirm('Signed sponsorship',f"{c['sponsor']}: {money(c['weekly'])}/week from {dated(self.v,c['start'])} to {dated(self.v,c['end'])}. Paid {money(c['paid'])}. Cash settles every seven days after the start date.",None) if c else self.sponsor_open(right))
