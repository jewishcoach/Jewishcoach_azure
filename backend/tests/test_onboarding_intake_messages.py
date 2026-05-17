"""Regression-style checks for deterministic onboarding copy (no LLM)."""

from app.bsd.onboarding_intake_messages import pick_intake_assistant_message


def test_pick_name_first_vs_redirect_hebrew():
    first = pick_intake_assistant_message(
        "he", missing="display_name", gender=None, user_message_count=1
    )
    redirect = pick_intake_assistant_message(
        "he", missing="display_name", gender=None, user_message_count=2
    )
    assert first != redirect
    assert "נשארתי" in redirect or "קשר" in redirect


def test_pick_topic_gendered_hebrew():
    male = pick_intake_assistant_message(
        "he", missing="topic", gender="male", user_message_count=3
    )
    female = pick_intake_assistant_message(
        "he", missing="topic", gender="female", user_message_count=3
    )
    assert male == female
    assert "נושא" in male and "מחייב" in male


def test_pick_topic_with_gender_skipped_hebrew():
    msg = pick_intake_assistant_message(
        "he",
        missing="topic",
        gender=None,
        user_message_count=3,
        gender_skipped=True,
    )
    male = pick_intake_assistant_message(
        "he", missing="topic", gender="male", user_message_count=3
    )
    assert msg == male
    assert "נושא" in msg
