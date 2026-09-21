"""Persistent manager candidates, assessed ability and bounded tactical adjustment."""
from copy import deepcopy
import math
from . import staff

CANDIDATES = [dict(id='m0', name='Alex Rowan', style='Balanced', skill=58, wage=140000, fee=150000, autonomy=.2),
              dict(id='m1', name='Morgan Vale', style='Attacking', skill=70, wage=240000, fee=300000, autonomy=.6),
              dict(id='m2', name='Casey Holt', style='Cautious', skill=64, wage=190000, fee=200000, autonomy=.4)]
WEIGHTS=dict(tactical_judgement=.30,coaching=.20,people_management=.15,
             ability_assessment=.10,youth_development=.05,adaptability=.20)
DEFAULTS=dict(review_minute=65,judgement_threshold=40,chase_risk=1.22,protect_risk=.90,
              short_handed_risk=.85,change_threshold=.015)


def enrich(s,p):
    from .simulation import rng_for
    rng=rng_for(s['seed'],'manager-capabilities:'+p['id'])
    p.setdefault('capabilities',{key:max(1,min(100,p['skill']+rng.randint(-18,18))) for key in staff.CAPABILITIES})
    p.setdefault('preferences',dict(style=p['style'],formation='4-4-2',
                                    risk=1.12 if p['style']=='Attacking' else .92 if p['style']=='Cautious' else 1.))


def initialise(s):
    cfg=s['config'].setdefault('managers',{})
    cfg.setdefault('weights',deepcopy(WEIGHTS))
    for key,value in DEFAULTS.items():cfg.setdefault(key,value)
    data=s.setdefault('managers',dict(people=deepcopy(CANDIDATES),assessments={}))
    for p in data['people']:enrich(s,p)
    if s['manager']:enrich(s,s['manager'])


def candidate(s,pid):
    return next((p for p in s['managers']['people'] if p['id']==pid),None)


def archive_current(s):
    if s['manager']:
        p=candidate(s,s['manager']['id'])
        p['capabilities']=deepcopy(s['manager']['capabilities'])
        p['preferences']=deepcopy(s['manager']['preferences'])
        context,person=assessment_context(s,s['manager'])
        # Leaving ends live club access, but never erases observed capabilities.
        # Retain dated evidence without granting access to future hidden changes.
        s['managers']['assessments'][p['id']]=dict(day=s['day'],
            source='Club observations at departure',knowledge='Partial',
            **staff.current_ratings(context,person))


def assessment_context(s,p):
    # Reuse staff's exact/partial/stale rules without adding a departmental post,
    # payroll entry or delegation authority for the already contracted manager.
    cfg=dict(s['config'],staff=dict(s['config']['staff'],weights={'Manager':s['config']['managers']['weights']}))
    context=dict(s,config=cfg,staff=dict(assessments=s['managers']['assessments']))
    owned=s['manager'] and s['manager']['id']==p['id']
    actual=s['manager'] if owned else p
    return context,dict(actual,role='Manager',club='c0' if owned else None)


def view(s,p):
    context,person=assessment_context(s,p)
    result={key:deepcopy(person[key]) for key in ('id','name','style','wage','fee','autonomy','preferences')}
    for key in ('contract_end','notice_weeks'):
        if key in person:result[key]=person[key]
    result['assessment']=staff.observed_assessment(context,person)
    return result


def apply(s,action,data):
    if action!='manager_assess':return None
    from .simulation import require
    require(s['match'] is None,'Manager interviews pause during matchday.')
    p=candidate(s,data.get('id'));require(p is not None,'Unknown manager candidate.')
    context,person=assessment_context(s,p)
    staff.assess(context,person,6,complete=True)
    return f"Manager interview and references completed. Current capability coverage lasts {s['config']['staff']['full_coverage_days']} days."


def plan(s):
    p=s['manager']
    return dict(manager=p['id'],baseline=p['preferences']['risk'],
                capabilities=deepcopy(p['capabilities']),settings=deepcopy(s['config']['managers']))


def adjustment(m,side):
    """Judgement selects a response; Adaptability coordinates its risk instruction.

    The preferred plan survives unchanged. This first pathway does not claim
    formation changes, personality inference or instant tactical familiarity.
    """
    p=m['manager_plan'];cfg=p['settings'];skills=p['capabilities']
    if skills['tactical_judgement']<cfg['judgement_threshold']:return None
    short=len(m['on_pitch'][side])<len(m['on_pitch'][1-side])
    if short:
        target=cfg['short_handed_risk'];reason='covers the numerical disadvantage'
    elif m['minute']>=cfg['review_minute']:
        difference=m['score'][side]-m['score'][1-side]
        target=cfg['chase_risk'] if difference<0 else cfg['protect_risk'] if difference>0 else p['baseline']
        reason='chases the score' if difference<0 else 'protects the lead' if difference>0 else 'returns to the preferred approach'
    else:return None
    desired=round(p['baseline']+(target-p['baseline'])*skills['adaptability']/100,6)
    if abs(desired-m['risk'][side])<cfg['change_threshold']:return None
    return desired,reason


def validate(s):
    from .simulation import require
    cfg=s['config']['managers'];weights=cfg['weights']
    require(bool(weights) and all(k in staff.CAPABILITIES and type(w) in (int,float) and math.isfinite(w) and w>=0 for k,w in weights.items()) and abs(sum(weights.values())-1)<1e-8 and weights.get('adaptability',0)>0,'Invalid manager ability weights.')
    require(type(cfg['review_minute']) is int and 45<=cfg['review_minute']<=90,'Invalid manager review time.')
    require(type(cfg['judgement_threshold']) is int and 1<=cfg['judgement_threshold']<=100,'Invalid manager judgement threshold.')
    for key in ('chase_risk','protect_risk','short_handed_risk','change_threshold'):
        require(type(cfg[key]) in (int,float) and math.isfinite(cfg[key]) and 0<cfg[key]<=2,'Invalid manager tactical setting.')
    people=s['managers']['people']+([s['manager']] if s['manager'] else [])
    require(len({p['id'] for p in s['managers']['people']})==len(s['managers']['people']),'Duplicate manager identity.')
    for p in people:
        require(set(p['capabilities'])==set(staff.CAPABILITIES) and all(type(v) in (int,float) and math.isfinite(v) and 1<=v<=100 for v in p['capabilities'].values()),'Invalid manager capability.')
        require(type(p['preferences']['risk']) in (int,float) and .5<=p['preferences']['risk']<=1.5,'Invalid manager risk preference.')
