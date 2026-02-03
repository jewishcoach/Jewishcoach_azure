import unittest

from app.bsd.reasoner import decide


class TestBsdReasoner(unittest.IsolatedAsyncioTestCase):
    async def test_s3_emotions_advances_with_four(self):
        d = await decide(stage="S3", user_message="כעס, פחד, עצב, בושה", language="he")
        self.assertEqual(d.decision, "advance")
        self.assertIsNotNone(d.next_stage)
        self.assertGreaterEqual(len(d.extracted.get("emotions_list", [])), 4)

    async def test_s3_emotions_loops_with_three(self):
        d = await decide(stage="S3", user_message="כעס, פחד, עצב", language="he")
        self.assertEqual(d.decision, "loop")
        self.assertIsNone(d.next_stage)


if __name__ == "__main__":
    unittest.main()




