import unittest

from src.faq_service import WorkOrderContext, local_candidates, suggest_faq


class FaqDecisionTest(unittest.TestCase):
    def test_photo_question_prefers_damage_entry(self) -> None:
        context = WorkOrderContext(
            question="Where is the damage photo?",
            photo_ref="work-orders/WO-1042/valve.jpg",
            dispatch_status="pending",
            technician_follow_up="replace valve",
        )
        self.assertEqual(suggest_faq(context).reason, "photo")
        self.assertEqual(local_candidates(context)[0].question, "How do I report a damaged valve?")


if __name__ == "__main__":
    unittest.main()
