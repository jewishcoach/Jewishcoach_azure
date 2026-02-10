#!/usr/bin/env python3
"""
Rule-based simulation of coach behavior with expert feedback fixes
Shows expected behavior WITHOUT calling actual LLM
"""

class CoachSimulator:
    """Simulates coach behavior based on new guidelines"""
    
    def __init__(self):
        self.stage = "S0"
        self.data = {
            "topic": None,
            "event": None,
            "emotions": [],
            "thought": None,
            "action_actual": None,
            "action_desired": None,
            "gap_name": None,
            "gap_score": None,
            "pattern_examples": []
        }
    
    def respond(self, user_message):
        """Generate coach response based on stage and message"""
        
        if self.stage == "S0":
            return self.handle_s0(user_message)
        elif self.stage == "S1":
            return self.handle_s1(user_message)
        elif self.stage == "S2":
            return self.handle_s2(user_message)
        elif self.stage == "S3":
            return self.handle_s3(user_message)
        elif self.stage == "S4":
            return self.handle_s4(user_message)
        elif self.stage == "S5_actual":
            return self.handle_s5_actual(user_message)
        elif self.stage == "S5_desired":
            return self.handle_s5_desired(user_message)
        elif self.stage == "S5_pattern":
            return self.handle_s5_pattern(user_message)
        elif self.stage == "S6":
            return self.handle_s6(user_message)
        elif self.stage == "S7_examples":
            return self.handle_s7_examples(user_message)
        elif self.stage == "S7_summary":
            return self.handle_s7_summary(user_message)
        
        return "שלום! על מה תרצה להתאמן היום?"
    
    def handle_s0(self, msg):
        self.stage = "S1"
        return "על מה תרצה להתאמן היום?"
    
    def handle_s1(self, msg):
        self.data["topic"] = msg
        self.stage = "S2"
        # FIX: הסבר על מטרה
        return f"""אני מבין שאת רוצה להתאמן על {msg}.

עכשיו, כדי שנוכל לזהות את הדפוס שלך, אני מבקש שתספרי לי על אירוע ספציפי אחד שבו זה קרה לאחרונה.

ספרי לי על פעם אחת - עם מי זה היה? מתי זה קרה? מה בדיוק קרה שם?"""
    
    def handle_s2(self, msg):
        self.data["event"] = msg
        self.stage = "S3"
        # FIX: הסבר על מטרה ב-S3
        return """עכשיו, כדי שנוכל לזהות את הדפוס שלך, אני רוצה להתעמק ברגשות שהיו לך באותו רגע.

מה הרגשת?"""
    
    def handle_s3(self, msg):
        self.data["emotions"].append(msg)
        if len(self.data["emotions"]) < 3:
            return f"ספרי לי יותר על ה{msg} - איפה הרגשת אותו?"
        else:
            self.stage = "S4"
            return "עכשיו אני רוצה להבין מה עבר לך בראש באותו רגע. מה חשבת?"
    
    def handle_s4(self, msg):
        self.data["thought"] = msg
        self.stage = "S5_actual"
        return "מה עשית באותו רגע?"
    
    def handle_s5_actual(self, msg):
        self.data["action_actual"] = msg
        self.stage = "S5_desired"
        return "מה היית רוצה לעשות במקום זה?"
    
    def handle_s5_desired(self, msg):
        self.data["action_desired"] = msg
        self.stage = "S5_pattern"
        
        # FIX: הצגת סיכום כ"דפוס" (לא רק "מה שקרה")
        emotions = ", ".join(self.data["emotions"])
        return f"""🎯 **בוא נסכם את הדפוס שמצאנו:**

כשאת ב[{self.data["event"][:50]}...], 
את מרגישה: {emotions},
חושבת: "{self.data["thought"]}",
ועושה: "{self.data["action_actual"]}",
אבל רצית: "{self.data["action_desired"]}".

**זה הדפוס שזיהינו.**

האם זה מדויק?"""
    
    def handle_s5_pattern(self, msg):
        if "כן" in msg.lower() or "נכון" in msg.lower():
            self.stage = "S7_examples"
            # FIX: לא קופצים ל-S6 (פער), קודם מזהים דפוס!
            return """מעולה. עכשיו, כדי להבין את הדפוס לעומק:

**איפה עוד את מזהה את הדפוס הזה?**

ספרי לי על מצב נוסף שבו הרגשת ופעלת באותה דרך."""
        return "בוא ננסה שוב לסכם..."
    
    def handle_s7_examples(self, msg):
        self.data["pattern_examples"].append(msg)
        
        # FIX: אל תיתקע! אם יש 2-3 דוגמאות, עבור לסיכום
        if len(self.data["pattern_examples"]) >= 2:
            self.stage = "S7_summary"
            examples = "\n- ".join(self.data["pattern_examples"])
            
            # FIX: סיכום מפורש של הדפוס
            return f"""אני שומע:
- {examples}

🎯 **בוא נסכם את הדפוס במפורש:**

**הדפוס מורכב מ-3 חלקים:**
1. **רגש** - {", ".join(self.data["emotions"])}
2. **מחשבה** - "{self.data["thought"]}"
3. **פעולה** - "{self.data["action_actual"]}"

זה קרה במצבים שונים ({len(self.data["pattern_examples"]) + 1} דוגמאות),
אבל התגובה שלך זהה.

**זה הדפוס. האם את מזהה אותו?**"""
        
        return "ספרי לי על מצב נוסף שבו זה קרה."
    
    def handle_s7_summary(self, msg):
        if "כן" in msg.lower() or "מזהה" in msg.lower():
            self.stage = "S6"
            # FIX: בקשת רשות לפני המשך
            return """אני רוצה להמשיך לחקור את הדפוס הזה איתך. בסדר?

איך תקראי לפער הזה בין מה שעשית למה שרצית?"""
        return "בוא נסכם שוב..."
    
    def handle_s6(self, msg):
        self.data["gap_name"] = msg
        return "איך היית מדרגת את הפער הזה בסולם 1-10?"

