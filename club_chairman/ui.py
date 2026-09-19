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

BG=(15,22,28);PANEL=(24,33,40);BORDER=(47,62,70);TEXT=(231,238,238);MUTED=(159,179,187);GREEN=(98,214,161);BUTTON=(32,77,65);RED=(246,150,142)
WIDTH,HEIGHT=1440,900


def money(v):return f'£{v/100:,.0f}'


class App:
    def __init__(self,save_root=None):
        pygame.display.init();pygame.font.init()
        self.window=pygame.display.set_mode((1280,800),pygame.RESIZABLE)
        pygame.display.set_caption('Club Chairman — First Season')
        self.canvas=pygame.Surface((WIDTH,HEIGHT))
        self.fonts={}
        self.state=None;self.v=None;self.screen='Home';self.buttons=[];self.focus=0;self.running=True
        self.message='';self.modal=None;self.collapsed=False;self.page=0;self.profile=None;self.search='';self.typing=False
        self.store=SaveStore(save_root);self.play=False;self.speed=1;self.elapsed=0;self.batch=False
        self.settings_path=(Path(save_root).parent if save_root else user_directory())/'settings.json'
        try:
            settings=json.loads(self.settings_path.read_text());self.collapsed=bool(settings.get('collapsed',False));self.speed=settings.get('speed',1)
            if self.speed not in (1,2,4):self.speed=1
        except (OSError,ValueError,TypeError):pass

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
        pygame.draw.rect(self.canvas,BUTTON if enabled else PANEL,r,border_radius=5)
        pygame.draw.rect(self.canvas,GREEN if idx==self.focus else BORDER,r,2 if idx==self.focus else 1,border_radius=5)
        self.text(label,r.x+12,r.y+12,21,TEXT if enabled else MUTED)
        self.buttons.append((r,callback,enabled))

    def nav(self,screen):
        self.screen=screen;self.page=0;self.profile=None;self.search='';self.typing=False;self.focus=0

    def confirm(self,title,body,callback):
        self.play=False;self.batch=False;self.typing=False
        self.modal=(title,body,callback);self.focus=0

    def command(self,action,**payload):
        try:
            self.state,self.message=execute(self.state,Command(uuid.uuid4().hex,self.state['revision'],action,payload))
            self.v=view(self.state)
            if action not in ('match_step',) or self.v['match']['minute']==90:
                try:self.store.autosave(self.state)
                except SaveError as exc:self.message=str(exc);self.play=False;self.batch=False
            if self.v['match'] and self.v['match']['minute']==90:self.play=False
            return True
        except ValueError as exc:
            self.message=str(exc);self.play=False;self.batch=False;return False

    def start(self):
        self.state=new_career(secrets.randbelow(1000000));self.state['career_id']=uuid.uuid4().hex[:16]
        self.v=view(self.state);self.nav('Overview');self.message='Welcome. Start by appointing your manager in Staff.'
        try:self.store.autosave(self.state)
        except SaveError as exc:self.message=str(exc)

    def manual_save(self):
        try:self.store.write(self.state);self.message='Career saved. Three autosave slots and the previous manual backup are retained.'
        except SaveError as exc:self.message=str(exc)

    def load_entry(self,path):
        try:
            state=load(path)
            # A restored timeline gets a separate folder, preserving damaged/newer files.
            state['career_id']=uuid.uuid4().hex[:16]
            self.state=state;self.v=view(state);self.modal=None;self.play=False;self.batch=False
            self.nav('Matchday' if self.v['match'] else 'Overview');self.message='Career loaded. Future saves use a separate recovery timeline.'
        except SaveError as exc:self.message=str(exc)

    def continue_day(self):
        if self.command('continue'):
            if self.v['match']:self.nav('Matchday');self.batch=False
            elif self.v['decision']:self.nav('Overview');self.batch=False

    def next_fixture(self):
        self.batch=True

    def quit_request(self):
        if self.state:self.confirm('Leave the game?', 'Save your career with Save before leaving. Autosaves are made after committed management actions and full time; use Save to retain an unfinished match.',lambda:setattr(self,'running',False))
        else:self.running=False

    def render(self):
        self.canvas.fill(BG);self.buttons=[]
        if self.state is None or self.screen in ('Home','Load'):
            self.home()
        else:
            self.v=view(self.state);self.chrome();x=100 if self.collapsed else 245
            self.text(self.screen if self.screen!='Overview' else "Chairman's Overview",x,100,40)
            self.text('Northbridge Athletic  /  First Season playable preview',x,145,22,MUTED)
            getattr(self,'draw_'+self.screen.lower())(x)
        self.text(self.message[:135],26,HEIGHT-39,20,GREEN)
        if self.modal:self.draw_modal()
        scale=min(self.window.get_width()/WIDTH,self.window.get_height()/HEIGHT)
        size=(round(WIDTH*scale),round(HEIGHT*scale));self.offset=((self.window.get_width()-size[0])//2,(self.window.get_height()-size[1])//2);self.scale=scale
        self.window.fill((8,12,16));self.window.blit(pygame.transform.smoothscale(self.canvas,size),self.offset);pygame.display.flip()

    def home(self):
        self.text('CLUB CHAIRMAN',100,100,60)
        self.text('FIRST SEASON',104,170,25,GREEN)
        self.wrap('Take the chair at Northbridge Athletic. Appoint your manager, strengthen the squad and balance ambition against the club bank account.',104,225,770,29,TEXT)
        self.wrap('Playable preview: eight fictional clubs, fourteen league matches and one complete season. The full game is still in development.',104,330,800,24)
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
        for text in ['1  Hire a manager in Staff.','2  Scout free agents in Recruitment.','3  Review budgets in Finances.','4  Continue to decisions and fixtures.','5  Watch, intervene or skip matches.','6  Finish the season and review results.']:
            y=self.wrap(text,980,y,340,23,TEXT)+16
        self.text('Tab / Enter: controls  •  Esc: back',980,685,20,MUTED)

    def chrome(self):
        v=self.v;sw=78 if self.collapsed else 220
        pygame.draw.rect(self.canvas,PANEL,(0,0,sw,850))
        self.text('CC' if self.collapsed else 'CLUB CHAIRMAN',18,30,26,GREEN)
        self.button('>' if self.collapsed else '< Collapse',(14,91,sw-28,44),self.toggle_sidebar)
        screens=['Overview','Inbox','Squad','Staff','Recruitment','Finances','League','Matchday','Help']
        for i,name in enumerate(screens):
            self.button(name[:2] if self.collapsed else name,(14,160+i*57,sw-28,45),lambda n=name:self.nav(n))
        self.button('M' if self.collapsed else 'Main menu',(14,760,sw-28,44),lambda:self.nav('Home'))
        self.text('NORTHBRIDGE ATHLETIC',sw+25,30,25)
        self.text(v['date'],650,32,23,MUTED)
        self.button('Save',(895,18,95,46),self.manual_save)
        self.button('Next fixture',(1005,18,160,46),self.next_fixture,not v['season_done'] and v['match'] is None)
        self.button('Continue  >',(1180,18,220,46),self.continue_day,not v['season_done'] and v['match'] is None)
        pygame.draw.line(self.canvas,BORDER,(sw,79),(1440,79))
        if self.batch:self.text('Advancing days… click Stop or press Esc',sw+25,810,23,GREEN);self.button('Stop',(1180,800,220,42),lambda:setattr(self,'batch',False))

    def toggle_sidebar(self):
        self.collapsed=not self.collapsed
        try:
            self.settings_path.parent.mkdir(parents=True,exist_ok=True)
            self.settings_path.write_text(json.dumps({'collapsed':self.collapsed,'speed':self.speed}))
        except OSError:self.message='Could not save interface preferences.'

    def draw_overview(self,x):
        v=self.v;w=(1400-x-45)//4
        pos=next(i+1 for i,c in enumerate(v['table']) if c['id']=='c0')
        for i,(label,value) in enumerate([('Club cash',money(v['cash'])),('Weekly payroll',money(v['payroll'])),('League position',f'{pos} / 8'),('Supporter mood',f"{v['supporters']} / 100")]):
            self.panel(x+i*(w+15),195,w,105,label);self.text(value,x+i*(w+15)+20,244,34,GREEN)
        self.panel(x,325,680,250,'Chairman decisions')
        if v['decision']:
            d=v['decision'];self.text(d['title'],x+20,380,29)
            self.wrap(f"Cost {money(d['cost'])}. Expected benefit: {'supporter goodwill' if d['supporters']>2 else 'squad preparation'}. Approval spends club cash; declining preserves it.",x+20,420,630)
            self.button('Review decision',(x+20,510,220,44),lambda:self.confirm(d['title'],f"Pay {money(d['cost'])} now? This is a one-off commitment. Club cash after payment: {money(v['cash']-d['cost'])}.",lambda:self.command('decision',choice='approve')))
            self.button('Decline',(x+260,510,160,44),lambda:self.command('decision',choice='decline'))
        elif not v['manager']:
            self.text('The dugout is waiting.',x+20,382,29);self.wrap('Appoint a manager before advancing. Your manager controls team selection and tactics.',x+20,427,630)
            self.button('Review candidates',(x+20,510,220,44),lambda:self.nav('Staff'))
        elif v['season_done']:
            self.text('Season complete',x+20,382,32,GREEN);self.wrap(f'You finished {pos} of 8. Prize money and final wages have been settled. Review League and Finances, or start another career from the menu.',x+20,430,630)
        else:
            self.text('No approval is waiting.',x+20,382,29);self.wrap('Review your squad and recruitment reports, then Continue one day or advance to the next fixture. New decisions interrupt time.',x+20,430,630)
        self.panel(x+700,325,1400-x-700,250,'Next fixture')
        f=next((f for f in v['fixtures'] if 'c0' in (f['home'],f['away']) and f['result'] is None),None)
        if f:
            self.wrap(self.club(f['home'])+' vs '+self.club(f['away']),x+720,385,1400-x-740,29,TEXT)
            self.text(self.fixture_date(f),x+720,485,25,GREEN)
        else:self.text('All fixtures complete',x+720,385,27,GREEN)
        self.panel(x,600,680,175,'Club outlook')
        self.text(f"Wage headroom: {money(v['budget']-v['payroll'])} / week",x+20,650,26)
        self.text(f"Owner funds: {money(v['owner_cash'])} — separate from club cash",x+20,692,23,MUTED)
        self.panel(x+700,600,1400-x-700,175,'Latest update')
        n=v['inbox'][-1];self.wrap(n['title'],x+720,650,1400-x-740,25,TEXT);self.button('Open inbox',(x+720,710,170,43),lambda:self.nav('Inbox'))

    def club(self,cid):return next(c['name'] for c in self.v['clubs'] if c['id']==cid)
    def fixture_date(self,f):return (date(2026,8,3)+timedelta(days=f['day'])).strftime('%d %b %Y')
    def pager(self,x,y,total,size):
        self.page=max(0,min(self.page,max(0,(total-1)//size)))
        self.button('Previous',(x,y,130,42),lambda:setattr(self,'page',max(0,self.page-1)),self.page>0)
        self.text(f'Page {self.page+1} / {max(1,(total+size-1)//size)}',x+150,y+12,21,MUTED)
        self.button('Next',(x+330,y,100,42),lambda:setattr(self,'page',self.page+1),(self.page+1)*size<total)

    def draw_inbox(self,x):
        rows=list(reversed(self.v['inbox']))
        for i,n in enumerate(rows[self.page*5:self.page*5+5]):
            y=198+i*113;self.panel(x,y,1400-x,100)
            self.text(f"Day {n['day']}  |  {n['title']}",x+18,y+15,25)
            self.wrap(n['body'],x+18,y+48,1350-x,21)
        self.pager(x,785,len(rows),5)

    def draw_staff(self,x):
        if self.v['manager']:
            m=self.v['manager'];self.panel(x,200,1400-x,370,'Manager office')
            self.text(m['name'],x+25,260,38);self.text(f"{m['style']} approach  |  {money(m['wage'])} / week",x+25,320,26,GREEN)
            self.wrap('Delegated: team selection and match tactics. You can send one bench message per match; the manager can refuse a request to attack. The appointment lasts for this preview season.',x+25,380,950,26)
            self.text(f"Working relationship: {self.v['trust']} / 100",x+25,490,27)
            return
        for i,m in enumerate(MANAGERS):
            y=205+i*185;self.panel(x,y,1400-x,168)
            self.text(m['name'],x+22,y+20,32);self.text(m['style']+' approach',x+22,y+62,24,GREEN)
            self.text(f"{money(m['wage'])} / week  |  {money(m['fee'])} signing fee",x+22,y+106,24)
            self.button('Review '+m['name'],(1110,y+58,260,48),lambda m=m:self.confirm('Appoint '+m['name'],f"Immediate signing fee: {money(m['fee'])}. Weekly salary: {money(m['wage'])}. Salary runs through the 14-match preview season. Squad selection and tactics are delegated. No dismissal or replacement is implemented in this build.",lambda:self.command('hire',id=m['id'])))

    def draw_squad(self,x):self.player_table(x,False)
    def draw_recruitment(self,x):self.player_table(x,True)

    def player_table(self,x,recruitment):
        if self.profile:
            p=next((p for p in self.v['players'] if p['id']==self.profile),None)
            if p:self.draw_profile(x,p);return
        self.button('Search: '+(self.search or 'click and type'),(x,190,480,44),lambda:setattr(self,'typing',True))
        self.button('Clear',(x+495,190,110,44),lambda:(setattr(self,'search',''),setattr(self,'page',0)))
        rows=[p for p in self.v['players'] if (p['club'] is None)==recruitment and self.search.lower() in p['name'].lower()]
        self.text('NAME',x+15,255,20,MUTED);self.text('ROLE / AGE',x+330,255,20,MUTED);self.text('WAGE / WEEK',x+500,255,20,MUTED);self.text('REPORT',x+710,255,20,MUTED)
        for i,p in enumerate(rows[self.page*8:self.page*8+8]):
            y=286+i*57;self.panel(x,y,1400-x,50)
            self.text(p['name'],x+15,y+15,24);self.text(f"{p['role']} / {p['age']}",x+330,y+15,23);self.text(money(p['wage']),x+500,y+15,23)
            self.text(p['report']['confidence'] if p['report'] else 'Due day '+str(p['scout_due']) if p['scout_due'] else 'Not assessed',x+710,y+15,22,MUTED)
            self.button('Profile',(1285,y+4,105,42),lambda pid=p['id']:setattr(self,'profile',pid))
        self.pager(x,780,len(rows),8)
        if not rows:self.text('No matching players. Clear the search to see the full list.',x+20,300,24)

    def draw_profile(self,x,p):
        self.button('< Back to list',(x,190,180,44),lambda:setattr(self,'profile',None))
        self.panel(x,255,1400-x,470,p['name'])
        self.text(f"{p['role']}  |  Age {p['age']}  |  {'Free agent' if p['club'] is None else 'Northbridge Athletic'}",x+25,310,29)
        self.text(f"Wage: {money(p['wage'])} / week   Signing fee: {money(p['fee']) if p['club'] is None else 'Already registered'}",x+25,365,26)
        report=p['report']
        if report:
            self.text(f"{report['confidence']} confidence | {report['source']} | day {report['day']}",x+25,420,24,GREEN)
            for i,(key,interval) in enumerate(report['ranges'].items()):self.text(f"{key.capitalize():16}  {interval[0]}–{interval[1]}",x+25,470+i*42,26)
            self.text('Estimates can be wrong. Potential is not assessed in this preview.',x+25,663,23,MUTED)
        else:self.wrap('Not assessed. Request a report for £250; it takes three days. Wage and signing terms are public fixed offers in this preview.',x+25,440,900,27)
        if p['club'] is None:
            self.button('Request scouting',(x,755,220,46),lambda:self.confirm('Commission scouting',f"Spend £250 to assess {p['name']}? The report arrives in three days.",lambda:self.command('scout',id=p['id'])),not report and not p['scout_due'])
            self.button('Review signing',(x+245,755,220,46),lambda:self.confirm('Sign '+p['name'],f"Pay {money(p['fee'])} now and {money(p['wage'])} weekly through the season. Total estimated remaining salary: {money(p['wage']*max(0,96-self.v['day'])//7)}. Scouting is uncertain; selection is the manager's decision. Fixed free-agent terms only in this preview.",lambda:self.command('sign',id=p['id'])),self.v['day']<=28 and not self.v['season_done'])

    def draw_finances(self,x):
        v=self.v;self.panel(x,200,1400-x,245,'Cash and commitments')
        self.text(f"Club cash {money(v['cash'])}     Owner funds {money(v['owner_cash'])}",x+20,249,30,GREEN)
        self.text(f"Payroll {money(v['payroll'])} / week  |  Authorised limit {money(v['budget'])}",x+20,295,27)
        self.button('Budget -£2k',(x+20,345,170,44),lambda:self.command('budget',value=v['budget']-200000))
        self.button('Budget +£2k',(x+205,345,170,44),lambda:self.command('budget',value=v['budget']+200000))
        self.button('Inject £50,000',(x+405,345,190,44),lambda:self.confirm('Fund the club', 'Transfer £50,000 of owner cash into club equity? This is not revenue or a loan. Both balances will change.',lambda:self.command('fund')))
        self.text(f"Home ticket price {money(v['tickets'])}",x+20,410,23)
        self.button('- £2',(x+370,399,85,35),lambda:self.command('tickets',value=v['tickets']-200))
        self.button('+ £2',(x+465,399,85,35),lambda:self.command('tickets',value=v['tickets']+200))
        self.text('Cash ledger — every movement reconciles to the balance',x,470,26)
        rows=list(reversed(v['ledger']))
        for i,e in enumerate(rows[self.page*5:self.page*5+5]):
            y=515+i*46;self.text(f"Day {e['day']}  {e['reason']}",x+10,y,23)
            self.text(money(e['amount']),1000,y,23,GREEN if e['amount']>=0 else RED)
            self.text(money(e['balance']),1225,y,23,MUTED)
        self.pager(x,780,len(rows),5)

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

    def draw_matchday(self,x):
        m=self.v['match']
        if not m:
            self.wrap('No active match. Use Next fixture to advance. Previous scores are available in League and the inbox.',x,230,1000,29);return
        self.panel(x,195,1400-x,130)
        self.text(f"{self.club(m['home'])}   {m['score'][0]} – {m['score'][1]}   {self.club(m['away'])}",x+25,225,35)
        self.text(f"{m['minute']}'  |  Shots {m['shots'][0]}–{m['shots'][1]}  |  On target {m['on_target'][0]}–{m['on_target'][1]}  |  xG {m['xg'][0]:.2f}–{m['xg'][1]:.2f}",x+25,280,24,GREEN)
        self.panel(x,345,1400-x,340,'Match commentary')
        events=m['events']
        for i,e in enumerate(events[max(0,len(events)-9-self.page*9):len(events)-self.page*9 if self.page else None]):
            self.text(f"{e['minute']:>2}'  {e['text']}",x+20,394+i*30,22,GREEN if e['kind']=='goal' else TEXT)
        if not events:self.text('The teams are ready. Press Play or Skip to full time.',x+20,395,25)
        if m['minute']<90:
            self.button('Pause' if self.play else 'Play',(x,710,130,44),lambda:setattr(self,'play',not self.play))
            self.button(f'{self.speed}x',(x+145,710,85,44),self.cycle_speed)
            self.button('Skip to full time',(x+245,710,200,44),lambda:self.command('match_step',minutes=90))
            self.button('Back the manager',(x,770,220,44),lambda:self.confirm('Back the manager','Send private encouragement? This supports the working relationship; it does not guarantee a result.',lambda:self.command('intervene',choice='encourage')),not m['intervened'])
            self.button('Request more attacking',(x+235,770,270,44),lambda:self.confirm('Request attacking football','Ask the manager to take more risks? They may refuse. If accepted, both attacking opportunities and defensive exposure increase.',lambda:self.command('intervene',choice='attack')),not m['intervened'])
        else:self.button('Finish review',(x,710,190,44),lambda:(self.command('match_close'),self.nav('Overview')))
        self.button('Earlier events',(1120,710,200,44),lambda:setattr(self,'page',self.page+1),(self.page+1)*9<len(events))
        self.button('Latest events',(1120,765,200,44),lambda:setattr(self,'page',0),self.page>0)

    def cycle_speed(self):
        self.speed={1:2,2:4,4:1}[self.speed]
        try:
            self.settings_path.parent.mkdir(parents=True,exist_ok=True);self.settings_path.write_text(json.dumps({'collapsed':self.collapsed,'speed':self.speed}))
        except OSError:self.message='Could not save speed preference.'

    def draw_help(self,x):
        self.panel(x,200,1400-x,590,'Playing this build')
        paragraphs=[
            'Hire a manager, commission scouting and advance days until reports arrive. Signings must fit cash reserves and your weekly wage budget. Budgets grant spending authority; they never create money.',
            'Continue advances one day. Next fixture advances until a match or required decision. All ordinary screens pause time. During match playback, opening another screen or a confirmation pauses the match.',
            'On matchday, your manager selects a 4-4-2. Watch the text engine at 1x, 2x or 4x, or skip. You can encourage your manager or request attacking football once per match. Save works mid-match.',
            'Save writes a manual slot. Autosaves follow management actions and full time. Load / recover lists dated checkpoints and backups. Loading makes a separate timeline, preserving existing files.',
            'Preview limits: one existing club and one 14-match season; four assessed player attributes; fixed free-agent terms; one manager appointment; simplified possession/chance engine. No injuries, cards, substitutions, cups, promotion, academy, multi-club ownership or succession yet.',
            'Keyboard: Tab / Shift+Tab moves focus, Enter activates, Esc cancels a dialog or stops time. Click Search in Squad or Recruitment and type a name; Backspace edits. Every essential action has a visible button.'
        ]
        y=250
        for p in paragraphs:y=self.wrap(p,x+25,y,1350-x,24)+19

    def draw_modal(self):
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA);overlay.fill((0,0,0,185));self.canvas.blit(overlay,(0,0))
        self.buttons=[];self.panel(340,250,760,360)
        pending=self.modal
        title,body,callback=pending
        self.text(title,370,285,34);self.wrap(body,370,345,700,26,TEXT)
        self.button('Cancel',(370,530,180,48),lambda:setattr(self,'modal',None))
        def commit():
            if self.modal is not pending:return
            self.modal=None;callback()
        self.button('Confirm',(880,530,180,48),commit)

    def event(self,event):
        if event.type==pygame.QUIT:self.quit_request()
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=((event.pos[0]-self.offset[0])/self.scale,(event.pos[1]-self.offset[1])/self.scale)
            for i,(rect,fn,enabled) in enumerate(self.buttons):
                if rect.collidepoint(pos):
                    self.focus=i
                    if enabled:fn()
                    break
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                self.play=False;self.batch=False
                if self.modal:self.modal=None
                elif self.typing:self.typing=False
                elif self.profile:self.profile=None
                else:self.nav('Home')
            elif event.key==pygame.K_TAB:
                self.typing=False;self.focus=(self.focus+(-1 if event.mod&pygame.KMOD_SHIFT else 1))%max(1,len(self.buttons))
            elif self.typing:
                if event.key==pygame.K_BACKSPACE:self.search=self.search[:-1]
                elif event.key==pygame.K_RETURN:self.typing=False
                elif event.unicode.isprintable() and len(self.search)<30:self.search+=event.unicode
                self.page=0
            elif event.key==pygame.K_RETURN and self.buttons:
                _,fn,enabled=self.buttons[self.focus%len(self.buttons)]
                if enabled:fn()

    def run(self,frames=None,screenshot=None):
        clock=pygame.time.Clock();n=0
        while self.running:
            dt=clock.tick(30)/1000;self.render()
            for event in pygame.event.get():
                self.event(event)
                self.render()
            if not self.modal:
                if self.batch:self.continue_day()
                if self.play and self.screen=='Matchday' and self.v and self.v['match'] and self.v['match']['minute']<90:
                    self.elapsed+=dt*self.speed
                    if self.elapsed>=.35:self.command('match_step',minutes=1);self.elapsed=0
                elif self.screen!='Matchday':self.play=False
            n+=1
            if frames and n>=frames:break
        if screenshot:pygame.image.save(self.canvas,screenshot)
        pygame.quit()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--smoke',action='store_true');parser.add_argument('--screenshot');parser.add_argument('--save-dir')
    args=parser.parse_args()
    if args.self_test:
        from .selftest import run
        run()
        return
    if args.smoke:os.environ['SDL_VIDEODRIVER']='dummy'
    app=App(args.save_dir)
    if args.smoke:
        app.state=new_career(42);app.v=view(app.state);app.screen='Overview'
    app.run(frames=3 if args.smoke else None,screenshot=args.screenshot)
