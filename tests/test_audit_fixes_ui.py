import unittest
from club_chairman import career
from club_chairman.simulation import view
import test_qol_ui


class AuditFixInterfaceTests(unittest.TestCase):
    setUp=test_qol_ui.QolInterfaceTests.setUp
    tearDown=test_qol_ui.QolInterfaceTests.tearDown

    def test_retired_profile_has_history_without_recruitment_actions(self):
        a=self.app;career.retire_player(a.state,career.person(a.state,'p2'))
        a.v=view(a.state);a.open_profile('p2');a.profile_tab='Contract'
        labels=[];texts=[];button=a.button;text=a.text
        def capture_button(label,*args,**kwargs):
            labels.append(label);return button(label,*args,**kwargs)
        def capture_text(value,*args,**kwargs):
            texts.append(value);return text(value,*args,**kwargs)
        a.button=capture_button;a.text=capture_text
        a.render()
        self.assertNotIn('Request scouting',labels);self.assertNotIn('Negotiate contract',labels)
        self.assertIn('Reputation history',labels)
        self.assertTrue(any(str(t).startswith('Retired: ') for t in texts))


if __name__=='__main__':unittest.main()
