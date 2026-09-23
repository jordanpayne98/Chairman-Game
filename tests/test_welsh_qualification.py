import unittest
from copy import deepcopy
from club_chairman.welsh_qualification import nomination_plan, semifinal_pairings, complete_nominations


class WelshQualificationTests(unittest.TestCase):
    def setUp(self):
        self.order=['club-'+str(i) for i in range(1,17)]
        self.licences={c:dict(tier_one=True,european=True) for c in self.order+['lower-cup-winner']}

    def plan(self,places=3,rank=1):
        return nomination_plan(league_order=self.order,cup_winner=self.order[rank-1] if rank<=16 else 'lower-cup-winner',
            licences=self.licences,total_places=places,career_start='2026-07-01',completed_on='2027-04-25')

    def test_every_published_cup_position_branch_conserves_three_or_four_unique_places(self):
        before=deepcopy(self.licences)
        for places in (3,4):
            for rank in range(1,18):
                with self.subTest(places=places,rank=rank):
                    p=self.plan(places,rank)
                    self.assertEqual(p['status'],'READY_FOR_PLAYOFFS')
                    q={q['id']:q['home'] for q in p['playoff']['quarterfinals']}
                    semis=semifinal_pairings(p,q)
                    s={s['id']:s['home'] for s in semis}
                    nominations=complete_nominations(p,quarterfinal_winners=q,semifinal_winners=s,final_winner=s['sf1'])
                    self.assertEqual(len(nominations),places)
                    self.assertEqual(len({n['club'] for n in nominations}),places)
                    self.assertEqual(nominations[0]['club'],'club-1')
        self.assertEqual(before,self.licences)

    def test_three_places_with_low_cup_winner_reseeds_quarterfinal_winners_by_league_rank(self):
        p=self.plan(3,17)
        self.assertEqual([(q['home'],q['away']) for q in p['playoff']['quarterfinals']],[('club-4','club-7'),('club-5','club-6')])
        semis=semifinal_pairings(p,{'qf1':'club-4','qf2':'club-6'})
        self.assertEqual([(s['home'],s['away']) for s in semis],[('club-2','club-6'),('club-3','club-4')])

    def test_four_places_and_double_winner_skip_quarterfinals(self):
        p=self.plan(4,1)
        self.assertEqual({n['club'] for n in p['direct']},{'club-1','club-2','club-3'})
        self.assertEqual(p['playoff']['quarterfinals'],[])
        self.assertEqual([(s['home'],s['away']) for s in semifinal_pairings(p,{})],[('club-4','club-7'),('club-5','club-6')])

    def test_licence_refusal_gives_opponent_bye_not_eighth_place_replacement(self):
        self.licences['club-7']['european']=False
        p=self.plan(3,1)
        q=p['playoff']['quarterfinals'][0]
        self.assertEqual(q['automatic_winner'],'club-6')
        self.assertIsNone(q['away'])
        self.assertNotIn('club-8',str(p['playoff']['quarterfinals']))
        with self.assertRaises(ValueError):semifinal_pairings(p,{'qf1':'club-7'})
        self.assertEqual(semifinal_pairings(p,{'qf1':'club-6'})[0]['away'],'club-6')

    def test_unlicensed_champion_falls_back_but_ambiguous_bracket_stays_blocked(self):
        self.licences['club-1']['european']=False
        p=self.plan(3,4)
        self.assertEqual(p['direct'][0]['club'],'club-2')
        self.assertEqual(p['status'],'DIRECTION_REQUIRED')
        with self.assertRaisesRegex(ValueError,'unresolved'):semifinal_pairings(p,{})

    def test_missing_licence_decisions_and_fabricated_finalist_are_rejected(self):
        p=self.plan(4,1)
        with self.assertRaises(ValueError):complete_nominations(p,quarterfinal_winners={},semifinal_winners={'sf1':'club-4','sf2':'club-5'},final_winner='club-1')
        del self.licences['club-8']['european']
        with self.assertRaisesRegex(ValueError,'decisions'):self.plan()


if __name__=='__main__':unittest.main()
