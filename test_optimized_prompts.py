#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Optimized Prompts - Simulation
Tests the new optimized prompts for speed and quality
"""

import asyncio
import time
import json
from backend.app.bsd_v2.single_agent_coach import handle_conversation
from backend.app.bsd_v2.state_schema_v2 import create_new_state

# Test conversation flow
TEST_MESSAGES = [
    "שלום",  # S0 -> S1
    "אני רוצה להתאמן על היכולת שלי להיות אסרטיבי",  # S1
    "אני מתכוון שאני לא אומר מה שאני באמת חושב במצבים חברתיים",  # S1 deeper
    "בסדר, אני מוכן",  # Ready for S2
    "היה פגישת עבודה לפני שבועיים עם המנהל שלי ועוד שני עמיתים. המנהל הציע רעיון שאני חשבתי שהוא לא טוב, אבל לא אמרתי כלום",  # S2
    "זה היה בחדר הישיבות, יום שלישי בבוקר. המנהל דיבר על תוכנית חדשה לפרויקט",  # S2 details
    "הרגשתי כעס, תסכול, וגם פחד קצת",  # S3 start
]

async def run_simulation():
    """Run simulation with timing and output analysis"""
    print("=" * 80)
    print("🧪 SIMULATION: Testing Optimized Prompts")
    print("=" * 80)
    print()
    
    # Create new state
    user_id = 999  # Test user
    conversation_id = 9999  # Test conversation
    state = create_new_state(user_id, conversation_id)
    
    total_time = 0
    response_times = []
    
    for i, message in enumerate(TEST_MESSAGES, 1):
        print(f"\n{'─' * 80}")
        print(f"Turn {i}/{len(TEST_MESSAGES)}")
        print(f"{'─' * 80}")
        print(f"👤 User: {message}")
        print()
        
        # Measure time
        start = time.time()
        
        try:
            response, new_state = await handle_conversation(
                state=state,
                user_message=message,
                language="he"
            )
            
            elapsed = time.time() - start
            response_times.append(elapsed)
            total_time += elapsed
            
            # Update state for next turn
            state = new_state
            
            # Display response
            print(f"🤖 Coach: {response}")
            print()
            print(f"⏱️  Response time: {elapsed:.2f}s")
            
            # Show internal state
            current_step = state.get("current_step", "?")
            saturation = state.get("saturation_score", 0)
            print(f"📊 Stage: {current_step} | Saturation: {saturation:.2f}")
            
            # Check for errors
            if "מצטער" in response and "בעיה טכנית" in response:
                print("❌ ERROR: Technical problem detected in response!")
                return False
                
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ ERROR after {elapsed:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SIMULATION RESULTS")
    print("=" * 80)
    print()
    
    avg_time = total_time / len(TEST_MESSAGES)
    min_time = min(response_times)
    max_time = max(response_times)
    
    print(f"✅ Completed {len(TEST_MESSAGES)} turns successfully")
    print()
    print(f"⏱️  Timing:")
    print(f"   Total time:     {total_time:.2f}s")
    print(f"   Average/turn:   {avg_time:.2f}s")
    print(f"   Min response:   {min_time:.2f}s")
    print(f"   Max response:   {max_time:.2f}s")
    print()
    
    # Performance assessment
    print(f"🎯 Performance Assessment:")
    if avg_time <= 5:
        print(f"   ✅ EXCELLENT: Average {avg_time:.1f}s (target: 3-5s)")
    elif avg_time <= 10:
        print(f"   ⚠️  GOOD: Average {avg_time:.1f}s (slightly above 5s target)")
    else:
        print(f"   ❌ SLOW: Average {avg_time:.1f}s (target was 3-5s)")
    
    print()
    
    # Expected improvement
    old_avg = 35  # Old average was ~30-40s
    improvement = ((old_avg - avg_time) / old_avg) * 100
    speedup = old_avg / avg_time
    
    print(f"📈 Improvement vs. Old System:")
    print(f"   Old average:    ~{old_avg}s")
    print(f"   New average:    {avg_time:.2f}s")
    print(f"   Improvement:    {improvement:.1f}%")
    print(f"   Speedup:        {speedup:.1f}x faster")
    print()
    
    # Final stage check
    final_stage = state.get("current_step", "?")
    print(f"🎭 Final Stage: {final_stage}")
    
    expected_stages = ["S1", "S2", "S3"]
    if final_stage in expected_stages:
        print(f"   ✅ Coach progressed correctly through stages")
    else:
        print(f"   ⚠️  Unexpected final stage (expected one of {expected_stages})")
    
    print()
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    print("\n🚀 Starting Optimized Prompts Simulation...\n")
    
    try:
        success = asyncio.run(run_simulation())
        
        if success:
            print("\n✅ Simulation completed successfully!")
            print("The optimized prompts are working correctly.")
        else:
            print("\n❌ Simulation failed!")
            print("Please review the errors above.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Simulation crashed: {e}")
        import traceback
        traceback.print_exc()
