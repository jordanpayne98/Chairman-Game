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
    act('staff_contact',id='staff:0:0');delegated=False
    act('development_plan',id='p4',focus='Technical',load='Light')
    act('registration_submit',players=list(s['registration']['c0']))
    act('planning',key='shortlist',value=['p145']);act('planning',key='comparison',value=['p145'])
    act('planning',key='notes',value={'p145':'Scout before committing.'})
    snapshot=view(s);target=next(p for p in snapshot['players'] if p['id']=='p145')
    if signing_terms(snapshot,[target])['reasons']:raise RuntimeError('Unexpected recruitment restriction')
    if forecast(snapshot,[target])['cash']>=forecast(snapshot)['cash']:raise RuntimeError('Signing costs missing from forecast')
    # Exercise the new departments in the actual executable as well as unit tests.
    act('club_enquire',id='p20');deal=next(reversed(s['market']['deals'].values()))
    act('club_propose',id=deal['id'],fee=deal['fee'],upfront_percent=50,defer_days=28,sell_on_kind='profit',sell_on_percent=10)
    act('club_accept',id=deal['id']);act('enquire',id='p20')
    target=next(p for p in s['players'] if p['id']=='p20')
    act('propose_offer',id='p20',wage=target['wage'],fee=target['fee'],duration=3,appearance_bonus=2500,goal_bonus=5000,club_option=True);act('accept_offer',id='p20')
    act('loan_enquire',id='p2',club='c1');loan_deal=next(reversed(s['market']['deals'].values()))
    act('loan_terms',id=loan_deal['id'],share=75,days=56);act('market_accept',id=loan_deal['id'])
    act('sale_enquire',id='p3',club='c2');sale_deal=next(reversed(s['market']['deals'].values()));act('market_accept',id=sale_deal['id'])
    act('sponsor_enquire',right='digital');act('sponsor_propose',right='digital',weekly=80000,weeks=16);act('sponsor_accept',right='digital')
    act('academy_intake')
    youth=max((p for p in s['players'] if p['youth']),key=lambda p:p['age'])
    act('academy_admit',id=youth['id'])
    if youth['age']>=16:act('academy_promote',id=youth['id'])
    act('project_plan',kind='training')
    signed=False;resumed=False;offered=False
    for season in (1,2):
        while not s['season_done']:
            if s['match'] is None:
                appointment=s['staff']['offers']['staff:0:0']
                if appointment['status']=='contact' and s['day']>=appointment['interview_due']:
                    employee=next(p for p in s['staff']['people'] if p['id']=='staff:0:0')
                    act('staff_interview',id=employee['id'])
                    act('staff_propose',id=employee['id'],wage=employee['expected_wage']*12//10,duration=3,autonomy='Advisory')
                    act('staff_accept',id=employee['id'])
                if not delegated and next(p for p in s['staff']['people'] if p['id']=='staff:0:0')['club']=='c0':
                    for key in ('executive','recruitment'):
                        act('delegation_set',key=key,delegate='staff:0:0',mode='Autonomous',limit=8000000,days=365,objective='Maintain')
                    delegated=True
                if s['career']['offers']['p20']['status']=='ready':
                    act('complete_offer',id='p20');act('exercise_option',id='p20')
                for key in (loan_deal['id'],sale_deal['id']):
                    if s['market']['deals'][key]['status']=='ready':act('market_complete',id=key)
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
                if not s['match'].get('finished',s['match']['minute']>=90):
                    if not resumed:
                        act('match_step',minutes=20);act('intervene',choice='attack')
                        with tempfile.TemporaryDirectory() as tmp:
                            path=Path(tmp)/'smoke.sqlite3';save(s,path);s=load(path)
                        if s['planning']['notes'].get('p145')!='Scout before committing.':raise RuntimeError('Planning save failed')
                        resumed=True
                    act('match_skip')
                else:act('match_close')
            else:act('continue')
        validate(s)
        if not all(c['played']==14 for c in s['clubs']):raise RuntimeError('Incomplete season')
        if s['match']:act('match_close')
        if season==1:act('manager_replace',id='m2',duration=2);act('next_season')
    if not signed or not resumed:raise RuntimeError('Missing contract completion or match resume')
    if len(s['career']['history'])!=1 or s['career']['projects'][0]['status']!='operational':raise RuntimeError('Missing archive or project milestone')
    if len([e for e in s['ledger'] if e['reason']=='League prize'])!=2:raise RuntimeError('Incorrect season settlement')
    if s['market']['deals'][deal['id']]['status']!='completed' or s['market']['obligations'][0]['status']!='paid':raise RuntimeError('Transfer or instalment did not complete')
    if s['market']['loans'][0]['status']!='returned':raise RuntimeError('Loan did not return')
    if s['commercial']['contracts'][0]['paid']!=1280000:raise RuntimeError('Sponsorship schedule did not settle exactly')
    if s['clauses']['employment']['p20']['option_status']!='exercised':raise RuntimeError('Club option was not exercised')
    if not s['clauses']['payables'] or any(b['amount']!=b['paid'] for b in s['clauses']['payables']):raise RuntimeError('Earned bonuses failed to settle')
    if s['clauses']['sell_on'][0]['percent']!=10:raise RuntimeError('Sell-on right was lost')
    p=next(p for p in s['players'] if p['id']=='p4')
    if not p['development']['history'] or p['development']['focus']!='Technical':raise RuntimeError('Development plan or history was lost')
    results=[f['result'] for f in s['fixtures']]
    if not all(m['engine']==2 and m['finished'] for m in results):raise RuntimeError('Football match did not finish')
    if not any(any(e['kind']=='substitution' for e in m['events']) for m in results):raise RuntimeError('Manager substitutions missing')
    if not delegated or not any(e['action']=='decision' for e in s['delegation']['log']):raise RuntimeError('Staff recruitment or autonomous club decisions missing')
    if not any(d['status']=='completed' for d in s['club_ai']['decisions']):raise RuntimeError('Rival club recruitment did not complete')
    print('Packaged career check passed: staff interviews and contracts, delegated decisions, rival recruitment, football rules and substitutions, registration, development, bonuses, options, sell-on rights, transfers, instalments, loans, sponsorship, two seasons, academy, facilities, manager replacement, save/resume and 112 fixtures.')
