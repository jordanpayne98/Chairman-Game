"""Recruitment and development screens consume authorised snapshots only."""
from .career_ui import money, GREEN, MUTED
from .planning import dated
from .playing_time import ROLES


class DevelopmentScreens:
    def development_tab(self,key,value):
        setattr(self,key,value);self.page=0;self.pathway_player=None

    def open_scouting(self):
        self.tab='Scouting';self.scouting_tab='Brief';self.page=0

    def scout_saved(self):
        ids=self.v['planning']['shortlist'][:12]
        rows=[p for p in self.v['players'] if p['id'] in ids and p['scout_quote'] and not p['scout_due']]
        total=sum(p['scout_quote']['cost'] for p in rows)
        self.confirm('Commission saved targets',f"Review up to twelve targets. Maximum immediate cost {money(total)}. Staff capacity determines each start and due date. Unavailable targets are skipped without charge; individual outcomes appear in Batch results.",lambda:self.command('scout_batch',ids=ids))

    def draw_scouting(self,x):
        v=self.v;w=v['scouting_work'];tab=getattr(self,'scouting_tab','Brief')
        self.button('< Recruitment',(x,190,220,42),lambda:self.development_tab('tab','Recruitment'))
        for i,label in enumerate(('Brief','Queue','Batch results','Outcomes')):
            self.button(label,(x+235+i*205,190,195,42),lambda label=label:self.development_tab('scouting_tab',label))
        self.text('SCOUTING / Paid observations, dated evidence',x,254,26,GREEN)
        if tab=='Brief':
            if not getattr(self,'brief_draft',None):self.brief_draft=dict(w['brief'] or dict(role='MID',min_age=16,max_age=30,ceiling=25000000,playing_role='Rotation'))
            d=self.brief_draft
            def cycle(key,choices):d[key]=choices[(choices.index(d[key])+1)%len(choices)] if d[key] in choices else choices[0]
            self.button('Position: '+d['role'],(x,298,180,40),lambda:cycle('role',('GK','DEF','MID','FWD')))
            self.button('Age 16–'+str(d['max_age']),(x+195,298,170,40),lambda:cycle('max_age',(21,25,30,35,40)))
            self.button(d['playing_role'],(x+380,298,235,40),lambda:cycle('playing_role',tuple(ROLES)))
            self.button('Cost '+money(d['ceiling']),(x+630,298,220,40),lambda:cycle('ceiling',(5000000,10000000,15000000,25000000,50000000)))
            self.button('Save brief',(x+865,298,220,40),lambda:self.command('recruitment_brief',**{k:d[k] for k in ('role','min_age','max_age','ceiling','playing_role')}))
            self.wrap('Estimated first-year fees and wages; final negotiations may differ. Recommendations use existing reports. Search never creates players.',x,357,1090,21,MUTED)
            rows=w['recommendations']
            for i,r in enumerate(rows[self.page*4:self.page*4+4]):
                y=421+i*82;self.panel(x,y,1400-x,74)
                self.text(f"{r['name']} / {r['rating'][0]}–{r['rating'][1]} / {money(r['cost'])}",x+15,y+9,24)
                self.text(f"{r['knowledge']} / {dated(v,r['day'])} / Position and age fit; terms unconfirmed",x+15,y+43,20,MUTED)
                self.button('Dossier',(1180,y+15,200,40),lambda r=r:self.open_profile(r['id']))
            if not rows:self.wrap('Save a brief and commission reports on suitable targets. No observed candidates currently meet this brief.',x+15,430,1030,25)
            self.button('Scout saved targets',(1120,790,280,42),self.scout_saved,bool(v['planning']['shortlist']) and not v['match'] and not v['season_done'])
            self.pager(x,790,len(rows),4);return
        rows=list(reversed(w['jobs'] if tab=='Queue' else w['history'] if tab=='Batch results' else w['signings']))
        size=4 if tab=='Outcomes' else 5
        for i,r in enumerate(rows[self.page*size:self.page*size+size]):
            y=310+i*(110 if size==4 else 90);self.panel(x,y,1400-x,100 if size==4 else 80)
            p=next((p for p in v['players'] if p['id']==r['player']),None);name=p['name'] if p else r['player']
            self.text(name,x+15,y+10,25)
            if tab=='Queue':
                paid='Legacy payment retained' if r['legacy'] else 'Paid '+money(r['cost'])
                self.text(f"{r['status'].upper()} / {r['observer']} / Starts {dated(v,r['start'])} / Due {dated(v,r['due'])} / {paid}",x+15,y+45,20,MUTED)
            elif tab=='Batch results':self.wrap(('Commissioned: ' if r['ok'] else 'Skipped: ')+r['message'],x+15,y+43,1050,20,MUTED)
            else:
                self.text(f"Signed {dated(v,r['day'])} / {r['role']} / {money(r['wage'])} weekly",x+15,y+42,21,MUTED)
                self.text(f"Since signing: {r['subsequent_appearances']} appearances / {r['subsequent_goals']} goals / Brief: "+(r['brief']['role'] if r['brief'] else 'None'),x+15,y+70,21,MUTED)
        if not rows:self.text('No recorded activity yet.',x+15,325,25,MUTED)
        self.pager(x,790,len(rows),size)

    def draw_pathways(self,x):
        v=self.v;w=v['pathways'];tab=getattr(self,'pathway_tab','Players')
        self.button('< Academy',(x,190,220,42),lambda:self.development_tab('tab','Academy'))
        for i,label in enumerate(('Players','Development fixtures','Loans','Tables')):
            self.button(label,(x+235+i*205,190,195,42),lambda label=label:self.development_tab('pathway_tab',label))
        self.text('PATHWAYS / Evidence, minutes and recovery',x,254,26,GREEN)
        pid=getattr(self,'pathway_player',None)
        if pid and tab in ('Players','Loans'):self.draw_pathway_player(x,next(p for p in w['players'] if p['id']==pid));return
        if tab=='Tables':
            group=getattr(self,'development_group','Youth');self.button(group,(x,303,220,40),lambda:setattr(self,'development_group','Reserves' if group=='Youth' else 'Youth'))
            for j,label in enumerate(('P','Pts','GF','GA')):self.text(label,x+570+j*105,313,22,MUTED)
            rows=w['tables'][group]
            for i,r in enumerate(rows[self.page*8:self.page*8+8]):
                y=363+i*46;self.text(self.club(r['club']),x+15,y,24)
                for j,k in enumerate(('played','points','gf','ga')):self.text(str(r[k]),x+570+j*105,y,24)
            self.pager(x,790,len(rows),8);return
        if tab=='Development fixtures':rows=sorted(w['fixtures'],key=lambda f:(f['day']<v['day'],abs(f['day']-v['day']),f['id']))
        else:rows=sorted([p for p in w['players'] if tab=='Players' or p['loan']],key=lambda p:(p['age'],p['id']))
        for i,p in enumerate(rows[self.page*5:self.page*5+5]):
            y=312+i*88;self.panel(x,y,1400-x,78)
            if tab=='Development fixtures':
                score='–'.join(map(str,p['result'])) if p['result'] is not None else p['status']
                self.text(f"{dated(v,p['day'])} / {p['group']} / {self.club(p['home'])} {score} {self.club(p['away'])}",x+15,y+10,23)
                self.text(p['reason'] or 'Separate development records; no senior appearance or goal credit.',x+15,y+46,20,MUTED)
            else:
                self.text(f"{p['name']} / Age {p['age']} / {p['group']}",x+15,y+10,25)
                r=p['review'];self.text((f"{r['minutes']} recent minutes / {r['route']} / "+dated(v,r['day'])) if r else 'First staff review due at the next monthly checkpoint.',x+15,y+45,21,MUTED)
                self.button('Development detail',(1150,y+18,230,40),lambda p=p:setattr(self,'pathway_player',p['id']))
        if not rows:self.text('No records for this view yet.',x+15,325,25,MUTED)
        self.pager(x,790,len(rows),5)

    def draw_pathway_player(self,x,p):
        v=self.v;r=p['review'];self.text(p['name']+' / '+p['group'],x,315,30)
        self.button('Player dossier',(1150,302,230,40),lambda:(self.nav('Squad' if p['club']=='c0' else 'Recruitment'),self.open_profile(p['id'])))
        self.wrap(f"Age {p['age']} / {money(p['wage'])} weekly / Agreement ends {dated(v,p['end'])}",x,363,1100,23,MUTED)
        if r:
            self.text(f"{r['author']} / {dated(v,r['day'])} / {r['coaching']}",x,410,23,GREEN)
            self.wrap(f"{r['route']}: {r['reason']} Recent minutes: {r['minutes']}.",x,450,1070,24)
        else:self.wrap('The first monthly staff review has not been completed.',x,423,1070,24)
        owned=p['club']=='c0';active=owned and not v['match']
        self.button('Apply advice',(x,550,230,42),lambda:self.confirm('Apply development advice','Apply the proposed focus, load and reserve group if recommended. Renewal, promotion and loan changes require their own review.',lambda:self.command('pathway_accept',id=p['id'])),bool(r) and active)
        if not p['youth']:
            group='Reserves' if p['group']=='Seniors' else 'Seniors'
            self.button('Assign '+group,(x+250,550,250,42),lambda:self.confirm('Change training group','Assign '+group+'. Contract and selection commitments remain as agreed.',lambda:self.command('pathway_group',id=p['id'],group=group)),active)
        else:
            end=v['contract_ends']['3'];cost=p['wage']*max(0,end-p['end'])//7
            self.button('Review renewal',(x+250,550,250,42),lambda:self.confirm('Renew academy agreement',f"Keep {money(p['wage'])} weekly until {dated(v,end)}. Approximately {money(cost)} additional guaranteed wages. No signing fee. Requires current wage authority and four weeks of available cash cover.",lambda:self.command('academy_renew',id=p['id'])),active and 0<=p['end']-v['day']<=28)
        if p['loan']:self.button('Review loan',(x+520,550,220,42),lambda:(self.nav('Transfers'),self.market_section('Loans')),owned or p['loan']['source']=='c0')
        for i,h in enumerate(p['history'][-3:]):self.text(f"{dated(v,h['day'])} / {h['minutes']} minutes / {h['focus']} / {h['load']}",x+15,631+i*42,23,MUTED)

    def draw_world_calendar(self,x):
        v=self.v;w=v['world_calendar'];tab=getattr(self,'world_tab','Calendar')
        self.button('< Competitions',(x,190,220,42),lambda:self.development_tab('tab','League'))
        for i,label in enumerate(('Calendar','Population','Reconciliation','Database')):
            self.button(label,(x+235+i*205,190,195,42),lambda label=label:self.development_tab('world_tab',label))
        title='Shared recovery rules / cutoff '+dated(v,w['cutoff']) if w['active'] else f"Legacy season retained / shared rules activate in season {w['activation']}"
        self.text(title,x,254,24,GREEN)
        if tab=='Database':self.draw_world_database(x);return
        if tab=='Calendar':
            self.text(f"{w['minimum_rest_days']} recovery days / {w['conflicts']} world scheduling conflicts / {len(w['blackouts'])} blackout days",x,293,22,MUTED)
            rows=w['fixtures'];size=4
            for i,f in enumerate(rows[self.page*size:self.page*size+size]):
                y=335+i*91;self.panel(x,y,1400-x,81)
                self.clipped_text(f"{dated(v,f['day'])} / {f['group']} / {self.club(f['home'])} v {self.club(f['away'])}",x+15,y+12,1100,23)
                self.clipped_text(f['reason'] or f['status'].capitalize(),x+15,y+47,1100,20,MUTED)
            self.wrap('Cup dates are reserved before each draw. Continental and international tournaments are not yet available in this development world.',x,712,1110,21,MUTED)
        elif tab=='Population':
            c=w['population']['counts']
            self.text(f"Active {c['active']} / Free {c['free']} / Retired or inactive {c['retired']}",x,295,23,MUTED)
            self.text('CLUB',x+15,341,20,MUTED)
            for i,label in enumerate(('Youth','Reserves','Seniors','Keepers')):self.text(label,x+600+i*125,341,20,MUTED)
            rows=w['population']['clubs'];size=7
            for i,r in enumerate(rows[self.page*size:self.page*size+size]):
                y=386+i*45;self.clipped_text(self.club(r['club']),x+15,y,560,24)
                for j,k in enumerate(('youth','reserves','seniors','keepers')):self.text(str(r[k]),x+600+j*125,y,24)
            self.wrap('Counts reflect persistent people in this saved world. Empty groups are visible; full launch rosters and sustainable replacement policies remain in development.',x,718,1110,21,MUTED)
        else:
            audit=w['audit'];rows=audit['changes'] if audit else [];size=4
            if audit:self.text(f"Season {audit['season']} / {audit['before']} people before / {audit['after']} after",x,295,23,MUTED)
            else:self.wrap('The first population reconciliation is recorded when you prepare the next season. No historical changes have been invented.',x,305,1080,25)
            for i,r in enumerate(rows[self.page*size:self.page*size+size]):
                y=344+i*92;self.panel(x,y,1400-x,80)
                self.text(r['name'],x+15,y+10,24)
                self.clipped_text(r['action']+' / '+(self.club(r['club']) if r['club'] else 'No club'),x+15,y+44,1100,21,MUTED)
        self.pager(x,790,len(rows),size)
