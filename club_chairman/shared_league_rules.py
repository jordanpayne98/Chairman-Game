"""Validate the approved shared league adaptation without certifying source gaps.

Profiles govern sporting structure only. National laws, calendars and population
remain separate, and this module never migrates an existing career.
"""
from copy import deepcopy


def shared_rulebook_issues(data):
    from .content_gate import DEPTH

    book = data.get('shared_league_rulebook')
    if not book:
        # Older snapshots remain testable under their own recorded rules.
        if any(c.get('league_model') for c in data.get('countries', [])):
            return ['Shared league rulebook is missing.']
        return []
    errors = []
    if (book.get('id') != 'shared-english-2026-v1'
            or book.get('decision_id') != 'GDD-0.18'
            or book.get('decision_status') != 'APPROVED'):
        errors.append('Shared league model lacks the approved version and decision.')
    profiles = book.get('profiles', [])
    by_level = {p.get('tier'): p for p in profiles}
    if len(profiles) != 5 or set(by_level) != set(range(1, 6)):
        errors.append('Exactly five equivalent English tier profiles are required.')
    for level, profile in by_level.items():
        definition = profile.get('definition', {})
        if 'promotion_eligibility' in definition or 'licensing' in definition:
            errors.append('Shared profiles cannot include club licensing or admission gates.')
        membership = 20 if level == 1 else 24
        fmt = dict(kind='round_robin', cycles=2, games_per_club=2*(membership-1))
        if (definition.get('membership') != membership or definition.get('format') != fmt
                or definition.get('points') != dict(win=3, draw=1, loss=0)):
            errors.append('Shared profile sizes, match counts or points differ from approval.')
    divisions = places = 0
    for country in data.get('countries', []):
        nation = country.get('id')
        tiers = country.get('tier_rules', [])
        if (country.get('league_model') != book.get('id')
                or len(tiers) != DEPTH.get(nation)
                or sorted(t.get('tier', 0) for t in tiers) != list(range(1, DEPTH.get(nation, 0)+1))):
            errors.append(str(nation)+': shared model requires one division per approved level.')
        for tier in tiers:
            if 'licensing' in tier or 'promotion_eligibility' in tier:
                errors.append(str(tier.get('id'))+': club licensing is not part of the shared model.')
            divisions += 1
            places += tier.get('membership', 0) if type(tier.get('membership')) is int else 0
            profile = by_level.get(tier.get('tier'), {})
            if (tier.get('rulebook_profile') != profile.get('id')
                    or tier.get('rulebook_version') != book.get('id')
                    or tier.get('design_decision') != book.get('decision_id')):
                errors.append(str(tier.get('id'))+': missing shared profile/version reference.')
            expected = deepcopy(profile.get('definition', {}))
            # Provenance is local to each national pack, but refers to the same text.
            if nation != 'england':
                for evidence in expected.get('league_structure', {}).get('evidence', {}).values():
                    evidence['source_ids'] = [nation+'-'+s for s in evidence.get('source_ids', [])]
            for field, value in expected.items():
                if tier.get(field) != value:
                    errors.append(str(tier.get('id'))+': shared profile drift in '+field+'.')
            expected_sources = [s if nation == 'england' else nation+'-'+s
                                for s in profile.get('source_ids', [])]
            if tier.get('source_ids') != expected_sources:
                errors.append(str(tier.get('id'))+': shared profile source references differ.')
            boundary = tier.get('feeder_boundary', {})
            mode = 'background_feeder' if tier.get('tier') == DEPTH.get(nation) else 'playable_lower_tier'
            if boundary.get('mode') != mode or boundary.get('equivalent_lower_tier') != tier.get('tier', 0)+1:
                errors.append(str(tier.get('id'))+': shared pyramid feeder boundary is missing.')
        if country.get('league_model') == book.get('id'):
            if 'european_nomination_rules' in country:
                errors.append(str(nation)+': licence-based continental nomination rules are superseded.')
            if any('admission_rules' in cup for cup in country.get('domestic_cups', [])):
                errors.append(str(nation)+': club admission rules are not active cup content.')
    if (divisions, places) != (38, 856):
        errors.append('Shared league inventory must reconcile to 38 divisions and 856 senior places.')
    return list(dict.fromkeys(errors))
