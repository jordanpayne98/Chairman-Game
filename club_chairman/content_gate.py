"""Production football-content gate. Development scenarios do not satisfy it.

The gate checks authored evidence and references before a production ruleset
can be activated. It never manufactures clubs, qualifiers or rule exceptions.
"""
import json
from pathlib import Path
from .competition_entries import audit_cup_allocation, welsh_cup_ground_issues, welsh_cup_admission_issues
from .production_cup import calendar_issues
from .qualification_gate import audit_access_graph
from .league_structures import structure_issues
from .shared_league_rules import shared_rulebook_issues

COUNTRIES = ('england','germany','france','spain','italy','netherlands',
             'portugal','scotland','ireland','northern-ireland','wales',
             'brazil','argentina','usa')
DEPTH = dict(zip(COUNTRIES,(5,3,3,3,3,2,2,3,2,2,2,3,3,2)))
FIELDS = ('id','nation','tier','format','membership','calendar','tiebreakers',
          'progression','registration','financial','governance','licensing',
          'effective_from','source_ids','first_season_members')
SOURCE_FIELDS = ('url','publisher','accessed','edition','article','status')
CLUB_FIELDS = ('id','name','nation','city','ground','colors','badge',
               'identity_tags','supporter_profile')


def load(path=None):
    path=Path(path) if path else Path(__file__).resolve().parent.parent/'data'/'production_rules_2026.json'
    return json.loads(path.read_text(encoding='utf-8'))


