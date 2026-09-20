from copy import deepcopy
import unittest
from club_chairman.simulation import new_career, execute, Command, view, posting, payroll
from club_chairman.planning import forecast


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.s=new_career(83)
        self.act('hire',id='m0')

    def act(self,action,**data):
        self.s,_=execute(self.s,Command(str(self.s['revision']),self.s['revision'],action,data))

    def test_same_day_guaranteed_income_can_pay_transfer_and_payroll(self):
        self.s['day']=6;self.s['owner_cash']=0
        due=payroll(self.s)+self.s['config']['weekly_overheads']
        self.s['accrued_costs']=6*due
        self.s['config']['weekly_sponsor']=due+200000
        posting(self.s,'fixture:low-cash',100000-self.s['cash'],'Test opening cash')
        self.s['market']['obligations'].append(dict(id='fixture:bill',source='c0',target='c1',amount=200000,due=7,status='scheduled',player='p20'))
        expected=forecast(view(self.s),horizon=1)['cash']
        self.act('continue')
        self.assertEqual(self.s['day'],7);self.assertEqual(self.s['cash'],expected)
        self.assertEqual(self.s['market']['obligations'][0]['status'],'paid')

    def test_unlisted_owned_player_can_leave_a_full_registration_list(self):
        for p in self.s['players']:p['age']=25
        self.s['registration']['c0'].remove('p2')
        self.s['config']['competition']['senior_limit']=17
        self.s['registration']['c1'].remove('p20')
        self.s['registration']['c1'].remove('p21')
        base=deepcopy(self.s)
        for action in ('sale_enquire','loan_enquire'):
            self.s=deepcopy(base);self.act(action,id='p2',club='c1')
            deal=next(reversed(self.s['market']['deals'].values()))
            self.assertEqual((deal['source'],deal['target']),('c0','c1'))
            self.assertNotIn('p2',self.s['registration']['c0'])

    def test_external_fitness_cannot_change_the_public_snapshot(self):
        before=view(self.s)
        for p in self.s['players']:
            if p['club']!='c0':
                p.update(condition=1,fatigue=99,sharpness=1,morale=1,injury_until=999)
                p['medical']=dict(type='Hidden injury',stage='rehabilitation',estimate=[99,999])
        self.assertEqual(before,view(self.s))


if __name__=='__main__':unittest.main()
