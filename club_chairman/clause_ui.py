"""Public clause controls and the signed-obligation register."""
from .clauses import terms, description
from . import contract_terms, loan_clauses
from .planning import dated

TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161)
def money(n):return f'£{n/100:,.0f}'


class ClauseScreens:
    def draw_offer_clauses(self,x,offer,current,editable):
        extra=getattr(self,'employment_clause_page',False)
        self.button('Performance clauses' if extra else 'Employment clauses',(x+790,732,350,36),lambda:setattr(self,'employment_clause_page',not extra))
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
            self.wrap('A player option gives the player the extension decision near expiry. It replaces a club option. Buy-outs fund player termination compensation; club releases enforce a transfer condition. Both require full funding and player consent.',right+20,546,1360-right,22,MUTED)
            self.button('Exit: '+('Player buy-out' if current.get('release_kind')=='buyout' else 'Club release'),(right+20,655,480,40),self.toggle_release_kind,editable and len(self.v['clause_settings']['allowed_release_kinds'])>1)
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
        if d['kind']!='loan':
            extra=getattr(self,'right_clause_page',False)
            self.button('Payment conditions' if extra else 'Transfer rights',(x+790,190,350,42),lambda:setattr(self,'right_clause_page',not extra))
            if extra:self.draw_right_terms(x,d);return
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

    def toggle_release_kind(self):
        choices=self.v['clause_settings']['allowed_release_kinds'];current=self.offer_draft.get('release_kind','transfer')
        self.offer_draft['release_kind']=choices[(choices.index(current)+1)%len(choices)];self.save_preferences()

    def draw_right_terms(self,x,d):
        editable=d['status'] in ('quote','counter')
        draft=self.market_draft if d['kind']=='buy' and editable else d
        for k,value in contract_terms.TRANSFER.items():
            if d['kind']=='buy' and editable:draft.setdefault(k,d.get(k,value))
        def change(**changes):
            updated={k:draft.get(k,v) for k,v in contract_terms.TRANSFER.items()};updated.update(changes)
            if updated['buy_back_fee'] and updated['buy_back_later']:updated['buy_back_later']=max(updated['buy_back_later'],updated['buy_back_fee'])
            if d['kind']=='buy':self.market_draft.update(updated);self.save_preferences()
            else:self.command('sale_terms',id=d['id'],**updated,sell_on_kind=d.get('sell_on_kind','none'),sell_on_percent=d.get('sell_on_percent',0))
        self.panel(x,255,1400-x,495,'Retained rights / seller remains the beneficiary')
        enabled=bool(draft.get('buy_back_fee'))
        self.button('Buy-back: '+('On' if enabled else 'Off'),(x+25,312,350,42),lambda:change(buy_back_fee=0 if enabled else min(100000000,max(100000,d['fee']*2)),buy_back_later=0),editable)
        for i,(key,label) in enumerate((('buy_back_fee','First window price'),('buy_back_later','Later window price'))):
            y=382+i*60;amount=draft.get(key,0)
            self.text(label,x+25,y,24);self.text(money(amount) if amount else ('Same as first price' if key=='buy_back_later' else 'Off'),x+375,y,24,GREEN)
            self.button('−£5k',(x+680,y-8,140,40),lambda key=key:change(**{key:max(100000 if key=='buy_back_fee' else 0,draft.get(key,0)-500000)}),editable and enabled)
            self.button('+£5k',(x+835,y-8,140,40),lambda key=key:change(**{key:min(100000000,(draft.get(key) or draft.get('buy_back_fee',0))+500000)}),editable and enabled)
        years=draft.get('rights_seasons',2)
        self.text('Valid for '+str(years)+' future season(s)',x+25,506,25)
        self.button('− season',(x+680,496,140,40),lambda:change(rights_seasons=max(1,years-1)),editable and years>1)
        self.button('+ season',(x+835,496,140,40),lambda:change(rights_seasons=min(3,years+1)),editable and years<3)
        self.button('First refusal: '+('On' if draft.get('first_refusal') else 'Off'),(x+25,553,420,42),lambda:change(first_refusal=not draft.get('first_refusal')),editable)
        self.wrap('Buy-back starts in the next season’s registration window. First refusal starts on completion and covers the entire future offer, including instalments and bonuses. Rights end on expiry, release or the next permanent departure. Buy-out termination is excluded. The player still decides whether to join.',x+25,622,1080,22,MUTED)
        self.text('Review the complete package before sending or accepting.',x+20,787,23,GREEN)

    def open_contract_exit(self,action,pid):
        if self.command(action,id=pid):
            self.nav('Transfers');self.market_id=next(reversed(self.v['market']['deals']));self.market_draft=None;self.deal_extra_page=False

    def respond_refusal(self,n,accept):
        if self.command('refusal_match' if accept else 'refusal_decline',id=n['id']) and accept:
            current=next(r for r in self.v['clauses']['notices'] if r['id']==n['id'])
            self.market_id=current['match_id'];self.market_draft=None;self.deal_extra_page=False

    def draw_transfer_rights(self,x):
        v=self.v;c=v['clauses'];people={p['id']:p for p in v['players']}
        notices=[('notice',n) for n in reversed(c['notices']) if 'c0' in (n['source'],n['beneficiary'],n['other_buyer'])]
        rights=[('right',r) for r in reversed(c['rights']) if 'c0' in (r['beneficiary'],r['liable'])]
        receipts=[('buyout',b) for b in reversed(c['buyouts']) if 'c0' in (b['sponsor'],b['employer'])]
        rows=notices+rights+receipts
        self.text('Contract rights, response deadlines and settled compensation',x,251,23,GREEN)
        for i,(kind,r) in enumerate(rows[self.page*3:self.page*3+3]):
            y=293+i*156;p=people[r['player']];self.panel(x,y,1400-x,144)
            state=r.get('status','paid');label=r.get('kind','First refusal' if kind=='notice' else 'Buy-out')
            self.text(p['name']+' / '+label.upper()+' / '+state.upper(),x+18,y+12,24)
            if kind=='notice':
                pack=r['package'];self.text('Match '+money(pack['fee'])+' / now '+money(pack['upfront'])+' / deadline '+dated(v,r['deadline']),x+18,y+47,22,MUTED)
                self.text(self.club(r['beneficiary'])+' has priority over '+self.club(r['other_buyer']),x+18,y+77,21,MUTED)
                if r['beneficiary']=='c0' and state=='pending':
                    body=f"Match {self.club(r['other_buyer'])}'s complete offer for {p['name']}: {money(pack['fee'])}, {money(pack['upfront'])} now and the balance after {pack['defer_days']} days. {self.sell_on_text(dict(pack,source=r['source']))} {contract_terms.transfer_description(pack)} Respond by {dated(v,r['deadline'])}; complete personal terms, medical and registration by {dated(v,r['expires'])}. No transfer occurs on this click."
                    self.button('Review match',(x+18,y+105,240,32),lambda r=r,body=body:self.confirm('Match first-refusal offer',body,lambda:self.respond_refusal(r,True)),not v['match'])
                    self.button('Decline',(x+275,y+105,160,32),lambda r=r:self.confirm('Decline this offer?','The other buyer may proceed on these exact terms. A materially changed package requires another notice.',lambda:self.respond_refusal(r,False)),not v['match'])
                elif state=='matching' and r['beneficiary']=='c0':
                    self.button('Personal terms',(x+18,y+105,240,32),lambda r=r:(setattr(self,'market_id',r['match_id']),setattr(self,'market_draft',None)))
            elif kind=='right':
                self.text(self.club(r['beneficiary'])+' holds rights against '+self.club(r['liable']),x+18,y+47,22,MUTED)
                self.text('From '+dated(v,r['start'])+' to '+dated(v,r['expiry']),x+18,y+78,21,MUTED)
                if r['kind']=='buyback':
                    amount=r['later_fee'] if v['day']>=r['second'] else r['fee']
                    self.text(money(r['fee'])+' → '+money(r['later_fee'])+' from '+dated(v,r['second']),x+18,y+108,21,GREEN)
                    usable=r['beneficiary']=='c0' and state=='active' and r['start']<=v['day']<=min(r['expiry'],v['window_end']) and p['club']==r['liable'] and not p.get('loan') and not v['season_done'] and not v['match']
                    if r['beneficiary']=='c0':self.button('Open buy-back',(1180,y+83,200,40),lambda p=p,amount=amount:self.confirm('Exercise club buy-back right',f"Price {money(amount)}, funded in full at completion. Negotiate fresh personal terms and pass medical/registration checks. The player can refuse; no payment is made now. Any existing sell-on is settled separately from the gross fee.",lambda:self.open_contract_exit('right_enquire',p['id'])),usable)
            else:
                self.text(money(r['amount'])+' funded by '+self.club(r['sponsor']),x+18,y+49,24,GREEN)
                self.text('Paid to '+self.club(r['employer'])+' on '+dated(v,r['day'])+' / player consent recorded',x+18,y+89,21,MUTED)
        if not rows:self.wrap('Negotiate retained buy-back or first-refusal rights in a permanent deal’s Additional terms. Signed rights, matching notices and completed player buy-outs appear here.',x+20,335,1080,27,TEXT)
        self.pager(x,790,len(rows),3)
