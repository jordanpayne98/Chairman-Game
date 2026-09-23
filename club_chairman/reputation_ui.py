"""Read-only reputation evidence on the established panel and navigation system."""
from .planning import dated
from .theme import GREEN, MUTED, TEXT


class ReputationScreens:
    def reputation_open(self,kind='clubs',key='c0'):
        self.nav('Reputation');self.reputation_kind=kind;self.reputation_entity=key;self.reputation_page=0;self.page=0

    def reputation_select(self,kind,key):
        self.reputation_kind=kind;self.reputation_entity=key;self.reputation_page=0

    def reputation_detail(self,x,y,w,h,rec,name=None):
        self.panel(x,y,w,h)
        self.clipped_text((name+' / domestic standing') if name else 'Domestic standing / public career evidence',x+20,y+16,w-40,21,MUTED)
        self.text(f"{rec['value']} / 100",x+20,y+48,34,GREEN)
        self.text(f"Last change {rec['trend']:+d} / "+dated(self.v,rec['day']),x+190,y+60,20,MUTED)
        base=rec['baseline']
        self.wrap(f"Baseline {base['value']}/100 on {dated(self.v,base['day'])}. "+base['source'],x+20,y+99,w-40,19,MUTED)
        rows=list(reversed(rec['reviews']));count=1 if h<450 else 2;maximum=max(0,(len(rows)-1)//count)
        self.reputation_page=max(0,min(self.reputation_page,maximum))
        if not rows:self.wrap('No eligible new evidence has been reviewed. Old achievements are not inferred; lack of minutes does not automatically reduce standing.',x+20,y+178,w-40,23)
        for i,row in enumerate(rows[self.reputation_page*count:self.reputation_page*count+count]):
            top=y+168+i*103
            self.text(dated(self.v,row['day'])+f" / Season {row['season']} / {row['before']} → {row['after']} ({row['change']:+d})",x+20,top,20,GREEN if row['change']>0 else TEXT)
            summary=row['summary']
            if row['evidence'].get('club'):summary+=' / '+self.club(row['evidence']['club'])
            self.wrap(summary,x+20,top+29,w-40,21,TEXT)
        self.button('< Evidence',(x+20,y+h-50,145,36),lambda:setattr(self,'reputation_page',self.reputation_page-1),self.reputation_page>0)
        self.text(f'{self.reputation_page+1} / {maximum+1}',x+183,y+h-40,20,MUTED)
        self.button('Evidence >',(x+w-165,y+h-50,145,36),lambda:setattr(self,'reputation_page',self.reputation_page+1),self.reputation_page<maximum)

    def draw_reputation(self,x):
        v=self.v;kind=self.reputation_kind;groups=(('clubs','Clubs'),('leagues','Leagues'),('cups','Domestic cup'))
        for i,(key,label) in enumerate(groups):
            self.button(('• ' if kind==key else '')+label,(x+i*200,190,190,40),lambda key=key:(self.reputation_select(key,None),setattr(self,'page',0)))
        coverage=v['reputation_coverage']
        self.text('Evidence since '+dated(v,coverage['start'])+' / next scheduled review '+dated(v,coverage['next_review']),x,248,21,MUTED)
        names={c['id']:c['name'] for c in v['clubs']}
        names.update({d['id']:d['name'] for d in v['leagues']['divisions']})
        cup=v['competitions']['cup']
        if cup:names[cup['id']]=cup['name']
        records=v['reputation'][kind];ids=sorted(records,key=lambda key:(-records[key]['value'],names.get(key,key)))
        if not ids:self.wrap('No competition exists in this career yet.',x,305,1000,25);return
        selected=self.reputation_entity if self.reputation_entity in records else ids[0]
        self.panel(x,282,430,480,'Public standing / separate from ability')
        self.page=min(self.page,max(0,(len(ids)-1)//6))
        for i,key in enumerate(ids[self.page*6:self.page*6+6]):
            y=338+i*60;rec=records[key]
            self.clipped_text(names.get(key,key),x+18,y,280,22,GREEN if key==selected else TEXT)
            self.text(f"{rec['value']}/100",x+18,y+26,18,MUTED)
            self.button('Evidence',(x+304,y,110,37),lambda key=key:self.reputation_select(kind,key))
        self.pager(x,779,len(ids),6)
        right=x+447;self.reputation_detail(right,282,1400-right,480,records[selected],names.get(selected,selected))
        self.wrap('Gradual, bounded reviews affect recruitment interest. Provisional baselines and tuning remain uncalibrated. No direct ability or match bonus.',right,778,1400-right,19,MUTED)
