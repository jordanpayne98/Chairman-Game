"""Pygame interface; only authorised snapshots are used for drawing."""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import secrets
import sys
import uuid
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from .simulation import Command, MANAGERS, execute, new_career, view
from .persistence import SaveStore, SaveError, load, user_directory
from .career_ui import CareerScreens
from .presentation import crest, portrait, Soundscape
from .planning import ATTRIBUTES, SORTS, dated, player_rows, signing_terms, forecast

BG=(15,22,28);PANEL=(24,33,40);BORDER=(47,62,70);TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161);BUTTON=(32,77,65);RED=(246,150,142)
WIDTH,HEIGHT=1440,900


def money(v):return f'£{v/100:,.0f}'


class App(CareerScreens):
    def __init__(self,save_root=None):
        pygame.display.init();pygame.font.init()
        self.window=pygame.display.set_mode((1280,800),pygame.RESIZABLE)
        pygame.display.set_caption('Club Chairman — Career Update 0.3')
        self.canvas=pygame.Surface((WIDTH,HEIGHT))
        self.fonts={}
        self.state=None;self.v=None;self.screen='Home';self.buttons=[];self.focus=0;self.running=True
        self.message='';self.modal=None;self.collapsed=False;self.page=0;self.profile=None;self.search='';self.typing=False
        self.store=SaveStore(save_root);self.play=False;self.speed=1;self.elapsed=0;self.batch=False
        self.role='All';self.sort='Name';self.descending=False;self.only_shortlist=False
        self.tab='Forecast';self.match_report=None;self.profile_ids=[];self.views={};self.history=[];self.forward=[]
        self.workspaces={};self.undo=None;self.editor=None;self.note_draft='';self.notification_log=[]
        self.modal_revision=None;self.modal_focus=0;self.message_seen='';self.note_active=False
        self.key_events_only=False;self.offer_id=None;self.offer_draft=None;self.history_season=None
        self.reduced_motion=False;self.tooltips_enabled=True;self.explain_focus=False;self.help_regions=[]
        self.hover_key=None;self.hover_since=0;self.goal_until=0;self.last_score=None
        self.sound=Soundscape()
        self.settings_path=(Path(save_root) if save_root else user_directory())/'settings.json'
        try:
            settings=json.loads(self.settings_path.read_text());self.reduced_motion=bool(settings.get('reduced_motion',False));self.tooltips_enabled=bool(settings.get('tooltips_enabled',True));self.sound.volume=0 if settings.get('muted',False) else .22;self.workspaces=settings.get('workspaces',{});self.collapsed=bool(settings.get('collapsed',False));self.speed=settings.get('speed',1)
            if self.speed not in (1,2,4):self.speed=1
        except (OSError,ValueError,TypeError,AttributeError):pass
        if not isinstance(self.workspaces,dict):self.workspaces={}

    def text(self,text,x,y,size=22,color=TEXT):
        if size not in self.fonts:self.fonts[size]=pygame.font.Font(None,size)
        self.canvas.blit(self.fonts[size].render(str(text),True,color),(x,y))

    def wrap(self,text,x,y,width,size=22,color=MUTED):
        font=self.fonts.setdefault(size,pygame.font.Font(None,size))
        line=''
        for word in str(text).split():
            if font.size(line+' '+word)[0]>width and line:
                self.text(line,x,y,size,color);y+=size+4;line=word
            else:line=(line+' '+word).strip()
        if line:self.text(line,x,y,size,color)
        return y+size+4

    def panel(self,x,y,w,h,title=None):
        pygame.draw.rect(self.canvas,PANEL,(x,y,w,h),border_radius=7)
        pygame.draw.rect(self.canvas,BORDER,(x,y,w,h),1,border_radius=7)
        if title:self.text(title.upper(),x+20,y+18,20,MUTED)

    def button(self,label,rect,callback,enabled=True):
        r=pygame.Rect(rect);idx=len(self.buttons)
        active=(r.x==14 and label in (self.screen,self.screen[:2])) or label.startswith('• ')
        primary=label in ('Continue  >','Confirm','New career','Review signing','Play','Save note')
        fill=BUTTON if enabled and (active or primary) else (28,41,48) if enabled else PANEL
        pygame.draw.rect(self.canvas,fill,r,border_radius=5)
        pygame.draw.rect(self.canvas,GREEN if idx==self.focus else BORDER,r,2 if idx==self.focus else 1,border_radius=5)
        self.text(label,r.x+12,r.y+12,21,TEXT if enabled else MUTED)
        self.buttons.append((r,callback,enabled))
        self.help_regions.append((r,self.control_help(label,enabled),idx))

    def position(self):
        return {key:getattr(self,key) for key in ('screen','page','profile','search','role','sort','descending','only_shortlist','tab','match_report','profile_ids','offer_id','offer_draft','history_season')}

    def restore_position(self,position):
        for key,value in position.items():
            if key in self.position():setattr(self,key,value)
        self.typing=False;self.focus=0;self.play=False;self.batch=False

    def remember(self):
        if self.screen not in ('Home','Load'):self.views[self.screen]=self.position()

    def save_preferences(self):
        self.remember()
        if self.state:self.workspaces[self.state['career_id']]=self.views.copy()
        try:
            self.settings_path.parent.mkdir(parents=True,exist_ok=True)
            self.settings_path.write_text(json.dumps(dict(version=2,collapsed=self.collapsed,speed=self.speed,workspaces=self.workspaces,reduced_motion=self.reduced_motion,tooltips_enabled=self.tooltips_enabled,muted=self.sound.volume==0)))
        except OSError:self.message='Could not save interface preferences.'

    def reset_workspace(self,views=None):
        self.views=views if isinstance(views,dict) else {};self.history=[];self.forward=[];self.undo=None;self.editor=None
        self.notification_log=[];self.message_seen='';self.offer_id=None;self.offer_draft=None;self.history_season=None;self.last_score=None;self.goal_until=0
        self.screen='Home';self.page=0;self.profile=None;self.search='';self.role='All';self.sort='Name'
        self.descending=False;self.only_shortlist=False;self.match_report=None;self.profile_ids=[];self.tab='Forecast'

    def nav(self,screen):
        if self.screen!=screen:
            self.remember();self.history.append(self.position());self.forward=[]
            default=dict(screen=screen,page=0,profile=None,search='',role='All',sort='Name',descending=False,
                         only_shortlist=False,tab='Forecast',match_report=None,profile_ids=[],offer_id=None,offer_draft=None,history_season=self.history_season)
            self.restore_position(self.views.get(screen,default))
        self.typing=False;self.focus=0;self.play=False;self.batch=False
        self.save_preferences()

    def go_back(self):
        if self.history:
            self.remember();self.forward.append(self.position());self.restore_position(self.history.pop());self.save_preferences()
        elif self.profile:self.profile=None

    def go_forward(self):
        if self.forward:
            self.remember();self.history.append(self.position());self.restore_position(self.forward.pop());self.save_preferences()

    def filter_change(self,key,value):
        setattr(self,key,value);self.page=0;self.save_preferences()

    def open_profile(self,pid):
        self.history.append(self.position());self.forward=[]
        self.profile_ids=[p['id'] for p in self.filtered_players()]
        self.profile=pid;self.typing=False;self.focus=0

    def profile_neighbor(self,delta):
        if self.profile not in self.profile_ids:return
        index=self.profile_ids.index(self.profile)+delta
        if 0<=index<len(self.profile_ids):self.profile=self.profile_ids[index]

    def toggle_plan(self,key,pid):
        old=list(self.v['planning'][key]);value=list(old)
        if pid in value:value.remove(pid)
        else:value.append(pid)
        if self.command('planning',key=key,value=value):self.undo=(self.state['revision'],key,old)

    def undo_planning(self):
        if self.undo and self.undo[0]==self.state['revision']:
            _,key,value=self.undo;self.command('planning',key=key,value=value);self.undo=None

    def open_note(self,pid):
        self.play=False;self.batch=False;self.typing=False
        self.editor=pid;self.note_draft=self.v['planning']['notes'].get(pid,'');self.focus=0;self.note_active=True

    def save_note(self):
        notes=dict(self.v['planning']['notes']);notes[self.editor]=self.note_draft.strip()
        if self.command('planning',key='notes',value=notes):self.editor=None

    def open_report(self,fid):
        self.nav('Matchday');self.match_report=fid;self.page=0;self.play=False


    def confirm(self,title,body,callback):
        self.play=False;self.batch=False;self.typing=False
        self.modal=(title,body,callback);self.modal_revision=self.state['revision'] if self.state else None;self.modal_focus=self.focus;self.focus=0

    def command(self,action,**payload):
        try:
            self.state,self.message=execute(self.state,Command(uuid.uuid4().hex,self.state['revision'],action,payload))
            self.v=view(self.state)
            if action=='match_step' and self.v['match']:
                score=tuple(self.v['match']['score'])
                if self.last_score is not None and score!=self.last_score:
                    self.goal_until=pygame.time.get_ticks()+950;self.sound.play('goal')
                self.last_score=score
            self.undo=None
            if action not in ('match_step',) or self.v['match']['minute']==90:
                try:self.store.autosave(self.state)
                except SaveError as exc:self.message=str(exc);self.play=False;self.batch=False
            if self.v['match'] and self.v['match']['minute']==90:self.play=False
            return True
        except ValueError as exc:
            self.message=str(exc);self.play=False;self.batch=False;return False

    def start(self):
        self.state=new_career(secrets.randbelow(1000000));self.state['career_id']=uuid.uuid4().hex[:16]
        self.reset_workspace();self.v=view(self.state);self.nav('Overview');self.message='Welcome. Start by appointing your manager in Staff.'
        try:self.store.autosave(self.state)
        except SaveError as exc:self.message=str(exc)

    def manual_save(self):
        self.save_preferences()
        try:self.store.write(self.state);self.message='Career saved. Three autosave slots and the previous manual backup are retained.'
        except SaveError as exc:self.message=str(exc)

    def load_entry(self,path):
        try:
            state=load(path)
            # A restored timeline gets a separate folder, preserving damaged/newer files.
            old_id=state['career_id'];state['career_id']=uuid.uuid4().hex[:16]
            self.reset_workspace(self.workspaces.get(old_id,{}).copy())
            self.state=state;self.v=view(state);self.modal=None;self.play=False;self.batch=False
            self.nav('Matchday' if self.v['match'] else 'Overview');self.message='Career loaded. Future saves use a separate recovery timeline.'
        except SaveError as exc:self.message=str(exc)

    def continue_day(self):
        if self.command('continue'):
            if self.v['match']:self.nav('Matchday');self.match_report=None;self.page=0;self.batch=False
            elif self.v['decision']:self.nav('Overview');self.batch=False

    def next_fixture(self):
        self.batch=True

    def quit_request(self):
        if self.state:self.confirm('Leave the game?', 'Save your career with Save before leaving. Autosaves are made after committed management actions and full time; use Save to retain an unfinished match.',lambda:setattr(self,'running',False))
        else:self.running=False

    def render(self):
        self.canvas.fill(BG);self.buttons=[];self.help_regions=[]
        if self.state is None or self.screen in ('Home','Load'):
            self.home()
        else:
            if self.v is None or self.v['revision']!=self.state['revision']:self.v=view(self.state)
            self.chrome();x=100 if self.collapsed else 245
            self.text(self.screen if self.screen!='Overview' else "Chairman's Overview",x,100,40)
            self.text('NORTHBRIDGE ATHLETIC  /  '+self.screen.upper()+('  /  PLAYER PROFILE' if self.profile else ''),x,147,19,MUTED)
            self.button('< Back',(1160,100,112,38),self.go_back,bool(self.history))
            self.button('Forward >',(1283,100,117,38),self.go_forward,bool(self.forward))
            getattr(self,'draw_'+self.screen.lower())(x)
        if self.message and self.message!=self.message_seen:
            self.notification_log.append(self.message);self.notification_log=self.notification_log[-40:];self.message_seen=self.message
        self.text(self.message[:116],26,HEIGHT-39,20,GREEN)
        if self.undo and self.undo[0]==self.state['revision']:
            self.button('Undo',(1280,850,120,34),self.undo_planning)
        if self.editor:self.draw_note_editor()
        if self.modal:self.draw_modal()
        self.draw_tooltip()
        scale=min(self.window.get_width()/WIDTH,self.window.get_height()/HEIGHT)
        size=(round(WIDTH*scale),round(HEIGHT*scale));self.offset=((self.window.get_width()-size[0])//2,(self.window.get_height()-size[1])//2);self.scale=scale
        self.window.fill((8,12,16));self.window.blit(pygame.transform.smoothscale(self.canvas,size),self.offset);pygame.display.flip()

    def home(self):
        self.text('CLUB CHAIRMAN',100,100,60)
        self.text('CAREER UPDATE 0.3  /  NORTHSHIRE LEAGUE',104,170,25,GREEN)
        self.wrap('Take the chair at Northbridge Athletic. Appoint your manager, strengthen the squad and balance ambition against the club bank account.',104,225,770,29,TEXT)
        self.wrap('An evolving ownership game: continuing seasons, contracts, academy development and facility investment in a compact fictional league. The full AA world remains in development.',104,330,800,24)
        if self.screen=='Load':
            entries=self.store.entries();start=self.page*6
            for i,e in enumerate(entries[start:start+6]):
                self.button(e['label'],(104,430+i*52,920,44),lambda p=e['path']:self.load_entry(p),e['valid'])
            self.pager(104,760,len(entries),6)
            self.button('Back',(1100,760,150,44),lambda:self.nav('Home'))
            if not entries:self.text('No saved careers yet.',104,450)
            return
        self.button('New career',(104,445,240,52),lambda:self.confirm('Start a new career?', 'A new seed creates a fresh fictional squad. Existing saved careers are kept. This preview begins with an already-owned club.',self.start))
        self.button('Load / recover career',(104,515,240,52),lambda:self.nav('Load'))
        if self.state:self.button('Resume career',(104,585,240,52),lambda:self.nav('Matchday' if self.v['match'] else 'Overview'))
        self.button('Quit',(104,655,240,52),self.quit_request)
        self.panel(960,150,380,505,'How to play')
        y=210
        for text in ['1  Hire a manager in Staff.','2  Scout free agents in Recruitment.','3  Review budgets in Finances.','4  Continue to decisions and fixtures.','5  Watch, intervene or skip matches.','6  Renew contracts and start the next season.']:
            y=self.wrap(text,980,y,340,23,TEXT)+16
        self.text('Tab / Enter: controls  •  Esc: back',980,685,20,MUTED)

    def chrome(self):
        v=self.v;sw=78 if self.collapsed else 220
        pygame.draw.rect(self.canvas,PANEL,(0,0,sw,850))
        self.text('CC' if self.collapsed else 'CLUB CHAIRMAN',18,30,26,GREEN)
        self.button('>' if self.collapsed else '< Collapse',(14,91,sw-28,44),self.toggle_sidebar)
        screens=['Overview','Inbox','Squad','Staff','Recruitment','Contracts','Academy','Facilities','Finances','League','Matchday','Career','Settings','Help']
        for i,name in enumerate(screens):
            self.button(name[:2] if self.collapsed else name,(14,151+i*42,sw-28,36),lambda n=name:self.nav(n))
            if self.screen==name or (self.screen=='Comparison' and name=='Recruitment'):
                pygame.draw.rect(self.canvas,GREEN,(14,156+i*42,3,26),border_radius=2)
            if name=='Inbox' and not self.collapsed:
                unread=len(v['inbox'])-v['planning']['inbox_read']
                if unread:self.text(str(unread),sw-47,163+i*42,20,GREEN)
        if v['decision'] and not self.collapsed:self.text('! Approval required',20,748,18,RED)
        self.button('M' if self.collapsed else 'Main menu',(14,792,sw-28,38),lambda:self.nav('Home'))
        crest(self.canvas,'c0',(sw+20,12,36,52))
        self.text('NORTHBRIDGE ATHLETIC',sw+69,26,24)
        self.text('Season '+str(v['season']),sw+69,52,17,MUTED)
        self.text(v['date'],650,32,23,MUTED)
        self.button('Activity',(790,18,92,46),lambda:self.nav('Activity'))
        self.button('Save',(895,18,95,46),self.manual_save)
        self.button('Next fixture',(1005,18,160,46),self.next_fixture,not v['season_done'] and v['match'] is None)
        self.button('Continue  >',(1180,18,220,46),self.continue_day,not v['season_done'] and v['match'] is None)
        pygame.draw.line(self.canvas,BORDER,(sw,79),(1440,79))
        if self.batch:self.text('Advancing days… click Stop or press Esc',sw+25,810,23,GREEN);self.button('Stop',(1180,800,220,42),lambda:setattr(self,'batch',False))

    def toggle_sidebar(self):
        self.collapsed=not self.collapsed;self.save_preferences()

    def draw_overview(self,x):
        v=self.v;w=(1400-x-45)//4;pos=next(i+1 for i,c in enumerate(v['table']) if c['id']=='c0')
        headroom=v['budget']-v['payroll'];own=next(c for c in v['clubs'] if c['id']=='c0')
        for i,(label,value,detail) in enumerate([('Club cash',money(v['cash']),'Reserve '+money(v['terms']['operating_buffer'])),('Weekly payroll',money(v['payroll']),money(headroom)+' headroom'),('League position',f'{pos} / 8',f"{own['points']} points / {own['played']} played"),('Supporter mood',f"{v['supporters']} / 100",'Squad morale '+str(v['morale']))]):
            left=x+i*(w+15);self.panel(left,195,w,124,label);self.text(value,left+20,240,35,GREEN);self.text(detail,left+20,284,20,MUTED)
        self.panel(x,342,650,246,'Chairman decisions')
        if v['decision']:
            d=v['decision'];self.text('ACTION REQUIRED',x+430,362,19,RED)
            self.text(d['title'],x+20,398,29)
            self.wrap(f"Cost {money(d['cost'])}. Expected benefit: {'supporter goodwill' if d['supporters']>2 else 'squad preparation'}. Time waits for your decision.",x+20,441,610,23)
            self.button('Review decision',(x+20,524,215,44),lambda:self.confirm(d['title'],f"Pay {money(d['cost'])} now? This is a one-off commitment. Club cash after payment: {money(v['cash']-d['cost'])}.",lambda:self.command('decision',choice='approve')))
            self.button('Decline',(x+255,524,150,44),lambda:self.command('decision',choice='decline'))
        elif not v['manager']:
            self.text('The dugout is waiting.',x+20,399,29);self.wrap('Appoint a manager before advancing. Your manager controls team selection and tactics.',x+20,445,610,23)
            self.button('Review candidates',(x+20,524,220,44),lambda:self.nav('Staff'))
        elif v['season_done']:
            self.text('Season complete',x+20,399,32,GREEN);self.wrap(f'You finished {pos} of 8. Prize money and final wages are settled. Review contracts, then prepare the next campaign in Career.',x+20,445,610,24)
            self.button('Continue your career',(x+20,524,245,44),lambda:self.nav('Career'))
        else:
            self.text('Ready for the next step.',x+20,399,29)
            self.wrap(f"{len(v['planning']['shortlist'])} shortlisted / {len(v['planning']['comparison'])} pinned for comparison. Compare costs before you commit to a signing.",x+20,445,610,23)
            self.button('Review recruitment',(x+20,524,230,44),lambda:self.nav('Recruitment'))
        right=x+670;rw=1400-right
        self.panel(right,342,rw,246,'Next fixture')
        f=next((f for f in v['fixtures'] if 'c0' in (f['home'],f['away']) and f['result'] is None),None)
        if f:
            opponent=f['away'] if f['home']=='c0' else f['home']
            self.wrap(self.club(opponent),right+20,401,rw-40,32,TEXT)
            self.text(('HOME' if f['home']=='c0' else 'AWAY')+' / '+self.fixture_date(f),right+20,450,23,GREEN)
        else:self.text('All fixtures complete',right+20,401,27,GREEN)
        self.text('RECENT FORM',right+20,489,18,MUTED)
        for i,result in enumerate(own['form'][-5:]):
            left=right+20+i*46;pygame.draw.rect(self.canvas,BUTTON if result=='W' else BORDER,(left,522,35,34),border_radius=5);self.text(result,left+10,531,21,GREEN if result=='W' else TEXT)
        if not own['form']:self.text('No matches played yet',right+20,534,22,MUTED)
        self.panel(x,610,650,209,'Cash outlook / next 28 days')
        projection=forecast(v);self.cash_chart(projection,projection,x+20,655,380,118)
        self.text(money(projection['cash']),x+425,665,34,GREEN)
        self.text('Projected cash',x+425,704,20,MUTED)
        self.button('View finances',(x+425,750,200,42),lambda:self.nav('Finances'))
        self.text('Current commitments; ticket income estimated',x+20,793,19,MUTED)
        self.panel(right,610,rw,209,'Latest update')
        n=v['inbox'][-1];self.wrap(n['title'],right+20,664,rw-40,27,TEXT)
        self.text(f"{len(v['inbox'])-v['planning']['inbox_read']} unread updates",right+20,723,22,MUTED)
        self.button('Open inbox',(right+20,760,170,40),lambda:self.nav('Inbox'))

    def club(self,cid):return next(c['name'] for c in self.v['clubs'] if c['id']==cid)
    def fixture_date(self,f):return dated(self.v,f['day'])
    def pager(self,x,y,total,size):
        self.page=max(0,min(self.page,max(0,(total-1)//size)))
        self.button('Previous',(x,y,130,42),lambda:setattr(self,'page',max(0,self.page-1)),self.page>0)
        self.text(f'Page {self.page+1} / {max(1,(total+size-1)//size)}',x+150,y+12,21,MUTED)
        self.button('Next',(x+330,y,100,42),lambda:setattr(self,'page',self.page+1),(self.page+1)*size<total)

    def draw_inbox(self,x):
        read=self.v['planning']['inbox_read'];rows=list(reversed(list(enumerate(self.v['inbox']))))
        unread=len(rows)-read
        self.text(f'{unread} unread updates',x,200,24,GREEN)
        self.button('Mark all read',(x+265,190,175,40),lambda:self.command('planning',key='inbox_read',value=len(self.v['inbox'])),unread>0)
        if self.v['decision']:self.button('Review required decision',(x+465,190,270,40),lambda:self.nav('Overview'))
        for i,(index,n) in enumerate(rows[self.page*4:self.page*4+4]):
            y=250+i*123;self.panel(x,y,1400-x,110)
            self.text(('NEW  /  ' if index>=read else '')+dated(self.v,n['day'])+'  /  '+n['title'],x+18,y+15,24,GREEN if index>=read else TEXT)
            self.wrap(n['body'],x+18,y+49,1350-x,22)
        self.pager(x,785,len(rows),4)

    def draw_staff(self,x):self.staff_screen(x)

    def draw_squad(self,x):self.player_table(x,False)
    def draw_recruitment(self,x):self.player_table(x,True)

    def filtered_players(self):
        return player_rows(self.v,self.screen=='Recruitment',self.search,self.role,self.only_shortlist,self.sort,self.descending)

    def player_table(self,x,recruitment):
        if self.profile:
            p=next((p for p in self.v['players'] if p['id']==self.profile),None)
            if p:self.draw_profile(x,p);return
        self.button('Search: '+(self.search or 'name / Ctrl+F'),(x,190,335,42),lambda:setattr(self,'typing',True))
        roles=('All','GK','DEF','MID','FWD')
        self.button('Role: '+self.role,(x+350,190,130,42),lambda:self.filter_change('role',roles[(roles.index(self.role)+1)%len(roles)]))
        self.button('Shortlist only' if self.only_shortlist else 'All players',(x+495,190,160,42),lambda:self.filter_change('only_shortlist',not self.only_shortlist))
        self.button('Reset filters',(x+670,190,145,42),self.reset_filters)
        self.button(f"Compare ({len(self.v['planning']['comparison'])}/4)",(1200,190,200,42),lambda:self.nav('Comparison'))
        rows=self.filtered_players();self.page=min(self.page,max(0,(len(rows)-1)//7))
        self.button('Sort: '+self.sort,(x,246,210,38),lambda:self.filter_change('sort',SORTS[(SORTS.index(self.sort)+1)%len(SORTS)]))
        self.button('High to low' if self.descending else 'Low to high',(x+225,246,155,38),lambda:self.filter_change('descending',not self.descending))
        self.text(f'{len(rows)} results  /  unknown estimates sort last',x+400,257,22,MUTED)
        self.text('NAME / ROLE',x+15,309,18,MUTED);self.text('WAGE / WEEK',x+395,309,18,MUTED)
        self.text('EVIDENCE',x+555,309,18,MUTED)
        for i,p in enumerate(rows[self.page*7:self.page*7+7]):
            y=340+i*57;self.panel(x,y,1400-x,51)
            self.text(p['name'],x+15,y+8,25)
            self.text(f"{p['role']}  /  Age {p['age']}  /  {p['goals']} goals",x+15,y+32,18,MUTED)
            self.right_text(money(p['wage']),x+515,y+18,23)
            report=p['report'];info=report['confidence'] if report else 'Due '+dated(self.v,p['scout_due'])[:6] if p['scout_due'] else 'Not assessed'
            if report and self.sort.lower() in ATTRIBUTES:
                lo,hi=report['ranges'][self.sort.lower()];info=f'{lo}–{hi} (estimate)'
            self.text(info,x+555,y+18,21,GREEN if report else MUTED)
            self.button('Saved' if p['id'] in self.v['planning']['shortlist'] else '+ List',(1100,y+5,82,40),lambda pid=p['id']:self.toggle_plan('shortlist',pid))
            self.button('Pinned' if p['id'] in self.v['planning']['comparison'] else '+ Pin',(1192,y+5,82,40),lambda pid=p['id']:self.toggle_plan('comparison',pid))
            self.button('Profile',(1285,y+5,105,40),lambda pid=p['id']:self.open_profile(pid))
        self.pager(x,780,len(rows),7)
        self.text('Reports are estimates. Sorting uses range midpoints, never hidden ratings.',x+460,794,20,MUTED)
        if not rows:self.wrap('No players match these filters. Use Reset filters, or turn off Shortlist only.',x+20,380,900,27)

    def reset_filters(self):
        self.search='';self.role='All';self.only_shortlist=False;self.sort='Name';self.descending=False;self.page=0;self.save_preferences()

    def draw_profile(self,x,p):
        self.button('< Back to list',(x,190,175,42),self.close_profile)
        index=self.profile_ids.index(p['id']) if p['id'] in self.profile_ids else -1
        self.button('Previous player',(x+190,190,180,42),lambda:self.profile_neighbor(-1),index>0)
        self.button('Next player',(x+385,190,155,42),lambda:self.profile_neighbor(1),0<=index<len(self.profile_ids)-1)
        self.button('Remove shortlist' if p['id'] in self.v['planning']['shortlist'] else 'Add to shortlist',(x+555,190,190,42),lambda:self.toggle_plan('shortlist',p['id']))
        self.button('Unpin' if p['id'] in self.v['planning']['comparison'] else 'Pin comparison',(1200,190,200,42),lambda:self.toggle_plan('comparison',p['id']))
        self.panel(x,255,1400-x,118)
        portrait(self.canvas,p['id'],p['age'],(x+20,266,82,97),p['club'])
        self.text(p['name'],x+124,275,38)
        self.text(f"{p['role']}  /  Age {p['age']}  /  {'Free agent' if p['club'] is None else 'Northbridge Athletic'}",x+124,328,24,MUTED)
        self.text(f"{p['appearances']} apps  /  {p['goals']} goals",1090,330,23,GREEN)
        left=650;right=x+left+20;rw=1400-right
        self.panel(x,390,left,310,'Scouted attributes  /  1–100')
        report=p['report']
        if report:
            for i,key in enumerate(ATTRIBUTES):
                y=445+i*48;lo,hi=report['ranges'][key]
                self.text(key.capitalize(),x+20,y,24)
                pygame.draw.rect(self.canvas,BG,(x+190,y+2,320,15),border_radius=4)
                pygame.draw.rect(self.canvas,BUTTON,(x+190,y+2,round(320*hi/100),15),border_radius=4)
                pygame.draw.rect(self.canvas,GREEN,(x+190+round(320*lo/100),y+2,max(3,round(320*(hi-lo)/100)),15),border_radius=3)
                self.text(f'{lo}–{hi}',x+538,y,24,GREEN)
            self.text(f"{report['confidence']} confidence  /  {dated(self.v,report['day'])}",x+20,655,22,MUTED)
        else:
            self.wrap('Not assessed. Commission a report to see estimated ability ranges.',x+25,465,left-50,28,TEXT)
            self.wrap(f"Scouting costs {money(self.v['terms']['scout_fee'])} and takes {self.v['terms']['scout_days']} days.",x+25,563,left-50,25)
        self.panel(right,390,rw,310,'Terms and evidence')
        self.text(money(p['wage'])+' / week',right+20,443,30,GREEN)
        if p['club'] is None:
            t=signing_terms(self.v,[p])
            self.text('Signing fee  '+money(t['fee']),right+20,490,23)
            self.text('Future wages  '+money(t['future']),right+20,527,23)
            self.text('Total exposure  '+money(t['total']),right+20,564,24)
            self.wrap('Fixed terms until '+t['end_date']+'.',right+20,606,rw-40,21)
        else:self.wrap('Registered until '+dated(self.v,p['contract_end'])+'. Selection is delegated to your manager.',right+20,490,rw-40,24)
        if report:self.wrap('Source: '+report['source'],right+20,653,rw-40,20)
        self.button('Private note',(x,722,160,42),lambda:self.open_note(p['id']))
        self.text((self.v['planning']['notes'].get(p['id']) or 'Private thoughts; no game effect.')[:65],x+175,736,20,MUTED)
        if p['club']=='c0':self.button('Negotiate renewal',(x,780,225,44),lambda:self.contract_open(p['id']),not self.v['match'] and not p['youth'])
        if p['club'] is None:
            due=p['scout_due'];terms=self.v['terms']
            self.button('Request scouting',(x,780,210,44),lambda:self.confirm('Commission scouting',f"Spend {money(terms['scout_fee'])} to assess {p['name']}? The report arrives in {terms['scout_days']} days, on {dated(self.v,self.v['day']+terms['scout_days'])}. Cash after payment: {money(self.v['cash']-terms['scout_fee'])}.",lambda:self.command('scout',id=p['id'])),not report and not due and not self.v['match'] and not self.v['season_done'])
            self.button('Negotiate contract',(x+225,780,220,44),lambda:self.contract_open(p['id']),not self.v['match'] and not p['retired'] and self.v['day']<=self.v['window_end'])
            self.button('Review signing',(1160,722,230,42),lambda:self.review_signing(p),not signing_terms(self.v,[p])['reasons'])
            reason='; '.join(signing_terms(self.v,[p])['reasons'])
            self.text((reason or ('Report due '+dated(self.v,due) if due else 'Review costs before committing.'))[:77],x+450,795,20,MUTED)

    def close_profile(self):
        if self.history and self.history[-1]['screen']==self.screen and self.history[-1]['profile'] is None:self.go_back()
        else:self.profile=None;self.typing=False;self.save_preferences()

    def review_signing(self,p):
        t=signing_terms(self.v,[p])
        self.confirm('Sign '+p['name'],f"Pay {money(t['fee'])} now. Cash afterwards: {money(t['cash_after'])}. Add {money(t['wage'])} / week until {t['end_date']}. Guaranteed future salary: approximately {money(t['future'])}; total acquisition exposure {money(t['total'])}. Weekly wage headroom afterwards: {money(t['headroom'])}. No contingent fees in these fixed preview terms. Selection belongs to the manager. A signed contract cannot be undone.",lambda:self.command('sign',id=p['id']))

    def comparison_players(self):
        by_id={p['id']:p for p in self.v['players']}
        return [by_id[pid] for pid in self.v['planning']['comparison'] if pid in by_id]

    def draw_comparison(self,x):
        players=self.comparison_players()
        self.text('PIN UP TO FOUR  /  estimates and costs on the same basis',x,202,23,GREEN)
        self.button('Recruitment',(1190,190,210,42),lambda:self.nav('Recruitment'))
        if not players:
            self.wrap('Pin players in Recruitment or Squad to compare their reports, wages and total costs. Pins remain when you change filters or sign a player.',x+20,295,950,30,TEXT);return
        width=(1400-x-15*(len(players)-1))//len(players)
        for i,p in enumerate(players):
            left=x+i*(width+15);self.panel(left,255,width,447)
            self.wrap(p['name'],left+15,275,width-30,27,TEXT)
            self.text(p['role']+' / '+str(p['age']),left+15,325,23,GREEN)
            self.text('Free agent' if p['club'] is None else 'At your club',left+15,357,21,MUTED)
            for j,key in enumerate(ATTRIBUTES):
                value='Unknown' if not p['report'] else '–'.join(map(str,p['report']['ranges'][key]))
                self.text(key.capitalize(),left+15,398+j*33,20,MUTED);self.text(value,left+width-93,398+j*33,23)
            r=p['report'];self.text(r['confidence']+' / '+dated(self.v,r['day']) if r else 'No report',left+15,535,19,MUTED)
            self.text(r['source'] if r else 'Source: unavailable',left+15,560,19,MUTED)
            self.text(money(p['wage'])+' / week',left+15,591,24,GREEN)
            t=signing_terms(self.v,[p]);self.text('Total '+money(t['total']) if p['club'] is None else 'Already registered',left+15,622,22)
            self.button('Remove',(left+15,655,width-30,34),lambda pid=p['id']:self.toggle_plan('comparison',pid))
        t=signing_terms(self.v,players)
        self.text(f"{t['count']} free agents combined: {money(t['fee'])} now + {money(t['future'])} future wages",x,718,26)
        self.text('Wage headroom after all signings: '+money(t['headroom'])+' / week',x,749,24,GREEN if t['headroom']>=0 else RED)
        self.wrap('; '.join(t['reasons']) or 'Each signing needs its own review. Plans do not reserve funds.',x,790,850,22,RED if t['reasons'] else MUTED)
        self.button('Forecast this plan',(1175,775,225,44),lambda:(self.nav('Finances'),setattr(self,'tab','Plan')))

    def draw_finances(self,x):
        v=self.v
        for i,name in enumerate(('Forecast','Plan','Ledger')):
            self.button(('• ' if self.tab==name else '')+name,(x+i*165,190,150,40),lambda n=name:self.set_finance_tab(n))
        self.button('Why this forecast?',(1160,190,240,40),lambda:self.confirm('Forecast assumptions','All money is stored in pence. Costs follow committed wages, contract expiry, scheduled project openings and weekly settlement dates. Gate receipts hold current supporter mood and ticket prices, with an attendance sensitivity of ±15%. Unaccepted future deals, prizes and unapproved projects are excluded. A pinned plan adds only prospective free-agent costs. This is a planning estimate, not a guaranteed bank balance.',None))
        self.panel(x,250,1400-x,142,'Cash and commitments')
        self.text(f"Club cash {money(v['cash'])}   /   Owner funds {money(v['owner_cash'])}",x+20,290,28,GREEN)
        self.text(f"Payroll {money(v['payroll'])} / week   |   Limit {money(v['budget'])}   |   Headroom {money(v['budget']-v['payroll'])}",x+20,334,24)
        self.button('Budget -£2k',(x,410,160,42),lambda:self.command('budget',value=v['budget']-200000))
        self.button('Budget +£2k',(x+170,410,160,42),lambda:self.command('budget',value=v['budget']+200000))
        self.button('Inject £50,000',(x+340,410,190,42),lambda:self.confirm('Fund the club',f"Transfer £50,000 from your owner funds into club equity? Club cash becomes {money(v['cash']+5000000)}; owner funds become {money(v['owner_cash']-5000000)}. This adds no repayment or weekly cost.",lambda:self.command('fund')),v['owner_cash']>=5000000)
        self.text('Tickets '+money(v['tickets']),x+560,424,23)
        self.button('- £2',(1200,410,88,42),lambda:self.command('tickets',value=v['tickets']-200),not v['match'] and v['tickets']>1000)
        self.button('+ £2',(1300,410,88,42),lambda:self.command('tickets',value=v['tickets']+200),not v['match'] and v['tickets']<3000)
        if self.tab=='Ledger':
            self.text('CASH LEDGER  /  latest first',x,485,23,GREEN)
            rows=list(reversed(v['ledger']))
            self.text('MOVEMENT',x+10,530,19,MUTED);self.text('AMOUNT',1040,530,19,MUTED);self.text('BALANCE',1260,530,19,MUTED)
            for i,e in enumerate(rows[self.page*4:self.page*4+4]):
                y=568+i*44;self.text(f"{dated(v,e['day'])}  /  {e['reason']}",x+10,y,22)
                self.right_text(money(e['amount']),1140,y,23,GREEN if e['amount']>=0 else RED)
                self.right_text(money(e['balance']),1380,y,23,MUTED)
            if not rows:self.text('No cash movements yet.',x+20,585,25,MUTED)
            self.pager(x,780,len(rows),4);return
        selected=self.comparison_players() if self.tab=='Plan' else []
        f=forecast(v,selected);base=forecast(v);t=f['terms']
        self.text(('PINNED SIGNINGS' if self.tab=='Plan' else 'CURRENT COMMITMENTS')+'  /  through '+dated(v,f['end']),x,485,22,GREEN)
        self.panel(x,526,660,206)
        self.cash_chart(f,base,x+25,550,610,145)
        self.text('Today',x+25,708,19,MUTED);self.text(dated(v,f['end']),x+515,708,19,MUTED)
        right=x+680
        self.text('Projected cash  '+money(f['cash']),right,535,28,GREEN)
        self.text('Gate sensitivity  '+money(f['low'])+'–'+money(f['high']),right,574,21,MUTED)
        self.text('Payroll + operations  '+money(f['costs']),right,611,22)
        self.text('Sponsor / gates  '+money(f['sponsorship'])+' / '+money(f['gates']),right,646,22)
        self.text('Unpaid accrual at end  '+money(f['accrued']),right,683,21,MUTED)
        warning='; '.join(t['reasons'])
        if f['minimum']<f['reserve']:warning=(warning+'; ' if warning else '')+'Projected cash falls below the operating reserve'
        caption=(f"Plan: {t['count']} targets, {money(t['fee'])} now, +{money(t['wage'])}/week. Baseline {money(base['cash'])}. " if self.tab=='Plan' else '')
        caption+='Gate income holds today’s support and ticket price; shaded band varies attendance ±15%. Excludes prizes and unapproved spending. Planning never commits a deal.'
        self.wrap(caption,x,750,1400-x,21,MUTED)
        if warning:self.text(warning[:115],x,820,21,RED)

    def set_finance_tab(self,tab):
        self.tab=tab;self.page=0;self.save_preferences()

    def right_text(self,text,right,y,size=22,color=TEXT):
        font=self.fonts.setdefault(size,pygame.font.Font(None,size))
        self.text(text,right-font.size(str(text))[0],y,size,color)

    def cash_chart(self,f,base,x,y,w,h):
        points=f['points'];values=[p[k] for p in points for k in ('low','high')]+[p['cash'] for p in base['points']]+[f['reserve']]
        lo=min(values);hi=max(values);pad=max(100000,(hi-lo)*.1);lo-=pad;hi+=pad
        def xy(p,key):
            span=max(1,f['end']-self.v['day'])
            return (round(x+(p['day']-self.v['day'])/span*w),round(y+h-(p[key]-lo)/(hi-lo)*h))
        reserve_y=round(y+h-(f['reserve']-lo)/(hi-lo)*h)
        pygame.draw.line(self.canvas,BORDER,(x,reserve_y),(x+w,reserve_y),1)
        if len(points)>1:
            polygon=[xy(p,'high') for p in points]+[xy(p,'low') for p in reversed(points)]
            pygame.draw.polygon(self.canvas,BUTTON,polygon)
            if self.tab=='Plan' and len(base['points'])>1:pygame.draw.lines(self.canvas,MUTED,False,[xy(p,'cash') for p in base['points']],2)
            pygame.draw.lines(self.canvas,GREEN,False,[xy(p,'cash') for p in points],3)
        else:pygame.draw.circle(self.canvas,GREEN,xy(points[0],'cash'),4)
        self.text('Reserve '+money(f['reserve']),x+8,min(y+h-18,max(y,reserve_y+3)),18,MUTED)
        self.text(money(f['cash']),x+w-115,y,21,GREEN)

    def draw_league(self,x):
        self.text('NORTHSHIRE LEAGUE  •  8 clubs / home and away',x,200,24,GREEN)
        self.text('CLUB',x+15,245,20,MUTED)
        for i,t in enumerate(['P','W','D','L','GF','GA','PTS']):self.text(t,890+i*70,245,20,MUTED)
        for i,c in enumerate(self.v['table']):
            y=285+i*48
            if c['id']=='c0':pygame.draw.rect(self.canvas,BUTTON,(x,y-8,1400-x,44),border_radius=4)
            self.text(f"{i+1}   {c['name']}",x+15,y,25)
            for j,key in enumerate(['played','won','drawn','lost','gf','ga','points']):self.text(c[key],890+j*70,y,24)
        fs=[f for f in self.v['fixtures'] if 'c0' in (f['home'],f['away'])]
        f=fs[min(len(fs)-1,self.page)]
        self.panel(x,690,1400-x,80)
        score='vs' if not f['result'] else f"{f['result']['score'][0]}–{f['result']['score'][1]}"
        self.text(f"{self.fixture_date(f)}   {self.club(f['home'])}  {score}  {self.club(f['away'])}",x+15,715,24)
        self.pager(x,785,len(fs),1)
        self.button('Open match report',(1160,785,240,42),lambda:self.open_report(f['id']),f['result'] is not None)

    def draw_matchday(self,x):
        archive=[f for h in self.v['career']['history'] for f in h['fixtures']]
        historical=next((f for f in self.v['fixtures']+archive if f['id']==self.match_report and f['result']),None)
        m=dict(historical['result'],home=historical['home'],away=historical['away'],minute=90) if historical else self.v['match']
        if not m:
            self.wrap('No active match. Use Next fixture to advance. Open a completed fixture in League to review commentary, statistics and lineups.',x,230,1000,29);return
        self.panel(x,195,1400-x,130)
        if pygame.time.get_ticks()<self.goal_until and not self.reduced_motion and not historical:
            pygame.draw.rect(self.canvas,GREEN,(x,195,1400-x,130),3,border_radius=7)
        crest(self.canvas,m['home'],(x+17,212,51,80));crest(self.canvas,m['away'],(1324,212,51,80))
        self.text(f"{self.club(m['home'])}   {m['score'][0]} – {m['score'][1]}   {self.club(m['away'])}",x+90,225,32)
        self.text(f"{m['minute']}'  |  Shots {m['shots'][0]}–{m['shots'][1]}  |  On target {m['on_target'][0]}–{m['on_target'][1]}  |  xG {m['xg'][0]:.2f}–{m['xg'][1]:.2f}",x+90,280,22,GREEN)
        self.button('Commentary' if self.tab!='Lineups' else 'Show commentary',(x,339,175,37),lambda:setattr(self,'tab','Commentary'))
        self.button('Lineups',(x+190,339,125,37),lambda:setattr(self,'tab','Lineups'))
        self.button('All events' if self.key_events_only else 'Key events',(x+330,339,150,37),lambda:setattr(self,'key_events_only',not self.key_events_only))
        total=max(1,sum(m['possession']));self.text(f"Possession {m['possession'][0]*100/total:.0f}% / {m['possession'][1]*100/total:.0f}%",x+510,349,22,MUTED)
        self.panel(x,385,1400-x,308)
        if self.tab=='Lineups':
            for side,ids in enumerate(m['lineups']):
                left=x+20+side*((1400-x)//2)
                for i,pid in enumerate(ids):
                    p=self.v['public_players'][pid];self.text(p['role']+'   '+p['name'],left,397+i*26,22)
        events=[e for e in m['events'] if not self.key_events_only or e['kind'] in ('goal','period','bench')]
        self.page=min(self.page,max(0,(len(events)-1)//9))
        for i,e in enumerate(events[max(0,len(events)-9-self.page*9):len(events)-self.page*9 if self.page else None]):
            if self.tab!='Lineups':self.text(f"{e['minute']:>2}'  {e['text']}",x+20,403+i*30,22,GREEN if e['kind']=='goal' else TEXT)
        if not events and self.tab!='Lineups':self.text('The teams are ready. Press Play or Skip to full time.',x+20,403,25)
        if m['minute']<90:
            self.button('Pause' if self.play else 'Play',(x,710,130,44),lambda:setattr(self,'play',not self.play))
            self.button(f'{self.speed}x',(x+145,710,85,44),self.cycle_speed)
            self.button('Skip to full time',(x+245,710,200,44),lambda:self.command('match_step',minutes=90))
            self.button('Back the manager',(x,770,220,44),lambda:self.confirm('Back the manager','Send private encouragement? This supports the working relationship; it does not guarantee a result.',lambda:self.command('intervene',choice='encourage')),not m['intervened'])
            self.button('Request more attacking',(x+235,770,270,44),lambda:self.confirm('Request attacking football','Ask the manager to take more risks? They may refuse. If accepted, both attacking opportunities and defensive exposure increase.',lambda:self.command('intervene',choice='attack')),not m['intervened'])
        elif historical:self.button('Back to fixtures',(x,710,200,44),lambda:self.nav('League'))
        else:self.button('Finish review',(x,710,190,44),lambda:(self.command('match_close'),self.nav('Overview')))
        if historical and self.v['match']:
            self.button('Return to live match',(x+220,710,250,44),lambda:(setattr(self,'match_report',None),setattr(self,'page',0)))
        if historical:self.text('ARCHIVED REPORT  /  '+self.fixture_date(historical),x,778,23,MUTED)
        self.button('Earlier events',(1120,710,200,44),lambda:setattr(self,'page',self.page+1),(self.page+1)*9<len(events))
        self.button('Latest events',(1120,765,200,44),lambda:setattr(self,'page',0),self.page>0)

    def cycle_speed(self):
        self.speed={1:2,2:4,4:1}[self.speed];self.save_preferences()

    def draw_activity(self,x):
        self.text('SESSION ACTIVITY  /  newest first',x,201,23,GREEN)
        self.text('Career news and decision outcomes remain saved in the Inbox.',x,244,23,MUTED)
        rows=list(reversed(self.notification_log))
        for i,message in enumerate(rows[self.page*6:self.page*6+6]):
            y=295+i*73;self.panel(x,y,1400-x,62);self.wrap(message,x+18,y+15,1355-x,22,TEXT)
        self.pager(x,780,len(rows),6)

    def draw_help(self,x):
        self.panel(x,200,1400-x,630,'Playing this build')
        paragraphs=[
            'Hire a manager, commission scouting and advance days until reports arrive. Signings must fit cash reserves and your weekly wage budget. Budgets grant spending authority; they never create money.',
            'Continue advances one day. Next fixture advances until a match or required decision. All ordinary screens pause time. During match playback, opening another screen or a confirmation pauses the match.',
            'On matchday, your manager selects a 4-4-2. Watch the text engine at 1x, 2x or 4x, or skip. You can encourage your manager or request attacking football once per match. Save works mid-match.',
            'Save writes a manual slot. Autosaves follow management actions and full time. Load / recover lists dated checkpoints and backups. Loading makes a separate timeline, preserving existing files.',
            'Career adds continuing compact seasons, negotiated free-agent and renewal terms, manager replacement, academy trials/development and facility projects. The broader world, acquisitions, succession, loans, full football rules and wider staff delegation remain in development.',
            'Shortcuts: Ctrl+S saves; Ctrl+F searches players; Alt+Left/Right navigates history; Space pauses live matches; F1 opens Help. Tab / Shift+Tab moves focus, Enter activates. Esc closes overlays or goes back.',
            'F2 explains the focused control. Settings offers optional sound and reduced motion. Contracts requires proposal, conditional acceptance, medical and final completion. Renew existing players before expiry; merely opening an offer cannot keep them registered.',
            'Recruitment: filter by role, save a shortlist and pin up to four players. Compare uses scouted ranges. Finances > Plan projects pinned free-agent costs. Forecasts are estimates and never sign players. League > Open match report reopens completed fixtures.'
        ]
        y=250
        for p in paragraphs:y=self.wrap(p,x+25,y,1350-x,21)+12

    def draw_modal(self):
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA);overlay.fill((0,0,0,185));self.canvas.blit(overlay,(0,0))
        self.buttons=[];self.help_regions=[];self.panel(290,195,860,510)
        pending=self.modal
        title,body,callback=pending
        self.wrap(title,325,225,790,34,TEXT);self.wrap(body,325,295,790,25,TEXT)
        if callback is None:
            self.button('Close',(325,630,180,48),self.cancel_modal);return
        self.button('Cancel',(325,630,180,48),self.cancel_modal)
        def commit():
            if self.modal is not pending:return
            self.modal=None
            if self.state and self.modal_revision!=self.state['revision']:
                self.message='The career changed. Open this review again to confirm the current terms.';return
            callback()
        self.button('Confirm',(925,630,180,48),commit)

    def cancel_modal(self):
        self.modal=None;self.focus=self.modal_focus

    def draw_note_editor(self):
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA);overlay.fill((0,0,0,185));self.canvas.blit(overlay,(0,0))
        self.buttons=[];self.help_regions=[];self.panel(310,240,820,400,'Private planning note')
        self.wrap('Notes have no effect on the player or your relationship. Type up to 240 characters. Tab moves to buttons; Enter does not submit while typing.',340,295,755,23)
        pygame.draw.rect(self.canvas,BG,(340,360,760,170),border_radius=5)
        self.buttons.append((pygame.Rect(340,360,760,170),lambda:setattr(self,'note_active',True),True))
        pygame.draw.rect(self.canvas,GREEN if self.note_active else BORDER,(340,360,760,170),1,border_radius=5)
        self.wrap(self.note_draft+'|',355,375,730,25,TEXT)
        self.text(f'{len(self.note_draft)} / 240',340,545,21,MUTED)
        self.button('Discard',(340,585,150,40),lambda:setattr(self,'editor',None))
        self.button('Save note',(910,585,190,40),self.save_note)

    def event(self,event):
        if event.type==pygame.QUIT:self.quit_request()
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=((event.pos[0]-self.offset[0])/self.scale,(event.pos[1]-self.offset[1])/self.scale)
            for i,(rect,fn,enabled) in enumerate(self.buttons):
                if rect.collidepoint(pos):
                    self.focus=i
                    if enabled:self.sound.play('click');fn()
                    break
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_F2:
                self.explain_focus=not self.explain_focus;return
            if event.key==pygame.K_ESCAPE and self.explain_focus:
                self.explain_focus=False;return
            if event.key==pygame.K_ESCAPE:
                self.play=False;self.batch=False
                if self.modal:self.cancel_modal()
                elif self.editor:self.confirm('Save and close this note?','Save your private planning note before closing. Cancel returns to editing. Use Discard in the editor to remove unsaved changes.',self.save_note)
                elif self.typing:self.typing=False
                elif self.profile:self.go_back()
                elif self.history:self.go_back()
                else:self.nav('Home')
            elif event.key==pygame.K_TAB:
                self.typing=False;self.note_active=False;self.focus=(self.focus+(-1 if event.mod&pygame.KMOD_SHIFT else 1))%max(1,len(self.buttons))
            elif self.editor and not self.modal and self.note_active:
                if event.key==pygame.K_BACKSPACE:self.note_draft=self.note_draft[:-1]
                elif event.key==pygame.K_RETURN:pass
                elif event.unicode.isprintable() and len(self.note_draft)<240:self.note_draft+=event.unicode
            elif self.typing:
                if event.key==pygame.K_BACKSPACE:self.search=self.search[:-1]
                elif event.key==pygame.K_RETURN:self.typing=False
                elif event.unicode.isprintable() and len(self.search)<30:self.search+=event.unicode
                self.page=0
            elif not self.modal and self.state and event.key==pygame.K_s and event.mod&pygame.KMOD_CTRL:self.manual_save()
            elif not self.modal and event.key==pygame.K_LEFT and event.mod&pygame.KMOD_ALT:self.go_back()
            elif not self.modal and event.key==pygame.K_RIGHT and event.mod&pygame.KMOD_ALT:self.go_forward()
            elif not self.modal and event.key==pygame.K_f and event.mod&pygame.KMOD_CTRL and self.screen in ('Squad','Recruitment'):
                self.profile=None;self.typing=True
            elif not self.modal and event.key==pygame.K_SPACE and self.screen=='Matchday' and self.v['match'] and not self.match_report:
                self.play=not self.play
            elif not self.modal and event.key==pygame.K_F1 and self.state:self.nav('Help')
            elif event.key==pygame.K_RETURN and self.buttons:
                _,fn,enabled=self.buttons[self.focus%len(self.buttons)]
                if enabled:fn()

    def run(self,frames=None,screenshot=None):
        clock=pygame.time.Clock();n=0
        while self.running:
            dt=clock.tick(60)/1000;self.render()
            for event in pygame.event.get():
                self.event(event)
                self.render()
            if not self.modal and not self.editor:
                if self.batch:self.continue_day()
                if self.play and not self.match_report and self.screen=='Matchday' and self.v and self.v['match'] and self.v['match']['minute']<90:
                    self.elapsed+=dt*self.speed
                    if self.elapsed>=.35:self.command('match_step',minutes=1);self.elapsed=0
                elif self.screen!='Matchday':self.play=False
            n+=1
            if frames and n>=frames:break
        self.save_preferences()
        if screenshot:pygame.image.save(self.canvas,screenshot)
        pygame.quit()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--smoke',action='store_true');parser.add_argument('--screenshot');parser.add_argument('--save-dir')
    args=parser.parse_args()
    if args.self_test:
        from .selftest import run
        run()
        return
    if args.smoke:
        os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
    app=App(args.save_dir)
    if args.smoke:
        app.state=new_career(42);app.v=view(app.state);app.screen='Overview'
    app.run(frames=3 if args.smoke else None,screenshot=args.screenshot)
