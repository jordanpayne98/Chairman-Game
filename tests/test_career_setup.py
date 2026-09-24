from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import career_setup as setup,people,world_population as wp,leagues,market
from club_chairman.simulation import new_career,validate,execute,Command,payroll
from club_chairman.persistence import save,load


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=new_career(47,'compact',{'club_index':10,'name':'Jordan Payne'})

    def test_selected_club_and_current_save_resume(self):
        s=deepcopy(self.base);validate(s)
        self.assertEqual(s['clubs'][0]['name'],setup.clubs('compact')[10]['name'])
        self.assertEqual(leagues.division_for(s)['tier'],2)
        self.assertEqual(s['owner']['name'],'Jordan Payne');self.assertIsNotNone(s['manager'])
        self.assertGreater(s['budget'],payroll(s))
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'career.sqlite3';save(s,path);resumed=load(path)
        self.assertEqual(s,resumed)
        s,_=execute(s,Command('first',s['revision'],'continue',{}));validate(s)

    def test_invalid_and_standard_isolated(self):
        for opts in ({'name':''},{'club_index':500},{'nationality':'invalid'},{'funding':100},{'age':True}):
            with self.assertRaises(ValueError):setup.validate_options(opts,'compact')
        with self.assertRaises(ValueError):setup.clubs('germany')
        self.assertFalse(self.base['career_setup']['customised'])
        self.assertFalse(any('sandbox' in row['id'] for row in self.base['ledger']))

    def test_profile_distribution_all_fourteen_nations(self):
        for nation in setup.NATION_LEVELS:
            upper=[setup.profile(i,nation,'club',1) for i in range(30)]
            lower=[setup.profile(i,nation,'club',5) for i in range(30)]
            self.assertGreater(sum(p['level'] for p in upper),sum(p['level'] for p in lower))
            self.assertTrue(all(18<=p['squad_size']<=25 and 'Coaching' in p['roles'] for p in upper+lower))
        db=wp.unpack(self.base['world_population']['blob'])
        self.assertTrue(all('stature' in c for c in db['clubs'].values()))

    def test_national_lower_club_and_sandbox_ledger(self):
        s=new_career(47,'wales',dict(club_index=14,sandbox=True,funding=10000000,reputation=75,facilities=4,confidence=80))
        validate(s);self.assertEqual(leagues.division_for(s)['tier'],2)
        self.assertEqual(s['cash'],s['config']['opening_cash']+10000000)
        self.assertEqual(s['ledger'][-1]['reason'],'Sandbox opening funding grant')
        self.assertEqual(s['trust'],80);self.assertEqual(s['career']['facilities']['training'],4)
        self.assertEqual(s['recruitment']['clubs']['c0']['value'],75)
        self.assertTrue(all(p['potential']>=people.overall(p) for p in s['players']))
        for c in s['clubs']:
            squad=[p for p in s['players'] if p['club']==c['id'] and not p['youth'] and p['development']['group']=='Seniors']
            self.assertEqual(len(squad),c['stature']['squad_size'])
            self.assertGreaterEqual(sum(p['role']=='GK' for p in squad),2)
            self.assertTrue(any(p['club']==c['id'] and p['role']=='Coaching' for p in s['staff']['people']))
        cid='c1';s['day']=7;before=market.club_cash(s,cid);market.process_day(s)
        self.assertEqual(market.club_cash(s,cid),before+s['market']['accounts'][cid]['income_weekly'])
        market.validate(s)

if __name__=='__main__':unittest.main()
