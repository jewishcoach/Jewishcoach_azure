#!/usr/bin/env python3
"""Export simulation transcripts to a readable text file."""
import json, glob, os
from pathlib import Path

logs_dir = Path(__file__).parent / "simulation_logs"
output_file = Path(__file__).parent / "simulation_transcripts.txt"

# Get the latest log per persona
latest = {}
for f in sorted(logs_dir.glob("sim_*.json")):
    key = f.stem.split("_")[1]  # e.g. "parenting"
    latest[key] = f  # last one wins (sorted by date)

with open(output_file, "w", encoding="utf-8") as out:
    out.write("=" * 80 + "\n")
    out.write("סימולציות LLM-vs-LLM — תמלילים מלאים\n")
    out.write("=" * 80 + "\n\n")

    for persona_key, filepath in sorted(latest.items()):
        data = json.loads(filepath.read_text(encoding="utf-8"))
        persona = data.get("persona", {})
        summary = data.get("summary", {})

        out.write("═" * 80 + "\n")
        out.write(f"פרסונה: {persona.get('name', persona_key)} ({persona.get('topic', '')})\n")
        out.write(f"נושא: {persona.get('issue', '')}\n")
        out.write(f"שלב סופי: {summary.get('final_step', '?')} | תורות: {summary.get('total_turns', '?')} | זמן: {summary.get('duration_seconds', 0):.0f}s\n")
        out.write("═" * 80 + "\n\n")

        for t in data.get("transcript", []):
            step = t.get("step", "?")
            sat = t.get("saturation", 0)
            out.write(f"--- תור {t['turn']} | {step} | רוויה: {sat:.2f} ---\n")
            out.write(f"👤 מתאמן: {t.get('user', '')}\n")
            out.write(f"🤖 מאמן: {t.get('coach', '')}\n\n")

        # Collected data
        cd = data.get("collected_data", {})
        out.write("\n📊 נתונים שנאספו:\n")
        for k, v in cd.items():
            if v and v != [] and v != {}:
                val = str(v)[:200]
                out.write(f"  {k}: {val}\n")
        out.write("\n\n")

    out.write("=" * 80 + "\n")
    out.write("סוף\n")

print(f"✅ נשמר: {output_file}")
print(f"   {len(latest)} פרסונות, {sum(len(json.loads(f.read_text()).get('transcript',[])) for f in latest.values())} תורות סה\"כ")
