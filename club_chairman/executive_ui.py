"""Figma Executive layouts rendered as live Pygame controls and read models."""
import pygame
from .theme import ASSETS, BG, PANEL, RAISED, BORDER, TEXT, MUTED, FAINT, GREEN, BUTTON, SELECTED, WARNING, RED
from .contract_review import attention
from .planning import dated, forecast
from .presentation import crest


TITLES = {'Overview': "Chairman’s overview", 'Inbox': 'Decision centre', 'Squad': 'First-team squad',
          'Recruitment': 'Recruitment', 'Facilities': 'Stadium & facilities', 'League': 'Competitions',
          'CupHistory': 'Archived domestic cup', 'Cup': 'Domestic cup', 'Career': 'Club history & career', 'Comparison': 'Player comparison'}
DESCRIPTIONS = {'Overview': 'Your club, your decisions. Here’s what needs your attention.',
    'Squad': 'Contracts, registration and availability. Selection belongs to your manager.',
    'Recruitment': 'Build your shortlist with evidence, context and clear commitments.',
    'Finances': 'Inspect cash, commitments and forecasts before making your next decision.',
    'Staff': 'Appoint the people. Define their authority. Review their work.',
    'Facilities': 'Plan your club’s future and review the full cost of each project.',
    'Commercial': 'Balance commercial income with the identity of your club.',
    'Fixtures': 'Your season, results and the next match in one place.',
    'Cup': 'Follow the draw, results and trophy through the season.', 'League': 'Standings and results from your current competition.',
    'Settings': 'Presentation preferences apply immediately and are saved on this device.'}


