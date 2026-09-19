"""Packaged-build smoke test of one complete connected career."""
import tempfile
from pathlib import Path
from .simulation import new_career, execute, Command, validate
from .persistence import save, load


def run():
    s=new_career(71)
    def act(action,**data):
        nonlocal s
        s,_=execute(s,Command(f"smoke:{s['revision']}",s['revision'],action,data))
    act('budget',value=4000000);act('hire',id='m1');act('scout',id='p145')
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
                    resumed=True
                act('match_step',minutes=90)
            else:act('match_close')
        else:act('continue')
    validate(s)
    if not all(c['played']==14 for c in s['clubs']):raise RuntimeError('Incomplete season')
    if not signed or not resumed:raise RuntimeError('Missing signing or match resume')
    print('Packaged career smoke passed: hiring, scouting, signing, intervention, mid-match save/resume, 56 league fixtures, season settlement.')
