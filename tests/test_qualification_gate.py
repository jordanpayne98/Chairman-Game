import unittest
from copy import deepcopy
from club_chairman.content_gate import audit,load
from club_chairman.qualification_gate import audit_access_graph


class QualificationGateTests(unittest.TestCase):
    def setUp(self):
        self.sources={'rule':dict(status='VERIFIED')}
        self.edge=dict(id='access',source_competition='league',target_competition='continental',
            status='VERIFIED',source_ids=['rule'],effective_from='2026-07-01',outcome='league_positions',
            places=2,target_slot='association_places',eligibility={'licence_required':True},
            duplicate_resolution='next_eligible_league_club',season_offset=1)
        self.data=dict(qualification_graph=[self.edge],regional_competitions=[dict(id='continental',entrant_count=2)])

    def check(self):return audit_access_graph(self.data,{'league','continental'},self.sources)

    def test_access_counts_source_references_and_duplicate_slots_are_checked(self):
        self.assertEqual(self.check(),[])
        self.edge['places']=1
        self.assertTrue(any('reconcile' in e for e in self.check()))
        self.edge['places']=2;self.data['qualification_graph'].append(deepcopy(self.edge))
        self.assertTrue(any('duplicate target slot' in e for e in self.check()))
        self.edge['source_ids']=['unknown']
        self.assertTrue(any('evidence' in e for e in self.check()))
        self.edge['source_competition']='unknown'
        self.assertTrue(any('unknown source' in e for e in self.check()))

    def test_nonempty_placeholder_cannot_satisfy_graph_gate(self):
        self.data['qualification_graph']='verified'
        self.assertTrue(self.check())
        self.data['qualification_graph']=[{'status':'VERIFIED'}]
        self.assertTrue(self.check())

    def test_status_and_removed_open_questions_cannot_hide_missing_cup_finances(self):
        data=load();w=next(c for c in data['countries'] if c['id']=='wales')
        c=w['domestic_cups'][0];c['status']='VERIFIED';c['open_requirements']=[]
        self.assertTrue(any('unresolved financial schedule' in e for e in audit(data)))
        c['calendar']['rounds'].pop('final')
        self.assertTrue(any('cover every round' in e for e in audit(data)))

    def test_regional_competition_needs_verified_sources_and_unique_id(self):
        data=load()
        data['regional_competitions']=[dict(id='wales-national-cup-2026',status='VERIFIED',source_ids=['unknown'])]
        issues=audit(data)
        self.assertTrue(any('assigned more than once' in e for e in issues))
        self.assertTrue(any('lacks verified source references' in e for e in issues))


if __name__=='__main__':unittest.main()
