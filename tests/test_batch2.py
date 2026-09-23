from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from club_chairman import scouting,pathways,people,career,market
from club_chairman.simulation import new_career,execute,Command,view,validate,payroll
from club_chairman.persistence import migrate,save,load


class Batch2Tests(unittest.TestCase):
    def setUp(self):self.s=new_career(83)
    def act(self,action,**payload):
        c=Command('batch2:'+str(self.s['revision']),self.s['revision'],action,payload)
        self.s,_=execute(self.s,c);return c

    def test_queue_partial_batch_charge_and_duplicate_receipt(self):
        p=career.person(self.s,'p144');p['nationality']='France';q=scouting.quote(self.s,p);cash=self.s['cash']
        self.assertEqual(q['cost'],2*self.s['config']['scout_fee'])
        c=self.act('scout_batch',ids=['p144','p144','missing','p145'])
        jobs=self.s['scouting_work']['jobs'];self.assertEqual(len(jobs),2)
        self.assertGreaterEqual(jobs[1]['start'],jobs[0]['due']);self.assertEqual(self.s['cash'],cash-sum(j['cost'] for j in jobs))
        self.assertEqual([r['ok'] for r in self.s['scouting_work']['history']],[True,False,True])
        again,_=execute(self.s,c);self.assertEqual(again,self.s)
        self.s['day']=max(j['due'] for j in jobs);scouting.process_day(self.s);before=deepcopy(self.s);scouting.process_day(self.s);self.assertEqual(before,self.s)
        r=people.observed_report(self.s,career.person(self.s,'p144'));self.assertEqual(r['overall'][0],r['overall'][1]);self.assertNotEqual(r['potential'][0],r['potential'][1])

    def test_recommendations_use_observed_evidence(self):
        p=career.person(self.s,'p144');self.s['reports'][p['id']]=people.report(self.s,p,'Trial',12)
        self.act('recruitment_brief',role=p['role'],min_age=16,max_age=45,ceiling=100000000,playing_role='Rotation')
        before=scouting.recommend(self.s);self.assertTrue(before)
        p=career.person(self.s,'p144');p['potential']=99
        for k in p['attrs']:p['attrs'][k]=99
        self.assertEqual(before,scouting.recommend(self.s))

    def test_development_fixtures_once_and_separate_records(self):
        f=next(f for f in self.s['pathways']['fixtures'] if f['group']=='Youth' and f['home']=='c0');self.s['day']=f['day']
        before=[(p['id'],p['goals'],p['appearances']) for p in self.s['players']];cash=self.s['cash'];ledger=deepcopy(self.s['ledger']);clubs=deepcopy(self.s['clubs'])
        pathways.process_day(self.s);self.assertEqual(f['status'],'played');self.assertTrue(self.s['pathways']['records'])
        once=deepcopy(self.s);pathways.process_day(self.s);self.assertEqual(once,self.s)
        self.assertEqual(before,[(p['id'],p['goals'],p['appearances']) for p in self.s['players']]);self.assertEqual(cash,self.s['cash']);self.assertEqual(ledger,self.s['ledger']);self.assertEqual(clubs,self.s['clubs'])
        table=pathways.standings(self.s,'Youth');self.assertEqual(sum(r['gf'] for r in table),sum(r['ga'] for r in table));validate(self.s)

    def test_injury_and_nearby_senior_match_block_reserves(self):
        p=next(p for p in self.s['players'] if p['club']=='c0' and p['development']['group']=='Reserves')
        self.s['day']=8;p['injury_until']=10;self.assertFalse(pathways.eligible(self.s,p,'c0','Reserves'))
        p['injury_until']=0;self.s['fixtures'].append(dict(id='near',day=9,home='c0',away='c1',result=None));self.assertFalse(pathways.eligible(self.s,p,'c0','Reserves'))

    def test_save_continuation_and_no_population_migration(self):
        self.act('scout',id='p144');old=deepcopy(self.s);old['schema']=26
        old.pop('pathways');old.pop('scouting_work');old['config'].pop('pathways');old['config'].pop('scouting_work')
        for p in old['players']:
            for k in ('group','exposure','last_played','pathway_history'):p['development'].pop(k)
        before=deepcopy(old);up=migrate(old);self.assertEqual(old,before);self.assertEqual(len(up['players']),len(old['players']));self.assertEqual(migrate(up),up)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.sqlite3';save(self.s,path);other=load(path);self.assertEqual(other,self.s)
            for s in (self.s,other):s['day']=8;pathways.process_day(s);scouting.process_day(s);people.process_day(s)
            self.assertEqual(self.s,other)

    def test_renewal_money_authority_and_group_terms(self):
        p=next(p for p in self.s['players'] if p['club']=='c0' and p['youth']);pid=p['id'];p['contract_end']=20;wage=p['wage']
        market.post(self.s,'c0','test:empty',-self.s['cash'],'Test fixture');before=deepcopy(self.s)
        with self.assertRaises(ValueError):self.act('academy_renew',id=pid)
        self.assertEqual(self.s,before);self.act('fund');self.act('budget',value=payroll(self.s)+100000);cash=self.s['cash'];self.act('academy_renew',id=pid)
        p=career.person(self.s,pid);self.assertGreater(p['contract_end'],20);self.assertEqual(p['wage'],wage);self.assertEqual(self.s['cash'],cash)
        with self.assertRaises(ValueError):self.act('academy_renew',id=pid)
        p=career.person(self.s,'p2');terms=(p['wage'],p['contract_end']);self.act('pathway_group',id='p2',group='Reserves');p=career.person(self.s,'p2');self.assertEqual(terms,(p['wage'],p['contract_end']))
        self.assertNotIn('potential',str(pathways.public(self.s)))

    def test_annual_population_has_capacity_fee_and_idempotence(self):
        self.s['day']=365;self.s['config']['club_ai']['payroll_income_percent']=200
        for c in self.s['clubs'][1:]:market.post(self.s,c['id'],'test:fund',100000000,'Test fixture')
        before=len(self.s['players']);pathways.population_checkpoint(self.s);decisions=self.s['pathways']['decisions'];self.assertGreater(len(self.s['players']),before)
        for c in self.s['clubs'][1:]:
            admissions=[r for r in decisions if r['club']==c['id']];self.assertLessEqual(len(admissions),6)
            charges=[e for e in self.s['market']['accounts'][c['id']]['ledger'] if e['reason']=='Annual academy admission'];self.assertEqual(-sum(e['amount'] for e in charges),sum(r['fee'] for r in admissions))
        once=deepcopy(self.s);pathways.population_checkpoint(self.s);self.assertEqual(once,self.s)
