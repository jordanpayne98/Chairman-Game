"""People and football screens consume authorised read models only."""
from .people import GROUPS
from .football import finished
from .planning import dated
from .presentation import portrait, crest


def interval(pair):return str(pair[0]) if pair and pair[0]==pair[1] else f'{pair[0]}–{pair[1]}' if pair else '—'


class FootballScreens:
    def player_profile(self,x,p):
        from .ui import GREEN,MUTED,TEXT,RED,money
        self.button('< Back to list',(x,190,175,42),self.close_profile)
        index=self.profile_ids.index(p['id']) if p['id'] in self.profile_ids else -1
        self.button('Previous player',(x+190,190,180,42),lambda:self.profile_neighbor(-1),index>0)
        self.button('Next player',(x+385,190,155,42),lambda:self.profile_neighbor(1),0<=index<len(self.profile_ids)-1)
        self.button('Remove shortlist' if p['id'] in self.v['planning']['shortlist'] else 'Add to shortlist',(x+555,190,190,42),lambda:self.toggle_plan('shortlist',p['id']))
        self.button('Unpin' if p['id'] in self.v['planning']['comparison'] else 'Pin comparison',(1200,190,200,42),lambda:self.toggle_plan('comparison',p['id']))
        report=p['report']
        self.panel(x,250,480,124)
        portrait(self.canvas,p['id'],p['age'],(x+14,261,85,102),p['club'])
        self.text(p['role']+' / Age '+str(p['age']),x+118,267,28)
        self.text(f"{p['foot']} foot / {p['height']} cm",x+118,307,21,MUTED)
        self.clipped_text('Free agent' if not p['club'] else self.club(p['club']),x+118,343,345,20,MUTED)
        width=(1400-x-525)/3
        exact=bool(report and report.get('exact_current'))
        metrics=[('CURRENT ABILITY' if exact else 'EST. ABILITY',interval(report.get('overall') if report else None),'Role: '+p['role']+' / 1–100'),
                 ('EST. POTENTIAL',interval(report.get('potential') if report else None),'Development is uncertain'),
                 ('KNOWLEDGE',report['knowledge'] if report else 'Unknown','Current ratings exact' if exact else 'Request scouting' if not report else dated(self.v,report['day']))]
        for i,(label,value,caption) in enumerate(metrics):
            left=x+495+i*(width+15);self.panel(left,250,width,124)
            self.text(label,left+15,267,16,MUTED)
            self.clipped_text(value,left+15,296,width-30,32,GREEN if i==0 else TEXT)
            self.clipped_text(caption,left+15,348,width-30,15,MUTED)
        name=self.shortlist_name()
        self.button('List: '+(name if len(name)<=19 else name[:18]+'…'),(970,389,235,38),self.open_shortlists)
        tabs=('Attributes','Goalkeeping','Development','Contract')
        active=self.profile_tab if self.profile_tab in tabs else 'Attributes'
        for i,label in enumerate(tabs):
            self.button(('• ' if active==label else '')+label,(x+i*180,389,170,38),lambda label=label:setattr(self,'profile_tab',label))
        if active in ('Attributes','Goalkeeping'):
            groups=('Technical','Mental','Physical') if active=='Attributes' else ('Goalkeeping','Mental','Physical')
            right=1110;columns=(right-x-30)/3
            self.panel(x,441,right-x-15,313)
            for i,group in enumerate(groups):
                left=x+i*columns;self.text(group.upper(),left+15,458,16,MUTED)
                for row,key in enumerate(GROUPS[group]):
                    y=491+row*23
                    self.clipped_text(key.replace('_',' ').capitalize(),left+15,y,columns-81,18)
                    pair=report['ranges'].get(key) if report else None
                    self.right_text(interval(pair),left+columns-15,y,18,GREEN if pair else MUTED)
                    import pygame
                    from .theme import BORDER
                    pygame.draw.line(self.canvas,BORDER,(left+15,y+21),(left+columns-15,y+21))
            self.section(right,441,290,313,"Player knowledge")
            self.text(report['knowledge'].upper() if report else 'NOT ASSESSED',right+20,509,17,GREEN)
            evidence=(('Current ability ' if exact else 'Estimated ability ')+interval(report.get('overall'))+' for '+p['role']+'. Potential '+interval(report.get('potential'))+' is a development outlook, not a guaranteed outcome.') if report else 'Commission a report before judging this player. Unknown attributes stay unknown.'
            self.wrap(evidence,right+20,550,248,21,TEXT)
            if report:
                self.clipped_text(report['source'],right+20,660,248,19,MUTED)
                self.text(('Coverage ends '+dated(self.v,report['coverage_until'])) if report['knowledge']=='Fully scouted' else 'Forecast dated '+dated(self.v,report['day']),right+20,690,18,MUTED)
                self.text('Potential: '+report['confidence'].lower()+' confidence',right+20,719,17,MUTED)
            else:self.text('No medical assessment available',right+20,703,17,MUTED)
            self.text(f"PUBLIC RECORD  /  {p['appearances']} appearances · {p['goals']} goals this season",x,764,19,MUTED)
        elif active=='Development':
            self.panel(x,441,560,313,'Condition and availability')
            self.text(p['availability'] or 'Available for selection',x+20,487,27,RED if p['availability'] else GREEN)
            for i,(label,key) in enumerate((('Condition','condition'),('Fatigue','fatigue'),('Sharpness','sharpness'))):
                self.text(label,x+20,533+i*38,23);self.right_text(f"{p[key]:.0f} / 100" if p[key] is not None else 'Not assessed',x+525,533+i*38,23,GREEN)
            med=p['medical']
            detail=med['type']+' / '+med['stage']+'. Estimated clearance '+dated(self.v,med['estimate'][0])+'–'+dated(self.v,med['estimate'][1]) if med else 'No medical assessment available.' if p['club']!='c0' else 'No active injury report. Condition is separate from long-term ability.'
            self.wrap(detail,x+20,653,520,21,MUTED)
            right=x+575;self.panel(right,441,1400-right,313,'Weekly development plan')
            plan=p['development']
            if plan:
                focus=plan['focus'];load=plan['load']
                self.button('Focus: '+focus,(right+20,491,310,42),lambda:self.cycle_training(p,'focus'),not self.v['match'])
                self.button('Load: '+load,(right+20,548,310,42),lambda:self.cycle_training(p,'load'),not self.v['match'])
                self.wrap('Plans guide weekly development. Intense training adds fatigue; lighter work supports recovery. Minutes and coaching matter. Potential is an uncertain outlook.',right+20,611,1360-right,23)
            else:self.wrap('The employing club controls this player’s development plan. Scouting can improve your evidence without changing their ability.',right+20,495,1360-right,25)
        else:
            self.panel(x,441,650,313,'Employment and public record')
            self.text(money(p['wage'])+' / week',x+20,488,30,GREEN)
            end=dated(self.v,p['contract_end']) if p['contract_end'] is not None else 'No current employment'
            self.text('Contract: '+end,x+20,532,24)
            self.text(f"This season: {p['appearances']} appearances / {p['goals']} goals",x+20,577,23)
            self.text(f"Earlier seasons: {p['career_appearances']} appearances / {p['career_goals']} goals",x+20,620,23)
            self.wrap('Registration, wages and medical eligibility are distinct. Signing a contract never guarantees selection.',x+20,668,600,22)
            right=x+665;self.panel(right,441,1400-right,313,'Terms and planning')
            if p.get('loan'):
                loan=p['loan'];body='On loan from '+self.club(loan['source'])+' until '+dated(self.v,loan['end'])+'. Wage share '+str(loan['share'])+'%.'
            elif p['club']=='c0':body='Manage renewals and signed clauses in Contracts. The manager controls selection and match changes.'
            elif p['club']:body='Club asking fee '+money(p['transfer_quote'])+'. Personal terms and signing fee require separate agreement.'
            else:body='Indicative signing fee '+money(p['fee'])+'. Negotiate personal terms, pass the medical review and confirm registration.'
            self.wrap(body,right+20,487,1360-right,24)
            self.wrap(self.v['planning']['notes'].get(p['id']) or 'No private note yet.',right+20,645,1360-right,22,MUTED)
        self.button('Private note',(1220,389,180,38),lambda:self.open_note(p['id']))
        if p['club']=='c0':
            self.button('Negotiate renewal',(x,794,225,44),lambda:self.contract_open(p['id']),not self.v['match'] and not p['youth'] and not p.get('loan'))
            self.button('Review sale',(x+245,794,195,44),lambda:self.outgoing_open(p['id'],'sale'),not self.v['match'] and not p.get('loan') and not p['youth'])
            self.button('Review loan',(x+460,794,195,44),lambda:self.outgoing_open(p['id'],'loan'),not self.v['match'] and not p.get('loan') and not p['youth'])
        else:
            due=p['scout_due'];terms=self.v['terms']
            self.button('Request scouting',(x,794,210,44),lambda:self.confirm('Commission scouting',f"Spend {money(terms['scout_fee'])} to assess {p['name']}? Report due {dated(self.v,self.v['day']+terms['scout_days'])}. Current ratings become exact on completion; potential stays uncertain.",lambda:self.command('scout',id=p['id'])),not due and (not report or report['day']<self.v['day']) and not self.v['match'] and not self.v['season_done'])
            if p['club'] is None:self.button('Negotiate contract',(x+225,794,220,44),lambda:self.contract_open(p['id']),not self.v['match'] and not p['retired'] and self.v['day']<=self.v['window_end'])
            else:
                self.button('Club enquiry',(x+225,794,195,44),lambda:self.market_open('club_enquire',p['id']),not self.v['match'] and not p.get('loan'))
                self.button('Discuss loan',(x+435,794,195,44),lambda:self.market_open('loan_enquire',p['id']),not self.v['match'] and not p.get('loan'))
                if p.get('buyout_amount'):
                    self.button('Review buy-out',(x+645,794,230,44),lambda:self.confirm('Fund player buy-out',f"Compensation {money(p['buyout_amount'])}, paid in full for the player at completion. The player must agree fresh employment terms and pass medical/registration checks. Existing buy-back, first-refusal and next-transfer sell-on rights end under their signed wording. Nothing is paid now.",lambda:self.open_contract_exit('buyout_enquire',p['id'])),not self.v['match'] and not p.get('loan'))

    def cycle_training(self,p,key):
        choices=('Balanced',*GROUPS) if key=='focus' else ('Light','Normal','Intense')
        plan=dict(p['development']);plan[key]=choices[(choices.index(plan[key])+1)%len(choices)]
        self.command('development_plan',id=p['id'],focus=plan['focus'],load=plan['load'])

    def registration_screen(self,x):
        from .ui import GREEN,MUTED,RED
        v=self.v;r=v['registration'];cfg=r['rules']
        self.button('Back to squad',(x,190,190,42),lambda:setattr(self,'tab','Squad'))
        self.text('List deadline '+dated(v,r['deadline']),x+220,204,23,MUTED)
        own=[p for p in v['players'] if p['club']=='c0' and not p['youth'] and not p['retired']]
        if self.registration_draft is None:self.registration_draft=list(r['players'])
        self.registration_draft=[pid for pid in self.registration_draft if pid in {p['id'] for p in own}]
        selected=[p for p in own if p['id'] in self.registration_draft]
        senior=sum(p['age']>=cfg['exempt_under'] for p in selected)
        self.panel(x,245,1400-x,113,'Competition registration')
        self.text(f"Senior places {senior} / {cfg['senior_limit']}   |   U{cfg['exempt_under']} exempt {len(selected)-senior}   |   Reserved arrivals {r['reserved']}",x+20,289,25,GREEN)
        self.text('Unlisted players remain employed and paid. Injuries, suspensions and loan restrictions still apply.',x+20,331,20,MUTED)
        editable=v['day']<=r['deadline'] and not v['match'] and not v['season_done']
        self.page=min(self.page,max(0,(len(own)-1)//7))
        for i,p in enumerate(own[self.page*7:self.page*7+7]):
            y=378+i*55;self.panel(x,y,1400-x,50)
            self.text(p['name']+' / '+p['role'],x+15,y+8,24)
            self.text(('U21 exempt' if p['age']<cfg['exempt_under'] else 'Senior place')+' / '+('Homegrown' if p['homegrown'] else 'Non-homegrown'),x+15,y+32,17,MUTED)
            self.text((p['availability'] or f"Available / condition {p['condition']:.0f}%")[:42],x+470,y+18,21,RED if p['availability'] else MUTED)
            self.button('Remove' if p['id'] in self.registration_draft else 'Include',(1240,y+5,145,40),lambda pid=p['id']:self.toggle_registration(pid),editable)
        self.pager(x,786,len(own),7)
        self.button('Reset draft',(970,786,155,42),lambda:setattr(self,'registration_draft',list(r['players'])))
        self.button('Review registration',(1140,786,260,42),lambda:self.confirm('Submit competition list',f"Register {len(selected)} players, using {senior} senior places. Players omitted from this list remain paid but cannot be selected. List edits close on {dated(v,r['deadline'])}. Pending arrivals also need capacity.",lambda:self.command('registration_submit',players=list(self.registration_draft))),editable)

    def toggle_registration(self,pid):
        if pid in self.registration_draft:self.registration_draft.remove(pid)
        else:self.registration_draft.append(pid)

    def football_screen(self,x):
        import pygame
        from .ui import GREEN,MUTED,TEXT,RED
        archive=[f for h in self.v['career']['history'] for f in h['fixtures']]
        historical=next((f for f in self.v['fixtures']+archive if f['id']==self.match_report and f['result']),None)
        m=dict(historical['result'],home=historical['home'],away=historical['away'],finished=True) if historical else self.v['match']
        if historical and 'minute' not in m:m['minute']=90
        if not m:
            self.wrap('No active match. Use Next fixture to advance. Completed matches stay available through League and Career history.',x,230,1000,29);return
        self.panel(x,195,1400-x,130)
        if not historical and not self.reduced_motion and pygame.time.get_ticks()<self.goal_until:
            pygame.draw.rect(self.canvas,GREEN,(x,195,1400-x,130),3,border_radius=7)
        crest(self.canvas,m['home'],(x+15,213,48,76));crest(self.canvas,m['away'],(1330,213,48,76))
        self.text(f"{self.club(m['home'])}   {m['score'][0]} – {m['score'][1]}   {self.club(m['away'])}",x+82,221,30)
        status='FT' if finished(m) else m.get('clock',str(m['minute']))+"'"
        self.text(f"{status}  |  Shots {m['shots'][0]}–{m['shots'][1]}  |  On target {m['on_target'][0]}–{m['on_target'][1]}  |  xG {m['xg'][0]:.2f}–{m['xg'][1]:.2f}",x+82,278,22,GREEN)
        fixture=historical or next((f for f in self.v['fixtures'] if f['id']==m.get('fixture')),None)
        if fixture and fixture.get('knockout'):
            from .competitions import label
            detail=label(fixture)
            if finished(m) and m.get('winner'):
                detail+='  /  Advances: '+self.club(m['winner'])
                if any(m.get('kicks',[0,0])):detail+=f"  /  Pens {m['shootout'][0]}–{m['shootout'][1]}"
            self.clipped_text(detail,x+82,305,1040,16,MUTED)
        self.button('Show commentary' if self.tab in ('Lineups','Statistics','Selection') else 'Commentary',(x,340,185,38),lambda:(setattr(self,'tab','Commentary'),setattr(self,'page',0)))
        self.button('Lineups',(x+200,340,125,38),lambda:(setattr(self,'tab','Lineups'),setattr(self,'page',0)))
        self.button('Statistics',(x+340,340,145,38),lambda:(setattr(self,'tab','Statistics'),setattr(self,'page',0)))
        self.button('All events' if self.key_events_only else 'Key events',(x+500,340,150,38),lambda:(setattr(self,'key_events_only',not self.key_events_only),setattr(self,'page',0)))
        self.button('Selection',(x+665,340,145,38),lambda:(setattr(self,'tab','Selection'),setattr(self,'page',0)))
        self.panel(x,392,1400-x,351)
        if self.tab=='Lineups':
            for side,ids in enumerate(m.get('participants',m['lineups'])):
                left=x+20+side*((1400-x)//2)
                for i,pid in enumerate(ids):
                    p=self.v['public_players'][pid];stat=m.get('stats',{}).get(pid,{})
                    marker=' OFF' if pid not in m.get('on_pitch',m['lineups'])[side] else ''
                    if pid in m.get('dismissed',[]):marker=' RED'
                    detail=f"{stat.get('minutes',0)}m / {stat.get('rating',6):.1f}" if stat else ''
                    self.text((p['role']+'  '+p['name']+marker)[:34],left,406+i*20,20,RED if marker==' RED' else TEXT)
                    self.right_text(detail,left+(1400-x)//2-42,406+i*20,19,MUTED)
        elif self.tab=='Selection':
            self.selection_report(x,m)
        elif self.tab=='Statistics':
            total=max(1,sum(m['possession']))
            rows=[('Possession',f"{m['possession'][0]*100/total:.0f}%",f"{m['possession'][1]*100/total:.0f}%")]
            for label,key in (('Shots','shots'),('On target','on_target'),('Expected goals','xg'),('Fouls','fouls'),('Corners','corners'),('Yellow cards','yellow_cards'),('Red cards','red_cards'),('Substitutions','substitutions')):
                a,b=m.get(key,[0,0]);rows.append((label,f'{a:.2f}' if key=='xg' else str(a),f'{b:.2f}' if key=='xg' else str(b)))
            for i,(label,a,b) in enumerate(rows):
                y=411+i*32;self.text(a,x+170,y,24,GREEN);self.text(label,x+350,y,23);self.text(b,1210,y,24,GREEN)
        else:
            kinds=('goal','period','bench','yellow','red','injury','substitution','penalty','shootout','abandonment','administrative_draw','tactic','selection')
            events=[e for e in m['events'] if not self.key_events_only or e['kind'] in kinds]
            self.page=min(self.page,max(0,(len(events)-1)//10))
            for i,e in enumerate(events[max(0,len(events)-10-self.page*10):len(events)-self.page*10 if self.page else None]):
                clock=e.get('clock',str(e['minute']));self.text(clock+"'",x+18,412+i*31,21,MUTED)
                self.text(e['text'][:109],x+90,412+i*31,21,GREEN if e['kind']=='goal' else RED if e['kind'] in ('red','injury') else TEXT)
            self.button('Earlier events',(1110,756,200,38),lambda:setattr(self,'page',self.page+1),(self.page+1)*10<len(events))
            self.button('Latest events',(1110,803,200,38),lambda:setattr(self,'page',0),self.page>0)
        if not finished(m):
            self.button('Pause' if self.play else 'Play',(x,757,125,42),lambda:setattr(self,'play',not self.play))
            self.button(f'{self.speed}x',(x+140,757,80,42),self.cycle_speed)
            self.button('Skip to full time',(x+235,757,200,42),lambda:self.command('match_skip'))
            self.button('Back the manager',(x,806,220,38),lambda:self.confirm('Back the manager','Send private encouragement? This supports the relationship without guaranteeing a result.',lambda:self.command('intervene',choice='encourage')),not m['intervened'])
            self.button('Request more attacking',(x+235,806,270,38),lambda:self.confirm('Request attacking football','Ask the manager to take more risks? They may refuse. An accepted request increases forward risk and defensive exposure.',lambda:self.command('intervene',choice='attack')),not m['intervened'])
        elif historical:self.button('Back to fixtures',(x,757,200,42),lambda:self.nav('League'))
        else:self.button('Finish review',(x,757,190,42),lambda:(self.command('match_close'),self.nav('Overview')))
        if historical and self.v['match']:
            self.button('Return to live match',(x+220,757,250,42),lambda:(setattr(self,'match_report',None),setattr(self,'page',0)))
        if finished(m):
            detail=f"Manager review: {m['shots'][0]}–{m['shots'][1]} shots, {m['xg'][0]:.2f}–{m['xg'][1]:.2f} xG."
            self.text(detail,x,817,20,MUTED)

    def selection_report(self,x,m):
        from .ui import GREEN,MUTED,TEXT
        plan=next((p for p in m.get('selection_plans',[]) if p),None)
        if not plan:
            self.wrap('No starting-selection record is available for this older match.',x+20,418,1100,25,MUTED);return
        self.text('Starting plan '+plan['formation']+' / preferred '+plan['preferred'],x+20,410,25,GREEN)
        counts=plan['selected_roles']
        self.text(f"Selected: {counts['GK']} GK, {counts['DEF']} DEF, {counts['MID']} MID, {counts['FWD']} FWD / "+plan['rotation']+' / '+plan['youth'],x+20,445,21,MUTED)
        self.wrap(plan['reason'],x+20,478,1110,21,TEXT)
        ids=plan['starters']+plan['bench'];self.page=min(self.page,max(0,(len(ids)-1)//7))
        for i,pid in enumerate(ids[self.page*7:self.page*7+7]):
            player=self.v['public_players'][pid];y=533+i*27
            label='Starter' if pid in plan['starters'] else 'Bench'
            self.text(label+' / '+player['role']+' / '+player['name'],x+20,y,21,TEXT)
            self.text(plan['reasons'][pid],x+590,y,20,MUTED)
        self.button('Previous selections',(x+700,757,220,38),lambda:setattr(self,'page',self.page-1),self.page>0)
        self.button('More selections',(x+935,757,220,38),lambda:setattr(self,'page',self.page+1),(self.page+1)*7<len(ids))
