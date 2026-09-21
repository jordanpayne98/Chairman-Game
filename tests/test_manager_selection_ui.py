import json
import unittest
from club_chairman import football
from club_chairman.simulation import view,record_result
import test_qol_ui


class ManagerSelectionInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_starting_selection_report_pages_and_archives_without_mutation(self):
        a=self.app;a.command('hire',id='m0')
        f=next(f for f in a.state['fixtures'] if f['home']=='c0')
        a.state['match']=football.start(a.state,f);a.v=view(a.state);a.nav('Matchday')
        self.click('Selection');seen=[];original=a.text
        def capture(value,*args,**kwargs):seen.append(value);return original(value,*args,**kwargs)
        a.text=capture;before=json.dumps(a.state,sort_keys=True);a.render()
        self.assertTrue(any(v.startswith('Starting plan') for v in seen))
        self.click('More selections');self.assertEqual(a.page,1);self.click('Previous selections')
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        while not football.finished(a.state['match']):football.step(a.state,a.state['match'])
        record_result(a.state,a.state['match']);a.state['match']=None;a.v=view(a.state);a.match_report=f['id']
        seen.clear();a.render();self.assertTrue(any(v.startswith('Starting plan') for v in seen))
        a.state['fixtures'][a.state['fixtures'].index(f)]['result'].pop('selection_plans');a.v=view(a.state)
        seen.clear();a.render();self.assertTrue(any('older match' in v for v in seen))


if __name__=='__main__':unittest.main()