class ExecutiveScreens:
    def icon(self, name, x, y, size=18):
        if not hasattr(self, '_icons'): self._icons = {}
        key = (name, size)
        if key not in self._icons:
            source = pygame.image.load(str(ASSETS / 'figma' / (name + '.png'))).convert_alpha()
            self._icons[key] = pygame.transform.smoothscale(source, (size, size))
        self.canvas.blit(self._icons[key], (x, y))

    def clipped_text(self, value, x, y, width, size=22, color=TEXT):
        value = str(value); font = self.get_font(size)
        if font.size(value)[0] > width:
            while value and font.size(value + '…')[0] > width: value = value[:-1]
            value += '…'
        self.text(value, x, y, size, color)

    def section(self, x, y, w, h, title, link=None, callback=None):
        self.panel(x, y, w, h)
        self.text(title, x+20, y+18, 23)
        pygame.draw.line(self.canvas, BORDER, (x+20, y+52), (x+w-20, y+52))
        if link: self.button(link, (x+w-170, y+9, 154, 34), callback)

    def unresolved_count(self):
        return int(bool(self.v['decision'])) + len(attention(self.v)) + sum(c['status']=='pending' for c in self.v['delegation']['cases'])

    def executive_chrome(self):
        v=self.v; sw=78 if self.collapsed else 220
        pygame.draw.rect(self.canvas, PANEL, (0,0,sw,900))
        pygame.draw.line(self.canvas, BORDER, (sw,0), (sw,900))
        crest(self.canvas, 'c0', ((sw-34)//2,17,34,44))
        if not self.collapsed:
            self.heading('CLUB CHAIRMAN',24,70,25)
            self.text('NORTHBRIDGE ATHLETIC',39,104,14,MUTED)
        self.button('>' if self.collapsed else '< Collapse', (14,123,sw-28,29), self.toggle_sidebar)
        groups=[('YOUR CLUB',[('Overview','overview'),('Inbox','inbox'),('Squad','people'),('Recruitment','search'),('Staff','people'),('Academy','academy')]),
            ('OPERATIONS',[('Finances','finance'),('Commercial','commercial'),('Facilities','stadium'),('Contracts','people'),('Transfers','search'),('Responsibilities','settings')]),
            ('WORLD & SEASON',[('League','world'),('Fixtures','calendar'),('Matchday','stadium'),('Career','clock')])]
        y=159
        for title, entries in groups:
            if not self.collapsed:self.text(title,21,y,13,FAINT)
            y+=20
            for name, icon in entries:
                callback=(lambda:self.open_responsibilities()) if name=='Responsibilities' else (lambda n=name:self.nav(n))
                active=(self.screen==name and not (name=='Staff' and self.staff_tab=='Responsibilities')) or (name=='Responsibilities' and self.screen=='Staff' and self.staff_tab=='Responsibilities')
                if self.screen=='Comparison' and name=='Recruitment':active=True
                if self.screen in ('Cup','CupHistory') and name=='League':active=True
                self._nav_style=(icon,active)
                self.button(name,(14,y,sw-28,29),callback)
                self._nav_style=None
                if name=='Inbox' and not self.collapsed:
                    unread=max(0,len(v['inbox'])-v['planning']['inbox_read'])
                    if unread:self.right_text(str(unread),sw-26,y+7,17,WARNING)
                y+=31
            y+=5
        pygame.draw.line(self.canvas,BORDER,(20,758),(sw-20,758))
        for label,top,icon in [('Settings',767,'settings'),('Help',802,'inbox')]:
            self._nav_style=(icon,self.screen==label);self.button(label,(14,top,sw-28,29),lambda n=label:self.nav(n));self._nav_style=None
        self._nav_style=('overview',False);self.button('Main menu',(14,843,sw-28,33),lambda:self.nav('Home'));self._nav_style=None
        crest(self.canvas,'c0',(sw+22,17,30,42))
        self.text(self.club('c0'),sw+65,18,23)
        self.text('Club ownership  /  Season '+str(v['season']),sw+65,46,16,FAINT)
        self.button('Search',(550,18,235,42),self.open_search)
        self.text(v['date'],805,17,20,MUTED)
        count=self.unresolved_count()
        status=f'{count} unresolved decisions' if count else 'Manager appointment required' if not v['manager'] else 'Match in progress' if v['match'] else 'Season review ready' if v['season_done'] else 'Ready for the next day'
        self.text(status,805,44,15,WARNING if count or not v['manager'] else MUTED)
        self.button('Save',(993,18,77,42),self.manual_save)
        self.button('Next fixture',(1080,18,145,42),self.next_fixture,not v['season_done'] and v['match'] is None)
        self.button('Continue  >',(1235,18,165,42),self.continue_day,not v['season_done'] and v['match'] is None)
        pygame.draw.line(self.canvas,BORDER,(sw,78),(1440,78))
        if self.batch:
            self.text('Advancing days…',sw+25,845,21,GREEN)
            self.button('Stop',(1250,842,150,35),lambda:setattr(self,'batch',False))

    def open_responsibilities(self):
        self.nav('Staff')
        if self.staff_tab!='Responsibilities':self.staff_section('Responsibilities')

    def executive_home(self):
        if self.screen=='Settings':
            self.heading('Settings',245,104,40)
            self.draw_settings(245)
            self.button('Back',(1220,100,180,42),lambda:self.nav('Home'))
            return
        if self.screen=='Load':
            self.heading('Your saved careers',100,90,46)
            self.text('Load a checkpoint into a separate recovery timeline. Original saves are preserved.',104,155,22,MUTED)
            if self.load_cache is None:self.load_cache=self.store.entries()
            entries=self.load_cache
            self.panel(104,225,1232,490)
            for i,e in enumerate(entries[self.page*6:self.page*6+6]):
                self.button(e['label'],(124,245+i*72,1192,60),lambda p=e['path']:self.load_entry(p),e['valid'])
            if not entries:self.text('No saved careers yet. Start a new career to create your first checkpoint.',128,275,25,MUTED)
            self.pager(104,755,len(entries),6)
            self.button('Back',(1175,755,160,42),lambda:self.nav('Home'))
            return
        crest(self.canvas,'c0',(105,99,74,95))
        self.text('CLUB',104,253,39,MUTED)
        self.heading('CHAIRMAN',99,302,80)
        self.text('Build a club. Shape its future.',104,401,28,MUTED)
        if self.load_cache is None:self.load_cache=self.store.entries()
        latest=next((entry for entry in self.load_cache if entry['valid']),None)
        callback=(lambda:self.nav('Matchday' if self.v['match'] else 'Overview')) if self.state else (lambda:self.load_entry(latest['path'])) if latest else (lambda:None)
        self.button('Resume career' if self.state else 'Continue career',(104,489,359,53),callback,bool(self.state or latest))
        self.clipped_text(self.club('c0')+'  /  '+self.v['date'] if self.state else latest['label'] if latest else 'No saved career yet. Begin your first story.',104,552,359,18,MUTED)
        from . import nations
        choices=[dict(id='compact',name='Compact',division_sizes=[8,8],start_month=8,end_month=11)]+[n for n in nations.catalogue()['nations'] if n['playable']]
        chosen=next(n for n in choices if n['id']==self.new_scenario)
        self.button('New career',(104,602,359,48),lambda:self.confirm('Start a new career?',f"Begin with Northbridge Athletic in the {chosen['name']} scenario: {len(chosen['division_sizes'])} divisions and {sum(chosen['division_sizes'])} clubs. A fresh seed creates the squads. National scenarios simulate one country; other nations, feeder pools and continental cups are not active yet. Existing saved careers are kept.",lambda id=chosen['id']:self.start(id)))
        self.panel(914,225,422,302)
        self.text('CAREER SCENARIO',938,250,16,GREEN)
        index=choices.index(chosen)
        self.button('Scenario: '+chosen['name'],(938,286,374,46),lambda:setattr(self,'new_scenario',choices[(index+1)%len(choices)]['id']))
        desc=f"{len(chosen['division_sizes'])} divisions / {sum(chosen['division_sizes'])} clubs\n{2*(chosen['division_sizes'][0]-1)} league matches per club\n"+('Compact calendar' if chosen['id']=='compact' else 'August–May' if chosen['start_month']==8 else 'February–November')
        self.wrap(desc,938,350,370,23,MUTED)
        self.wrap('One playable national system. Development club content; wider world still to come.' if chosen['id']!='compact' else 'Short seasons in the familiar Northshire development world.',938,443,370,20,MUTED)
        self.button('Load / recover career',(104,664,359,48),lambda:self.nav('Load'))
        self.button('Settings',(104,728,166,43),lambda:self.nav('Settings'))
        self.button('Quit',(285,728,178,43),self.quit_request)
        self.panel(914,560,422,214)
        self.text('THE OWNERSHIP GAME',938,587,16,GREEN)
        self.wrap('Appoint the people.\nMake the big decisions.\nLeave a lasting club.',938,627,370,29,TEXT)
        self.text('NATIONAL CALENDARS 0.12',104,820,16,FAINT)
        self.text('Single-country scenarios / Development build',914,820,16,FAINT)

    def executive_overview(self,x):
        from .ui import money
        v=self.v;own=next(c for c in v['clubs'] if c['id']=='c0')
        pos=next(i+1 for i,c in enumerate(v['table']) if c['id']=='c0')
        mood='Positive' if v['supporters']>=60 else 'Concerned' if v['supporters']<40 else 'Steady'
        w=(1400-x-45)//4
        metrics=[('AVAILABLE CASH',money(v['cash']),'Operating reserve '+money(v['terms']['operating_buffer'])),
            ('WAGE BUDGET',f"{v['payroll']/v['budget']:.0%}" if v['budget'] else 'No budget',money(v['payroll'])+' / '+money(v['budget'])+' per week'),
            ('LEAGUE POSITION',f"{pos} / {len(v['table'])}",f"{own['points']} points · {own['played']} played"),
            ('SUPPORTER MOOD',mood,f"Support {v['supporters']} / 100 · Morale {v['morale']}")]
        for i,(label,value,detail) in enumerate(metrics):
            left=x+i*(w+15);self.panel(left,200,w,113)
            self.text(label,left+17,215,16,MUTED);self.text(value,left+17,240,38,GREEN if i==3 else TEXT)
            self.clipped_text(detail,left+17,288,w-34,17,MUTED)
        width=round((1400-x-20)*.60);right=x+width+20;rw=1400-right
        self.section(x,334,width,266,'Key decisions','View inbox',lambda:self.nav('Inbox'))
        rows=[]
        if v['decision']:
            d=v['decision'];rows.append((d['title'],money(d['cost'])+' one-off commitment · approval required','Review decision',self.review_owner_decision,'inbox'))
        elif not v['manager']:rows.append(('Appoint your manager','Your manager controls selection and tactics.','Review candidates',lambda:self.nav('Staff'),'people'))
        elif v['season_done']:rows.append(('Season complete',f'Finished {pos} of {len(v["table"])}. Review before the next season.','Continue your career',lambda:self.nav('Career'),'world'))
        for item in attention(v)[:2]:rows.append((item['name'],item['label']+' · due '+dated(v,item['deadline']),'Review contract',lambda item=item:self.business_attention(item),'people'))
        cases=[c for c in v['delegation']['cases'] if c['status']=='pending']
        if cases:rows.append(('Delegated approvals',str(len(cases))+' cases need your decision.','Review approvals',lambda:(self.nav('Staff'),self.staff_section('Approvals')),'settings'))
        if len(rows)<3:rows.append(('Recruitment planning',str(len(v['planning']['shortlist']))+' shortlisted · '+str(len(v['planning']['comparison']))+' pinned for comparison','Review recruitment',lambda:self.nav('Recruitment'),'search'))
        for i,(title,detail,label,callback,icon) in enumerate(rows[:3]):
            y=397+i*63;pygame.draw.rect(self.canvas,RAISED,(x+16,y,width-32,56),border_radius=5)
            self.icon(icon,x+28,y+18,21)
            self.clipped_text(title,x+62,y+7,width-288,23)
            self.clipped_text(detail,x+62,y+32,width-288,17,MUTED)
            self.button(label,(x+width-215,y+8,195,40),callback)
        self.section(right,334,rw,266,'Next fixture','Fixtures',lambda:self.nav('Fixtures'))
        f=next((f for f in v['fixtures'] if 'c0' in (f['home'],f['away']) and f['result'] is None),None)
        if f:
            centers=(right+rw*.26,right+rw*.74)
            for cid,cx in zip((f['home'],f['away']),centers):
                crest(self.canvas,cid,(cx-24,410,48,64))
                self.clipped_text(self.club(cid),cx-rw*.23,489,rw*.46,20)
            self.text('vs',right+rw//2-8,433,21,MUTED)
            self.text(self.fixture_date(f)+'  /  '+('Home' if f['home']=='c0' else 'Away'),right+24,523,19,MUTED)
        else:self.text('All fixtures complete',right+24,429,27,GREEN)
        for i,result in enumerate(own['form'][-5:]):
            left=right+24+i*36;pygame.draw.rect(self.canvas,SELECTED if result=='W' else RAISED,(left,557,27,25),border_radius=4)
            self.text(result,left+8,562,16,GREEN if result=='W' else TEXT)
        if not own['form']:self.text('No matches played yet',right+24,560,17,FAINT)
        self.section(x,620,width,217,'Club outlook','View finances',lambda:self.nav('Finances'))
        projection=forecast(v)
        self.text(money(projection['cash']),x+22,680,30,TEXT)
        self.text('Estimated cash in 28 days',x+208,689,17,MUTED)
        self.cash_chart(projection,projection,x+25,724,width-52, 60)
        self.text('Today',x+25,798,15,MUTED)
        self.right_text(dated(v,projection['end']),x+width-24,798,15,MUTED)
        self.text('Band: attendance ±15% · Dashed: operating reserve',x+25,819,14,FAINT)
        self.section(right,620,rw,217,'Projects','Open stadium',lambda:self.nav('Facilities'))
        projects=[p for p in v['career']['projects'] if p['status'] not in ('cancelled','operational')]
        if projects:
            p=projects[-1];self.text(p['kind'].title()+' development',right+22,688,25)
            self.text(p['status'].replace('_',' ').title(),right+22,725,21,GREEN)
            self.wrap('Open the project to review its cost, schedule and ongoing commitments.',right+22,764,rw-44,20)
        else:
            self.text('Plan your next investment',right+22,688,24)
            self.wrap('Review stadium, training and academy proposals before committing club funds.',right+22,724,rw-44,21)
            self.button('Open academy',(right+22,785,180,35),lambda:self.nav('Academy'))

    def review_owner_decision(self):
        from .ui import money
        d=self.v['decision']
        if d:self.confirm(d['title'],f"{self.club('c0')}: pay {money(d['cost'])} now? This is a one-off commitment. Club cash after payment: {money(self.v['cash']-d['cost'])}. Cancel keeps this decision open; Decline is available in the decision centre.",lambda:self.command('decision',choice='approve'))

    def executive_inbox(self,x):
        from .ui import money
        v=self.v;read=v['planning']['inbox_read'];rows=list(reversed(list(enumerate(v['inbox']))))
        self.text(f'{self.unresolved_count()} unresolved decisions · {max(0,len(rows)-read)} unread updates',x,200,23,MUTED)
        self.button('Mark all read',(1220,190,180,40),lambda:self.command('planning',key='inbox_read',value=len(v['inbox'])),len(rows)>read)
        self.panel(x,249,330,520);detail=x+348;dw=1400-detail
        self.panel(detail,249,dw,520)
        self.page=min(self.page,max(0,(len(rows)-1)//4));visible=rows[self.page*4:self.page*4+4]
        selected=next((entry for entry in visible if entry[0]==self.inbox_selection),visible[0] if visible else None)
        for i,(index,n) in enumerate(visible):
            y=269+i*113
            self._inbox_style=(index==selected[0])
            self.button(n['title'],(x+14,y,302,99),lambda index=index:self.select_message(index))
            self._inbox_style=None
            self.text(dated(v,n['day'])+(' · Unread' if index>=read else ' · Read'),x+29,y+68,17,GREEN if index>=read else MUTED)
        self.text('Reading a message does not resolve a decision.',x+16,738,15,FAINT)
        if selected:
            n=selected[1];self.text('CLUB UPDATE  /  '+dated(v,n['day']),detail+24,275,17,GREEN)
            self.heading(n['title'],detail+24,311,31,width=dw-48)
            # Independent reader pages keep long monthly reports clear of actions.
            lines=[];line='';font=self.get_font(23)
            for word in n['body'].split():
                candidate=(line+' '+word).strip()
                if line and font.size(candidate)[0]>dw-48:lines.append(line);line=word
                else:line=candidate
            if line:lines.append(line)
            size=7 if v['decision'] else 11
            reader_key=selected[0]
            if self.inbox_reader_key!=reader_key:self.inbox_reader_page=0;self.inbox_reader_key=reader_key
            pages=max(1,(len(lines)+size-1)//size);self.inbox_reader_page=min(self.inbox_reader_page,pages-1)
            for i,line in enumerate(lines[self.inbox_reader_page*size:(self.inbox_reader_page+1)*size]):self.text(line,detail+24,363+i*25,23,TEXT)
            if pages>1:
                self.button('Earlier text',(detail+24,638,140,32),lambda:setattr(self,'inbox_reader_page',max(0,self.inbox_reader_page-1)),self.inbox_reader_page>0)
                self.text(f'{self.inbox_reader_page+1} / {pages}',detail+182,646,17,MUTED)
                self.button('More text',(detail+260,638,140,32),lambda:setattr(self,'inbox_reader_page',self.inbox_reader_page+1),self.inbox_reader_page+1<pages)
            if v['decision']:
                d=v['decision'];y=541;pygame.draw.rect(self.canvas,RAISED,(detail+24,y,dw-48,88),border_radius=6)
                self.text('REQUIRED DECISION',detail+40,y+14,16,WARNING)
                self.clipped_text(d['title'],detail+40,y+40,dw-80,23)
                self.text('One-off cost '+money(d['cost']),detail+40,y+68,18,MUTED)
                self.button('Review required decision',(detail+24,689,265,43),self.review_owner_decision)
                self.button('Decline',(detail+308,689,130,43),lambda:self.confirm('Decline this decision?',d['title']+' will be declined with no approval payment.',lambda:self.command('decision',choice='decline')))
            elif attention(v):
                item=attention(v)[0];self.button('Review contract',(detail+24,689,215,43),lambda:self.business_attention(item))
        else:self.wrap('No messages yet. Career news and outcomes will appear here.',detail+24,290,dw-48,26)
        self.pager(x,789,len(rows),4)

    def select_message(self,index):
        self.inbox_selection=index;self.inbox_reader_page=0;self.inbox_reader_key=index
        self.save_preferences()

    def draw_fixtures(self,x):
        from .competitions import label as fixture_label, result_text
        rows=[f for f in self.v['fixtures'] if 'c0' in (f['home'],f['away'])]
        self.text('LEAGUE & CUP  /  Season '+str(self.v['season']),x,200,22,GREEN)
        self.button('League table',(1220,190,180,42),lambda:self.nav('League'))
        self.page=min(self.page,max(0,(len(rows)-1)//7))
        pygame.draw.rect(self.canvas,RAISED,(x,253,1400-x,43),border_radius=5)
        for label,left in [('DATE',x+18),('FIXTURE',x+200),('RESULT',1100)]:self.text(label,left,267,17,MUTED)
        for i,f in enumerate(rows[self.page*7:self.page*7+7]):
            y=299+i*64
            if i%2==0:pygame.draw.rect(self.canvas,PANEL,(x,y,1400-x,63))
            self.text(self.fixture_date(f),x+18,y+21,21,MUTED)
            self.clipped_text(self.club(f['home'])+'  v  '+self.club(f['away']),x+200,y+7,585,22)
            self.text(fixture_label(f),x+200,y+34,16,MUTED)
            self.clipped_text(result_text(f),1080,y+21,152,18,GREEN if f['result'] else MUTED)
            self.button('Match report',(1240,y+12,145,40),lambda fid=f['id']:self.open_report(fid),f['result'] is not None)
        self.pager(x,789,len(rows),7)


    def cup_screen(self,x,archived=False):
        from .competitions import result_text
        from .planning import dated
        source=next((h for h in self.v['career']['history'] if h['season']==self.history_season),{}) if archived else self.v
        cup=source.get('competitions',{}).get('cup')
        self.button('League table',(1200,190,200,42),lambda:self.nav('League'))
        if not cup:
            self.wrap('This saved season keeps its original schedule. The Northshire Cup begins when you prepare the next season.',x,263,1050,28)
            return
        self.text('SINGLE MATCH TIES  /  Extra time and penalties',x,205,22,GREEN)
        self.wrap('Shared domestic registration and bans. No replays. Your home ties use current ticket pricing. No cup prize money in this development database.',x,253,1090,19,MUTED)
        if cup['winner']:
            self.heading('Winners  '+self.club(cup['winner']),x,305,30)
        else:
            self.text('Current round  /  '+cup['rounds'][-1]['label'],x,308,26)
        rows=[]
        fixtures={f['id']:f for f in source.get('fixtures',[])}
        for r in cup['rounds']:
            for cid in r['byes']:rows.append((r,None,cid))
            for fid in r['fixtures']:rows.append((r,fixtures[fid],None))
        self.page=min(self.page,max(0,(len(rows)-1)//5))
        for i,(r,f,bye) in enumerate(rows[self.page*5:self.page*5+5]):
            y=357+i*81
            self.panel(x,y,1400-x,73)
            self.text(r['label']+'  /  '+dated(self.v,r['day']),x+16,y+9,17,MUTED)
            if bye:
                self.text(self.club(bye)+' — bye to the next round',x+16,y+36,23)
            else:
                self.clipped_text(self.club(f['home'])+' v '+self.club(f['away']),x+16,y+36,630,23)
                self.text(result_text(f),x+655,y+38,20,GREEN if f['result'] else MUTED)
                self.button('Cup report',(1238,y+21,145,39),lambda fid=f['id']:self.open_report(fid),f['result'] is not None)
        self.pager(x,787,len(rows),5)
        future=cup['dates'][len(cup['rounds']):]
        self.clipped_text('Later round dates reserved: '+', '.join(dated(self.v,d) for d in future) if future else 'All rounds drawn. Results and the winner are saved with season history.',x,832,1130,15,MUTED)


    def division_screen(self,x):
        data=self.v['leagues']
        if self.league_season!=self.v['season']:
            self.league_id=data['own_division'];self.league_season=self.v['season']
        d=next((d for d in data['divisions'] if d['id']==self.league_id),data['divisions'][0])
        rows=data['tables'][d['id']];index=data['divisions'].index(d)
        self.text(d['name'].upper(),x,200,24,GREEN)
        other=data['divisions'][(index+1)%len(data['divisions'])]
        self.button('Switch division',(974,190,205,42),lambda:(setattr(self,'league_id',other['id']),setattr(self,'page',0)),len(data['divisions'])>1)
        self.button(self.v['competitions']['cup']['name'] if self.v['competitions']['cup'] else 'Northshire Cup',(1200,190,200,42),lambda:self.nav('Cup'))
        self.text('CLUB',x+15,245,20,MUTED)
        for i,t in enumerate(['P','W','D','L','GF','GA','PTS']):self.text(t,890+i*70,245,20,MUTED)
        count=data['exchange']
        self.page=min(self.page,max(0,(len(rows)-1)//8))
        for local,c in enumerate(rows[self.page*8:self.page*8+8]):
            i=self.page*8+local;y=285+local*43
            if c['id']=='c0':pygame.draw.rect(self.canvas,SELECTED,(x,y-8,1400-x,40),border_radius=4)
            self.clipped_text(f"{i+1}   {c['name']}",x+15,y,540,24)
            marker='UP' if index>0 and i<count else 'DOWN' if index<len(data['divisions'])-1 and i>=len(rows)-count else ''
            if marker:self.text(marker,815,y+4,16,GREEN if marker=='UP' else WARNING)
            for j,key in enumerate(['played','won','drawn','lost','gf','ga','points']):self.text(c[key],890+j*70,y,24)
        rule='Legacy season: second division added next season.' if data['legacy'] else f'{count} clubs move each way. '+('No lower feeder division in this development world.' if index==len(data['divisions'])-1 else f'Bottom {count} move to the next division.')
        self.clipped_text(rule,x+15,636,1100,18,MUTED)
        self.text('Tie-breaks: points, goal difference, goals scored, head-to-head points, recorded draw.' if not data['legacy'] else 'This saved season retains its original tie-break rules.',x+15,662,17,MUTED)
        if data['closed']:
            own=next((m for m in data['movements'] if m['club']=='c0'),None)
            message=own['kind']+' next season' if own else 'Division retained next season'
            self.text('SEASON CLOSED  /  '+message,x+15,708,23,GREEN)
            self.button('Season review',(1160,700,240,42),lambda:self.nav('Career'))
        else:
            self.text('Membership is fixed for this season. Results determine next season’s division.',x+15,714,20,MUTED)
        self.pager(x,781,len(rows),8)
        self.button('Your division',(x+465,781,170,42),lambda:(setattr(self,'league_id',data['own_division']),setattr(self,'page',0)))
        self.button('Fixtures & reports',(x+650,781,230,42),lambda:self.nav('Fixtures'))

        played=[f for f in self.v['fixtures'] if f['result'] is not None and 'c0' in (f['home'],f['away'])]
        self.button('Open match report',(1160,781,240,42),lambda:self.open_report(played[-1]['id']),bool(played))
