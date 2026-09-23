"""Opening cup allocation and knockout conservation checks (no draw generation)."""
from datetime import date


def welsh_cup_admission_issues(evidence, rules):
    """Check authored opening eligibility facts, without posting cash or history.

    Rule 7 requires the fee with the application, not merely before the draw.
    Association acceptance is an explicit setup fact, never inferred from tier.
    Ground suitability is checked separately against the actual entry round.
    """
    if not isinstance(evidence, dict):
        return ['Missing opening admission facts.']
    issues=[]
    if evidence.get('basis')!='initial_database_assessment':
        issues.append('Admission must use an explicit opening assessment.')
    if (evidence.get('association')!=rules.get('association_jurisdiction')
            or evidence.get('all_football_under_association') is not True
            or evidence.get('team_category')!='mens'):
        issues.append('Club is outside the competition jurisdiction/category.')
    if evidence.get('association_accepted') is not True:
        issues.append('Association acceptance is missing or refused.')
    application=evidence.get('application',{})
    fee=evidence.get('entry_fee',{})
    if not isinstance(application,dict):application={}
    if not isinstance(fee,dict):fee={}
    try:
        deadline=date.fromisoformat(rules['deadline'])
        submitted=date.fromisoformat(application['received_on'])
        settled=date.fromisoformat(fee['settled_on'])
        if submitted>deadline:issues.append('Application received after the entry deadline.')
        if settled>submitted:issues.append('Entry fee was not settled with the application.')
    except (KeyError,TypeError,ValueError):
        issues.append('Admission dates are missing or invalid.')
    if application.get('complete') is not True:
        issues.append('Entry application is incomplete.')
    amount=fee.get('amount_pence')
    if (type(amount) is not int or amount!=rules.get('entry_fee_pence')
            or fee.get('currency')!=rules.get('currency')
            or fee.get('settled') is not True):
        issues.append('Required entry fee is not settled in the correct amount/currency.')
    if fee.get('accounting_basis')!='included_in_opening_balances':
        issues.append('Opening fee accounting basis is missing.')
    return issues


def audit_cup_allocation(cup, allocation, known_clubs, tier_members):
    errors=[];prefix=str(cup.get('id'))
    cohorts=allocation.get('entry_rounds',{})
    if allocation.get('competition')!=cup.get('id') or allocation.get('basis')!='initial_database_allocation':
        return [prefix+': missing explicit opening cup allocation.']
    entrants=[club for cohort in cohorts.values() for club in cohort]
    if (len(entrants)!=cup.get('entrant_count') or len(entrants)!=len(set(entrants))
            or set(entrants)!=set(allocation.get('club_ids',[]))
            or len(allocation.get('club_ids',[]))!=len(entrants)
            or not set(entrants)<=set(known_clubs)):
        errors.append(prefix+': cup entrant identities/count do not reconcile.')
    counts=cup.get('entry_counts',{})
    if set(counts)!=set(cohorts) or any(len(cohorts.get(rid,[]))!=count for rid,count in counts.items()):
        errors.append(prefix+': cup entry-round counts do not reconcile.')
    rounds=cup.get('rounds',[]);round_ids=[r.get('id') for r in rounds]
    if not rounds or len(set(round_ids))!=len(round_ids) or not set(cohorts)<=set(round_ids):
        errors.append(prefix+': invalid cup round definitions.')
        return errors
    survivors=0
    for round_def in rounds:
        incoming=round_def.get('new_entries');count=round_def.get('entrants');ties=round_def.get('ties')
        if (type(count) is not int or type(incoming) is not int or type(ties) is not int
                or count<2 or count%2 or incoming!=counts.get(round_def['id'],0)
                or count!=survivors+incoming or ties!=count//2):
            errors.append(prefix+': round progression does not conserve entrants.')
            return errors
        survivors=ties
    if survivors!=1:errors.append(prefix+': cup does not end with one winner.')
    if cup.get('id')=='wales-national-cup-2026':
        # The dated source specifies tier-specific entry, not just total counts.
        t1=set(tier_members.get(1,[]));t2=set(tier_members.get(2,[]));t3=set(tier_members.get(3,[]))
        p2=allocation.get('tier_two_priority',[]);p3=allocation.get('tier_three_priority',[])
        if (len(p2)!=32 or len(set(p2))!=32 or set(p2)!=t2
                or len(p3)!=64 or len(set(p3))!=64 or set(p3)!=t3):
            errors.append(prefix+': opening tier seed priorities do not reconcile.')
        expected={'qualifying_1':232,'qualifying_2':4,'round_1':28,'round_2':20}
        if (counts!=expected or set(cohorts.get('round_2',[]))!=t1|set(p2[:4])
                or set(cohorts.get('round_1',[]))!=set(p2[4:])
                or set(cohorts.get('qualifying_2',[]))!=set(p3[:4])
                or not (t3-set(p3[:4]))<=set(cohorts.get('qualifying_1',[]))
                or (t1|t2)&set(cohorts.get('qualifying_1',[]))):
            errors.append(prefix+': tier-specific entry rounds violate the sourced allocation.')
    return errors


def welsh_cup_ground_issues(facilities, round_id):
    """Rules 13.1/13.2: current venue suitability, separate from club admission."""
    rounds=('qualifying_1','qualifying_2','round_1','round_2','round_3','round_4',
            'quarter_final','semi_final','final')
    if round_id not in rounds:return ['Unknown cup round.']
    issues=[]
    for field in ('paid_admission','goal_nets','separate_team_changing_and_showers',
                  'separate_official_changing_and_showers','association_accepted_walking_distance'):
        if facilities.get(field) is not True:issues.append('Ground requirement missing: '+field+'.')
    permitted=('rope','rail','wall') if round_id.startswith('qualifying_') else ('rail','wall')
    if facilities.get('spectator_barrier') not in permitted:
        issues.append('Ground spectator barrier is unsuitable for this round.')
    if not round_id.startswith('qualifying_') and facilities.get('private_dressing_area_toilets') is not True:
        issues.append('Private dressing-area toilets are required from round one.')
    return issues
