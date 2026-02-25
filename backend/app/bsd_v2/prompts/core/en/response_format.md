# Response Format – JSON Only

**Return only JSON. No free text.** Without JSON the system cannot detect the stage.

```json
{
  "coach_message": "response to user",
  "internal_state": {
    "current_step": "S1",
    "saturation_score": 0.5,
    "collected_data": {
      "topic": null
    },
    "reflection": "short internal note"
  }
}
```

**Required:**
- The entire response is one JSON object. No text before or after.
- `current_step` – Current stage (S0, S1, S2...).
- `collected_data` – **Important!** Update every turn with new data the user provided. S1: topic. S3: emotions. S4: thought. S5: action_actual, action_desired. S6: gap_name, gap_score. S7: pattern. Insights are shown live to the user – never return empty collected_data.
