#!/usr/bin/env python3
"""
Static verification of expert feedback fixes
Checks if all fixes are present in the code
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.prompt_compact import SYSTEM_PROMPT_COMPACT_HE, SYSTEM_PROMPT_COMPACT_EN

def check_fixes():
    """Check if all expert feedback fixes are present"""
    
    print("=" * 80)
    print("🔍 STATIC VERIFICATION: Expert Feedback Fixes")
    print("=" * 80)
    print()
    
    fixes_found = 0
    fixes_missing = 0
    
    # Fix 1: S5 is not the end - must proceed to S6
    print("1️⃣  Checking: S5 → S6 enforcement (CRITICAL)")
    print("─" * 80)
    
    checks = [
        ("S5 זה לא סוף", "Warning that S5 is not the end"),
        ("חובה S6", "Mandate to proceed to S6"),
        ("אל תסיים את השיחה ב-S5", "Don't end conversation at S5"),
        ("עכשיו כשאנחנו רואים את המצוי", "Transition text to S6"),
    ]
    
    for keyword, description in checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_missing += 1
    
    print()
    
    # Fix 2: S7 validation questions
    print("2️⃣  Checking: S7 validation questions (per expert)")
    print("─" * 80)
    
    validation_questions = [
        ("האם אתה מכיר את עצמך מופיע כך", "Q1: Do you recognize yourself like this elsewhere?"),
        ("האם זה קורה רק עם", "Q2: Does this only happen with...?"),
        ("האם זה תלוי בנסיבות", "Q3: Does this depend on circumstances?"),
        ("איפה עוד זה קורה", "Q4: Where else does this happen?"),
    ]
    
    for keyword, description in validation_questions:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_missing += 1
    
    print()
    
    # Fix 3: Purpose explanation in S2/S3
    print("3️⃣  Checking: Purpose explanation (S2/S3)")
    print("─" * 80)
    
    purpose_checks = [
        ("כדי שנוכל לזהות את הדפוס שלך", "Purpose explanation: 'to identify your pattern'"),
        ("S7 הוא השלב החשוב ביותר", "S7 is the most important stage"),
    ]
    
    for keyword, description in purpose_checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_missing += 1
    
    print()
    
    # Fix 4: "מה בדיוק קרה שם?" in S2
    print("4️⃣  Checking: 'What exactly happened there?' in S2")
    print("─" * 80)
    
    if "מה בדיוק קרה שם" in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: 'מה בדיוק קרה שם?'")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: 'מה בדיוק קרה שם?'")
        fixes_missing += 1
    
    print()
    
    # Fix 5: Terminology - "רגשות" not "תחושות"
    print("5️⃣  Checking: Correct terminology (emotions vs sensations)")
    print("─" * 80)
    
    terminology_checks = [
        ('השתמש במילה: **"רגשות"**', "Use word: 'emotions'"),
        ('❌ **אל תשתמש** במילה: **"תחושות"**', "Don't use: 'sensations' for emotions"),
        ("רגש = כעס, עצב, פחד", "Emotion = anger, sadness, fear"),
    ]
    
    for keyword, description in terminology_checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_missing += 1
    
    print()
    
    # Fix 6: Question order (emotion → description → body location)
    print("6️⃣  Checking: Question order (emotion → description → body)")
    print("─" * 80)
    
    order_checks = [
        ("שם רגש → תיאור הרגש → מיקום בגוף", "Order: emotion name → description → body location"),
        ("רק אחרי שיש תיאור", "Only after description, ask body location"),
    ]
    
    for keyword, description in order_checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword}'")
            fixes_missing += 1
    
    print()
    
    # Fix 7: Don't repeat emotion lists
    print("7️⃣  Checking: Avoid redundant repetitions")
    print("─" * 80)
    
    if "❌ אל תחזור על רשימות של רגשות" in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: Warning against repeating emotion lists")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: Warning against repeating emotion lists")
        fixes_missing += 1
    
    print()
    
    # Fix 8: Summarize pattern (not story) at S8
    print("8️⃣  Checking: S8 - Summarize pattern (not story)")
    print("─" * 80)
    
    if "אל תסכם שוב את הסיפור" in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: 'Don't summarize the story again!'")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: 'Don't summarize the story again!'")
        fixes_missing += 1
    
    print()
    print("=" * 80)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"✅ Fixes found: {fixes_found}")
    print(f"❌ Fixes missing: {fixes_missing}")
    print(f"📈 Success rate: {fixes_found}/{fixes_found + fixes_missing} ({100 * fixes_found / (fixes_found + fixes_missing):.1f}%)")
    print()
    
    if fixes_missing == 0:
        print("🎉 All fixes verified! The code is ready.")
        return 0
    else:
        print("⚠️  Some fixes are missing. Please review.")
        return 1

if __name__ == "__main__":
    sys.exit(check_fixes())
