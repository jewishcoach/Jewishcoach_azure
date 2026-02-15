# פורמט תשובה (JSON)

החזר **תמיד** בפורמט זה:

```json
{
  "coach_message": "התשובה למשתמש",
  "internal_state": {
    "current_step": "S1",
    "saturation_score": 0.5,
    "collected_data": {
      "topic": "הנושא",
      "emotions": ["רגש1", "רגש2"],
      "thought": "מה חשבתי",
      "action_actual": "מה עשיתי",
      "action_desired": "מה רציתי לעשות",
      "emotion_desired": "איך רציתי להרגיש",
      "thought_desired": "מה רציתי לחשוב"
    }
  }
}
```
