"""Drive the real contract workflow for integration tests."""
def prepare_signings(case, ids):
    for pid in ids:
        p=next(p for p in case.s['players'] if p['id']==pid)
        case.act('enquire',id=pid)
        case.act('propose_offer',id=pid,wage=p['wage'],fee=p['fee'],duration=2)
        case.act('accept_offer',id=pid)
    while any(case.s['career']['offers'][pid]['status']=='medical' for pid in ids) or case.s['match']:
        if case.s['match']:
            case.act('match_skip') if not case.s['match'].get('finished',case.s['match']['minute']>=90) else case.act('match_close')
        elif case.s['decision']:case.act('decision',choice='decline')
        else:case.act('continue')
