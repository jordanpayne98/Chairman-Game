"""Private club mood evidence with keyboard-accessible reasons."""
from .planning import dated
from .theme import TEXT,MUTED,GREEN,RED


class MoraleScreens:
    def draw_morale(self,x,p):
        mood=self.v['mood']['players'].get(p['id'])
        if mood is None:
            self.wrap('Private mood information is unavailable outside current club access.',x,460,1000,26,MUTED);return
        right=x+700
        self.panel(x,441,680,340,'Player morale / '+dated(self.v,self.v['day']))
        self.text(f"{mood['band']} / {mood['value']:.0f}",x+20,487,28,GREEN)
        self.text(mood['trend'],x+365,490,21,MUTED)
        import pygame
        from .theme import BORDER
        pygame.draw.rect(self.canvas,BORDER,(x+20,530,630,8),border_radius=3)
        pygame.draw.rect(self.canvas,GREEN,(x+20,530,round(630*mood['value']/100),8),border_radius=3)
        rows=mood['reasons'];self.page=min(self.page,max(0,(len(rows)-1)//3))
        for i,row in enumerate(rows[self.page*3:self.page*3+3]):
            y=551+i*59
            self.clipped_text(('Ongoing concern' if row['ongoing'] else row['direction']+' reaction')+' / '+dated(self.v,row['start']),x+20,y,630,18,RED if row['direction']=='Negative' else GREEN)
            self.wrap(row['reason'],x+20,y+22,630,18,TEXT)
        if not rows:self.wrap('Neutral reference: no active recorded causes. Earlier events are not inferred.',x+20,558,620,24,MUTED)
        self.button('< Reasons',(x+20,742,145,30),lambda:setattr(self,'page',self.page-1),self.page>0)
        self.text(f'{self.page+1}/{max(1,(len(rows)+2)//3)}',x+194,746,18,MUTED)
        self.button('Reasons >',(x+270,742,145,30),lambda:setattr(self,'page',self.page+1),self.page<(len(rows)-1)//3)
        squad=self.v['mood']['squad'];counts=squad['counts']
        self.panel(right,441,1400-right,340,'Current first team')
        self.text(squad['band'],right+18,488,27,GREEN)
        self.wrap(f"{counts['unhappy']} unhappy / {counts['content']} content / {counts['happy']} happy",right+18,531,1364-right,20)
        self.wrap(f"{squad['trend']} / {squad['compared']} shared players compared over seven days",right+18,585,1364-right,20,MUTED)
        membership=('Collecting membership history' if squad['arrivals'] is None else f"{squad['arrivals']} arrivals / {squad['departures']} departures in seven days")
        self.wrap(membership+f". {squad['concerns']} players have ongoing concerns. Includes injured players; excludes loaned-out players and academy.",right+18,645,1364-right,20,MUTED)
        self.button('Review playing time',(x,801,250,38),lambda:(setattr(self,'profile_tab','Playing time'),setattr(self,'page',0)))
        self.button('Private support',(x+270,801,220,38),lambda:(setattr(self,'profile_tab','Relationship'),setattr(self,'page',0)))
        self.wrap('Mood affects execution once.',x+515,805,580,20,MUTED)

    def support_meeting(self,p,approach):
        self.confirm('Private player meeting',
            approach+' to '+p['name']+'. This is a private conversation with no promised selection. '
            'The player may remain unconvinced. Existing concerns require actual fulfilment; '
            'repeating a conversation cannot repair them.',
            lambda:self.command('support_player',id=p['id'],approach=approach))

    def draw_relationship(self,x,p):
        row=self.v['relationships'].get(p['id'])
        if row is None:
            self.wrap('No authorised private relationship evidence.',x,460,1000,26,MUTED);return
        right=x+700
        self.panel(x,441,680,340,'Private relationship with the chairman')
        self.text(row['assessment'],x+20,488,27,GREEN)
        self.text('Evidence from recorded contact; no hidden scores',x+20,529,20,MUTED)
        events=list(reversed(row['events']));self.page=min(self.page,max(0,(len(events)-1)//2))
        for i,event in enumerate(events[self.page*2:self.page*2+2]):
            y=565+i*77
            self.text(dated(self.v,event['day'])+' / '+event['kind'].capitalize(),x+20,y,19,GREEN)
            self.wrap(event['reason'],x+20,y+24,630,20,TEXT)
        if not events:self.wrap('No previous meetings or relationship outcomes are inferred. A first meeting starts the record.',x+20,566,630,23,MUTED)
        self.button('< Evidence',(x+20,742,145,30),lambda:setattr(self,'page',self.page-1),self.page>0)
        self.text(f'{self.page+1}/{max(1,(len(events)+1)//2)}',x+194,746,18,MUTED)
        self.button('Evidence >',(x+270,742,145,30),lambda:setattr(self,'page',self.page+1),self.page<(len(events)-1)//2)
        self.panel(right,441,1400-right,340,'Private support')
        self.button('Listen to concerns',(right+18,490,1364-right,38),lambda:self.support_meeting(p,'Listen'),row['can_meet'])
        self.button('Offer encouragement',(right+18,543,1364-right,38),lambda:self.support_meeting(p,'Encourage'),row['can_meet'])
        text=('Earliest next meeting '+dated(self.v,row['next_day'])+'. A heard concern requires new circumstances.' if row['meetings'] else 'No previous support meeting.')
        self.wrap(text,right+18,604,1364-right,21,MUTED)
        self.wrap('Only you and this player know this conversation. Fulfilled commitments rebuild trust; a win or reassuring words cannot erase a breach.',right+18,682,1364-right,19,MUTED)
        self.button('Morale reasons',(x,801,220,38),lambda:(setattr(self,'profile_tab','Morale'),setattr(self,'page',0)))
        self.button('Review playing time',(x+240,801,250,38),lambda:(setattr(self,'profile_tab','Playing time'),setattr(self,'page',0)))
