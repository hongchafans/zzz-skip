import unittest

from main import pick_match_by_priority
from template_matching import TemplateMatch


class PickMatchByPriorityTests(unittest.TestCase):
    def test_returns_highest_priority_match(self) -> None:
        matches = [
            TemplateMatch(score=0.99, position=(10, 10), template_name="skip_menu.png"),
            TemplateMatch(score=0.98, position=(20, 20), template_name="confirm.png"),
            TemplateMatch(score=0.97, position=(30, 30), template_name="dialog_main.png"),
        ]

        selected = pick_match_by_priority(matches)

        self.assertIsNotNone(selected)
        self.assertEqual(selected.template_name, "confirm.png")

    def test_returns_none_when_no_match_exists(self) -> None:
        self.assertIsNone(pick_match_by_priority([]))


if __name__ == "__main__":
    unittest.main()
