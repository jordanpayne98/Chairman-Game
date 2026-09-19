"""Packaged-build smoke test of one complete connected career."""
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
    act('planning',key='shortlist',value=['p145'])
    act('planning',key='comparison',value=['p145'])
    act('planning',key='notes',value={'p145':'Scout before committing.'})
    snapshot=view(s);target=next(p for p in snapshot['players'] if p['id']=='p145')
    if signing_terms(snapshot,[target])['reasons']:raise RuntimeError('Unexpected recruitment restriction')
    if forecast(snapshot,[target])['cash']>=forecast(snapshot)['cash']:raise RuntimeError('Signing costs missing from forecast')
    signed=False;resumed=False
    while not s['season_done']:
        if not signed and 'p145' in s['reports']:
            act('sign',id='p145');signed=True
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
    if not signed or not resumed:raise RuntimeError('Missing signing or match resume')
    print('Packaged career smoke passed: planning, forecasts, hiring, scouting, signing, intervention, mid-match save/resume, 56 league fixtures, season settlement.')
