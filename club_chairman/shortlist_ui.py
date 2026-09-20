"""Named-list controls using the existing modal, input and undo conventions."""
from copy import deepcopy
import pygame
from .shortlists import active, MAX_NAME, MAX_LISTS
from .theme import BG, GREEN, BORDER, MUTED, TEXT


class ShortlistScreens:
    def shortlist_name(self):return active(self.v['planning'])['name']

    def open_shortlists(self):
        self.play=False;self.batch=False;self.typing=False
        self.list_manager=True;self.list_name='';self.list_typing=False;self.list_page=0;self.focus=0

    def manage_shortlist(self,operation,**payload):
        before=deepcopy(self.v['planning']['shortlists'])
        if self.command('shortlist_manage',operation=operation,**payload):
            self.undo=(self.state['revision'],'shortlists',before)
            self.page=0
            if operation in ('create','rename'):self.list_name='';self.list_typing=False
            if operation=='create':self.list_page=(len(self.v['planning']['shortlists']['items'])-1)//4
            return True
        return False

    def close_shortlists(self):
        if self.list_name:
            self.confirm('Discard the unfinished list name?','Your saved lists remain unchanged. Cancel returns to the name you were typing.',lambda:setattr(self,'list_manager',False))
        else:self.list_manager=False

    def save_shortlist_page(self):
        old=list(self.v['planning']['shortlist'])
        ids=[p['id'] for p in self.filtered_players()[self.page*7:self.page*7+7] if p['id'] not in old]
        def commit():
            if self.command('planning',key='shortlist',value=old+ids):
                self.undo=(self.state['revision'],'shortlist',old)
                self.message=f'Saved {len(ids)} players to {self.shortlist_name()}. No time or money spent.'
        self.confirm('Save visible page to '+self.shortlist_name()+'?',
            f'Add {len(ids)} new players from this page only. Existing entries are kept. No other search results are selected. Scouting and contract offers require separate actions.',commit)

    def delete_shortlist(self):
        item=active(self.v['planning'])
        self.confirm('Delete '+item['name']+'?',
            f"Remove this private list and its {len(item['players'])} saved links? Players, reports, notes and other lists are unchanged. Undo is available immediately after deletion.",
            lambda:self.manage_shortlist('delete',id=item['id']))

    def draw_shortlists(self):
        overlay=pygame.Surface((1440,900),pygame.SRCALPHA);overlay.fill((0,0,0,185));self.canvas.blit(overlay,(0,0))
        self.buttons=[];self.help_regions=[];self.panel(270,160,900,635,'Recruitment shortlists')
        self.wrap('Select a list for the table and profile actions. A player can belong to several lists. Saved links survive transfers and retirement.',300,215,820,21)
        data=self.v['planning']['shortlists'];items=data['items'];last=(len(items)-1)//4
        self.list_page=min(self.list_page,last)
        for index,item in enumerate(items[self.list_page*4:self.list_page*4+4]):
            y=283+index*48;selected=item['id']==data['active']
            self.button(('• ' if selected else '')+item['name'],(300,y,570,40),lambda sid=item['id']:self.manage_shortlist('select',id=sid))
            self.text(f"{len(item['players'])} saved",895,y+9,21,GREEN if selected else MUTED)
        self.button('< Lists',(300,483,120,35),lambda:setattr(self,'list_page',self.list_page-1),self.list_page>0)
        self.text(f'{self.list_page+1} / {last+1}',440,490,20,MUTED)
        self.button('Lists >',(525,483,120,35),lambda:setattr(self,'list_page',self.list_page+1),self.list_page<last)
        self.button('Delete selected',(915,483,225,35),self.delete_shortlist,len(items)>1)
        self.text('New name (32 characters maximum)',300,538,20,MUTED)
        pygame.draw.rect(self.canvas,BG,(300,567,520,45),border_radius=5)
        pygame.draw.rect(self.canvas,GREEN if self.list_typing else BORDER,(300,567,520,45),1,border_radius=5)
        self.clipped_text(self.list_name+('|' if self.list_typing else ''),312,579,495,21,TEXT)
        self.buttons.append((pygame.Rect(300,567,520,45),lambda:setattr(self,'list_typing',True),True))
        self.button('Create list',(835,567,145,45),lambda:self.manage_shortlist('create',name=self.list_name.strip()),len(items)<MAX_LISTS)
        self.button('Rename',(995,567,145,45),lambda:self.manage_shortlist('rename',id=data['active'],name=self.list_name.strip()))
        self.wrap('Type a name, then Tab to Create list or Rename. Enter never submits while typing. Planning changes do not advance time or spend money.',300,627,825,20)
        self.clipped_text(self.message,300,688,825,19,GREEN)
        self.button('Close',(990,738,150,40),self.close_shortlists)
        if self.undo and self.undo[0]==self.state['revision']:
            self.button('Undo',(300,738,140,40),self.undo_planning)

    def shortlist_event(self,event):
        if not self.list_manager or self.modal or event.type!=pygame.KEYDOWN:return False
        if event.key==pygame.K_0 and event.mod&pygame.KMOD_CTRL:
            self.change_zoom(1);return True
        if event.key==pygame.K_F2:
            self.explain_focus=not self.explain_focus;return True
        if event.key==pygame.K_ESCAPE:
            if self.explain_focus:self.explain_focus=False
            else:self.close_shortlists()
        elif event.key==pygame.K_TAB:
            self.list_typing=False;self.focus=(self.focus+(-1 if event.mod&pygame.KMOD_SHIFT else 1))%max(1,len(self.buttons));self.focus_reveal=True
        elif self.list_typing:
            if event.key==pygame.K_BACKSPACE:self.list_name=self.list_name[:-1]
            elif event.key==pygame.K_RETURN:pass
            elif event.unicode.isprintable() and len(self.list_name)<MAX_NAME:self.list_name+=event.unicode
        elif event.key==pygame.K_RETURN and self.buttons:
            _,fn,enabled=self.buttons[self.focus%len(self.buttons)]
            if enabled:fn()
        return True
