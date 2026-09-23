import unittest
from copy import deepcopy
from club_chairman.content_gate import audit
from reference_leagues import load_reference as load
from club_chairman.competition_entries import audit_cup_allocation,welsh_cup_ground_issues,welsh_cup_admission_issues
from tools.build_welsh_cup_content import build


class CupAllocationTests(unittest.TestCase):
    def setUp(self):
        self.data=load();w=next(c for c in self.data['countries'] if c['id']=='wales')
        self.cup=w['domestic_cups'][0]
        self.allocation=next(a for a in self.data['opening_allocations'] if a['id']==self.cup['opening_allocation'])
        self.members={1:w['tier_rules'][0]['first_season_members'],
                      2:w['tier_rules'][1]['first_season_members']+w['tier_rules'][2]['first_season_members'],
                      3:w['supporting_pools'][0]['club_ids']}

    def check(self):
        return audit_cup_allocation(self.cup,self.allocation,[c['id'] for c in self.data['clubs']],self.members)

    def test_all_named_entries_conserve_to_one_winner_without_history(self):
        original=deepcopy(self.data)
        self.assertEqual(self.check(),[])
        self.assertEqual(self.data,original)
        self.assertEqual(sum(r['ties'] for r in self.cup['rounds']),283)
        self.assertEqual([r['entrants'] for r in self.cup['rounds']],[232,120,88,64,32,16,8,4,2])
        self.assertEqual(len(self.allocation['club_ids']),284)
        self.assertNotIn('competition_history',self.data)

    def test_builder_is_repeatable_and_preserves_unrelated_content(self):
        data=deepcopy(self.data);data['editorial_note']='keep'
        self.assertEqual(build(deepcopy(data)),data)

    def test_unknown_or_duplicate_club_cannot_fill_a_draw(self):
        cohort=self.allocation['entry_rounds']['qualifying_1']
        cohort[0]='unknown'
        self.assertTrue(any('identities/count' in e for e in self.check()))
        cohort[0]=cohort[1]
        self.assertTrue(any('identities/count' in e for e in self.check()))

    def test_correct_counts_cannot_hide_wrong_tier_entry(self):
        early=self.allocation['entry_rounds']['qualifying_1']
        late=self.allocation['entry_rounds']['round_2']
        early[0],late[-1]=late[-1],early[0]
        self.assertTrue(any('tier-specific' in e for e in self.check()))

    def test_round_cannot_create_an_extra_survivor(self):
        self.cup['rounds'][1]['entrants']=122
        self.assertTrue(any('conserve' in e for e in self.check()))

    def test_full_gate_rechecks_admission_and_entry_round(self):
        issues=audit(self.data)
        self.assertFalse(any('admission assessments remain unverified' in e for e in issues))
        self.data['first_season_entrants'][0]['eligibility_evidence']['association_accepted']=False
        self.assertTrue(any('acceptance is missing or refused' in e for e in audit(self.data)))
        self.data['first_season_entrants'][0]['entry_round']='round_2'
        self.assertTrue(any('wrong entry round' in e for e in audit(self.data)))

    def test_admission_rejects_invalid_facts_even_with_verified_label(self):
        original=self.data['first_season_entrants'][0]['eligibility_evidence']
        rules=self.cup['admission_rules']
        self.assertEqual(welsh_cup_admission_issues(original,rules),[])
        cases=[('association','england'),('all_football_under_association',False),
               ('team_category','womens'),('association_accepted',False),
               ('application',None),('entry_fee',None)]
        for key,value in cases:
            with self.subTest(key=key):
                evidence=deepcopy(original);evidence[key]=value
                self.assertTrue(welsh_cup_admission_issues(evidence,rules))
        for key,value in [('amount_pence',9999),('amount_pence',True),('currency','EUR'),
                          ('settled',False),('settled_on','2026-07-01'),
                          ('accounting_basis','charge_again_at_career_start')]:
            with self.subTest(key=key):
                evidence=deepcopy(original);evidence['entry_fee'][key]=value
                self.assertTrue(welsh_cup_admission_issues(evidence,rules))
        for value in ['2026-07-01','2026-02-30',None]:
            evidence=deepcopy(original);evidence['application']['received_on']=value
            self.assertTrue(welsh_cup_admission_issues(evidence,rules))
        earlier=deepcopy(original);earlier['entry_fee']['settled_on']='2026-06-29'
        self.assertEqual(welsh_cup_admission_issues(earlier,rules),[])

    def test_verified_label_alone_and_duplicate_records_cannot_pass(self):
        entry=self.data['first_season_entrants'][0]
        entry['eligibility_evidence']={'status':'VERIFIED'}
        self.assertTrue(any('Admission dates' in e for e in audit(self.data)))
        self.data['first_season_entrants'].append(deepcopy(entry))
        self.assertTrue(any('records differ from opening allocation' in e for e in audit(self.data)))

    def test_qualifying_ground_needs_improvements_after_promotion_to_main_rounds(self):
        club=next(c for c in self.data['clubs'] if c.get('simulation_scope')=='supporting_cup_club')
        ground=club['cup_ground']
        self.assertEqual(welsh_cup_ground_issues(ground,'qualifying_1'),[])
        self.assertEqual(len(welsh_cup_ground_issues(ground,'round_1')),2)
        ground.update(spectator_barrier='rail',private_dressing_area_toilets=True)
        self.assertEqual(welsh_cup_ground_issues(ground,'round_1'),[])
        ground['goal_nets']=False
        self.assertTrue(any('suitable registered ground' in e for e in audit(self.data)))


if __name__=='__main__':unittest.main()
