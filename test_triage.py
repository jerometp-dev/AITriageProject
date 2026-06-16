import unittest
from pydantic import ValidationError
from triage_engine import TriageAnalysis 

class TestDataIntegrity(unittest.TestCase):

    def test_valid_analysis_payload_passes(self):
        """Proves that a correctly structured AI analysis payload passes validation smoothly."""
        valid_data = {
            "intent": "technical_support",
            "sentiment": "frustrated",
            "priority_score": 5,
            "summary": "Our GoHighLevel workflow isn't syncing data to our external system.",
            "recommended_action": "escalate_to_human"  # Fixed to match your strict Literal routing rules!
        }
        analysis = TriageAnalysis(**valid_data)
        self.assertEqual(analysis.intent, "technical_support")
        self.assertEqual(analysis.priority_score, 5)

    def test_missing_required_fields_fails_cleanly(self):
        """Proves that a payload missing key analytical data is caught and rejected."""
        invalid_data = {
            "intent": "billing_inquiry",
            "sentiment": "neutral"
            # Missing priority_score, summary, and recommended_action
        }
        with self.assertRaises(ValidationError):
            TriageAnalysis(**invalid_data)

    def test_incorrect_data_types_fail(self):
        """Proves that malformed data types (like text inside a score integer) are rejected."""
        bad_data = {
            "intent": "technical_support",
            "sentiment": "urgent",
            "priority_score": "HIGH_PRIORITY_STRING",
            "summary": "Testing a broken payload format.",
            "recommended_action": "escalate_to_human"
        }
        with self.assertRaises(ValidationError):
            TriageAnalysis(**bad_data)

if __name__ == "__main__":
    unittest.main()