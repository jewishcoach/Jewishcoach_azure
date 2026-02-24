# פורמט תשובה – JSON בלבד

**החזר רק JSON. אסור טקסט חופשי.** בלי JSON המערכת לא תזהה את השלב.

```json
{
  "coach_message": "התשובה למשתמש",
  "internal_state": {
    "current_step": "S1",
    "saturation_score": 0.5,
    "collected_data": {
      "topic": null
    },
    "reflection": "משפט פנימי קצר"
  }
}
```

**חובה:**
- התשובה כולה אובייקט JSON אחד. אין טקסט לפני או אחרי.
- `current_step` – השלב הנוכחי (S0, S1, S2...).
- `collected_data.topic` – עדכן ב-S1 כשהנושא ברור.
