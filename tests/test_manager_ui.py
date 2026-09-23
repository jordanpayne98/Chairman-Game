import json
import unittest
from club_chairman.simulation import view
import test_qol_ui


class ManagerInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_profile_assess_expire_refresh_appoint_and_display(self):
        a=self.app;a.nav('Staff');self.click('Manager profile',0)
        seen=[];original=a.text
        def capture(value,*args,**kwargs):seen.append(value);return original(value,*args,**kwargs)
        a.text=capture;a.render();self.assertIn('Not assessed',seen)
        self.click('Assess manager');seen.clear();a.render()
        self.assertIn('Adaptability',seen);self.assertTrue(any(v.startswith('Fully assessed') for v in seen))
        a.state['day']=28;a.v=view(a.state);seen.clear();before=json.dumps(a.state,sort_keys=True);a.render()
        self.assertTrue(any(v.startswith('Stale') for v in seen));self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        self.click('Refresh manager assessment');self.click('Back to manager office')
        self.click('Review '+a.v['manager_candidates'][0]["name"]);self.click('Confirm');self.click('Manager profile',0);seen.clear();a.render()
        self.assertIn('Club access',seen);self.assertTrue(any(v.startswith('Current ability') for v in seen))


if __name__=='__main__':unittest.main()