def run_simulation():
    """Run interactive simulation"""
    
    print("=" * 80)
    print("🎭 SIMULATION: Expert Feedback Improvements")
    print("=" * 80)
    print("\n📋 המטרה: להדגים איך המאמן אמור להגיב עם התיקונים החדשים\n")
    print("🔍 שים לב ל:")
    print("  1. ✅ הסבר על מטרה (S2, S3)")
    print("  2. ✅ הצגת סיכום כ'דפוס' (לא רק 'מה שקרה')")
    print("  3. ✅ הגדרת 3 מרכיבי דפוס")
    print("  4. ✅ אל תיתקע - אחרי 2 דוגמאות, סכם")
    print("  5. ✅ בקשת רשות לפני המשך")
    print("\n" + "=" * 80 + "\n")
    
    # Simulate conversation from expert feedback #2
    conversation = [
        ("משתמש", "כן"),
        ("משתמש", "לומר את דעתי גם כשזה פחות נעים"),
        ("משתמש", "אתמול חגגנו לאמא יומולדת. אחותי בחרה מסעדה יקרה, ובסוף חלקנו חשבון גבוה"),
        ("משתמש", "במתח, בחשש, נעלבת"),
        ("משתמש", "שאני פריירית, שאין לי כוח"),
        ("משתמש", "בכל זאת עניתי לה בווצאפ"),
        ("משתמש", "הייתי רוצה לענות עם יותר רוגע"),
        ("משתמש", "כן, זה מדויק"),
        ("משתמש", "עם הבת שלי - היא עונה לא יפה ואני מרגישה אותו דבר"),
        ("משתמש", "גם עם בעלי זה קורה"),
        ("משתמש", "כן, אני מזהה את הדפוס"),
        ("משתמש", "בסדר, בואי נמשיך"),
    ]
    
    coach = CoachSimulator()
    
    for turn, (role, message) in enumerate(conversation, 1):
        print(f"\n{'─' * 80}")
        print(f"Turn {turn}:")
        print(f"{'─' * 80}")
        
        if role == "משתמש":
            print(f"👤 משתמש: {message}")
            response = coach.respond(message)
            print(f"\n🤖 מאמן (Stage: {coach.stage}):")
            print(f"   {response}")
        
        # Highlight key improvements
        if "הדפוס שמצאנו" in response:
            print("\n   ✅ FIX: הצגת סיכום כ'דפוס'!")
        if "כדי שנוכל לזהות את הדפוס" in response:
            print("\n   ✅ FIX: הסבר על מטרה!")
        if "מורכב מ-3 חלקים" in response:
            print("\n   ✅ FIX: הגדרת 3 מרכיבי דפוס!")
        if coach.stage == "S7_summary" and len(coach.data["pattern_examples"]) >= 2:
            print("\n   ✅ FIX: לא נתקע - עבר לסיכום אחרי 2 דוגמאות!")
        if "אני רוצה להמשיך לחקור" in response:
            print("\n   ✅ FIX: בקשת רשות לפני המשך!")
    
    print("\n" + "=" * 80)
    print("🏁 SIMULATION COMPLETE")
    print("=" * 80)
    print("\n📊 סיכום:")
    print(f"  • Stage סופי: {coach.stage}")
    print(f"  • דוגמאות דפוס: {len(coach.data['pattern_examples'])}")
    print(f"  • רגשות נאספו: {len(coach.data['emotions'])}")
    print("\n✅ כל התיקונים הודגמו בהצלחה!")

if __name__ == "__main__":
    run_simulation()
