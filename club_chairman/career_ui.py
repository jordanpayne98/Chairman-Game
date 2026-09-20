"""Career, negotiations, academy and facilities screens for the Executive shell."""
import pygame
from .planning import dated
from .contract_review import review, CLOSED
from .presentation import crest,portrait,pitch
from .simulation import MANAGERS
from .commercial import venue_name
from .clause_ui import ClauseScreens
from .clauses import terms as clause_terms, description as clause_description

TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161);RED=(246,150,142)
def money(value):return f'£{value/100:,.0f}'


class CareerScreens(ClauseScreens):
    def contract_open(self,pid):
        offer=self.v['career']['offers'].get(pid)
        if not offer or offer['status'] in ('completed','withdrawn','expired','rejected'):
            if not self.command('enquire',id=pid):return
        self.nav('Contracts');self.offer_id=pid;self.offer_draft=None;self.offer_archive=None;self.offer_tab='Terms';self.page=0

    def draw_contracts(self,x):
        offers=self.v['career']['offers']
        archive=self.v['career'].get('offer_history',[])
        if self.offer_archive is not None and 0<=self.offer_archive<len(archive):
            self.draw_offer(x,archive[self.offer_archive],archived=True);return
        if self.offer_id in offers:self.draw_offer(x,offers[self.offer_id]);return
        self.text('CONTRACT DESK  /  every agreement requires your review',x,200,23,GREEN)
        self.button('Discussions' if self.tab=='Expiring' else 'Expiring agreements',(1150,190,250,42),lambda:(setattr(self,'tab','Discussions' if self.tab=='Expiring' else 'Expiring'),setattr(self,'page',0)))
        self.button('Clauses' if self.tab!='Clauses' else 'Discussions',(960,190,175,42),lambda:(setattr(self,'tab','Discussions' if self.tab=='Clauses' else 'Clauses'),setattr(self,'page',0)))
        if self.tab=='Clauses':self.draw_clause_register(x);return
        if self.tab=='Expiring':
            self.text('SENIOR PLAYER AGREEMENTS / earliest expiry first',x,246,23,MUTED)
            rows=sorted((p for p in self.v['players'] if p['club']=='c0' and not p['youth']),key=lambda p:(p['contract_end'],p['id']))
            for i,p in enumerate(rows[self.page*5:self.page*5+5]):
                y=292+i*90;self.panel(x,y,1400-x,78)
                self.text(p['name']+' / '+p['role'],x+20,y+15,26)
                self.text(dated(self.v,p['contract_end'])+f" / {max(0,p['contract_end']-self.v['day'])} days remaining / {money(p['wage'])} per week",x+20,y+48,21,RED if p['contract_end']-self.v['day']<=28 else MUTED)
                self.button('Discuss renewal',(1180,y+19,200,42),lambda pid=p['id']:self.contract_open(pid),not self.v['match'] and not p.get('loan'))
            self.pager(x,780,len(rows),5);return
        self.button('Current' if self.tab=='History' else 'History',(790,190,150,42),lambda:(setattr(self,'tab','Discussions' if self.tab=='History' else 'History'),setattr(self,'page',0)))
        self.text(f"Reserved cash {money(self.v['reserved_cash'])}  /  Reserved wages {money(self.v['reserved_wages'])} per week",x,241,24)
        rows=list(reversed(archive)) if self.tab=='History' else list(reversed(list(offers.values())))
        for i,o in enumerate(rows[self.page*5:self.page*5+5]):
            p=next(p for p in self.v['players'] if p['id']==o['player']);y=290+i*91
            self.panel(x,y,1400-x,78)
            self.text(p['name']+'  /  '+o['kind'].capitalize(),x+20,y+14,26)
            self.text(o['status'].upper()+'  /  '+money(o['wage'])+' per week  /  expires '+dated(self.v,o['expires']),x+20,y+48,21,MUTED)
            def open_row(offer=o):
                self.offer_archive=archive.index(offer) if self.tab=='History' else None
                self.offer_id=offer['player'];self.offer_draft=None;self.offer_tab='Terms';self.page=0
            self.button('Open discussion',(1190,y+18,190,42),open_row)
        if not rows and self.tab=='History':self.wrap('Earlier discussions appear here when you reopen a closed negotiation. Completed and withdrawn terms remain read-only.',x+20,335,1000,28,TEXT)
        elif not rows:self.wrap('Open a free agent in Recruitment or a player in your Squad, then choose Negotiate contract. Drafts do not reserve money. Conditional acceptance reserves capacity until the final review.',x+20,335,1000,28,TEXT)
        self.pager(x,780,len(rows),5)

    def offer_edit(self,key,delta):
        draft=dict(self.offer_draft);draft[key]+=delta
        limits={'wage':(10000,500000),'fee':(0,10000000),'duration':(1,3),'appearance_bonus':(0,100000),'goal_bonus':(0,100000)}
        draft[key]=max(limits[key][0],min(limits[key][1],draft[key]));self.offer_draft=draft;self.save_preferences()

    def offer_action(self,action,o):
        if self.command(action,id=o['player'],**(self.offer_draft if action=='propose_offer' else {})):
            self.offer_draft=None;self.save_preferences()

    def offer_section(self,section):
        self.offer_tab=section;self.page=0;self.save_preferences()

    def draw_offer(self,x,o,archived=False):
        p=next(p for p in self.v['players'] if p['id']==o['player'])
        if self.offer_draft is None:self.offer_draft={k:o[k] for k in ('wage','fee','duration')}
        for key,value in clause_terms(o).items():self.offer_draft.setdefault(key,value)
        editable=not archived and o['status'] in ('draft','counter','agreed')
        terms=self.offer_draft if editable else o
        details=review(self.v,o,terms if editable else None)
        accepted=review(self.v,o)
        self.button('< Discussions',(x,190,185,42),lambda:(setattr(self,'offer_id',None),setattr(self,'offer_archive',None),setattr(self,'offer_draft',None),setattr(self,'page',0)))
        self.text(p['name']+' / '+o['status'].upper()+(' / ARCHIVED' if archived else ''),x+205,202,27,GREEN)
        for i,label in enumerate(('Terms','Cash review','Conversation','Clauses')):
            self.button(('• ' if self.offer_tab==label else '')+label,(x+i*190,244,180,40),lambda label=label:self.offer_section(label))
        stages=('Personal terms','Conditional acceptance','Medical review','Registration')
        stage={'draft':0,'counter':0,'agreed':1,'medical':2,'ready':3,'completed':4}.get(o['status'],-1)
        width=(1400-x)/4
        for i,label in enumerate(stages):
            left=x+i*width
            pygame.draw.rect(self.canvas,GREEN if i<stage else (47,62,70),(left,303,width-10,3))
            self.text(str(i+1)+'. '+label,left,316,20,GREEN if i==stage else MUTED)
        if self.offer_tab=='Clauses':self.draw_offer_clauses(x,o,terms,editable)
        elif self.offer_tab=='Conversation':
            self.panel(x,360,1400-x,335,'Offer history / oldest first')
            lines=o['transcript'];page=min(self.page,max(0,(len(lines)-1)//3));self.page=page
            y=410
            for line in lines[page*3:page*3+3]:y=self.wrap(line,x+24,y,1350-x,24,TEXT)+22
            self.pager(x,706,len(lines),3)
        elif self.offer_tab=='Cash review':
            self.panel(x,360,1400-x,353,'Recorded terms against current finances' if archived or o['status'] in CLOSED else 'Draft scenario' if editable else 'Reviewed package')
            rows=[('Personal fee / club payment now',money(terms['fee'])+' / '+money(details['upfront'])),('Cash after completion',money(details['cash_after'])),
                  ('Other reserved fees',money(details['reserved_cash'])),('Available above operating reserve',money(details['available'])),
                  ('Weekly payroll change',money(details['wage_delta'])),('Weekly headroom after other offers',money(details['headroom'])),
                  ('Deferred fee / guaranteed package',money(details['deferred'])+' / '+money(details['total'])),
                  ('Sell-on receipt on this acquisition',money(details['sell_on_receipt'])),
                  ('Additional exposure over current contract',money(details['additional']))]
            for i,(label,value) in enumerate(rows):
                y=408+i*32;self.text(label,x+24,y,23,MUTED);self.text(value,x+625,y,24,TEXT)
            self.text('Historical what-if only; cash is not charged again.' if archived or o['status'] in CLOSED else 'Completion today; excludes accrued wages, future bonuses and unused options.',x+20,727,21,MUTED)
        else:
            self.panel(x,360,560,351,'Editable draft / not yet sent' if editable else 'Recorded terms')
            for i,(key,label,value,step) in enumerate([('wage','Weekly salary',money(terms['wage']),5000),('fee','Signing fee',money(terms['fee']),50000),('duration','Seasons',str(terms['duration']),1)]):
                y=414+i*65;self.text(label,x+20,y,24,MUTED);self.text(value,x+215,y,26)
                self.button('−',(x+410,y-7,50,38),lambda k=key,n=step:self.offer_edit(k,-n),editable)
                self.button('+',(x+475,y-7,50,38),lambda k=key,n=step:self.offer_edit(k,n),editable)
            self.text('Employment to '+dated(self.v,details['end']),x+20,610,23)
            self.text('Review cutoff '+dated(self.v,accepted['cutoff']),x+20,647,22,MUTED)
            right=x+580;self.panel(right,360,1400-right,351,'Adviser briefing')
            y=self.wrap(o['transcript'][-1],right+20,410,1360-right,24,TEXT)
            if editable and o.get('last_proposal'):
                sent=o['last_proposal'];changes=[]
                if o['wage']!=sent[0]:changes.append('Salary '+money(sent[0])+' to '+money(o['wage']))
                if o['fee']!=sent[1]:changes.append('Fee '+money(sent[1])+' to '+money(o['fee']))
                if changes:y=self.wrap('Agent changed: '+'. '.join(changes)+'.',right+20,y+12,1360-right,22,GREEN)
            if o['status'] in ('medical','ready'):
                y=self.wrap(o.get('medical','Medical due '+dated(self.v,o['due'])+'. Employment has not changed.'),right+20,y+12,1360-right,23,GREEN)
            if not archived and o['status'] not in CLOSED:
                issue=' '.join(accepted['reasons']) or 'Cash and wage capacity are available at the latest agent terms.'
                self.wrap(issue,right+20,y+16,1360-right,22,RED if accepted['reasons'] else MUTED)
        if archived or o['status'] in CLOSED:
            self.text('Closed discussion. Its recorded terms cannot be edited or submitted again.',x,789,23,MUTED)
        elif editable:
            self.button('Send proposal',(x,779,190,44),lambda:self.offer_action('propose_offer',o),not self.v['match'])
            self.button('Review conditional acceptance',(x+210,779,335,44),lambda:self.confirm('Reserve capacity for '+p['name'],f"Latest agent terms: {money(o['fee'])} personal fee + {money(accepted['upfront'])} club fee now, {money(accepted['deferred'])} deferred; {money(o['wage'])} per week to {dated(self.v,o['end'])}. Cash after completion {money(accepted['cash_after'])}; remaining weekly headroom {money(accepted['headroom'])}. Unsent draft edits are excluded. A medical and final review follow; nothing is paid now. Medical due {dated(self.v,accepted['due'])}. Registration must complete within the offer deadline and registration window. {clause_description(o)} Future bonuses and the unused option are additional to the displayed package.",lambda:self.offer_action('accept_offer',o)),o['status'] in ('counter','agreed') and not accepted['reasons'])
        elif o['status']=='ready':
            self.button('Review completion',(x,779,230,44),lambda:self.confirm('Complete '+p['name']+' contract',f"Pay {money(o['fee']+accepted['upfront'])} now plus {money(accepted['deferred'])} in dated transfer obligations, and {money(o['wage'])} per week until {dated(self.v,o['end'])}. Total exposure approximately {money(accepted['total'])}; cash after completion {money(accepted['cash_after'])}; weekly headroom {money(accepted['headroom'])}. {clause_description(o)} Future bonuses and the unused option are additional. {o['medical']} Completion changes employment and registration together and cannot be undone.",lambda:self.offer_action('complete_offer',o)),not accepted['reasons'])
        elif o['status']=='medical':self.text('Continue to the medical date, then review completion.',x,789,23,GREEN)
        if not archived and o['status'] not in CLOSED:
            self.button('Withdraw',(1225,779,175,44),lambda:self.confirm('Withdraw this discussion?','No contract will be signed. Reserved cash and wage capacity will be released. The transcript will be retained.',lambda:self.offer_action('withdraw_offer',o)),not self.v['match'])

    def staff_screen(self,x):
        v=self.v;m=v['manager'];cost=v['severance']
        if m:
            self.panel(x,195,1400-x,182,'Manager office');portrait(self.canvas,m['id'],40,(x+20,242,74,108))
            self.text(m['name'],x+115,250,34);self.text(m['style']+' / '+money(m['wage'])+' per week',x+115,296,24,GREEN)
            self.text('Contract to '+dated(v,m['contract_end'])+' / Notice exposure '+money(cost),x+115,340,22,MUTED)
            self.button('Renew contract',(1190,248,190,42),lambda:self.confirm('Renew manager contract','Keep the current salary, autonomy and notice terms through the next season. This extends guaranteed employment; no signing fee is charged.',lambda:self.command('manager_renew')))
            self.text('Relationship '+str(v['trust'])+'/100',1190,313,22,MUTED)
        else:self.wrap('Appoint a manager to run selection, training and tactics. Candidates below have fixed quoted salary demands in this build.',x,205,1050,27,TEXT)
        for i,candidate in enumerate(MANAGERS):
            y=401+i*122;self.panel(x,y,1400-x,108)
            portrait(self.canvas,candidate['id'],40,(x+20,y+20,48,65))
            self.text(candidate['name'],x+90,y+18,28);self.text(candidate['style']+' approach',x+90,y+59,22,MUTED)
            self.text(money(candidate['wage'])+'/week',x+400,y+24,24,GREEN)
            self.text('Fee '+money(candidate['fee']),x+400,y+62,22,MUTED)
            current=m and m['id']==candidate['id']
            def review(c=candidate):
                if not m:
                    self.confirm('Appoint '+c['name'],f"Pay {money(c['fee'])} now and {money(c['wage'])} per week. The initial appointment covers three compact league seasons. Notice is capped at four weeks’ salary or remaining guaranteed salary, whichever is less. Selection and tactics remain delegated.",lambda:self.command('hire',id=c['id']))
                else:
                    self.confirm('Replace '+m['name']+' with '+c['name'],f"Immediate notice payment {money(cost)} plus signing fee {money(c['fee'])}. New weekly salary {money(c['wage'])} through next season. Existing player contracts and accrued payroll remain. The working relationship with the new manager starts afresh.",lambda:self.command('manager_replace',id=c['id'],duration=2))
            self.button('Appointed' if current else 'Review '+candidate['name'],(1110,y+34,270,44),review,not current and not v['match'])
        self.text('Candidate styles are public. Staff interviews and wider department recruitment remain in development.',x,797,21,MUTED)

    def draw_career(self,x):
        v=self.v;self.panel(x,195,1400-x,190,'Career journal')
        self.text('Northbridge Athletic / Season '+str(v['season']),x+20,245,36,GREEN)
        self.text('Current campaign ends '+dated(v,v['season_end']),x+20,293,24)
        self.wrap('A compact eight-club development league with fourteen matches per season. Preseason lasts two weeks; wages, medicals and construction continue day by day.',x+20,333,1080,21)
        self.button('Prepare next season',(x,408,240,44),lambda:self.confirm('Prepare the next campaign', 'Archive this season’s table and match reports, reset seasonal statistics and generate the next fixtures. Days will not skip: preseason wages and contract expiries process through Continue. Unfinished offers expire. Review renewals first; expired players become free agents.',lambda:self.command('next_season')),v['season_done'] and not v['match'])
        self.button('Review squad contracts',(x+260,408,280,44),lambda:self.nav('Squad'))
        self.text('SEASON HISTORY',x,486,21,MUTED)
        history=list(reversed(v['career']['history']))
        for i,h in enumerate(history[self.page*4:self.page*4+4]):
            y=525+i*55;own=next(c for c in h['table'] if c['id']=='c0');position=next(j+1 for j,c in enumerate(h['table']) if c['id']=='c0')
            self.text(f"Season {h['season']} / {position} of 8 / {own['points']} pts / {own['gf']} goals / cash {money(h['cash'])}",x+15,y,24)
            self.button('Season report',(1190,y-9,205,38),lambda season=h['season']:self.open_season_history(season))
        if not history:self.text('Completed campaigns appear here when the next season is prepared.',x+15,543,25,MUTED)
        self.pager(x,780,len(history),4)

    def open_season_history(self,season):
        self.nav('History');self.history_season=season;self.page=0

    def draw_history(self,x):
        h=next((h for h in self.v['career']['history'] if h['season']==self.history_season),None)
        if not h:self.wrap('Choose a completed season in Career.',x,220,1000,28);return
        self.text('ARCHIVE / SEASON '+str(h['season']),x,204,25,GREEN)
        for i,c in enumerate(h['table']):
            self.text(f"{i+1}  {c['name']}",x+20,254+i*36,24)
            self.text(f"{c['points']} pts   {c['won']}W  {c['drawn']}D  {c['lost']}L",1050,254+i*36,23,MUTED)
        fixtures=[f for f in h['fixtures'] if 'c0' in (f['home'],f['away'])]
        self.page=min(self.page,len(fixtures)-1);f=fixtures[self.page]
        self.panel(x,575,1400-x,152)
        self.text(self.fixture_date(f),x+20,598,23,MUTED)
        self.text(f"{self.club(f['home'])}   {f['result']['score'][0]}–{f['result']['score'][1]}   {self.club(f['away'])}",x+20,638,30)
        self.button('Archived match',(x+20,678,220,36),lambda:self.open_report(f['id']))
        self.pager(x,780,len(fixtures),1)

    def draw_academy(self,x):
        v=self.v;owned=[p for p in v['players'] if p['youth'] and p['club']=='c0' and not p['retired']]
        candidates=[p for p in v['players'] if p['youth'] and p['club'] is None and not p['retired']]
        self.text(f"ACADEMY / Level {v['career']['facilities']['academy']} / {len(owned)} enrolled",x,202,26,GREEN)
        self.button('Arrange annual trials',(1120,190,280,44),lambda:self.confirm('Commission academy trials',f"Pay {money(v['career_settings']['academy_trial_fee'])} for this year’s six regional candidates. Reports are uncertain. Each admission needs a separate review. Candidates are available until this compact season ends; trials cannot be rerolled.",lambda:self.command('academy_intake')),v['day']//365 not in v['career']['intakes'] and not v['match'])
        self.wrap('Coaches review young players every 28 days. Better training improves opportunities; it cannot guarantee development. Promotion is available from age 16.',x,254,1100,23)
        rows=owned+candidates
        for i,p in enumerate(rows[self.page*5:self.page*5+5]):
            y=331+i*85;self.panel(x,y,1400-x,74);portrait(self.canvas,p['id'],p['age'],(x+10,y+7,49,59))
            self.text(p['name']+f" / {p['role']} / {p['age']}",x+78,y+13,25)
            r=p['report'];key={'GK':'goalkeeping','DEF':'tackling','MID':'passing','FWD':'finishing'}[p['role']]
            interval=r['ranges'][key] if r else None
            self.text((key.capitalize()+f' {interval[0]}–{interval[1]}' if interval else 'Unknown ability')+' / '+('Enrolled' if p['club'] else 'Trial candidate'),x+78,y+45,21,MUTED)
            if p['club'] is None:
                span=v['season_end']-v['season_start']+v['career_settings']['season_gap'];end=v['season_end']+span*(3 if v['season_done'] else 2)
                self.button('Review admission',(1165,y+17,220,42),lambda p=p,end=end:self.confirm('Admit '+p['name'],f"Admission fee {money(v['career_settings']['academy_admission_fee'])}. Academy wage {money(p['wage'])} per week until {dated(v,end)}, included in the club wage budget. Future wages approximately {money(p['wage']*max(0,end-v['day'])//7)}. Future ability is uncertain.",lambda:self.command('academy_admit',id=p['id'])))
            else:self.button('Promote to seniors',(1165,y+17,220,42),lambda p=p:self.confirm('Promote '+p['name'],'Move this player into the senior squad on existing financial terms. Selection and minutes remain the manager’s decision.',lambda:self.command('academy_promote',id=p['id'])),p['age']>=16 and not v['match'])
        if not rows:self.wrap('Your academy has no enrolled prospects yet. Arrange trials, review the evidence and choose whom to admit.',x+20,370,1020,29,TEXT)
        self.pager(x,790,len(rows),5)

    def draw_facilities(self,x):
        v=self.v;projects=v['career']['projects'];tick=pygame.time.get_ticks()
        self.panel(x,190,575,275,venue_name(v))
        closed=any(p['status']=='construction' and p['closure'] for p in projects)
        pitch(self.canvas,(x+20,239,535,200),closed,tick,self.reduced_motion)
        inspect=lambda:self.confirm('East stand and venue capacity',f"Usable seats: {v['terms']['capacity']:,}. Physical capacity: {v['terms']['physical_capacity']:,}. Construction closes 800 seats until the agreed opening milestone; completed expansion adds 800 seats. Attendance is demand-limited, so extra capacity is not guaranteed revenue.",None)
        region=pygame.Rect(x+525,266,22,146);idx=len(self.buttons)
        self.buttons.append((region,inspect,True));self.help_regions.append((region,'Inspect the east stand and current capacity restrictions.',idx))
        if self.focus==idx:pygame.draw.rect(self.canvas,GREEN,region,2)
        self.text(f"Usable capacity {v['terms']['capacity']:,} / physical capacity {v['terms']['physical_capacity']:,}",x+595,211,23,GREEN)
        self.wrap('Amber seats show the east-stand closure during construction. More seats do not guarantee more supporters. Training and academy projects affect development opportunities and intake capacity.',x+595,260,550,24)
        self.text('Weekly operations '+money(v['terms']['weekly_overheads']),x+595,395,25)
        self.button('Inspect east stand',(x+595,429,255,36),inspect)
        for i,(kind,spec) in enumerate(v['project_specs'].items()):
            y=490+i*105;self.panel(x,y,1400-x,94)
            level=v['career']['facilities'][kind];active=next((p for p in reversed(projects) if p['kind']==kind and p['status'] not in ('cancelled','operational')),None)
            self.text(spec['name']+f' / level {level}',x+20,y+15,27)
            status=active['status'] if active else 'No active project'
            detail=(status.upper()+' / '+dated(v,active['due'])) if active else f"Estimate {money(spec['cost']*level)} / {spec['days']} days / +{money(spec['upkeep'])} weekly"
            self.text(detail,x+20,y+54,21,MUTED)
            if active and active['status'] in ('feasibility','quoted'):
                self.button('Cancel proposal',(945,y+25,172,42),lambda p=active:self.confirm('Cancel this proposal?','The £500 feasibility fee remains spent. No construction payment will be made.',lambda:self.command('project_cancel',id=p['id'])))
            if active and active['status']=='construction':
                fraction=min(1,(v['day']-active['started'])/active['days']);pygame.draw.rect(self.canvas,(39,63,62),(1100,y+42,260,13),border_radius=5);pygame.draw.rect(self.canvas,GREEN,(1100,y+42,max(1,260*fraction),13),border_radius=5)
                self.text(str(round(fraction*100))+'% complete',1100,y+65,19,MUTED)
            elif active and active['status']=='quoted':
                self.button('Review project',(1170,y+25,215,42),lambda p=active:self.confirm(p['name'],f"Fixed construction price {money(p['cost'])}, fully paid now. Duration {p['days']} days. Temporary closure: {p['closure']} seats. On opening: +{p['capacity']} seats and +{money(p['upkeep'])} weekly operating costs. Construction is binding; the feasibility fee is already spent.",lambda:self.command('project_approve',id=p['id'])))
            else:self.button('Commission proposal' if not active else 'Study in progress',(1130,y+25,255,42),lambda k=kind:self.confirm('Commission facility proposal','Pay £500 for a three-day feasibility study. This does not commit the construction cost. A proposal can be cancelled before approval.',lambda:self.command('project_plan',kind=k)),not active and level<5)
        self.text('Proposals can be cancelled before construction. Operational costs and capacity feed the cash forecast.',x,820,20,MUTED)

    def draw_settings(self,x):
        self.panel(x,195,1400-x,410,'Presentation settings / applies immediately')
        self.button('Reduced motion: '+('On' if self.reduced_motion else 'Off'),(x+25,255,330,46),lambda:self.setting('reduced_motion',not self.reduced_motion))
        self.wrap('Disables decorative goal emphasis and construction movement. Match outcomes and simulation speed stay unchanged.',x+385,263,720,24)
        self.button('Interface sounds: '+('On' if self.sound.volume>0 else 'Off'),(x+25,340,330,46),lambda:self.toggle_audio())
        self.wrap('Original short click and goal cues. Every sound has a visible equivalent. Audio is optional; a missing device never blocks play.',x+385,348,720,24)
        self.button('Tooltips: '+('On' if self.tooltips_enabled else 'Off'),(x+25,425,330,46),lambda:self.setting('tooltips_enabled',not self.tooltips_enabled))
        self.wrap('Hover over a control for an explanation. Keyboard: focus the control with Tab and press F2. Escape closes the explanation.',x+385,433,720,24)
        self.text('Your preferences are separate from career saves.',x+25,540,24,MUTED)
        self.panel(x,630,1400-x,155,'Shortcuts')
        self.wrap('Ctrl+S: save / Ctrl+F: player search / Alt+Left or Right: history / Space: pause live match / F1: handbook / F2: focused explanation / Tab and Shift+Tab: navigate controls. Every essential action also has a visible control.',x+25,680,1080,23,TEXT)

    def setting(self,key,value):setattr(self,key,value);self.save_preferences()
    def toggle_audio(self):
        self.sound.volume=0 if self.sound.volume>0 else .22;self.save_preferences()

    def control_help(self,label,enabled):
        hints={
            'Clauses':'Inspect signed performance bonuses, extension options, sell-on rights and any unpaid earned bonuses. New terms are sent with the contract proposal.',
            'Review extension':'Use a signed club option once, before employment expires. Review the additional guaranteed wages; existing bonuses continue.',
            'Term -14 days':'Change the requested loan length. New loan terms run from final registration, after the medical, and must fit inside employment.',
            'Term +14 days':'Change the requested loan length up to 84 days. Employment dates are checked again before final registration.',
            'Transfers':'Review club consent, sales, loans, return dates and dated transfer payments. Nothing changes registration without final completion.',
            'Commercial':'Negotiate exclusive sponsorship rights. Signed income is paid weekly on its own schedule and included in cash forecasts.',
            'Club enquiry':'Ask the current club for a transfer quote. A club agreement is separate from personal terms and medical consent.',
            'Discuss loan':'Open a temporary-registration quote. Existing employment survives; wages return to the employer when the loan ends.',
            'Review sale':'Choose a receiving club and review its offer. Fees, consent and squad cover are checked before final registration.',
            'Review loan':'Arrange a temporary move to another club. A loan cannot outlast the parent employment agreement.',
            'Personal terms':'Continue an agreed club transfer through Contracts. Both agreements must remain valid until completion.',
            'Send club offer':'Submit the draft club fee and payment schedule. A counteroffer remains separate from your unsent edits.',
            'Review club consent':'Agree the latest selling-club terms. No fee is paid or reserved until conditional personal acceptance.',
            'Review conditional deal':'Reserve receiving-club capacity while medical and player-consent checks finish. Registration remains unchanged.',
            'Review registration':'Complete the reviewed sale or loan. Club payments and registration update in one transaction.',
            'Payments':'Inspect guaranteed dated transfer fees. They remain due after a season change or subsequent player sale.',
            'Loans':'Inspect borrower, parent club, wage contribution and return dates. Recall requires an open registration window.',
            'Send sponsor proposal':'Submit proposed income and duration. Signing uses the latest sponsor response, not unsent draft edits.',
            'Review sponsor agreement':'Review exclusive rights, total payments and supporter consequences before a binding agreement.',

            'Continue  >':'Advance one committed day. Pending chairman decisions, staffing gaps and match reviews must be resolved first. Browsing never advances time.',
            'Next fixture':'Advance toward the next match, stopping at mandatory decisions. Use Stop or Escape to cancel between committed days.',
            'Save':'Write a manual career save. Ctrl+S also saves. Autosaves follow committed management actions; saves include match RNG and accepted obligations.',
            'Recruitment':'Find senior free agents using public terms and uncertain scouting. Pin candidates to compare their combined cost before starting negotiations.',
            'Contracts':'Manage proposals, counteroffers, medicals and registration. Conditional acceptance reserves cash and payroll; only final completion signs employment.',
            'Academy':'Arrange one trial cohort per 365 world days. Places carry fees and wages. Promotion from age 16 preserves identity and existing terms.',
            'Facilities':'Commission a proposal, review its fixed price and approve construction. Temporary closures reduce usable stadium capacity; upkeep begins when facilities open.',
            'Career':'Prepare further seasons and revisit historical tables and matches. Preseason progresses normally: it does not skip wages or contract expiry.',
            'Finances':'Cash is the bank balance. Wage budget is permission to spend, not money. Forecasts combine scheduled costs with labelled estimates for gate income.',
            'Staff':'Managers control selection and tactics. Replacement pays the current manager’s contractual notice plus the incoming manager’s signing fee.',
            'Inbox':'Unread news is separate from unresolved approvals. Marking messages read never authorises a payment or clears a required decision.',
            'Squad':'Review senior players, scouting estimates, records and contracts. Renew before the expiry date; opening discussions alone does not extend employment.',
            'League':'Current standings and fixtures. Select a completed fixture to reopen its stored report without replaying the simulation.',
            'Matchday':'Watch the current match or an archived report. The owner may contact the bench, but team selection and tactical decisions belong to the manager.',
            'Settings':'Presentation preferences apply immediately and remain separate from career saves. Reduced motion removes decorative animation.',
            'Overview':'A live summary of club cash, wages, required decisions, next fixture, form and estimated cash outlook.',
            'Forecast':'Project cash under current obligations. Ticket income holds today’s supporter mood and price; the shaded band varies attendance by 15%, not probability.',
            'Plan':'Preview pinned free-agent signings together. A plan spends nothing and signs nobody. Existing reserved offers still consume cash and wage capacity.',
            'Ledger':'Every committed cash movement, with the resulting bank balance. Contract reservations do not move cash and are shown separately in Contracts.',
            'Request scouting':'Commission an uncertain assessment at the fee and delivery time shown in the review. Existing reports and pending assignments cannot be duplicated.',
            'Negotiate contract':'Open a free-agent discussion. Edit a draft, submit terms, review the agent’s response and conditionally accept before the medical and final completion.',
            'Negotiate renewal':'Extend an existing player’s contract by agreement. A pending discussion does not prevent expiry. Renewal medical review is immediate for existing employment.',
            'Cash review':'Compare the current draft with existing obligations. Other offers retain their reservations; this offer is never counted twice. Estimates assume completion today.',
            'Conversation':'Read the complete discussion with pagination. Reopening a closed negotiation preserves the earlier transcript in History.',
            'History':'Read previous closed discussions. Their original terms and outcomes remain unchanged.',
            'Review contract':'Review an urgent contract or completed medical before advancing time.',
            'Send proposal':'Send the displayed draft to the agent. Repeated identical proposals are blocked. Three unsuccessful rounds end the discussion with a cooling-off period.',
            'Review conditional acceptance':'Review the latest agent terms, not unsent edits. Acceptance reserves the signing fee and additional payroll capacity; no employment changes yet.',
            'Review completion':'Final irreversible review of agreed terms, medical advice and registration. Cash, employment and registration commit together.',
            'Renew contract':'Extend the current manager’s agreement on the same salary and notice terms. The review explains the additional guaranteed commitment.',
            'Prepare next season':'Archive the current table and results and create the next calendar once. Existing obligations persist; unresolved negotiations lapse.',
            'Undo':'Reverse the last local shortlist or pin change. This is unavailable after another committed command and never reverses contracts, payments or matches.',
            'Key events':'Filter commentary to goals, period markers and bench messages. This only changes the display; it does not change the match simulation.',
            'Lineups':'Show the players selected by each manager for this match. Names and roles are public; hidden abilities are not disclosed.',
            'Cancel':'Close this review without executing the proposed action. Focus returns to the control that opened it.',
            'Confirm':'Execute only the action described in this review. The game revalidates state, available funds and authority; stale reviews must be reopened.',
            '+':'Increase the proposed term. This only edits the draft; Send proposal starts negotiation.',
            '−':'Decrease the proposed term. This only edits the draft; Send proposal starts negotiation.',
        }
        plain=label.removeprefix('• ')
        if plain.startswith('Club option:'):return 'Add or remove a one-season club option from this draft. Send the proposal for consent. An exercised option extends wages and bonuses once.'
        if plain.startswith('Type:') or plain in ('−5%','+5%'):return 'Choose one sell-on basis: gross fee or profit above the total acquisition fee. A retained right reduces an outgoing buyer’s cash bid. Purchases use these terms only after Send club offer.'
        if not enabled and plain in ('Review completion','Review conditional acceptance') and self.v and self.offer_id:
            offer=self.v['career']['offers'].get(self.offer_id)
            if offer:return ' '.join(review(self.v,offer)['reasons']) or 'Submit terms and receive an agent response before accepting.'
        if plain.startswith('Sort:'):return 'Sort by the selected public field. Attribute sorting uses the midpoint of the observed range; unknown assessments always appear last. True hidden ratings are never used.'
        if plain.startswith('Role:'):return 'Cycle All, GK, DEF, MID and FWD. The resulting list remains intact when opening and closing player profiles.'
        if plain.startswith('Budget'):return 'Change the authorised weekly payroll ceiling. It cannot fall below existing wages and reserved contract commitments. This does not create or spend cash.'
        if plain.startswith('Review ') and plain not in hints:return 'Open the full terms and immediate costs before committing. Nothing is agreed merely by viewing this review.'
        if plain in ('+ List','Saved','Add to shortlist','Remove shortlist'):return 'Toggle shortlist membership. This planning record is saved with the career and can be undone until another command commits.'
        if plain in ('+ Pin','Pinned','Unpin','Pin comparison') or plain.startswith('Compare'):return 'Pin up to four people. Comparisons preserve scouting uncertainty and show recurring wages plus guaranteed acquisition exposure.'
        return hints.get(plain,('This control is currently unavailable. Review the nearby status and terms.' if not enabled else ''))

    def draw_tooltip(self):
        tick=pygame.time.get_ticks();target=None
        if self.explain_focus:
            target=next((h for h in self.help_regions if h[2]==self.focus),None)
            if target and not target[1]:target=(target[0],'This control performs the labelled action. Financial commitments open a review before execution.',target[2])
        elif self.tooltips_enabled:
            position=pygame.mouse.get_pos();scale=getattr(self,'scale',1);offset=getattr(self,'offset',(0,0))
            point=((position[0]-offset[0])/scale,(position[1]-offset[1])/scale)
            candidate=next((h for h in self.help_regions if h[0].collidepoint(point) and h[1]),None)
            key=(tuple(candidate[0]),candidate[1]) if candidate else None
            if key!=self.hover_key:self.hover_key=key;self.hover_since=tick
            if candidate and tick-self.hover_since>450:target=candidate
        if not target:return
        rect,message,_=target;w=435
        x=max(12,min(1440-w-12,rect.x));y=rect.bottom+10
        font=self.fonts.setdefault(22,pygame.font.Font(None,22));lines=1;line=''
        for word in message.split():
            if font.size(line+' '+word)[0]>w-32:lines+=1;line=word
            else:line+=' '+word
        h=44+lines*26
        if y+h>840:y=max(12,rect.y-h-10)
        self.panel(x,y,w,h);pygame.draw.rect(self.canvas,GREEN,(x,y,w,h),1,border_radius=7)
        self.wrap(message,x+16,y+14,w-32,22,TEXT)
        self.text('F2: pin explanation / Esc: close',x+16,y+h-23,17,MUTED)
