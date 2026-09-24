"""Career creation wizard using the existing Executive controls."""
import pygame
import secrets
from . import career_setup, nations, identities
from .theme import MUTED,GREEN,TEXT
from .presentation import portrait


class SetupScreens:
    def open_setup(self):
        self.setup_seed=secrets.randbelow(1000000);self.setup_world=None;self.setup_filter=''
        self.setup_options=career_setup.defaults();self.setup_step=0;self.setup_field=None
        self.setup_scenario=self.new_scenario;self.setup_tier=1;self.setup_page=0
        self.play=False;self.batch=False;self.nav('Setup')

    def setup_cycle(self,key,values):
        current=self.setup_options[key];self.setup_options[key]=values[(values.index(current)+1)%len(values)]

    def setup_country(self,key):
        self.setup_scenario=key;self.setup_tier=1;self.setup_page=0;self.setup_options['club_index']=0

    def setup_reset(self):
        for k in ('sandbox','funding','reputation','facilities','confidence'):self.setup_options[k]=career_setup.defaults()[k]

    def setup_next(self):
        self.setup_field=None
        if self.setup_step==0:
            try:career_setup.validate_options(self.setup_options,self.setup_scenario)
            except ValueError as exc:self.message=str(exc);return
        if self.setup_step==3:
            from .simulation import new_career,validate
            try:
                self.setup_world=new_career(self.setup_seed,self.setup_scenario,dict(self.setup_options));validate(self.setup_world)
            except ValueError as exc:self.message='Cannot prepare career: '+str(exc);return
        self.setup_step=min(4,self.setup_step+1)

    def finish_setup(self):
        self.setup_field=None
        return self.start(self.setup_scenario,dict(self.setup_options),self.setup_world)

    def setup_key(self,event):
        if self.setup_field is None:return False
        if event.key in (pygame.K_RETURN,pygame.K_TAB,pygame.K_ESCAPE):self.setup_field=None;return True
        if self.setup_field=='nationality':
            if event.key==pygame.K_BACKSPACE:self.setup_filter=self.setup_filter[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.setup_filter)<40:self.setup_filter+=event.unicode
        elif event.key==pygame.K_BACKSPACE:self.setup_options['name']=self.setup_options['name'][:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.setup_options['name'])<40:self.setup_options['name']+=event.unicode
        return True

    def draw_setup(self):
        from .ui import money
        o=self.setup_options;step=self.setup_step
        self.heading('Create your career',100,65,44)
        self.text(' / '.join(('Owner','Country','Club','Sandbox','Review')),104,126,23,MUTED)
        self.text(f'Step {step+1} of 5',1170,126,23,GREEN)
        self.panel(104,195,1232,560)
        if self.setup_field=='nationality':
            self.text('Type to find your nationality: '+self.setup_filter,130,220,26)
            found=[n for n in identities.catalogue()['nations'] if self.setup_filter.casefold() in n['name'].casefold()]
            for i,n in enumerate(found[:9]):
                self.button(n['name'],(130,280+i*46,1050,39),lambda n=n:(o.update(nationality=n['id']),setattr(self,'setup_field',None)))
            self.button('Back to owner',(104,790,250,45),lambda:setattr(self,'setup_field',None))
            return
        if step==0:
            self.text('Your owner / chairman',130,220,30)
            portrait(self.canvas,'owner:'+str(o['portrait']),o['age'],(1060,285,180,220),None)
            self.button('Name: '+(o['name'] or 'Type your name'),(130,285,820,48),lambda:setattr(self,'setup_field','name'))
            self.text('Click the name, then type. Enter finishes editing.',130,344,20,GREEN if self.setup_field else MUTED)
            ns=identities.catalogue()['nations'];name=next(n['name'] for n in ns if n['id']==o['nationality'])
            self.button('Nationality: '+name,(130,388,820,45),lambda:(setattr(self,'setup_field','nationality'),setattr(self,'setup_filter','')))
            self.button('Age: '+str(o['age']),(130,454,390,45),lambda:self.setup_cycle('age',list(range(18,91))))
            self.button('Portrait: '+str(o['portrait']+1),(545,454,405,45),lambda:self.setup_cycle('portrait',list(range(8))))
            self.button('Background: '+o['background'],(130,520,820,45),lambda:self.setup_cycle('background',list(career_setup.BACKGROUNDS)))
            self.wrap('Your background describes your owner. It grants no hidden money or match advantage.',130,606,1020,23,MUTED)
        elif step==1:
            self.text('Where will you take charge?',130,220,30)
            options=[dict(id='compact',name='Compact development world',playable=True)]+nations.catalogue()['nations']
            for i,n in enumerate(options):
                col=i//8;row=i%8;label=('• ' if n['id']==self.setup_scenario else '')+n['name']+('' if n['playable'] else ' — background only')
                self.button(label,(130+col*595,275+row*49,565,40),lambda key=n['id']:self.setup_country(key),n['playable'])
            self.text('One active domestic pyramid; other nations retain background people.',130,697,22,MUTED)
        elif step==2:
            rows=career_setup.clubs(self.setup_scenario);tiers=sorted({c['tier'] for c in rows})
            self.button('Division '+str(self.setup_tier),(130,220,230,42),lambda:(setattr(self,'setup_tier',tiers[(tiers.index(self.setup_tier)+1)%len(tiers)]),setattr(self,'setup_page',0)))
            filtered=[c for c in rows if c['tier']==self.setup_tier]
            for i,c in enumerate(filtered[self.setup_page*7:self.setup_page*7+7]):
                label=('Selected: ' if c['index']==o['club_index'] else '')+c['name']
                self.button(label,(130,285+i*54,650,43),lambda c=c:o.update(club_index=c['index']))
            self.button('Previous',(130,689,170,38),lambda:setattr(self,'setup_page',max(0,self.setup_page-1)),self.setup_page>0)
            self.button('More clubs',(315,689,170,38),lambda:setattr(self,'setup_page',self.setup_page+1),(self.setup_page+1)*7<len(filtered))
            chosen=rows[o['club_index']]
            pr=career_setup.profile(self.setup_seed,self.setup_scenario,'c'+str(chosen['index']),chosen['tier'])
            self.wrap(chosen['name']+'\nDivision '+str(chosen['tier'])+f"\nReputation: {pr['reputation']}/100\nFacilities: {pr['facilities']}/5\nSenior squad: {pr['squad_size']}\nDepartments: {len(pr['roles'])}"+'\n\nYou inherit a manager and existing employment. Negotiated purchases and creating a club are not yet available.',820,285,465,25,MUTED)
        elif step==3:
            self.text('Starting conditions',130,220,30)
            self.button('Sandbox: '+('On' if o['sandbox'] else 'Off'),(130,282,510,45),lambda:self.setup_reset() if o['sandbox'] else o.update(sandbox=True))
            fields=[('funding','Extra club funding',[0,10000000,100000000,1000000000,10000000000]),('reputation','Club reputation',[0,25,50,75,90]),('facilities','Facilities',[0,1,2,3,4,5]),('confidence','Board confidence',[60,40,80,100])]
            for i,(key,label,values) in enumerate(fields):
                val=money(o[key]) if key=='funding' else str(o[key]) if o[key] else 'Club default'
                self.button(label+': '+val,(130,350+i*65,650,45),lambda k=key,v=values:self.setup_cycle(k,v),o['sandbox'])
            self.button('Reset to standard',(830,282,450,45),self.setup_reset)
            self.wrap('Sandbox careers are labelled. Extra funding is recorded in the club ledger.\n\nReputation and facilities affect the starting squad. Match rules and scouting uncertainty stay unchanged.\n\nConfidence sets initial board trust; it does not disable consequences.',830,360,450,23,MUTED)
        else:
            chosen=career_setup.clubs(self.setup_scenario)[o['club_index']]
            self.text('Review your career',130,220,30)
            nation=next(n['name'] for n in identities.catalogue()['nations'] if n['id']==o['nationality'])
            self.wrap(f"{o['name']} / {o['age']} / {nation}\n{o['background']}\n\n{chosen['name']} / Division {chosen['tier']}\nScenario: {self.setup_scenario}\nMode: {'Sandbox' if o['sandbox'] else 'Standard'}\nExtra club funding: {money(o['funding'])}\nReputation: {o['reputation'] or 'Club default'} / Facilities: {o['facilities'] or 'Club default'}\nBoard confidence: {o['confidence']}",130,280,800,26,TEXT)
            s=self.setup_world
            from .simulation import payroll
            self.wrap(f"Opening club cash: {money(s['cash'])}\nOwner cash: {money(s['owner_cash'])}\nWeekly payroll: {money(payroll(s))}\nWage authority: {money(s['budget'])}\nStart: {s['config']['start_date']}\nSeed: {s['seed']}\n\nWorld validated. Start saves this exact setup before Continue.",975,280,320,23,MUTED)
        self.button('Cancel',(104,790,160,45),lambda:(setattr(self,'setup_field',None),self.nav('Home')))
        if step:self.button('Previous step',(890,790,210,45),lambda:(setattr(self,'setup_field',None),setattr(self,'setup_step',step-1)))
        self.button('Start career' if step==4 else 'Next step',(1120,790,216,45),self.finish_setup if step==4 else self.setup_next)

    def draw_owner(self,x):
        o=self.v['owner']
        if not o:return
        portrait(self.canvas,'owner:'+str(o['portrait']),o['age'],(x+30,240,180,220),None)
        name=next(n['name'] for n in identities.catalogue()['nations'] if n['id']==o['nationality'])
        self.wrap(o['name']+'\n'+name+' / Age at career start: '+str(o['age'])+'\n'+o['background']+'\n\n'+self.club('c0')+'\n'+('Sandbox career' if self.v['career_setup']['customised'] else 'Standard career'),x+250,245,780,28,TEXT)
