"""Public clause controls and the signed-obligation register."""
from .clauses import terms, description
from . import contract_terms, loan_clauses
from .planning import dated

TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161)
def money(n):return f'£{n/100:,.0f}'


class ClauseScreens:
    def draw_offer_clauses(self,x,offer,current,editable):
        extra=getattr(self,'employment_clause_page',False)
        self.button('Performance clauses' if extra else 'Employment clauses',(x+790,244,350,40),lambda:setattr(self,'employment_clause_page',not extra))
        if extra:
            self.panel(x,360,560,351,'Employment conditions / send for consent')
            fields=[('release_fee','Release amount',500000),('annual_raise','Annual raise %',5),('relegation_cut','Relegation cut %',5),('promotion_bonus','Promotion bonus',50000)]
            for i,(key,label,step) in enumerate(fields):
                y=412+i*54;value=current.get(key,0)
                self.text(label,x+20,y,23,MUTED);self.text(str(value)+'%' if key in ('annual_raise','relegation_cut') else money(value),x+260,y,24)
                self.button('−',(x+420,y-6,50,36),lambda k=key,n=step:self.offer_edit(k,-n),editable)
                self.button('+',(x+480,y-6,50,36),lambda k=key,n=step:self.offer_edit(k,n),editable)
            self.button('Player option: '+('One season' if current.get('player_option') else 'None'),(x+20,646,510,40),self.toggle_player_option,editable)
            right=x+580;self.panel(right,360,1400-right,351,'Triggers and commitments')
            self.wrap('Annual increases take effect on signing anniversaries. Relegation reductions apply at division rollover. A promotion bonus is earned once during this contract.',right+20,410,1360-right,22,TEXT)
            self.wrap('A player option gives the player the extension decision near expiry. It replaces a club option. Release amounts require full club payment, personal consent and valid registration.',right+20,546,1360-right,22,MUTED)
            return
        self.panel(x,360,560,351,'Optional terms / part of the sent proposal')
        for i,(key,label) in enumerate((('appearance_bonus','Per appearance'),('goal_bonus','Per goal'))):
            y=416+i*64
            self.text(label,x+20,y,24,MUTED);self.text(money(current.get(key,0)),x+235,y,26)
            self.button('−',(x+410,y-7,50,38),lambda k=key:self.offer_edit(k,-2500),editable)
            self.button('+',(x+475,y-7,50,38),lambda k=key:self.offer_edit(k,2500),editable)
        option=current.get('club_option',False)
        self.button('Club option: '+('One season' if option else 'None'),(x+20,550,510,42),self.toggle_club_option,editable)
        self.text('Bonus cap: none / ends with employment',x+20,624,22,MUTED)
        self.text('Loan bonuses remain with the employer.',x+20,659,22,MUTED)
        right=x+580;self.panel(right,360,1400-right,351,'What these clauses mean')
        y=self.wrap('Appearance bonuses pay for each match played. Goal bonuses pay per recorded goal. Neither guarantees selection; the manager still chooses the team.',right+20,410,1360-right,23,TEXT)
        y=self.wrap('Bonuses are extra cash costs outside the base wage budget. Future performances are unknown and excluded from guaranteed forecasts.',right+20,y+18,1360-right,22,MUTED)
        self.wrap('A club option gives one extra season continuing the signed wage conditions and bonuses. The agent asks for a 5% higher minimum base wage when it is included.',right+20,y+18,1360-right,22,MUTED)

    def toggle_club_option(self):
        self.offer_draft['club_option']=not self.offer_draft.get('club_option',False)
        if self.offer_draft['club_option']:self.offer_draft['player_option']=False
        self.save_preferences()

    def toggle_player_option(self):
        self.offer_draft['player_option']=not self.offer_draft.get('player_option',False)
        if self.offer_draft['player_option']:self.offer_draft['club_option']=False
        self.save_preferences()

    def draw_clause_register(self,x):
        v=self.v;c=v['clauses'];people={p['id']:p for p in v['players']}
        outstanding=sum(b['amount']-b['paid'] for b in c['payables'] if b['source']=='c0')
        self.text('SIGNED CLAUSES / unpaid player bonuses '+money(outstanding),x,250,24,GREEN)
        rows=[]
        for pid,contract in c['employment'].items():
            rows.append(('employment',people[pid],contract))
        for clause in c.get('conditional',[]):rows.append(('conditional',people[clause['player']],clause))
        for right in reversed(c['sell_on']):rows.append(('sell-on',people[right['player']],right))
        for pid in sorted({b['player'] for b in c['payables']}):
            bills=[b for b in c['payables'] if b['player']==pid]
            rows.append(('payments',people[pid],dict(earned=sum(b['amount'] for b in bills),paid=sum(b['paid'] for b in bills))))
        for i,(kind,p,row) in enumerate(rows[self.page*4:self.page*4+4]):
            y=293+i*113;self.panel(x,y,1400-x,101)
            self.text(p['name']+' / '+kind.upper(),x+18,y+12,25)
            if kind=='employment':
                self.text(money(row['appearance_bonus'])+'/appearance; '+money(row['goal_bonus'])+'/goal; ends '+dated(v,row['end']),x+18,y+46,21,MUTED)
                self.text(('Player option: ' if row.get('player_option') else 'Club option: ')+row['option_status']+' / bonuses stay with employer on loan',x+18,y+75,20,MUTED)
                self.button('View terms',(x+720,y+14,180,38),lambda row=row:self.confirm('Signed employment terms',description(row),lambda:None))
                if row['option_status']=='available' and row.get('club_option'):
                    exposure=contract_terms.remaining(p['wage'],row,v['day'],row['option_end'],v['start_date'])-contract_terms.remaining(p['wage'],row,v['day'],row['end'],v['start_date'])
                    self.button('Review extension',(1180,y+24,200,42),lambda pid=p['id'],p=p,row=row,exposure=exposure:self.confirm('Exercise '+p['name']+' club option',f"Extend employment to {dated(v,row['option_end'])} from {money(p['wage'])}/week, including signed wage changes. Additional guaranteed wages approximately {money(exposure)}; no immediate fee. {description(row)} This option can be used once. Existing loan registration stays unchanged.",lambda:self.command('exercise_option',id=pid)),not v['match'] and v['day']<=row['end'])
            elif kind=='conditional':
                self.text(row['trigger']+' / '+row['status']+' / '+money(row['amount'])+' / paid '+money(row['paid']),x+18,y+46,22,GREEN)
                self.text(str(row['count'])+'/'+str(row['threshold'])+' appearances / expires '+dated(v,row['expiry'])+' / '+self.club(row['source'])+' to '+self.club(row['target']),x+18,y+75,20,MUTED)
            elif kind=='sell-on':
                self.text(f"{row['percent']}% of {'gross fee' if row['kind']=='gross' else 'profit above '+money(row['basis'])} / {row['status'].upper()}",x+18,y+46,23,GREEN)
                self.text(self.club(row['liable'])+' owes '+self.club(row['beneficiary'])+' on next permanent sale; release ends right.',x+18,y+75,20,MUTED)
            else:
                self.text('Earned '+money(row['earned'])+' / paid '+money(row['paid'])+' / still due '+money(row['earned']-row['paid']),x+18,y+49,25,GREEN)
                self.text('Earned amounts remain payable after a transfer or contract expiry.',x+18,y+78,20,MUTED)
        if not rows:self.wrap('No extra clauses have been signed. Add performance bonuses or a club option in a contract proposal, or negotiate a sell-on right in Transfers.',x+20,330,1040,28,TEXT)
        self.pager(x,780,len(rows),4)

    def sell_on_text(self,d):
        return ('No new sell-on right.' if not d.get('sell_on_percent') else
                f"{d['sell_on_percent']}% of {'the next gross transfer fee' if d['sell_on_kind']=='gross' else 'profit above this purchase fee'} payable to {self.club(d['source'])}. Settles at the next permanent registration, including deferred sale proceeds; ends on release.")

    def change_sell_on(self,d,kind=None,delta=0):
        if d['kind']=='buy':
            draft=dict(self.market_draft)
        else: draft=dict(sell_on_kind=d.get('sell_on_kind','none'),sell_on_percent=d.get('sell_on_percent',0))
        if kind:
            draft['sell_on_kind']=kind
            draft['sell_on_percent']=0 if kind=='none' else max(10,draft.get('sell_on_percent',0))
        else:
            draft['sell_on_percent']=max(0,min(50,draft.get('sell_on_percent',0)+delta))
            if draft['sell_on_percent']==0:draft['sell_on_kind']='none'
            elif draft.get('sell_on_kind','none')=='none':draft['sell_on_kind']='gross'
        if d['kind']=='buy':self.market_draft=draft;self.save_preferences()
        else:self.command('sale_terms',id=d['id'],**draft)

    def sell_on_controls(self,x,y,d,editable):
        data=self.market_draft if d['kind']=='buy' and editable else d
        kind=data.get('sell_on_kind','none');percent=data.get('sell_on_percent',0)
        self.text('Sell-on '+str(percent)+'% / '+kind,x,y,23,GREEN)
        next_kind={'none':'gross','gross':'profit','profit':'none'}[kind]
        self.button('Type: '+kind,(x,y+34,230,38),lambda:self.change_sell_on(d,next_kind),editable)
        self.button('−5%',(x+242,y+34,90,38),lambda:self.change_sell_on(d,delta=-5),editable)
        self.button('+5%',(x+344,y+34,90,38),lambda:self.change_sell_on(d,delta=5),editable)

    def deal_extras(self,x,d):
        self.button('Back to deal',(x,190,200,42),lambda:setattr(self,'deal_extra_page',False))
        self.panel(x,255,1400-x,455,'Additional club terms / agreed before acceptance')
        editable=d['status'] in ('quote','counter')
        if d['kind']=='loan':
            kind=d.get('purchase_kind','none');next_kind={'none':'option','option':'obligation','obligation':'none'}[kind]
            def edit(**changes):
                self.command('loan_terms',id=d['id'],share=d['share'],days=d.get('days') or 14,**changes)
            self.button('Purchase: '+kind,(x+25,322,350,44),lambda:edit(purchase_kind=next_kind),editable)
            self.text('Appearance condition: '+str(d.get('purchase_count') or 2),x+25,394,25)
            self.button('−1',(x+425,385,90,40),lambda:edit(purchase_count=max(1,(d.get('purchase_count') or 2)-1)),editable and kind=='obligation')
            self.button('+1',(x+535,385,90,40),lambda:edit(purchase_count=min(30,(d.get('purchase_count') or 2)+1)),editable and kind=='obligation')
            self.wrap(loan_clauses.description(d,self.v['start_date']),x+25,463,1080,25,TEXT)
            self.wrap('Binding purchase fees and future wage capacity are reserved. The loan must end inside the registration window. Recall cannot cancel a binding purchase condition. Optional purchases reserve nothing until exercised.',x+25,593,1080,22,MUTED)
        else:
            draft=self.market_draft if d['kind']=='buy' and editable else d
            if draft is None:
                self.market_draft=dict(fee=d['fee'],upfront_percent=100,defer_days=d['defer_days'],sell_on_kind=d.get('sell_on_kind','none'),sell_on_percent=d.get('sell_on_percent',0))
                draft=self.market_draft
            for key,value in contract_terms.TRANSFER.items():
                if d['kind']=='buy' and editable:self.market_draft.setdefault(key,d.get(key,value))
            def edit(key,delta):
                limits={'appearance_fee':(0,100000000),'appearance_count':(1,100),'promotion_fee':(0,100000000)}
                value=max(limits[key][0],min(limits[key][1],draft.get(key,contract_terms.TRANSFER[key])+delta))
                if d['kind']=='buy':self.market_draft[key]=value;self.save_preferences()
                else:self.command('sale_terms',id=d['id'],**{**{k:d.get(k,v) for k,v in contract_terms.TRANSFER.items()},key:value,'sell_on_kind':d.get('sell_on_kind','none'),'sell_on_percent':d.get('sell_on_percent',0)})
            for i,(key,label,step) in enumerate([('appearance_fee','Appearance payment',50000),('appearance_count','Required appearances',1),('promotion_fee','Promotion payment',50000)]):
                y=328+i*78;value=draft.get(key,contract_terms.TRANSFER[key])
                self.text(label,x+25,y,26);self.text(str(value) if key=='appearance_count' else money(value),x+460,y,26,GREEN)
                self.button('−',(x+650,y-8,65,42),lambda k=key,n=step:edit(k,-n),editable)
                self.button('+',(x+735,y-8,65,42),lambda k=key,n=step:edit(k,n),editable)
            self.wrap('Each condition can pay once before the new employment end date. Match appearances exclude forfeits and unused substitutes. Earned amounts survive later transfers and remain due until paid. Future conditional amounts are excluded from guaranteed cash forecasts. Outgoing bonuses replace guaranteed money in the buyer’s quote.',x+25,578,1080,23,MUTED)
        self.text('Return to the deal to review and send the complete package.',x+20,753,23,GREEN)
