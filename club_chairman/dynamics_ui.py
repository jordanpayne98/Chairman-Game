"""Club dynamics evidence and actionable private concerns."""
from .theme import GREEN,MUTED,TEXT,BORDER
from .planning import dated


class DynamicsScreens:
    def dynamics_section(self,section):
        self.dynamics_tab=section;self.page=0

    def dynamics_player(self,pid):
        self.open_profile(pid);self.profile_tab='Relationship';self.page=0

    def dynamics_meeting(self,row,approach):
        self.confirm('Private staff follow-up',approach+' / '+row['name']+'. Hear the concern and record the response. '
            'A conversation does not guarantee repaired trust or change selection authority.',
            lambda:self.command('dynamics_followup',id=row['person'],approach=approach))

    def draw_dynamics(self,x):
        import pygame
        data=self.v['dynamics'];summary=data['summary'];tab=getattr(self,'dynamics_tab','Concerns')
        self.button('Back to squad',(x,190,200,40),lambda:(setattr(self,'tab','Squad'),setattr(self,'page',0)))
        for i,label in enumerate(('Concerns','Connections','Staff reactions','Meetings')):
            self.button(('• ' if tab==label else '')+label,(x+215+i*220,190,210,40),lambda label=label:self.dynamics_section(label))
        self.panel(x,249,1400-x,146,'First-team cohesion / '+dated(self.v,self.v['day']))
        value=summary['value'];label=summary['label']+(f' / {value:.0f}' if value is not None else '')
        self.text(label,x+20,294,28,GREEN)
        self.text(summary['trend'],x+370,300,22,MUTED)
        self.text(f"{summary['covered']}/{summary['total']} player relationships observed",x+600,300,22,MUTED)
        pygame.draw.rect(self.canvas,BORDER,(x+20,337,400,7),border_radius=3)
        if value is not None:pygame.draw.rect(self.canvas,GREEN,(x+20,337,round(4*value),7),border_radius=3)
        self.text('Social evidence only. Mood and tactical practice are separate; unseen links are not excellent relationships.',x+20,359,18,MUTED)
        if tab=='Concerns':
            rows=data['concerns'];size=3
            self.page=min(self.page,max(0,(len(rows)-1)//size))
            for i,row in enumerate(rows[self.page*size:self.page*size+size]):
                y=413+i*116;self.panel(x,y,1400-x,106)
                self.text(row['name'],x+18,y+12,24)
                self.clipped_text(row['reason'],x+18,y+43,650,21,MUTED)
                self.clipped_text(row['action'],x+18,y+73,650,18,MUTED)
                if row['kind']=='player':self.button('Review privately',(1150,y+32,225,40),lambda row=row:self.dynamics_player(row['person']))
                else:
                    self.button('Listen',(1115,y+12,260,36),lambda row=row:self.dynamics_meeting(row,'Listen'),row['can_meet'])
                    self.button('Respect remit',(1115,y+57,260,36),lambda row=row:self.dynamics_meeting(row,'Respect remit'),row['can_meet'])
            if not rows:self.wrap('No recorded unresolved concerns. Private player conversations do not automatically spread to teammates. Monthly reviews arrive in the inbox.',x+20,453,1010,27,MUTED)
        elif tab=='Connections':
            rows=data['players'];size=4;self.page=min(self.page,max(0,(len(rows)-1)//size))
            for i,row in enumerate(rows[self.page*size:self.page*size+size]):
                y=413+i*87;self.panel(x,y,1400-x,78)
                self.text(row['name'],x+18,y+12,23)
                self.text(f"{row['settling']} / {row['days']} observed training days",x+18,y+43,19,MUTED)
                self.text(row['influence'],x+500,y+12,22,GREEN)
                self.text(f"{row['contacts']} connections / {row['sessions']} shared sessions (most familiar pair)",x+500,y+43,18,MUTED)
        elif tab=='Staff reactions':
            rows=[dict(day=e['day'],**r) for e in reversed(data['events']) if e['kind']=='bench' for r in e['reactions']];size=3
            self.page=min(self.page,max(0,(len(rows)-1)//size))
            for i,row in enumerate(rows[self.page*size:self.page*size+size]):
                y=413+i*116;self.panel(x,y,1400-x,106)
                self.text(row['name']+' / '+dated(self.v,row['day']),x+18,y+12,23)
                self.text('Football: '+row['football'],x+18,y+44,21,GREEN)
                self.text('Process: '+row['process'],x+18,y+75,20,MUTED)
            if not rows:self.wrap('No witnessed bench conversations recorded. Reactions belong to the manager and available coaching staff who heard the request; other departments and players are not assumed to know.',x+20,453,1010,27,MUTED)
        else:
            rows=list(reversed(data['meetings']));size=3;self.page=min(self.page,max(0,(len(rows)-1)//size))
            for i,row in enumerate(rows[self.page*size:self.page*size+size]):
                y=413+i*116;self.panel(x,y,1400-x,106)
                self.text(row['name']+' / '+row['approach']+' / '+dated(self.v,row['day']),x+18,y+12,23)
                self.wrap(row['response'],x+18,y+46,1020,23,MUTED)
            if not rows:self.text('Completed staff follow-ups appear here.',x+20,453,24,MUTED)
        self.pager(x,788,len(rows),size)
