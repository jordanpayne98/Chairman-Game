import json
import unittest
import pygame
from club_chairman.simulation import view
from club_chairman import delegation
import test_qol_ui
import test_staff_delegation


class StaffInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click
    key=test_qol_ui.QolInterfaceTests.key

    def prepared(self):
        domain=test_staff_delegation.StaffDelegationTests();domain.setUp()
        domain.hire_staff(('staff:0:0','staff:1:0','staff:7:0'))
        self.app.state=domain.s;self.app.v=view(domain.s);self.app.nav('Staff')

    def test_contact_interview_terms_and_appointment_use_rendered_controls(self):
        a=self.app;a.command('budget',value=4000000);a.command('hire',id='m0');a.nav('Staff')
        self.click('People');self.click('Open staff profile',0);pid=a.staff_person
        self.click('Contact candidate');self.assertEqual(a.state['staff']['offers'][pid]['status'],'contact')
        self.click('Continue  >');self.click('Conduct interview');self.click('Send staff proposal')
        cash=a.state['cash'];self.click('Review staff appointment');self.assertIsNotNone(a.modal)
        self.assertEqual(a.state['cash'],cash);self.click('Confirm')
        self.assertEqual(a.state['staff']['offers'][pid]['status'],'starting')
        self.assertIsNotNone(next(p for p in a.state['staff']['people'] if p['id']==pid)['pending'])

    def test_coverage_and_preset_preview_leave_state_unchanged_until_confirmed(self):
        self.prepared();a=self.app;self.click('Responsibilities');before=json.dumps(a.state,sort_keys=True)
        self.click('Review coverage');self.assertEqual(before,json.dumps(a.state,sort_keys=True));self.click('Cancel')
        self.click('Review coverage');self.click('Confirm')
        self.assertTrue(all(r['delegate'] for r in a.state['delegation']['responsibilities'].values()))
        before=json.dumps(a.state,sort_keys=True);self.click('Executive');self.assertEqual(before,json.dumps(a.state,sort_keys=True));self.click('Confirm')
        self.assertTrue(all(r['mode']=='Autonomous' for r in a.state['delegation']['responsibilities'].values()))

    def test_authority_draft_survives_navigation_and_declined_review(self):
        self.prepared();a=self.app;self.click('Responsibilities');self.click('Edit responsibility',0)
        self.click('Limit −£5k');draft=dict(a.authority_draft);before=json.dumps(a.state,sort_keys=True)
        self.click('Overview');self.click('Staff');self.assertEqual(a.authority_draft,draft)
        self.click('Review responsibility');self.click('Cancel');self.assertEqual(before,json.dumps(a.state,sort_keys=True))
        self.assertEqual(a.authority_draft,draft)

    def test_approval_and_report_record_one_real_scouting_payment(self):
        self.prepared();a=self.app
        a.command('delegation_set',key='recruitment',delegate='staff:0:0',mode='Approval required',limit=0,days=365,objective='Maintain')
        delegation.propose(a.state,'recruitment','scout',dict(id='p144'),'Assess potential squad cover.')
        a.v=view(a.state);a.staff_section('Approvals');before=a.state['cash']
        self.click('Review proposal');self.assertEqual(a.state['cash'],before);self.click('Confirm')
        self.assertEqual(before-a.state['cash'],a.state['config']['scout_fee'])
        self.click('Reports');state=json.dumps(a.state,sort_keys=True);a.render();self.assertEqual(state,json.dumps(a.state,sort_keys=True))
        self.assertEqual(len(a.state['delegation']['log']),1)

    def test_staff_workflow_controls_remain_reachable_at_maximum_zoom(self):
        self.prepared();a=self.app;self.click('People');a.staff_person='staff:0:0';a.change_zoom(1.75)
        before=json.dumps(a.state,sort_keys=True)
        for _ in range(55):
            self.key(pygame.K_TAB);a.render();rect=a.buttons[a.focus%len(a.buttons)][0]
            point=(rect.centerx*a.scale+a.offset[0],rect.centery*a.scale+a.offset[1])
            self.assertTrue(0<=point[0]<=a.window.get_width() and 0<=point[1]<=a.window.get_height())
        self.assertEqual(before,json.dumps(a.state,sort_keys=True))


if __name__=='__main__':unittest.main()
