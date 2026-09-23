"""Run from the repository root: python tools/audit_content_gate.py."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from club_chairman.content_gate import coverage_report,load
from club_chairman.league_structures import league_coverage

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true',help='Emit measured country coverage and blockers as JSON.')
    parser.add_argument('--leagues',action='store_true',help='Audit the cross-nation league structure pass separately.')
    args=parser.parse_args()
    if args.leagues:
        rows=league_coverage(load())
        if args.json:
            print(json.dumps(rows,indent=2))
        else:
            for row in rows:
                print(f"{row['nation']}: {row['status']} — {row['mapped_competitions']} competitions, "
                      f"{row['structures_verified']} verified, depth {row['depth']}")
                for tier in row['tiers']:
                    for issue in tier['issues']:print(' - '+tier['id']+': '+issue)
        sys.exit(1 if any(r['status']!='VERIFIED' for r in rows) else 0)
    report=coverage_report(load());issues=report['blockers']
    if args.json:
        print(json.dumps(report,indent=2))
        sys.exit(1 if issues else 0)
    if issues:
        print(f'Production content gate BLOCKED ({len(issues)} issues):')
        for issue in issues:print(' - '+issue)
        sys.exit(1)
    print('Production content gate: verified.')
