"""Role conversations and dated evidence in the established player profile."""
from .playing_time import ROLES
from .planning import dated
from .theme import GREEN, MUTED, RED, TEXT


class PlayingTimeScreens:
    def role_discuss(self,p,role):
        self.confirm('Discuss '+role+'?',
            'This is a working commitment, not a selection order. The player can refuse a reduction. '
            'Existing evidence and concerns remain. Changes to an existing role are discussed on its review day. '
            'You can reopen a role conversation after one review period.',
            lambda:self.command('discuss_playing_role',id=p['id'],role=role))

    def draw_playing_time(self,x,p):
        state=self.v['playing_time'];cfg=state['settings'];row=state['agreements'].get(p['id'])
        self.panel(x,441,660,350,'Working agreement / senior league and cup')
        right=x+680;self.panel(right,441,1400-right,350,'Explicit role conversation')
        if row:
            self.text(row['role'],x+20,488,28,GREEN)
            indicator=f"{row['target']}% of available {'fixtures with meaningful starts' if row['metric']=='starts' else '90-minute opportunities'}"
            self.wrap(indicator,x+20,527,620,21)
            self.text('Next review '+dated(self.v,row['next_review'])+f" / {row['review_days']}-day window",x+20,581,20,MUTED)
            self.text('Unresolved shortfall' if row['concern'] else 'No unresolved shortfall',x+20,611,21,RED if row['concern'] else GREEN)
            reviews=list(reversed(row['reviews']));self.page=min(self.page,max(0,len(reviews)-1))
            if reviews:
                r=reviews[self.page]
                self.wrap(dated(self.v,r['day'])+': '+r['outcome']+f". {r['starts']} meaningful starts, {r['minutes']} minutes / {r['fixtures']} available fixtures; {r['excused']} excused. Agreed: {r['role']}.",x+20,646,620,20)
                self.button('< Review',(x+20,748,135,30),lambda:setattr(self,'page',self.page-1),self.page>0)
                self.text(f'{self.page+1}/{len(reviews)}',x+190,752,18,MUTED)
                self.button('Review >',(x+290,748,135,30),lambda:setattr(self,'page',self.page+1),self.page<len(reviews)-1)
            else:self.wrap('Collecting new evidence; no past promise or missed minutes has been inferred.',x+20,653,620,21,MUTED)
        else:
            self.wrap('No current role agreement. Discuss one explicitly, or include it in new employment terms. Old contracts have no invented promises.',x+20,491,620,24)
            old=[r for r in state['history'] if r['player']==p['id']]
            if old:self.wrap('Last agreement closed: '+old[-1]['closure']+' / '+dated(self.v,old[-1]['closed']),x+20,627,620,22,MUTED)
        for i,role in enumerate(ROLES):
            self.button(role,(right+18,489+i*42,1364-right,34),lambda role=role:self.role_discuss(p,role),
                p['club']=='c0' and not p.get('loan') and not self.v['match'] and (not row or row['role']!=role))
        talks=[r for r in state['conversations'] if r['player']==p['id']]
        self.wrap(talks[-1]['response'] if talks else 'Selection stays with the manager. Token cameos cannot satisfy a starting role.',right+18,706,1364-right,19,MUTED)
        self.wrap('Injury, suspension and medical fitness excuse missed fixtures. Omission from the competition list does not. The agreed minimum of available fixtures is required for a verdict. Thresholds are provisional.',x,802,1400-x,18,MUTED)

    def cycle_playing_role(self):
        options=[None,*ROLES];old=self.offer_draft.get('playing_role')
        self.offer_draft['playing_role']=options[(options.index(old)+1)%len(options)]
        self.save_preferences()

    def draw_role_offer(self,x,o,terms,editable):
        self.panel(x,360,1400-x,370,'Playing-time commitment / begins on completed employment')
        role=terms.get('playing_role')
        self.button('Role: '+(role or 'No new commitment'),(x+24,415,460,42),self.cycle_playing_role,editable)
        cfg=self.v['playing_time']['settings']
        metric=ROLES[role][0] if role else 'minutes'
        target=cfg[role.lower().replace(' ','_')] if role else 0
        text=(f"{target}% {'meaningful starts in available fixtures' if metric=='starts' else 'of available 90-minute opportunities'}. " if role else '')
        self.wrap(text+f"Reviews cover senior domestic league and cup in {cfg['review_days']}-day windows, requiring {cfg['minimum_fixtures']} available fixtures. A meaningful start requires {cfg['meaningful_minutes']} minutes. Injury, suspension and fitness exceptions apply. These thresholds are provisional.",x+24,485,1345-x,24)
        self.wrap('The player considers positional capacity and unresolved delivery concerns. Incompatible promises receive no recruitment credit. Submit terms to record the response. Renewals preserve existing commitments and evidence; discuss a different role in the profile first.',x+24,615,1345-x,23,MUTED)
