"""Staff recruitment and owner oversight through authorised snapshots."""
import pygame
from .staff import ROLES,CAPABILITIES
from .delegation import DEPARTMENTS,MODES,cover_plan
from .planning import dated
from .presentation import portrait
from .football_ui import interval


class StaffScreens:
    def staff_section(self,tab):
        self.staff_tab=tab;self.staff_person=None;self.staff_draft=None;self.responsibility=None;self.authority_draft=None
        self.page=0;self.focus=0;self.focus_reveal=True;self.save_preferences()

    def draw_staff(self,x):
        from .ui import BG
        pygame.draw.rect(self.canvas,BG,(x,142,1155,37))
        for i,(tab,width) in enumerate((('Manager',150),('People',150),('Responsibilities',215),('Approvals',170),('Reports',150))):
            left=x+(0,165,330,560,745)[i]
            count=sum(c['status'] in ('pending','blocked') for c in self.v['delegation']['cases'])
            label=tab+(f' ({count})' if tab=='Approvals' and count else '')
            self.button(('• ' if self.staff_tab==tab else '')+label,(left,142,width,36),lambda tab=tab:self.staff_section(tab))
        if self.staff_tab=='Manager':self.staff_screen(x)
        elif self.staff_tab=='People':self.staff_people(x)
        elif self.staff_tab=='Responsibilities':self.staff_responsibilities(x)
        elif self.staff_tab=='Approvals':self.staff_approvals(x)
        else:self.staff_reports(x)

    def staff_people(self,x):
        from .ui import GREEN,MUTED,money
        people=self.v['staff']['people']
        p=next((p for p in people if p['id']==self.staff_person),None)
        if p:self.staff_profile(x,p);return
        scopes=('Candidates','Employed here','Shortlist','All')
        self.button(self.staff_scope,(x,195,225,42),lambda:(setattr(self,'staff_scope',scopes[(scopes.index(self.staff_scope)+1)%len(scopes)]),setattr(self,'page',0)))
        roles=('All roles',*ROLES)
        self.button(self.staff_role,(x+240,195,235,42),lambda:(setattr(self,'staff_role',roles[(roles.index(self.staff_role)+1)%len(roles)]),setattr(self,'page',0)))
        self.text('Completed assessments reveal current ability. Hiring reserves future payroll.',x,253,22,MUTED)
        def in_scope(p):
            return {'All':True,'Employed here':p['club']=='c0','Shortlist':p['id'] in self.v['staff']['shortlist'],'Candidates':p['club']!='c0'}[self.staff_scope]
        rows=[p for p in people if in_scope(p) and (self.staff_role=='All roles' or p['role']==self.staff_role)]
        self.page=min(self.page,max(0,(len(rows)-1)//5))
        for i,p in enumerate(rows[self.page*5:self.page*5+5]):
            y=295+i*91;self.panel(x,y,1400-x,80);portrait(self.canvas,p['id'],42,(x+15,y+12,45,58))
            self.text(p['name'],x+78,y+15,26);self.text(ROLES[p['role']][0],x+78,y+47,21,MUTED)
            self.text(money(p['wage'] if p['club']=='c0' else p['expected_wage'])+'/week',x+420,y+17,24,GREEN)
            caption='Joining '+dated(self.v,p['pending']['start']) if p['pending'] else 'Your club' if p['club']=='c0' else self.club(p['club']) if p['club'] else 'Available candidate'
            self.text(caption,x+420,y+50,19,MUTED)
            report=p['assessment']
            self.clipped_text(('CA ' if report.get('exact_current') else 'Est. CA ')+interval(report.get('overall')) if report else 'Not assessed',x+720,y+21,190,22,GREEN)
            self.button('Open staff profile',(1170,y+19,210,42),lambda p=p:(setattr(self,'staff_person',p['id']),setattr(self,'staff_draft',None),setattr(self,'page',0)))
        if not rows:self.text('No people match these filters.',x+20,340,25,MUTED)
        self.pager(x,788,len(rows),5)

    def staff_profile(self,x,p):
        from .ui import GREEN,MUTED,TEXT,money
        v=self.v;o=v['staff']['offers'].get(p['id']);own=p['club']=='c0';pending=p['pending']
        self.button('Back to staff list',(x,195,205,42),lambda:(setattr(self,'staff_person',None),setattr(self,'staff_draft',None)))
        self.button('Remove staff shortlist' if p['id'] in v['staff']['shortlist'] else 'Shortlist staff',(x+225,195,245,42),lambda:self.command('staff_shortlist',id=p['id']))
        self.panel(x,255,1400-x,115);portrait(self.canvas,p['id'],42,(x+18,267,72,88))
        self.text(p['name'],x+110,274,35);self.text(ROLES[p['role']][0],x+110,319,24,GREEN)
        caption='Joining '+dated(v,pending['start']) if pending else 'Contract to '+dated(v,p['end']) if own else 'Employed by '+self.club(p['club']) if p['club'] else 'Available for appointment'
        self.text(caption,950,282,22,MUTED);self.text('Capacity '+str(p['availability'])+'%',950,320,22,MUTED)
        report=p['assessment'];exact=bool(report and report['exact_current'])
        self.text(('Current ability ' if exact else 'Estimated ability ')+interval(report.get('overall') if report else None)+' / '+p['role'],x+110,348,17,MUTED)
        self.panel(x,387,570,348,'Current capabilities / 1–100' if exact else 'Capability estimates / 1–100')
        for i,key in enumerate(CAPABILITIES):
            left=x+20+(i//6)*275;y=430+(i%6)*47
            self.text(key.replace('_',' ').capitalize(),left,y,21)
            pair=report['ranges'].get(key) if report else None
            self.text(interval(pair) if pair else 'Not assessed',left,y+20,21,GREEN if pair else MUTED)
        right=x+590;self.panel(right,387,1400-right,348,'Employment review')
        editable=o and o['status'] in ('interviewed','counter','agreed')
        if self.staff_draft is None:self.staff_draft=dict(wage=o['wage'] if o else p['expected_wage'],duration=o['duration'] if o else 2,autonomy=o['autonomy'] if o else 'Advisory')
        d=self.staff_draft if editable else o or dict(wage=p['wage'] if own else p['expected_wage'],duration=2,autonomy=p['autonomy'])
        self.text(('EMPLOYED' if own else 'JOINING' if pending else o['status'].upper() if o else 'CONTACT REQUIRED'),right+20,431,22,GREEN)
        self.text('Weekly salary',right+20,478,22,MUTED);self.text(money(d['wage']),right+218,478,25)
        self.text('Compact seasons',right+20,529,22,MUTED);self.text(str(d['duration']),right+218,529,25)
        def edit(key,delta):
            self.staff_draft[key]=max(10000,min(1000000,self.staff_draft[key]+delta)) if key=='wage' else max(1,min(3,self.staff_draft[key]+delta))
        for i,(key,step) in enumerate((('wage',5000),('duration',1))):
            y=468+i*51
            self.button('−',(right+360,y,52,38),lambda key=key,step=step:edit(key,-step),editable)
            self.button('+',(right+425,y,52,38),lambda key=key,step=step:edit(key,step),editable)
        self.button(d['autonomy'],(right+20,578,310,40),lambda:self.staff_draft.update(autonomy='Approval required' if self.staff_draft['autonomy']=='Advisory' else 'Advisory'),editable)
        self.text('Compensation '+money(p['compensation'])+' / '+str(p['notice_weeks'])+' weeks notice',right+20,640,21,MUTED)
        self.wrap('Protected approval terms prevent autonomous commitments. Salary starts on joining; authority requires assignment.',right+20,676,1360-right,20,MUTED)
        caption=report['knowledge'] if report else 'Not assessed'
        if report and report['knowledge']=='Fully assessed':caption+=' / coverage ends '+dated(v,report['coverage_until'])
        elif report and not exact:caption+=' / evidence dated '+dated(v,report['day'])
        self.text(caption+'. Personality and future performance remain uncertain.',x,749,19,MUTED)
        self.clipped_text(o['transcript'][-1] if o else 'Contact, interview, then agree terms.',x,774,1400-x,17,TEXT)
        if own or pending:
            if own:self.button('Review staff renewal',(x,798,240,42),lambda:self.confirm('Renew '+p['name'],'Extend at the existing salary, notice and approval terms for three compact seasons. Current contract: '+dated(v,p['end'])+'.',lambda:self.command('staff_renew',id=p['id'],duration=3)))
            self.button('Review staff dismissal',(x+260,798,260,42),lambda:self.confirm('End '+p['name']+' agreement','Pay notice of '+money(p['notice_cost'])+'. Uncovered responsibilities return to you and unsigned delegated actions are cancelled. Existing signed contracts remain binding.',lambda:self.command('staff_dismiss',id=p['id'])))
        elif not o or o['status'] in ('withdrawn','expired','rejected','ended'):
            self.button('Contact candidate',(x,798,220,42),lambda:(self.command('staff_contact',id=p['id']),setattr(self,'staff_draft',None)))
        elif o['status']=='contact':
            self.button('Conduct interview',(x,798,220,42),lambda:self.command('staff_interview',id=p['id']),v['day']>=o['interview_due'])
            self.text('Available '+dated(v,o['interview_due']),x+245,811,22,MUTED)
        elif editable:
            self.button('Send staff proposal',(x,798,225,42),lambda:(self.command('staff_propose',id=p['id'],**self.staff_draft),setattr(self,'staff_draft',None)))
            delay=7 if p['club'] else 2
            span=v['season_end']-v['season_start']+v['career_settings']['season_gap']
            end=v['season_end']+span*(o['duration']-1 if not v['season_done'] else o['duration'])
            total=p['compensation']+o['wage']*max(0,end-v['day']-delay+1)//7
            body=f"Latest terms: {money(o['wage'])}/week, {o['autonomy']}. Pay {money(p['compensation'])} employer compensation now. Employment {dated(v,v['day']+delay)} to {dated(v,end)}; guaranteed exposure approximately {money(total)}. Notice is capped at {p['notice_weeks']} weeks or remaining salary. Future wages are reserved; unsent edits are excluded."
            self.button('Review staff appointment',(x+245,798,280,42),lambda:self.confirm('Appoint '+p['name'],body,lambda:self.command('staff_accept',id=p['id'])),o['status'] in ('counter','agreed'))
        if o and o['status'] in ('contact','interviewed','counter','agreed'):
            self.button('Withdraw staff discussion',(1120,798,280,42),lambda:self.command('staff_withdraw',id=p['id']))

    def staff_responsibilities(self,x):
        from .ui import GREEN,MUTED,money
        v=self.v;d=v['delegation'];rules=d['responsibilities'];names={p['id']:p['name'] for p in v['staff']['people']}
        if self.responsibility in rules:self.authority_editor(x,self.responsibility);return
        for i,preset in enumerate(('Hands-on','Balanced','Executive')):
            def review(preset=preset):
                details=[]
                for key,r in rules.items():
                    if r['delegate']:details.append(DEPARTMENTS[key][0])
                mode='advice only' if preset=='Hands-on' else 'owner approval' if preset=='Balanced' else 'automatic action within limits'
                self.confirm(preset+' responsibilities','Apply '+mode+' to '+(', '.join(details) or 'no staffed departments')+'. Contractual approval protections remain. Vacancies stay with you. Changed authority cancels unsigned delegated work; existing contracts remain binding.',lambda:self.command('delegation_preset',preset=preset))
            self.button(preset,(x+i*175,195,160,42),review)
        plan=cover_plan(v)
        self.button('Review coverage',(1120,195,280,42),lambda:self.confirm('Assign advisory cover',f"Allocate {len(plan)} uncovered departments using observed capabilities and available staff capacity. Each assignment uses 25% of a staff member’s capacity. All new assignments remain advisory until you change their mode. "+'; '.join(DEPARTMENTS[k][0]+': '+names[a] for k,a in plan.items()),lambda:self.command('delegation_cover')),bool(plan))
        self.text('Rolling 28-day commitments '+money(d['used'])+' / club limit '+money(d['club_limit']),x,252,23,GREEN)
        self.text('Manager selection and tactics retain their existing autonomy. Hiring and firing remain with you.',x,285,20,MUTED)
        rows=list(rules.items());self.page=min(self.page,max(0,(len(rows)-1)//6))
        for i,(key,r) in enumerate(rows[self.page*6:self.page*6+6]):
            y=325+i*70;self.panel(x,y,1400-x,60)
            self.text(DEPARTMENTS[key][0],x+15,y+13,25)
            self.text(names.get(r['delegate'],'Owner coverage')+' / '+r['mode'],x+260,y+13,21,MUTED)
            self.text(money(r['used'])+' / '+money(r['limit']),x+260,y+37,18,MUTED)
            self.button('Edit responsibility',(1170,y+10,210,40),lambda key=key:(setattr(self,'responsibility',key),setattr(self,'authority_draft',None)))
        self.pager(x,788,len(rows),6)
        self.button('Club limit −£25k',(990,788,195,40),lambda:self.confirm('Lower club authority','Set the rolling delegated limit to '+money(max(0,d['club_limit']-2500000))+'. Existing signed commitments remain binding.',lambda:self.command('delegation_club_limit',value=max(0,d['club_limit']-2500000))))
        self.button('Club limit +£25k',(1200,788,200,40),lambda:self.confirm('Raise club authority','Set the rolling delegated limit to '+money(d['club_limit']+2500000)+'. This does not add cash or change wage budgets.',lambda:self.command('delegation_club_limit',value=d['club_limit']+2500000)))

    def authority_editor(self,x,key):
        from .ui import GREEN,MUTED,money
        current=self.v['delegation']['responsibilities'][key]
        if self.authority_draft is None:self.authority_draft={k:current[k] for k in ('delegate','mode','limit','days','objective')}
        d=self.authority_draft;own=[p for p in self.v['staff']['people'] if p['club']=='c0'];ids=[None]+[p['id'] for p in own]
        names={p['id']:p['name'] for p in own};names[None]='Owner / unassigned'
        self.button('Back to responsibilities',(x,195,270,42),lambda:(setattr(self,'responsibility',None),setattr(self,'authority_draft',None)))
        self.panel(x,260,1400-x,456,DEPARTMENTS[key][0]+' / future authority')
        def cycle_delegate():
            d['delegate']=ids[(ids.index(d['delegate'])+1)%len(ids)] if d['delegate'] in ids else None
            if not d['delegate']:d['mode']='Manual'
        self.button(names.get(d['delegate'],'Owner / unassigned'),(x+25,320,380,44),cycle_delegate)
        self.button(d['mode'],(x+450,320,340,44),lambda:d.update(mode=MODES[(MODES.index(d['mode'])+1)%len(MODES)]))
        self.text('28-day commitment allowance',x+25,407,25,MUTED);self.text(money(d['limit']),x+450,407,29,GREEN)
        self.button('Limit −£5k',(x+725,393,160,42),lambda:d.update(limit=max(0,d['limit']-500000)))
        self.button('Limit +£5k',(x+905,393,170,42),lambda:d.update(limit=min(100000000,d['limit']+500000)))
        self.text('Maximum contract duration',x+25,482,25,MUTED);self.text(str(d['days'])+' days',x+450,482,29,GREEN)
        self.button('Duration −30',(x+725,468,160,42),lambda:d.update(days=max(0,d['days']-30)))
        self.button('Duration +30',(x+905,468,170,42),lambda:d.update(days=min(1095,d['days']+30)))
        self.button('Objective: '+d['objective'],(x+25,554,365,42),lambda:d.update(objective='Develop' if d['objective']=='Maintain' else 'Maintain'),key=='operations')
        self.wrap('This allocation uses 25% staff capacity. The lower department or club commitment limit applies. Cash reserves, wage budgets, registration and contractual consent are checked again before commitment. Medical authority only permits light recovery work.',x+25,628,1070,23,MUTED)
        self.button('Review responsibility',(x,765,275,44),lambda:self.confirm('Change '+DEPARTMENTS[key][0],f"Delegate: {names.get(d['delegate'],'Owner')}. Mode: {d['mode']}. Rolling 28-day allowance {money(d['limit'])}; maximum {d['days']} days. Objective {d['objective']}. Reassigning cancels unsigned delegated work and keeps signed obligations.",lambda:(self.command('delegation_set',key=key,**d),setattr(self,'authority_draft',None))))

    def staff_approvals(self,x):
        from .ui import GREEN,MUTED,money
        rows=[c for c in self.v['delegation']['cases'] if c['status'] in ('pending','blocked')]
        self.text('Each approval authorises the displayed step once. Signed obligations remain binding.',x,206,23,MUTED)
        self.page=min(self.page,max(0,(len(rows)-1)//4))
        for i,c in enumerate(rows[self.page*4:self.page*4+4]):
            y=260+i*124;self.panel(x,y,1400-x,110)
            self.text(DEPARTMENTS[c['responsibility']][0]+' / due '+dated(self.v,c['expires']),x+18,y+14,25,GREEN)
            self.text(c['reason'][:93],x+18,y+48,20)
            self.text((c['issue']+' Exposure '+money(c['exposure']['cost']))[:98],x+18,y+77,19,MUTED)
            def review(c=c):
                p=next((p for p in self.v['players'] if p['id']==c['data'].get('id')),None)
                subject=(p['name']+'. ' if p else '')
                extras=''
                if 'wage' in c['data']:extras+='Salary '+money(c['data']['wage'])+'/week. '
                if 'fee' in c['data']:extras+='Signing fee '+money(c['data']['fee'])+'. '
                if c['data'].get('right')=='stadium':extras+='Stadium naming rights affect supporter sentiment. '
                self.confirm('Approve '+DEPARTMENTS[c['responsibility']][0],subject+c['reason']+' '+extras+'Guaranteed exposure '+money(c['exposure']['cost'])+'; duration '+str(c['exposure']['days'])+' days. This is a one-off owner approval above delegate limits where needed; affordability and consent still apply.',lambda:self.command('delegation_case',id=c['id'],choice='approve'))
            self.button('Review proposal',(1180,y+14,200,40),review)
            self.button('Decline proposal',(1180,y+62,200,36),lambda c=c:self.command('delegation_case',id=c['id'],choice='decline'))
        if not rows:self.wrap('No staff proposals need approval. Unstaffed and manual departments remain under your control. Review Responsibilities to change who can act.',x+25,310,1040,27,MUTED)
        self.pager(x,795,len(rows),4)

    def staff_reports(self,x):
        from .ui import GREEN,MUTED,money
        self.text('RECORDED ACTIONS / reasons, outcomes and guaranteed exposure',x,205,23,GREEN)
        self.button('League activity' if not self.staff_league else 'Your staff activity',(1110,195,290,42),lambda:(setattr(self,'staff_league',not self.staff_league),setattr(self,'page',0)))
        rows=list(reversed(self.v['club_ai']['transfers'] if self.staff_league else self.v['delegation']['log']))
        names={p['id']:p['name'] for p in self.v['staff']['people']};players={p['id']:p['name'] for p in self.v['players']}
        for i,e in enumerate(rows[self.page*4:self.page*4+4]):
            y=270+i*125;self.panel(x,y,1400-x,110)
            if self.staff_league:
                self.text(self.club(e['club'])+' signed '+players[e['player']],x+20,y+18,26)
                self.text(dated(self.v,e['completed'])+' / Transfer fee '+money(e['fee']),x+20,y+60,23,MUTED)
            else:
                self.text(dated(self.v,e['day'])+' / '+names.get(e['actor'],'Staff')+' / '+DEPARTMENTS[e['responsibility']][0],x+20,y+13,23,GREEN)
                self.text(e['reason'][:111],x+20,y+46,20)
                self.text((e['outcome']+' / Committed '+money(e['committed']))[:111],x+20,y+77,19,MUTED)
        if not rows:self.wrap('Completed actions appear here. Browsing reports changes no agreements or funds. Opponents’ private targets and ability estimates are not available.',x+25,320,1040,26,MUTED)
        self.pager(x,795,len(rows),4)