def audit(data):
    """Return precise, stable blockers; zero blockers is required for release."""
    errors=shared_rulebook_issues(data)
    if data.get('schema')!=1:return ['Unsupported production content schema.']
    countries=data.get('countries',[])
    ids=[c.get('id') for c in countries]
    if len(ids)!=len(set(ids)) or set(ids)!=set(COUNTRIES):
        errors.append('Exactly the fourteen approved national IDs are required.')
    club_ids=set();competition_ids=set();all_sources=set();source_records={}
    for c in sorted(countries,key=lambda c:str(c.get('id'))):
        nid=c.get('id');prefix=str(nid)
        for requirement in c.get('open_requirements',[]):
            errors.append(prefix+': unresolved content: '+requirement)
        if c.get('minimum_playable_depth')!=DEPTH.get(nid):
            errors.append(prefix+': approved minimum depth differs.')
        if not c.get('baseline_season'):errors.append(prefix+': missing dated baseline.')
        sources={}
        for source in c.get('evidence',[]):
            sid=source.get('id')
            if not sid or sid in all_sources:errors.append(prefix+': missing or duplicate source ID.')
            all_sources.add(sid)
            if any(not source.get(k) for k in SOURCE_FIELDS):errors.append(prefix+': incomplete source provenance.')
            if source.get('status') not in ('VERIFIED','PARTIAL','UNVERIFIED','DELIBERATE ADAPTATION'):
                errors.append(prefix+': invalid evidence status.')
            sources[sid]=source
            source_records[sid]=source
        tiers=c.get('tier_rules',[])
        if len({t.get('id') for t in tiers})!=len(tiers):errors.append(prefix+': duplicate tier ID.')
        levels={t.get('tier') for t in tiers}
        if not set(range(1,DEPTH.get(nid,0)+1))<=levels:
            errors.append(prefix+': missing tier rules through approved playable depth.')
        for t in tiers:
            tid=str(t.get('id'))
            errors.extend(prefix+'/'+tid+': league structure: '+issue for issue in structure_issues(t,sources))
            if tid in competition_ids:errors.append('Competition ID assigned more than once: '+tid+'.')
            competition_ids.add(tid)
            if t.get('status')!='VERIFIED':errors.append(prefix+'/'+tid+': tier remains PARTIAL.')
            if any(not t.get(k) for k in FIELDS):errors.append(prefix+'/'+tid+': missing mandatory rule field.')
            if t.get('nation')!=nid:errors.append(prefix+'/'+tid+': wrong association.')
            if not t.get('source_ids') or any(sources.get(sid,{}).get('status')!='VERIFIED' for sid in t['source_ids']):
                errors.append(prefix+'/'+tid+': rule lacks verified, article-level sources.')
            members=t.get('first_season_members',[])
            if len(members)!=t.get('membership') or len(members)!=len(set(members)):
                errors.append(prefix+'/'+tid+': first-season membership does not reconcile.')
            for club in members:
                if club in club_ids:errors.append(prefix+'/'+tid+': club assigned twice.')
                club_ids.add(club)
        cups=c.get('domestic_cups',[])
        if not cups:errors.append(prefix+': domestic cup eligibility and dates missing.')
        for cup in cups:
            cup_id=cup.get('id')
            if cup_id in competition_ids:errors.append('Competition ID assigned more than once: '+str(cup_id)+'.')
            competition_ids.add(cup_id)
            if cup.get('status')!='VERIFIED':errors.append(prefix+'/'+str(cup_id)+': cup remains PARTIAL.')
            if any(not cup.get(k) for k in ('id','eligibility','calendar','format','qualification','source_ids')):
                errors.append(prefix+'/'+str(cup_id)+': incomplete domestic cup.')
            if any(sources.get(sid,{}).get('status')!='VERIFIED' for sid in cup.get('source_ids',[])):
                errors.append(prefix+'/'+str(cup_id)+': domestic cup source not verified.')
        pools=c.get('supporting_pools',[])
        if not pools:errors.append(prefix+': supporting region/feeder pool missing.')
        for pool in pools:
            if pool.get('status')!='VERIFIED':errors.append(prefix+'/'+str(pool.get('id'))+': supporting pool remains PARTIAL.')
            if any(not pool.get(k) for k in ('id','nation','entry_rule','club_ids','source_ids')):
                errors.append(prefix+'/'+str(pool.get('id'))+': incomplete supporting pool.')
            if any(sources.get(sid,{}).get('status')!='VERIFIED' for sid in pool.get('source_ids',[])):
                errors.append(prefix+'/'+str(pool.get('id'))+': supporting pool source not verified.')
            for club in pool.get('club_ids',[]):
                if club in club_ids:errors.append(prefix+'/'+str(pool.get('id'))+': club assigned twice.')
                club_ids.add(club)
            if len(pool.get('club_ids',[]))!=pool.get('membership'):
                errors.append(prefix+'/'+str(pool.get('id'))+': supporting club membership does not reconcile.')
            if pool.get('groups'):
                groups=pool.get('group_members',{})
                members=[club for group in groups.values() for club in group]
                if (set(groups)!=set(pool['groups']) or len(members)!=len(set(members))
                        or set(members)!=set(pool.get('club_ids',[]))):
                    errors.append(prefix+'/'+str(pool.get('id'))+': regional groups do not reconcile.')
        for inactive in c.get('inactive_competitions',[]):
            if inactive.get('status')!='NOT_HELD' or inactive.get('season')!=c.get('baseline_season'):
                errors.append(prefix+': invalid inactive competition decision.')
            if not inactive.get('source_ids') or any(sources.get(sid,{}).get('status')!='VERIFIED' for sid in inactive.get('source_ids',[])):
                errors.append(prefix+': inactive competition decision lacks verified evidence.')
            if inactive.get('id') in competition_ids:errors.append(prefix+': inactive competition has active rules.')
    for family in ('regional_competitions','international_competitions'):
        records=data.get(family,[])
        if not records:errors.append(family+': no verified competition records.')
        for comp in records:
            if any(not comp.get(k) for k in ('id','format','effective_from','entrant_count','qualification_sources','calendar','source_ids')):
                errors.append(family+'/'+str(comp.get('id'))+': incomplete competition definition.')
            if comp.get('status')!='VERIFIED':errors.append(str(comp.get('id'))+': competition remains unverified.')
            if not comp.get('source_ids') or any(source_records.get(sid,{}).get('status')!='VERIFIED' for sid in comp.get('source_ids',[])):
                errors.append(str(comp.get('id'))+': competition lacks verified source references.')
            if comp.get('id') in competition_ids:errors.append('Competition ID assigned more than once: '+str(comp.get('id'))+'.')
            competition_ids.add(comp.get('id'))
    entries=data.get('first_season_entrants',[])
    if not entries:errors.append('First-season qualifiers absent; no draw can invent entrants.')
    if len({(e.get('competition'),e.get('club')) for e in entries})!=len(entries):
        errors.append('Duplicate first-season entrant.')
    for e in entries:
        if e.get('competition') not in competition_ids or e.get('club') not in club_ids:
            errors.append('First-season entrant references an unknown club or competition.')
        if not e.get('opening_allocation') or not e.get('eligibility_evidence'):
            errors.append('First-season entrant lacks opening allocation and eligibility evidence.')
    for comp in data.get('regional_competitions',[])+data.get('international_competitions',[]):
        count=sum(e.get('competition')==comp.get('id') for e in entries)
        if comp.get('entrant_count')!=count:
            errors.append(str(comp.get('id'))+': first-season entrants do not match the competition access list.')
    authored=data.get('clubs',[])
    authored_ids=[c.get('id') for c in authored]
    club_by_id={club.get('id'):club for club in authored}
    if len(authored_ids)!=len(set(authored_ids)) or set(authored_ids)!=club_ids:
        errors.append('Authored club identities do not reconcile with every tier and supporting pool.')
    assignments={club:country['id'] for country in countries
                 for record in country.get('tier_rules',[])+country.get('supporting_pools',[])
                 for club in record.get('first_season_members',record.get('club_ids',[]))}
    for club in authored:
        if any(not club.get(field) for field in CLUB_FIELDS):
            errors.append(str(club.get('id'))+': incomplete original club identity.')
        if club.get('rival_id') and club['rival_id'] not in club_ids:
            errors.append(str(club.get('id'))+': rival references missing club.')
        if club.get('nation')!=assignments.get(club.get('id')):
            errors.append(str(club.get('id'))+': club association disagrees with membership.')
    # Opening allocations are setup facts, never fictional previous results.
    if data.get('history_policy')!='career_start_only':
        errors.append('Production history must begin at career start.')
    for key in ('competition_history','historical_people','historical_rule_versions','membership_transitions'):
        if data.get(key):errors.append('Pre-game historical content is not permitted: '+key+'.')
    for club in authored:
        if any(club.get(key) for key in ('history','milestones','defining_era','historical_person_id')):
            errors.append(str(club.get('id'))+': pre-game club history is not permitted.')
    allocations={record.get('id'):record for record in data.get('opening_allocations',[])}
    if len(allocations)!=len(data.get('opening_allocations',[])):
        errors.append('Duplicate opening allocation ID.')
    for entry in entries:
        allocation=allocations.get(entry.get('opening_allocation'),{})
        if (allocation.get('competition')!=entry.get('competition')
                or entry.get('club') not in allocation.get('club_ids',[])
                or allocation.get('basis')!='initial_database_allocation'):
            errors.append('First-season entrant does not match its opening allocation.')
        if entry.get('history_result'):
            errors.append('First-season entrant cannot claim a pre-game historical result.')
    for country in countries:
        tier_members={}
        for tier in country.get('tier_rules',[]):
            tier_members.setdefault(tier.get('tier'),[]).extend(tier.get('first_season_members',[]))
        for pool in country.get('supporting_pools',[]):
            if pool.get('id')=='wales-ardal-2026':tier_members[3]=pool.get('club_ids',[])
        for cup in country.get('domestic_cups',[]):
            cid=cup.get('id');allocation=allocations.get(cup.get('opening_allocation'),{})
            for requirement in cup.get('open_requirements',[]):
                errors.append(str(cid)+': unresolved content: '+requirement)
            errors.extend(audit_cup_allocation(cup,allocation,club_ids,tier_members))
            if cid=='wales-national-cup-2026':
                cup_clubs={key:value for key,value in club_by_id.items() if key in allocation.get('club_ids',[])}
                errors.extend(str(cid)+': '+issue for issue in calendar_issues(cup,cup_clubs))
                financial=cup.get('financial_rules',{})
                for field in ('prize_schedule','official_fee_schedule','gate_distribution'):
                    if financial.get(field) is None:
                        errors.append(str(cid)+': unresolved financial schedule: '+field+'.')
            cup_entries=[entry for entry in entries if entry.get('competition')==cid]
            if (len(cup_entries)!=len(allocation.get('club_ids',[]))
                    or {entry.get('club') for entry in cup_entries}!=set(allocation.get('club_ids',[]))):
                errors.append(str(cid)+': cup entrant records differ from opening allocation.')
            cohorts=allocation.get('entry_rounds',{})
            for entry in cup_entries:
                if entry.get('club') not in cohorts.get(entry.get('entry_round'),[]):
                    errors.append(str(cid)+': entrant assigned to the wrong entry round.')
                if cid=='wales-national-cup-2026':
                    facilities=club_by_id.get(entry.get('club'),{}).get('cup_ground',{})
                    if welsh_cup_ground_issues(facilities,entry.get('entry_round')):
                        errors.append(str(cid)+': opening entrant lacks a suitable registered ground.')
                evidence=entry.get('eligibility_evidence',{})
                if cid=='wales-national-cup-2026':
                    for issue in welsh_cup_admission_issues(evidence,cup.get('admission_rules',{})):
                        errors.append(str(cid)+': '+str(entry.get('club'))+': '+issue)
                if not isinstance(evidence,dict) or evidence.get('status')!='VERIFIED':
                    errors.append(str(cid)+': cup admission assessments remain unverified.')
        for tier in country.get('tier_rules',[]):
            allocation=allocations.get(tier.get('opening_allocation'),{})
            if (allocation.get('competition')!=tier.get('id')
                    or allocation.get('basis')!='initial_database_allocation'
                    or allocation.get('club_ids')!=tier.get('first_season_members')):
                errors.append(str(tier.get('id'))+': opening tier allocation does not reconcile.')
    errors.extend(audit_access_graph(data,competition_ids,source_records))
    if data.get('status')!='VERIFIED':errors.append('Content status remains INCOMPLETE.')
    return sorted(set(errors))


