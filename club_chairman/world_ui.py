"""Browse authorised world read models; detailed ratings require assessment."""
from .planning import dated
from .theme import GREEN,MUTED
from . import world_population


class WorldScreens:
    def world_country(self,nid):
        self.world_nation=nid;self.world_browser='People';self.page=0;self.world_person=None

    def world_market_person(self,row):
        def done():
            if self.command('world_person_activate',id=row['id']):
                if row['kind']=='player':self.nav('Recruitment');self.open_profile(row['id'])
                else:self.nav('Staff')
        self.confirm('Add to recruitment','Add '+row['name']+' to your recruitment candidates? They are unattached. Scouting and employment terms are reviewed separately.',done)

    def draw_world_database(self,x):
        w=self.v['world_population'];tab=getattr(self,'world_browser','Nations')
        if not w['enabled']:
            self.wrap('This career predates the worldwide population. Create its persistent database to add non-playable countries, player and staff careers, and future intakes. Existing identities and contracts stay intact.',x,305,1100,26)
            self.button('Create world database',(x,460,320,44),lambda:self.confirm('Create world population','Build the worldwide population once for this career. This may take several seconds. Existing people are preserved and the new population begins today.',lambda:self.command('world_population_enable')),not self.v['match']);return
        total=w['manifest']['people'];counts=w['manifest']['counts'];regions=['All','Europe','South America','North America','Asia','Africa','Oceania']
        self.text(f"{len(w['nations'])} countries and territories / {total:,} recorded people / Updated {dated(self.v,w['last_day'])}",x,286,22,MUTED)
        recent=w.get('recent_cycles',[])
        if recent:self.text(f"Latest world cycle: {recent[-1].get('transfers',0)} employed transfers / {recent[-1]['signings']} free signings",x,311,17,MUTED)
        if tab=='Nations':
            region=getattr(self,'world_region','All')
            self.button('Region: '+region,(x,330,330,40),lambda:(setattr(self,'world_region',regions[(regions.index(region)+1)%len(regions)]),setattr(self,'page',0)))
            rows=sorted([n for n in w['nations'] if region=='All' or n['region']==region],key=lambda n:n['name'])
            for i,n in enumerate(rows[self.page*10:self.page*10+10]):
                col=i%2;line=i//2;xx=x+col*580;y=395+line*72;c=counts[n['id']]
                self.button(n['name'],(xx,y,300,42),lambda n=n:self.world_country(n['id']))
                self.text(f"{c['players']:,} players / {c['staff']:,} staff",xx+315,y+5,18,MUTED)
                self.text('Planned playable nation' if n['playable'] else 'Supporting nation',xx+315,y+28,16,MUTED)
            self.pager(x,790,len(rows),10);return
        nid=getattr(self,'world_nation','england');nation=next(n for n in w['nations'] if n['id']==nid)
        kind=getattr(self,'world_kind','player');only=getattr(self,'world_available',False)
        self.button('< Countries',(x,330,180,40),lambda:(setattr(self,'world_browser','Nations'),setattr(self,'world_person',None),setattr(self,'page',0)))
        self.button('Players' if kind=='player' else 'Staff',(x+195,330,170,40),lambda:(setattr(self,'world_kind','staff' if kind=='player' else 'player'),setattr(self,'world_person',None),setattr(self,'page',0)))
        self.button('Unattached only' if only else 'All active people',(x+380,330,240,40),lambda:(setattr(self,'world_available',not only),setattr(self,'world_person',None),setattr(self,'page',0)))
        self.text(nation['name'],x+645,340,24,GREEN)
        key=(self.v['revision'],self.v['day'],w['manifest']['sha256'],nid,kind,only,self.page)
        if getattr(self,'world_query_key',None)!=key:
            self.world_query=world_population.search(self.state,nid,kind,page=self.page,available_only=only);self.world_query_key=key
        data=self.world_query;selected=getattr(self,'world_person',None)
        row=next((r for r in data['rows'] if r['id']==selected),None)
        if row:
            self.panel(x,393,1400-x,339)
            self.text(row['name'],x+18,412,30,GREEN)
            self.text(f"Age {row['age']} / {row['nationality']} / {row['role']} / {row['group']}",x+18,455,23)
            self.clipped_text(row['club'] or 'Unattached',x+18,497,1090,24,MUTED)
            if row['contract_end'] is not None:self.text('Contract ends '+dated(self.v,row['contract_end']),x+18,535,21,MUTED)
            for i,event in enumerate(row['history'][-4:]):self.clipped_text(dated(self.v,event['day'])+' / '+event.get('summary',event['event']),x+18,575+i*31,1100,20,MUTED)
            self.button('Back to people',(x,790,220,42),lambda:setattr(self,'world_person',None))
            self.button('Add to recruitment',(x+240,790,270,42),lambda:self.world_market_person(row),row['available'] and not self.v['match'])
            self.wrap('Ability and potential are not assessed. Only unattached people can currently be added to recruitment.',x+545,785,600,20,MUTED);return
        for i,r in enumerate(data['rows']):
            y=395+i*45;self.clipped_text(r['name'],x+10,y,330,22)
            self.text(f"{r['age']} / {r['role']}",x+350,y,20,MUTED)
            self.clipped_text(r['club'] or 'Unattached',x+565,y,345,20,MUTED)
            self.button('History',(1220,y-7,170,36),lambda r=r:setattr(self,'world_person',r['id']))
        self.pager(x,790,data['total'],8)
