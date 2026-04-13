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
- `collected_data` – **Important!** Update every turn with new data the user provided. S1: `topic`. S2: `event_description` (the event, in their words) **and** `topic` — **one short phrase** for the **current coaching focus**. Whenever the trainee refines or corrects the focus (e.g. joy → joy + lightness), **you must** update `topic` to match; do not keep an outdated S1 wording once a new formulation is clear. S3: emotions. S4: thought. S5: action_actual. S6: action_desired, emotion_desired, thought_desired. S7: gap_name, gap_score; also `gap_booklet_moves` (array of strings: belief, opportunity, dwelling, waiver, authenticity) — keep cumulative so you never repeat the same booklet question type. S8: pattern. S9: paradigm ("this is how I am" action-paradigm). S10: in `stance` fill `reality_belief` (reality perception / stance wording) and `activation_trigger` (trigger). S11: in `stance` fill `gains` and `losses` (profit & loss table). S12: forces (source/nature - KaMaZ) and `offer_trait_picker` (boolean): **false** on most S12 turns; **true only** on the turn where you have finished the KMZ explanation and verbal consolidation per the booklet and you invite the trainee to the forces screen — then the app shows the form. S13: renewal (new choice/new stance). S14: vision. S15: commitment (concrete first step). Insights are shown live to the user – never return empty collected_data.
- `entities` – **Critical context memory!** Whenever the user mentions names, places, or specific examples — add them to `entities`. This allows you to reference real details ("boss Daniel", "the small meeting room") throughout the conversation without forgetting them.
