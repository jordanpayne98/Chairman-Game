from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from club_chairman.simulation import Command, execute, new_career, view, payroll
from club_chairman.persistence import save, load
from club_chairman.contract_review import review, attention
from club_chairman.planning import signing_terms
from contract_support import prepare_signings


class ContractWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83)
        self.act('budget',value=4000000);self.act('hire',id='m0')

    def act(self, action, **payload):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,payload))

    def test_instant_signing_cannot_bypass_medical_or_cooldown(self):
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'Instant signing'):self.act('sign',id='p144')
        self.assertEqual(before,self.s)
        self.act('enquire',id='p144')
        for wage in (10000,10001,10002):self.act('propose_offer',id='p144',wage=wage,fee=0,duration=1)
        self.assertEqual(self.s['career']['offers']['p144']['status'],'rejected')
        with self.assertRaises(ValueError):self.act('enquire',id='p144')
        with self.assertRaises(ValueError):self.act('sign',id='p144')
        self.assertEqual(before['cash'],self.s['cash'])

    def test_review_and_plan_count_reservations_once_and_match_completion(self):
        prepare_signings(self,['p144','p145'])
        v=view(self.s);o=v['career']['offers']['p144'];r=review(v,o)
        self.act('budget',value=payroll(self.s)+v['reserved_wages'])
        v=view(self.s);r=review(v,o)
        self.assertEqual(r['headroom'],0);self.assertEqual(r['reasons'],[])
        targets=[p for p in v['players'] if p['id'] in ('p144','p145')]
        plan=signing_terms(v,targets)
        self.assertEqual(plan['headroom'],0);self.assertEqual(plan['reasons'],[])
        self.act('complete_offer',id='p144')
        self.assertEqual(r['cash_after'],self.s['cash'])
        self.assertEqual(r['headroom'],self.s['budget']-payroll(self.s)-self.s['career']['offers']['p145']['wage_delta'])
        self.act('complete_offer',id='p145')
        self.assertEqual(plan['cash_after'],self.s['cash'])
        self.assertEqual(plan['headroom'],self.s['budget']-payroll(self.s))

    def test_draft_reviews_duration_and_renewal_liability_without_mutation(self):
        p=next(p for p in self.s['players'] if p['id']=='p0');p['contract_end']=50
        self.act('enquire',id='p0');v=view(self.s);before=deepcopy(v);o=v['career']['offers']['p0']
        draft=dict(wage=p['wage']+10000,fee=0,duration=3)
        r=review(v,o,draft)
        self.assertEqual(r['end'],316)
        self.assertEqual(r['wage_delta'],10000)
        self.assertEqual(r['additional'],r['total']-p['wage']*50//7)
        self.assertEqual(v,before)

    def test_late_medical_rejected_atomically_and_cutoff_is_inclusive(self):
        # Narrow the content's season opening window without skipping financial days.
        self.s['career']['start']=-27  # Window closes on day 1; medical takes 2 days.
        self.act('enquire',id='p144')
        p=next(p for p in self.s['players'] if p['id']=='p144')
        self.act('propose_offer',id=p['id'],wage=p['wage'],fee=p['fee'],duration=2)
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'medical cannot finish'):self.act('accept_offer',id=p['id'])
        self.assertEqual(self.s,before)
        self.assertTrue(review(view(self.s),self.s['career']['offers'][p['id']])['reasons'])
        self.s['career']['start']=-26  # Completion remains legal on day 2.
        self.act('accept_offer',id=p['id']);self.act('continue');self.act('continue')
        self.act('complete_offer',id=p['id'])
        self.assertEqual(next(player for player in self.s['players'] if player['id']=='p144')['club'],'c0')

    def test_reopened_discussions_retain_history_and_save_roundtrip(self):
        self.act('enquire',id='p144');self.act('withdraw_offer',id='p144')
        original=deepcopy(self.s['career']['offers']['p144'])
        self.act('enquire',id='p144')
        self.assertEqual(self.s['career']['offer_history'],[original])
        self.assertNotEqual(original['id'],self.s['career']['offers']['p144']['id'])
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'career.sqlite3';save(self.s,path);self.assertEqual(load(path),self.s)

    def test_completion_revalidates_manager_and_attention_does_not_leak(self):
        prepare_signings(self,['p144']);v=view(self.s)
        self.assertEqual(attention(v)[0]['player'],'p144')
        self.s['manager']=None;before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'manager'):self.act('complete_offer',id='p144')
        self.assertEqual(self.s,before)
        self.assertIn('Appoint a manager first.',review(view(self.s),self.s['career']['offers']['p144'])['reasons'])
        for p in self.s['players']:p['attrs']={k:1 for k in p['attrs']}
        self.assertEqual(attention(view(self.s)),attention(v))
