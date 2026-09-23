from copy import deepcopy
import unittest
import test_qol_ui
from club_chairman import dynamics,playing_time
from club_chairman.simulation import view


class DynamicsInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown
    click=test_qol_ui.QolInterfaceTests.click

    def test_squad_route_pagination_and_read_only_views(self):
        a=self.app;a.nav('Squad');self.click('Club dynamics')
        self.assertEqual(a.tab,'Dynamics');before=deepcopy(a.state)
        self.click('Connections');self.click('Staff reactions');self.click('Meetings');self.click('Concerns')
        self.assertEqual(before,a.state);self.click('Back to squad');self.assertEqual(a.tab,'Squad')

    def test_concern_opens_actual_player_support_and_staff_route(self):
        a=self.app;p=a.state['players'][2];playing_time.sign(a.state,p,'c0','Key starter','test')
        playing_time.active(a.state,p['id'])['concern']={'id':'test:shortfall','since':0}
        a.v=view(a.state);a.nav('Staff');self.click('Club dynamics');self.click('Review privately')
        self.assertEqual(a.profile,p['id']);self.assertEqual(a.profile_tab,'Relationship')

    def test_staff_followup_cancel_and_confirm(self):
        a=self.app;a.command('hire',id='m0');mid=a.state['manager']['id']
        a.state['dynamics']['staff_links']['c0|'+mid]=dict(person=mid,club='c0',trust=47,respect=48,alignment=50,
            concern={'event':'test','day':0,'reason':'Concerned about owner pressure'},meetings=[])
        a.v=view(a.state);a.nav('Squad');self.click('Club dynamics');before=deepcopy(a.state)
        self.click('Respect remit');self.click('Cancel');self.assertEqual(before,a.state)
        self.click('Respect remit');self.click('Confirm')
        self.assertEqual(len(a.state['dynamics']['staff_links']['c0|'+mid]['meetings']),1)
        self.click('Meetings');a.render()

    def test_monthly_review_routes_to_concerns(self):
        a=self.app;a.state['day']=28;dynamics.process_day(a.state);a.v=view(a.state)
        a.nav('Inbox');a.inbox_selection=len(a.state['inbox'])-1
        self.click('Review club dynamics');self.assertEqual(a.tab,'Dynamics');self.assertEqual(a.screen,'Squad')
