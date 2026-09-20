"""Search routes through public snapshots; results never execute transactions."""
SCREENS=('Overview','Inbox','Squad','Staff','Recruitment','Contracts','Transfers','Commercial',
         'Academy','Facilities','Finances','League','Fixtures','Matchday','Career','Settings','Help','Activity')
HELP={
    'staff people recruitment interview appointment delegation responsibilities approvals authority capacity':'Staff',
    'cash budget payroll funding forecast':'Finances',
    'registration eligibility suspension injury fitness training':'Squad',
    'signing renewal bonus option release employment':'Contracts',
    'transfer purchase sale loan recall instalment':'Transfers',
    'scouting reports potential shortlist comparison':'Recruitment',
    'intake academy youth promotion':'Academy',
    'stadium building construction stand facilities':'Facilities',
    'sponsor naming rights commercial':'Commercial',
    'save recovery keyboard accessibility zoom':'Help',
}


def search(v,query):
    q=query.strip().casefold();rows=[]
    for screen in SCREENS:
        if not q or q in screen.casefold() or any(q in terms and route==screen for terms,route in HELP.items()):
            rows.append(dict(label=screen+' / department',screen=screen,player=None))
    if q:
        for p in sorted(v['players'],key=lambda p:(p['name'].casefold(),p['id'])):
            if q in p['name'].casefold():
                rows.append(dict(label=p['name']+' / '+p['role']+' / '+('your club' if p['club']=='c0' else 'player'),
                                 screen='Squad' if p['club']=='c0' else 'Recruitment',player=p['id']))
        for c in v['clubs']:
            if q in c['name'].casefold():rows.append(dict(label=c['name']+' / league club',screen='League',player=None))
    return rows


class NavigationScreens:
    def open_search(self):
        self.play=False;self.batch=False;self.typing=False;self.palette='';self.palette_typing=True
        self.palette_page=0;self.focus=0;self.focus_reveal=True

    def search_route(self,row):
        self.palette=None;self.nav(row['screen'])
        if row['player']:self.open_profile(row['player'])
        self.focus_reveal=True

    def draw_search(self):
        import pygame
        from .ui import WIDTH,HEIGHT,MUTED,TEXT
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA);overlay.fill((0,0,0,195));self.canvas.blit(overlay,(0,0))
        self.buttons=[];self.help_regions=[];self.panel(300,145,840,626,'Search the club')
        self.button('Search: '+(self.palette or 'people, departments, help'),(325,202,790,48),lambda:setattr(self,'palette_typing',True))
        rows=search(self.v,self.palette);start=self.palette_page*6
        for i,row in enumerate(rows[start:start+6]):
            self.button(row['label'][:75],(325,272+i*61,790,49),lambda row=row:self.search_route(row))
        if not rows:self.wrap('No known person or department matches. Try a surname, registration, contracts or cash.',325,287,760,25,TEXT)
        self.button('Previous',(325,663,135,42),lambda:setattr(self,'palette_page',max(0,self.palette_page-1)),self.palette_page>0)
        self.button('Next',(475,663,115,42),lambda:setattr(self,'palette_page',self.palette_page+1),start+6<len(rows))
        self.button('Close',(975,663,140,42),lambda:setattr(self,'palette',None))
        self.text('Search opens a screen. It never signs an agreement or spends money.',325,730,21,MUTED)

    def change_zoom(self,value=None):
        levels=(1,1.25,1.5,1.75)
        self.ui_zoom=value if value in levels else levels[(levels.index(self.ui_zoom)+1)%len(levels)]
        self.pan=[0,0];self.focus_reveal=True;self.save_preferences()

    def fit_viewport(self):
        """Zoom the complete layout without clipping text inside its controls.

        Overflow is navigable with wheel/Shift+wheel. Keyboard focus and dialogs
        pan into view, and Ctrl+0 always restores the full interface.
        """
        from .ui import WIDTH,HEIGHT
        scale=min(self.window.get_width()/WIDTH,self.window.get_height()/HEIGHT)*self.ui_zoom
        w,h=round(WIDTH*scale),round(HEIGHT*scale)
        overflow=[max(0,w-self.window.get_width()),max(0,h-self.window.get_height())]
        if self.focus_reveal and self.buttons:
            rect=self.buttons[self.focus%len(self.buttons)][0]
            for axis,(start,end,view_size) in enumerate(((rect.left,rect.right,self.window.get_width()),(rect.top,rect.bottom,self.window.get_height()))):
                lo=start*scale;hi=end*scale
                if lo<self.pan[axis]+20:self.pan[axis]=lo-20
                if hi>self.pan[axis]+view_size-20:self.pan[axis]=hi-view_size+20
            self.focus_reveal=False
        self.pan=[max(0,min(overflow[i],self.pan[i])) for i in (0,1)]
        offset=(max(0,(self.window.get_width()-w)//2)-round(self.pan[0]),max(0,(self.window.get_height()-h)//2)-round(self.pan[1]))
        return scale,(w,h),offset
