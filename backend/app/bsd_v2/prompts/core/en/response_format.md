# Response Format (JSON)

Always return valid JSON only (no extra text outside JSON):

```json
{
  "coach_message": "response to user",
  "internal_state": {
    "current_step": "S1",
    "saturation_score": 0.5,
    "collected_data": {
      "topic": null,
      "event_description": null,
      "emotions": [],
      "thought": null,
      "action_actual": null,
      "action_desired": null,
      "emotion_desired": null,
      "thought_desired": null,
      "gap_name": null,
      "gap_score": null,
      "pattern": null,
      "stance": { "gains": [], "losses": [] },
      "forces": { "source": [], "nature": [] },
      "renewal": null,
      "vision": null,
      "commitment": null
    },
    "reflection": "short internal reasoning note"
  }
}
```

Rules:
- Keep `current_step` and `saturation_score` aligned with the stage.
- Update only the data you confidently have; keep other fields null/empty.
- `coach_message` should be one natural coaching prompt (not advice).
