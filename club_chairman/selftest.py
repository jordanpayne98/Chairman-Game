"""Packaged-build check of two connected seasons and management workflows."""
import tempfile
from pathlib import Path
from .simulation import new_career, execute, Command, validate, view
from .persistence import save, load
from .planning import forecast, signing_terms


def run():
    s=new_career(71)
    def act(action,**data):
        nonlocal s
        s,_=execute(s,Command(f"smoke:{s['revision']}",s['revision'],action,data))
    act('budget',value=4000000);act('hire',id='m1');act('scout',id='p145')
    act('planning',key='shortlist',value=['p145']);act('planning',key='comparison',value=['p145'])
    act('planning',key='notes',value={'p145':'Scout before committing.'})
    snapshot=view(s);target=next(p for p in snapshot['players'] if p['id']=='p145')
    if signing_terms(snapshot,[target])['reasons']:raise RuntimeError('Unexpected recruitment restriction')
    if forecast(snapshot,[target])['cash']>=forecast(snapshot)['cash']:raise RuntimeError('Signing costs missing from forecast')
    act('academy_intake')
    youth=max((p for p in s['players'] if p['youth']),key=lambda p:p['age'])
    act('academy_admit',id=youth['id'])
    if youth['age']>=16:act('academy_promote',id=youth['id'])
    act('project_plan',kind='training')
    signed=False;resumed=False;offered=False
    for season in (1,2):
        while not s['season_done']:
            project=s['career']['projects'][0]
            if project['status']=='quoted' and s['match'] is None:act('project_approve',id=project['id'])
            if not offered and 'p145' in s['reports'] and s['match'] is None:
                act('enquire',id='p145')
                p=next(p for p in s['players'] if p['id']=='p145')
                act('propose_offer',id='p145',wage=round(p['wage']*1.1),fee=p['fee'],duration=3)
                act('accept_offer',id='p145');offered=True
            if offered and not signed and s['career']['offers']['p145']['status']=='ready' and s['match'] is None:
                act('complete_offer',id='p145');signed=True
            if s['decision']:act('decision',choice='approve')
            elif s['match']:
                if s['match']['minute']<90:
                    if not resumed:
                        act('match_step',minutes=20);act('intervene',choice='attack')
                        with tempfile.TemporaryDirectory() as tmp:
                            path=Path(tmp)/'smoke.sqlite3';save(s,path);s=load(path)
                        if s['planning']['notes'].get('p145')!='Scout before committing.':raise RuntimeError('Planning save failed')
                        resumed=True
                    act('match_step',minutes=90)
                else:act('match_close')
            else:act('continue')
        validate(s)
        if not all(c['played']==14 for c in s['clubs']):raise RuntimeError('Incomplete season')
        if s['match']:act('match_close')
        if season==1:act('manager_replace',id='m2',duration=2);act('next_season')
    if not signed or not resumed:raise RuntimeError('Missing contract completion or match resume')
    if len(s['career']['history'])!=1 or s['career']['projects'][0]['status']!='operational':raise RuntimeError('Missing archive or project milestone')
    if len([e for e in s['ledger'] if e['reason']=='League prize'])!=2:raise RuntimeError('Incorrect season settlement')
    print('Packaged career check passed: two seasons, negotiations, reservations, academy, completed project, manager replacement, save/resume and 112 fixtures.')
