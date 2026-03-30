# מערכת תשלומים ומנויים 💳

## סקירה כללית

המערכת כוללת 3 חבילות:
- **BASIC** (חינם) - 150 הודעות/חודש
- **PREMIUM** (₪89/חודש) - 100 הודעות + 30 דק' דיבור
- **PRO** (₪249/חודש) - ללא הגבלה

---

## 🎫 קופון מיוחד: BSD100

**קוד הקופון:** `BSD100`
- ✨ **גישה לצמיתות לחבילת PRO בחינם**
- 🎯 הודעות ללא הגבלה
- 🗣️ זמן דיבור ללא הגבלה
- 📊 כל הפיצ'רים המתקדמים
- ✅ כבר מוכן לשימוש!

---

## התקנה והפעלה

### 1️⃣ Backend - הרצת המיגרציה

המיגרציה כבר רצה! אבל אם צריך להריץ שוב:

```bash
cd backend
source venv/bin/activate
python -m migrations.002_add_billing_tables
```

### 2️⃣ בדיקת הקופון

```bash
python -m scripts.add_bsd100_coupon
```

### 3️⃣ הוספת הנתיב בפרונטאנד

הוסף את `BillingPage` ל-App routing:

```tsx
// In App.tsx or router config
import { BillingPage } from './components/BillingPage';

// Add route:
<Route path="/billing" element={<BillingPage />} />
```

---

## שימוש ב-API

### 📋 קבלת סקירת חיוב

```bash
GET /api/billing/overview
Authorization: Bearer {token}
```

תשובה:
```json
{
  "current_plan": "basic",
  "usage": {
    "messages_used": 5,
    "messages_limit": 150,
    "speech_minutes_used": 0,
    "speech_minutes_limit": 10
  },
  "available_plans": [...],
  "has_active_coupon": false
}
```

### 🎁 הפעלת קופון

```bash
POST /api/billing/redeem-coupon
Authorization: Bearer {token}
Content-Type: application/json

{
  "code": "BSD100"
}
```

תשובה מוצלחת:
```json
{
  "success": true,
  "message": "Coupon BSD100 redeemed successfully!",
  "plan_granted": "pro",
  "expires_at": null
}
```

### 📊 בדיקת שימוש נוכחי

```bash
GET /api/billing/usage
Authorization: Bearer {token}
```

### 🚫 בדיקת מגבלות

```bash
POST /api/billing/check-limit/message
Authorization: Bearer {token}
```

תשובה כשאין מכסה:
```json
{
  "has_quota": false,
  "message": "You have reached your message limit",
  "current_plan": "basic",
  "upgrade_available": true
}
```

---

## Middleware למגבלות שימוש

להוסיף למסלולים שצריכים מגבלה:

```python
from app.middleware.usage_limiter import check_message_limit

@router.post("/messages")
async def send_message(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check limits BEFORE processing
    await check_message_limit(request, user, db)
    
    # Process message...
```

---

## מבנה הטבלאות

### `subscriptions`
- `id`: מזהה מנוי
- `user_id`: מזהה משתמש
- `plan`: "basic" | "premium" | "pro"
- `status`: "active" | "canceled" | "expired"
- `coupon_code`: קוד קופון (אם קיים)
- `current_period_start/end`: תקופת חיוב

### `usage_records`
- `id`: מזהה רשומה
- `user_id`: מזהה משתמש
- `period_start/end`: תקופת מדידה
- `messages_used`: מספר הודעות בשימוש
- `speech_minutes_used`: דקות דיבור בשימוש

### `coupons`
- `id`: מזהה קופון
- `code`: קוד הקופון (unique)
- `plan_granted`: "premium" | "pro"
- `duration_days`: מספר ימים (null = לצמיתות)
- `max_uses`: מספר שימושים מקסימלי (null = ללא הגבלה)
- `is_active`: פעיל/לא פעיל

### `coupon_redemptions`
- `id`: מזהה פדיון
- `user_id`: מי פדה
- `coupon_id`: איזה קופון
- `redeemed_at`: מתי
- `expires_at`: תוקף (null = לצמיתות)
- `is_active`: פעיל/לא פעיל

---

## הוספת קופונים נוספים

```python
from app.models import Coupon
from app.database import SessionLocal

db = SessionLocal()

# קופון ל-30 ימים של PREMIUM
new_coupon = Coupon(
    code="WELCOME30",
    plan_granted="premium",
    duration_days=30,
    max_uses=100,
    is_active=True,
    description="Welcome offer - 30 days premium"
)

db.add(new_coupon)
db.commit()
```

---

## אינטגרציה עם Stripe (עתידי)

התשתית מוכנה לאינטגרציה עם Stripe:

1. **התקנה:**
```bash
pip install stripe
```

2. **הוספת Keys ל-.env:**
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

3. **יצירת מוצרים ב-Stripe Dashboard:**
   - Premium: ₪89/חודש
   - Pro: ₪249/חודש

4. **הוספת Price IDs ל-schemas/billing.py**

5. **יצירת Checkout Session** - הקוד כבר מוכן ב-`routers/billing.py`

---

## בדיקה מהירה

### 1. בדוק שהבאקאנד רץ:
```bash
curl http://localhost:8000/api/billing/plans
```

### 2. פתח את הפרונטאנד:
```
http://localhost:5173/billing
```

### 3. נסה להפעיל BSD100:
- לחץ על "יש לך קוד קופון?"
- הזן: `BSD100`
- לחץ "הפעל"
- ✅ אמור לקבל PRO לצמיתות!

---

## FAQ

**Q: איך אני יכול לראות את כל הקופונים?**

```bash
cd backend
python
>>> from app.database import SessionLocal
>>> from app.models import Coupon
>>> db = SessionLocal()
>>> coupons = db.query(Coupon).all()
>>> for c in coupons:
...     print(f"{c.code}: {c.plan_granted} ({c.current_uses} uses)")
```

**Q: איך אני מוסיף משתמש חדש ישירות ל-PRO?**

```python
from app.models import User, Subscription
from app.database import SessionLocal

db = SessionLocal()
user = db.query(User).filter_by(email="user@example.com").first()
user.current_plan = "pro"

subscription = Subscription(
    user_id=user.id,
    plan="pro",
    status="active"
)
db.add(subscription)
db.commit()
```

**Q: איך למחוק את המגבלות זמנית?**

פשוט עדכן את המשתמש ל-PRO או שנה את `PLAN_LIMITS` ב-`schemas/billing.py`

---

## תמיכה

אם יש בעיות, בדוק:
1. ✅ המיגרציה רצה בהצלחה
2. ✅ הקופון BSD100 קיים במסד הנתונים
3. ✅ הטוקן של המשתמש תקף
4. ✅ ה-API endpoint `/api/billing/*` עובד

---

🎉 **המערכת מוכנה לשימוש!**

קוד BSD100 פעיל ומחכה למשתמשים הראשונים! 🚀



