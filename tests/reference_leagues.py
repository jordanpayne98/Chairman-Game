"""Superseded national definitions used only to retain legacy service coverage."""
import json
from pathlib import Path
from club_chairman.content_gate import load


def load_reference():
    data = load()
    reference = json.loads((Path(__file__).resolve().parents[1] / 'data' /
                            'reference_national_leagues_2026.json').read_text())
    countries = {c['id']: c for c in reference['countries']}
    data.pop('shared_league_rulebook', None)
    data['basis'] = reference['basis']
    for country in data['countries']:
        original = countries[country['id']]
        country.clear()
        country.update(original)
    data['opening_allocations'] = reference['opening_allocations']
    return data
