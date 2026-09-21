from copy import deepcopy
import unittest
from club_chairman import preparation
from club_chairman.simulation import view
import test_qol_ui


class PreparationInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_training_report_unknown_learning_and_read_only_navigation(self):
        a=self.app;a.command('hire',id='m0');a.nav('Staff');self.click('Training report')
        seen=[];original=a.text
        def capture(value,*args,**kwargs):seen.append(value);return original(value,*args,**kwargs)
        a.text=capture;before=deepcopy(a.state);a.render()
        self.assertIn('Not assessed',seen);self.assertEqual(a.state,before)
        a.state['day']=1;preparation.process_day(a.state);a.v=view(a.state);seen.clear();a.render()
        self.assertIn('Trained',seen);self.assertIn('1 session / 0 min',seen)
        self.click('Next');self.assertEqual(a.page,1);self.click('Previous');self.assertEqual(a.page,0)
        self.click('Back to manager office');self.assertFalse(a.training_report)


if __name__=='__main__':unittest.main()
