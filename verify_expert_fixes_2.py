#!/usr/bin/env python3
"""
Static verification of expert feedback #2 fixes
Based on conversation from 10.2.2026
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.bsd_v2.prompt_compact import SYSTEM_PROMPT_COMPACT_HE, SYSTEM_PROMPT_COMPACT_EN

def check_fixes():
    """Check if all expert feedback #2 fixes are present"""
    
    print("=" * 80)
    print("🔍 STATIC VERIFICATION: Expert Feedback #2 Fixes")
    print("   Based on conversation from 10.2.2026")
    print("=" * 80)
    print()
    
    fixes_found = 0
    fixes_missing = 0
    
    # Fix 1: Pattern definition with 3 components
    print("1️⃣  Checking: Pattern definition (3 components)")
    print("─" * 80)
    
    checks = [
        ("דפוס מורכב מ-3 חלקים", "Pattern consists of 3 components"),
        ("רגש** - מה הרגשת", "Component 1: Emotion"),
        ("מחשבה** - מה אמרת לעצמך", "Component 2: Thought"),
        ("פעולה** - מה עשית", "Component 3: Action"),
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
    
    # Fix 2: Pattern explanation when user asks
    print("2️⃣  Checking: Explicit pattern explanation")
    print("─" * 80)
    
    if 'כשהמשתמש שואל "מה זה דפוס?"' in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: Handler for 'what is a pattern?' question")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: Handler for 'what is a pattern?' question")
        fixes_missing += 1
    
    if "המצבים שונים, אבל התגובה שלך זהה" in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: Explanation of pattern (different situations, same response)")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: Explanation of pattern")
        fixes_missing += 1
    
    print()
    
    # Fix 3: Present summary as "pattern"
    print("3️⃣  Checking: Present S5 summary as 'pattern'")
    print("─" * 80)
    
    checks = [
        ('הצג את הסיכום כ"דפוס"', "Instruction to present as pattern"),
        ("בוא נסכם את **הדפוס** שמצאנו", "Template: 'the pattern we found'"),
        ("זה הדפוס שזיהינו", "Template: 'this is the pattern'"),
    ]
    
    for keyword, description in checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_missing += 1
    
    print()
    
    # Fix 4: Don't get stuck on repeated questions
    print("4️⃣  Checking: 'Don't get stuck' fix")
    print("─" * 80)
    
    checks = [
        ("🚨 אל תיתקע", "Warning: don't get stuck"),
        ("נתקע! המשתמש כבר נתן", "Example of stuck behavior"),
        ('אם המשתמש נתן **2-3 דוגמאות**', "Rule: if user gave 2-3 examples"),
    ]
    
    for keyword, description in checks:
        if keyword in SYSTEM_PROMPT_COMPACT_HE:
            print(f"   ✅ Found: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
            print(f"      Keyword: '{keyword[:50]}...'")
            fixes_missing += 1
    
    print()
    
    # Fix 5: Ask permission before S7
    print("5️⃣  Checking: Ask permission before S7")
    print("─" * 80)
    
    if "אני רוצה להמשיך לחקור את הדפוס שלך. בסדר?" in SYSTEM_PROMPT_COMPACT_HE:
        print(f"   ✅ Found: Permission request before S7")
        fixes_found += 1
    else:
        print(f"   ❌ Missing: Permission request before S7")
        fixes_missing += 1
    
    print()
    
    # Verify English version too
    print("6️⃣  Checking: English translations")
    print("─" * 80)
    
    en_checks = [
        ("A pattern consists of 3 components", "3 components in English"),
        ("Emotion** - what you felt", "Component 1 in English"),
        ("Don't get stuck", "Stuck fix in English"),
        ("I want to continue exploring your pattern", "Permission in English"),
    ]
    
    for keyword, description in en_checks:
        if keyword in SYSTEM_PROMPT_COMPACT_EN:
            print(f"   ✅ Found: {description}")
            fixes_found += 1
        else:
            print(f"   ❌ Missing: {description}")
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
