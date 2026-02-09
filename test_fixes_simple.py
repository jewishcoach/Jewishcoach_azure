#!/usr/bin/env python3
"""
Simple test for BSD v2 fixes - creates conversation and tests stage transitions
"""
import requests
import json
import time
import sys

API_BASE = "https://jewishcoach-api.azurewebsites.net"

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_message(role, text, step=None):
    """Pretty print messages"""
    if role == "user":
        print(f"\n{Colors.BLUE}👤 אני:{Colors.END} {text}")
    else:
        step_info = f" [שלב {step}]" if step else ""
        print(f"{Colors.GREEN}🤖 מאמן{step_info}:{Colors.END} {text}")

def send_v2_message(conv_id, message):
    """Send message to V2 API"""
    print_message("user", message)
    
    try:
        response = requests.post(
            f"{API_BASE}/api/chat/v2/message",
            json={
                "conversation_id": conv_id,
                "message": message,
                "language": "he"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"{Colors.RED}❌ Error {response.status_code}:{Colors.END}")
            print(response.text[:500])
            return None
            
        data = response.json()
        coach_msg = data.get("coach_message", data.get("response", ""))
        current_step = data.get("current_step", "?")
        
        print_message("coach", coach_msg, current_step)
        return data
        
    except Exception as e:
        print(f"{Colors.RED}❌ Exception: {e}{Colors.END}")
        return None

def test_s2_to_s3_blocking():
    """
    Test 1: S2→S4 blocking
    Verify that LLM cannot skip S3 (emotions)
    """
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"🧪 TEST 1: חסימת S2→S4 (אי אפשר לדלג על רגשות)")
    print(f"{'='*80}{Colors.END}\n")
    
    # We'll use a simple flow and see if coach goes S2→S3 (not S2→S4)
    conv_id = input(f"{Colors.YELLOW}הזן conversation_id (או Enter ליצירת חדש):{Colors.END} ").strip()
    
    if not conv_id:
        print(f"{Colors.YELLOW}ℹ️  צריך conversation_id קיים. פתח את האפליקציה:{Colors.END}")
        print(f"   https://purple-bush-0e1fa021e.4.azurestaticapps.net/")
        print(f"{Colors.YELLOW}   התחל שיחה והעתק את ה-ID מה-URL{Colors.END}")
        return
    
    try:
        conv_id = int(conv_id)
    except:
        print(f"{Colors.RED}❌ ID לא תקין{Colors.END}")
        return
    
    print(f"\n{Colors.YELLOW}📝 תסריט: עובר דרך S1→S2 ומנסה לראות אם עובר ל-S3 או קופץ ל-S4{Colors.END}\n")
    time.sleep(1)
    
    # These messages should get us through S1 to S2
    messages = [
        "כן",
        "על הקשר שלי עם אחותי",
        "על היכולת להיות כנה אבל גם שומרת על גבולות",
        "היום אני נותנת הרבה ולפעמים מרגישה שהיא לא מכבדת את הבית שלי",
        "הייתי רוצה שתהיה יותר רגישה לסגנון החיים שלי",
        "8",
        # S2 event
        "אחותי ישבה אצלי כל השבת וחסמה את כל הבית עם הלימודים שלה למבחן"
    ]
    
    last_resp = None
    for msg in messages:
        last_resp = send_v2_message(conv_id, msg)
        if not last_resp:
            print(f"{Colors.RED}❌ נכשל בשליחת הודעה{Colors.END}")
            return
        time.sleep(1.5)
    
    # Now analyze: are we in S2 or S3?
    current_step = last_resp.get("current_step", "")
    coach_msg = last_resp.get("coach_message", last_resp.get("response", ""))
    
    print(f"\n{Colors.BOLD}🔍 בדיקה:{Colors.END}")
    print(f"   שלב נוכחי: {Colors.YELLOW}{current_step}{Colors.END}")
    
    # Check 1: Generic question in S2 (not "מה נאמר?")
    if current_step == "S2":
        print(f"\n   ✓ עדיין ב-S2, בודק את השאלה...")
        if "מה בדיוק נאמר" in coach_msg or "מה המילים שנאמרו" in coach_msg:
            print(f"   {Colors.RED}❌ BAD: שואל 'מה נאמר?' כשאלה ראשונה!{Colors.END}")
        elif "מה עוד קרה" in coach_msg or "איך זה התפתח" in coach_msg or "ספר לי יותר" in coach_msg:
            print(f"   {Colors.GREEN}✅ GOOD: שאלה גנרית ראשונה{Colors.END}")
        else:
            print(f"   {Colors.YELLOW}⚠️  שאלה אחרת: {coach_msg[:80]}{Colors.END}")
    
    # Continue a bit more to see transition
    print(f"\n{Colors.YELLOW}📝 ממשיך כדי לראות מעבר שלבים...{Colors.END}")
    
    # Answer with event details
    resp = send_v2_message(conv_id, "זה גרם לי לשים בצד את הרצונות שלי")
    time.sleep(1.5)
    
    # Now mention emotion - see if goes to S3 or S4
    resp = send_v2_message(conv_id, "חשבתי שהיא מגזימה")
    time.sleep(1.5)
    
    if resp:
        current_step = resp.get("current_step", "")
        coach_msg = resp.get("coach_message", resp.get("response", ""))
        
        print(f"\n{Colors.BOLD}🔍 בדיקה קריטית:{Colors.END}")
        
        if current_step == "S4":
            print(f"   {Colors.RED}❌ BAD: קפץ ל-S4 (מחשבות) בלי לעבור דרך S3 (רגשות)!{Colors.END}")
        elif current_step == "S3":
            print(f"   {Colors.GREEN}✅ GOOD: עבר ל-S3 (רגשות) כמו שצריך!{Colors.END}")
        elif "מה הרגשת" in coach_msg or "רגש" in coach_msg:
            print(f"   {Colors.GREEN}✅ GOOD: המערכת אולצה לשאול על רגשות!{Colors.END}")
        else:
            print(f"   {Colors.YELLOW}⚠️  שלב: {current_step}, הודעה: {coach_msg[:80]}{Colors.END}")

def test_s2_generic_questions():
    """
    Test 2: S2 generic questions
    """
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"🧪 TEST 2: שאלות גנריות ב-S2 (לא 'מה נאמר?' לאירועים פנימיים)")
    print(f"{'='*80}{Colors.END}\n")
    
    print(f"{Colors.YELLOW}ℹ️  בדיקה זו דורשת conversation חדש. פתח אחד באפליקציה והזן את ה-ID.{Colors.END}")

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}🚀 בדיקת תיקוני BSD v2{Colors.END}")
    print(f"{'='*80}\n")
    
    try:
        test_s2_to_s3_blocking()
        
        print(f"\n{Colors.BOLD}{'='*80}")
        print(f"✅ בדיקה הסתיימה!")
        print(f"{'='*80}{Colors.END}\n")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  הופסק על ידי המשתמש{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ שגיאה: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