def require_verified(data):
    blockers=audit(data)
    if blockers:raise ValueError('Production world content blocked:\n'+'\n'.join(blockers))
    return data


def coverage_report(data):
    """Measured inventory alongside blockers; never present blocker count as % done."""
    blockers=audit(data);countries={c['id']:c for c in data.get('countries',[])}
    records=[]
    for nid in COUNTRIES:
        country=countries.get(nid,{})
        tiers=country.get('tier_rules',[]);cups=country.get('domestic_cups',[])
        levels=sorted({t['tier'] for t in tiers})
        records.append(dict(nation=nid,required_depth=DEPTH[nid],defined_levels=levels,
            missing_levels=sorted(set(range(1,DEPTH[nid]+1))-set(levels)),
            tier_records=len(tiers),verified_tier_records=sum(t.get('status')=='VERIFIED' for t in tiers),
            domestic_cups=len(cups),verified_domestic_cups=sum(c.get('status')=='VERIFIED' for c in cups),
            named_clubs=sum(c.get('nation')==nid for c in data.get('clubs',[])),
            supporting_pools=len(country.get('supporting_pools',[]))))
    return dict(status='BLOCKED' if blockers else 'VERIFIED',countries=records,
        regional_competitions=len(data.get('regional_competitions',[])),
        international_competitions=len(data.get('international_competitions',[])),
        opening_allocations=len(data.get('opening_allocations',[])),blockers=blockers)
