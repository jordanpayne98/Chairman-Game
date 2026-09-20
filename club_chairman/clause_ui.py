"""Public clause controls and the signed-obligation register."""
from .clauses import terms, description
from .planning import dated

TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161)
def money(n):return f'£{n/100:,.0f}'


class ClauseScreens:
    def draw_offer_clauses(self,x,offer,current,editable):
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
        self.wrap('A club option gives one extra season at the same wages and bonuses. The agent asks for a 5% higher minimum base wage when it is included.',right+20,y+18,1360-right,22,MUTED)

    def toggle_club_option(self):
        self.offer_draft['club_option']=not self.offer_draft.get('club_option',False)
        self.save_preferences()

    def draw_clause_register(self,x):
        v=self.v;c=v['clauses'];people={p['id']:p for p in v['players']}
        outstanding=sum(b['amount']-b['paid'] for b in c['payables'] if b['source']=='c0')
        self.text('SIGNED CLAUSES / unpaid player bonuses '+money(outstanding),x,250,24,GREEN)
        rows=[]
        for pid,contract in c['employment'].items():
            rows.append(('employment',people[pid],contract))
        for right in reversed(c['sell_on']):rows.append(('sell-on',people[right['player']],right))
        for pid in sorted({b['player'] for b in c['payables']}):
            bills=[b for b in c['payables'] if b['player']==pid]
            rows.append(('payments',people[pid],dict(earned=sum(b['amount'] for b in bills),paid=sum(b['paid'] for b in bills))))
        for i,(kind,p,row) in enumerate(rows[self.page*4:self.page*4+4]):
            y=293+i*113;self.panel(x,y,1400-x,101)
            self.text(p['name']+' / '+kind.upper(),x+18,y+12,25)
            if kind=='employment':
                self.text(money(row['appearance_bonus'])+'/appearance; '+money(row['goal_bonus'])+'/goal; ends '+dated(v,row['end']),x+18,y+46,21,MUTED)
                self.text('Club option: '+row['option_status']+' / bonuses stay with employer on loan',x+18,y+75,20,MUTED)
                if row['option_status']=='available':
                    exposure=p['wage']*(row['option_end']-row['end'])//7
                    self.button('Review extension',(1180,y+24,200,42),lambda pid=p['id'],p=p,row=row,exposure=exposure:self.confirm('Exercise '+p['name']+' club option',f"Extend employment to {dated(v,row['option_end'])} at {money(p['wage'])}/week. Additional guaranteed wages approximately {money(exposure)}; no immediate fee. {description(row)} This option can be used once. Existing loan registration stays unchanged.",lambda:self.command('exercise_option',id=pid)),not v['match'] and v['day']<=row['end'])
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
