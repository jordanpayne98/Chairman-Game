"""Build fixed original Welsh supporting identities and initial cup allocations.

Run deliberately during content production. Never called by career creation or
by a draw. Opening seed order is a database condition, not a past league table.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLACES={
    'north': 'Holyhead|Llangefni|Amlwch|Beaumaris|Menai Bridge|Bangor|Caernarfon|Bethesda|Llanberis|Penygroes|Porthmadog|Criccieth|Pwllheli|Nefyn|Harlech|Barmouth|Dolgellau|Bala|Conwy|Llandudno|Colwyn Bay|Rhyl',
    'south': 'Cardiff|Penarth|Barry|Newport|Cwmbran|Pontypool|Abergavenny|Chepstow|Monmouth|Caerphilly|Pontypridd|Merthyr Tydfil|Aberdare|Bridgend|Maesteg|Neath|Swansea|Llanelli|Carmarthen|Pembroke|Haverfordwest',
}
NAMES=('Willowgate','Reedcross','Ashweir','Stonefen','Coppergrove','Hazelbank',
       'Elmreach','Birchfold','Alderfield','Brookspire','Rowanbridge','Oakmere',
       'Cedarvale','Flintmeadow','Fernridge','Maplehaven')
COLORS=(('#234D66','#E5CD88'),('#663746','#E6DCCD'),('#2E5544','#EAE2BC'),
        ('#323E79','#D7DEE8'),('#823C28','#F0D4A5'),('#4C3A63','#D9C9E7'))
ROUND_WINDOWS=(('2026-07-24','2026-07-26'),('2026-08-21','2026-08-23'),
    ('2026-09-18','2026-09-20'),('2026-10-16','2026-10-18'),
    ('2026-11-13','2026-11-15'),('2026-12-11','2026-12-13'),
    ('2027-01-29','2027-01-31'),('2027-03-05','2027-03-07'),('2027-04-18','2027-04-18'))
CONFERENCE_DATES=('2026-07-25','2026-08-22','2026-09-19','2026-10-17',
                  '2026-11-13','2026-12-12','2027-01-30','2027-03-06','2027-04-18')


def complete_cup_operations(data,wales,cup,allocation):
    """Source-backed rules and explicit fictional association setup decisions."""
    sources=[dict(id='FAW-26-CUP-DATES',url='https://faw.cymru/news/faw-cup-conference-dates-2026-27/',
        article='Men\u2019s Welsh Cup conference dates',scope='All nine rounds; webpage wording retained alongside PDF windows.'),
        dict(id='FAW-26-CUP-DATES-PDF',url='https://d3ltsdzld9nilp.cloudfront.net/20260601102649/Cup-Conference-Dates-26-27.pdf',
        article='Page 1, Men\u2019s Welsh Cup',scope='Full Friday-to-Sunday permitted round windows; final 18 April.'),
        dict(id='FAW-26-SEMI',url='https://faw.cymru/news/faw-cup-competition-semi-finals-to-move-away-from-neutral-venues/',
        article='15 September 2026 announcement',scope='Home semi-finals and GBP 1000 away-club compensation.'),
        dict(id='FAW-26-REMOVED-CUPS',url='https://faw.cymru/cymru-leagues/news/statement-nathaniel-mg-cup-and-welsh-blood-service-league-cup/',
        article='7 May 2026 announcement',scope='Both senior league cups removed for 2026/27.')]
    for source in sources:
        source.update(publisher='FAW',accessed='2026-09-23',edition='2026/27',status='VERIFIED')
    added={s['id'] for s in sources}
    wales['evidence']=[s for s in wales['evidence'] if s['id'] not in added]+sources
    cup['source_ids']=list(dict.fromkeys(cup['source_ids']+list(s['id'] for s in sources[:3])))
    cup['calendar'].update(timezone='Europe/London',default_kickoff='14:00',
        source_variation='PDF gives full weekend windows; web page lists narrower dates for R1/R2/R4 and 13 November alone for R3. R3 uses 13 November as its conference date; alternative dates require association approval.',
        rounds={r['id']:dict(window=list(window),conference_date=day,
            kickoff_status='provisional',source_ids=['FAW-26-CUP-DATES','FAW-26-CUP-DATES-PDF'])
            for r,window,day in zip(cup['rounds'],ROUND_WINDOWS,CONFERENCE_DATES)})
    north_top={'Wrexham','Bangor','Caernarfon','Aberystwyth','Rhyl','Llandudno','Newtown'}
    for club in data['clubs']:
        if club['nation']!='wales':continue
        region=club['region']
        club['cup_draw_zone']=('north' if club['city'] in north_top else 'south') if region=='premier' else region.split('_')[0]
    # Priority is authored geography, not a ranking or a claim of prior results.
    boundary=('Aberystwyth','Newtown','Llanidloes','Machynlleth','Welshpool','Dolgellau',
              'Barmouth','Bala','Harlech','Brecon','Carmarthen','Llandovery')
    clubs={c['id']:c for c in data['clubs']}
    priority=sorted(allocation['club_ids'],key=lambda cid:(
        boundary.index(clubs[cid]['city']) if clubs[cid]['city'] in boundary else len(boundary),cid))
    cup['draw_policy']=dict(regional_rounds=['qualifying_1','qualifying_2','round_1','round_2'],
        zones=['north','south'],odd_group_policy='move_first_boundary_priority_club_from_north_to_south',
        boundary_priority=priority,basis='authored_fictional_association_group_assignment',
        source_id='FAW-26-CUP',source_article='10')
    cup['financial_rules']=dict(currency='GBP',source_ids=['FAW-26-CUP','FAW-26-SEMI'],
        semifinal_away_compensation_pence=100000,
        officials=dict(expense_payer='actual_host_before_final',car_pence_per_mile=55,
            motorcycle_pence_per_mile=24,bicycle_pence_per_mile=20,
            meal_threshold_miles=150,meal_receipt_cap_pence=1000,
            unplayed_fee_fraction=[1,2],bank_transfer_business_days=3),
        tv_facility_fee='association_award_shared_between_competing_clubs',
        prize_schedule=None,official_fee_schedule=None,gate_distribution=None,
        status='PARTIAL; unpublished award/fee schedules are not assumed to be zero')
    cup['match_rules'].update(substitutes_named_max=7,substitutes_used_max=5,
        substitution_stoppages_max=3,halftime_additional_opportunity=True)
    wales['inactive_competitions']=[dict(id='wales-league-cup-2026',season='2026/27',status='NOT_HELD',source_ids=['FAW-26-REMOVED-CUPS']),
        dict(id='wales-tier-two-league-cup-2026',season='2026/27',status='NOT_HELD',source_ids=['FAW-26-REMOVED-CUPS'])]
    wales['european_nomination_rules']=dict(source_id='FAW-26-T1',source_article='16.1-16.7',
        supported_total_places=[3,4],primary='highest_placed_european_licensed_club',
        cup_duplicate='next_eligible_league_club',playoff_rank_limit=7,
        playoff_licences=['tier_one','european'],ineligible_opponent='bye_without_replacement',
        higher_league_rank_hosts=True,extra_time=False,
        unresolved_licence_interaction='association_direction_required',
        annual_access_list_and_entry_stages='UNVERIFIED')
    cup['open_requirements']=['Complete prize, official fee and gate-distribution schedules',
                              'Complete European qualification paths']


def build(data):
    if data.get('shared_league_rulebook'):
        raise ValueError('Legacy Welsh cup allocations require reconciliation with the shared league model.')
    wales=next(c for c in data['countries'] if c['id']=='wales')
    pool_id='wales-lower-cup-pool-2026'
    previous=next((p for p in wales['supporting_pools'] if p['id']==pool_id),{})
    old_ids=set(previous.get('club_ids',[]))
    data['clubs']=[c for c in data['clubs'] if c['id'] not in old_ids]
    wales['supporting_pools']=[p for p in wales['supporting_pools'] if p['id']!=pool_id]
    lower=[]
    for region,places in PLACES.items():
        for place in places.split('|'):
            for branch in range(4):
                index=len(lower);name=place+' '+NAMES[(index+index//4)%len(NAMES)]
                cid='wal-lower-'+re.sub('[^a-z0-9]+','-',name.lower()).strip('-')
                colors=list(COLORS[(index+index//6)%len(COLORS)])
                ground=name+' Field'
                lower.append(dict(id=cid,name=name,nation='wales',city=place,ground=ground,
                    colors=colors,badge=dict(style='quartered_shield',initials=''.join(p[0] for p in name.split()),primary=colors[0],secondary=colors[1]),
                    identity_tags=['community_football','local_youth',region],
                    supporter_profile=dict(priorities=['affordable_tickets','local_youth','financial_stability'],matchday_tradition='Local supporters gather at '+ground+'.'),
                    content_origin='original_fiction',region=region,simulation_scope='supporting_cup_club'))
    assert len(lower)==172 and len({c['id'] for c in lower})==172
    data['clubs'].extend(lower)
    wales['supporting_pools'].append(dict(id=pool_id,status='PARTIAL',nation='wales',membership=172,
        scope='Cup-admitted clubs below tier three; not a complete lower pyramid or a single league.',
        entry_rule='Explicit initial cup admission, subject to completed ground and association criteria.',
        club_ids=[c['id'] for c in lower],source_ids=['FAW-26-CUP','FAW-26-CUP-ENTRY']))
    sid='FAW-26-CUP-ENTRY'
    wales['evidence']=[e for e in wales['evidence'] if e['id']!=sid]
    wales['evidence'].append(dict(id=sid,url='https://faw.cymru/news/faw-welsh-cup-first-qualifying-round-draw/',
        publisher='FAW',accessed='2026-09-23',edition='2026/27',article='Entry numbers, joining rounds and opening weekend',
        scope='284 entrants: 232 QR1, 4 QR2, 28 R1, 20 R2; QR1 on 24-26 July.',status='VERIFIED'))
    cup=wales['domestic_cups'][0];cup_id=cup['id'];aid=cup_id+'-opening'
    top,north,south=[t['first_season_members'] for t in wales['tier_rules']]
    groups=wales['supporting_pools'][0]['group_members']
    tier3=[cid for members in groups.values() for cid in members]
    tier3_byes=[members[0] for members in groups.values()]
    tier2_byes=north[:2]+south[:2]
    cohorts={
        'qualifying_1':[cid for cid in tier3 if cid not in tier3_byes]+[c['id'] for c in lower],
        'qualifying_2':tier3_byes,
        'round_1':[cid for cid in north+south if cid not in tier2_byes],
        'round_2':tier2_byes+top,
    }
    lower_ids={club['id'] for club in lower}
    for club in data['clubs']:
        if club['nation']!='wales':continue
        club['cup_ground']=dict(paid_admission=True,goal_nets=True,
            separate_team_changing_and_showers=True,separate_official_changing_and_showers=True,
            association_accepted_walking_distance=True,spectator_barrier='rope' if club['id'] in lower_ids else 'rail',
            private_dressing_area_toilets=club['id'] not in lower_ids,
            basis='authored_current_facilities')
    cup['ground_rules']=dict(source_id='FAW-26-CUP',articles=['12.10','13.1','13.2'],
        qualifying_barriers=['rope','rail','wall'],main_round_barriers=['rail','wall'],
        private_dressing_area_toilets_from='round_1',unsuitable_home_ground='approved_alternative_or_opponents_ground')
    cup['admission_rules']=dict(source_id='FAW-26-CUP',articles=['6','7'],
        association_jurisdiction='wales',mandatory_tiers=[1,2,3],deadline='2026-06-30',
        entry_fee_pence=10000,currency='GBP',association_may_reject=True)
    for evidence in wales['evidence']:
        if evidence['id']=='FAW-26-CUP':evidence['article']='Rules 6-7, 9-10, 12-13, 16.7-18, 22'
    cup['entrant_count']=284;cup['opening_allocation']=aid
    cup['calendar']['opening_qualifying']=['2026-07-24','2026-07-26']
    cup['source_ids']=list(dict.fromkeys(cup['source_ids']+[sid]))
    cup['entry_counts']={key:len(ids) for key,ids in cohorts.items()}
    cup['rounds']=[dict(id=rid,entrants=count,new_entries=cup['entry_counts'].get(rid,0),ties=count//2)
                   for rid,count in [('qualifying_1',232),('qualifying_2',120),('round_1',88),('round_2',64),('round_3',32),('round_4',16),('quarter_final',8),('semi_final',4),('final',2)]]
    cup['open_requirements']=['Full round dates and geographic draw assignments','Financial distributions and complete European qualification paths']
    allocation=dict(id=aid,competition=cup_id,basis='initial_database_allocation',
        club_ids=[cid for ids in cohorts.values() for cid in ids],entry_rounds=cohorts,
        seeding_basis='Explicit opening database seed priority; no prior results or honours.',
        tier_two_priority=tier2_byes+[cid for cid in north+south if cid not in tier2_byes],
        tier_three_priority=tier3_byes+[cid for cid in tier3 if cid not in tier3_byes])
    data['opening_allocations']=[a for a in data['opening_allocations'] if a['id']!=aid]+[allocation]
    data['first_season_entrants']=[e for e in data['first_season_entrants'] if e['competition']!=cup_id]
    for rid,ids in cohorts.items():
        for cid in ids:
            data['first_season_entrants'].append(dict(competition=cup_id,club=cid,entry_round=rid,opening_allocation=aid,
                eligibility_evidence=dict(basis='initial_database_assessment',status='VERIFIED',association='wales',
                    all_football_under_association=True,team_category='mens',association_accepted=True,
                    application=dict(complete=True,received_on='2026-06-30'),
                    entry_fee=dict(amount_pence=10000,currency='GBP',settled=True,settled_on='2026-06-30',
                                   accounting_basis='included_in_opening_balances'))))
    wales['open_requirements']=[r for r in wales['open_requirements'] if r!='Additional lower-tier Welsh Cup entrant inventory and dated entry rounds']
    wales['open_requirements']=[r.replace('Remaining domestic competitions and full cup round dates',
        'Supporting amateur/youth competition coverage') for r in wales['open_requirements']]
    complete_cup_operations(data,wales,cup,allocation)
    return data


if __name__=='__main__':
    path=ROOT/'data'/'production_rules_2026.json'
    path.write_text(json.dumps(build(json.loads(path.read_text())),ensure_ascii=False,indent=2)+'\n')
