"""
Judge a coaching transcript with the BSD rubric (Claude on Bedrock). Run from backend/:
    .venv/bin/python scripts/judge_transcript.py --db /tmp/tmpXXXX.db [--conversation 1] [--persona career]
    .venv/bin/python scripts/judge_transcript.py --latest-sim            # newest simulation DB in /tmp
Writes the full JSON report next to the summary: /tmp/v3_judge/<name>.json
"""
import argparse, glob, json, os, sys

sys.path.insert(0, os.getcwd())
from app.bsd_v2.eval.judge import JudgeRefused, judge_transcript, load_transcript


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="SQLAlchemy URL or path to a SQLite file")
    ap.add_argument("--latest-sim", action="store_true", help="use the newest /tmp/tmp*.db simulation DB")
    ap.add_argument("--conversation", type=int)
    ap.add_argument("--persona", default="", help="persona key (adds its background as judge context)")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()

    db = a.db
    if a.latest_sim:
        db = max(glob.glob("/tmp/tmp*.db"), key=os.path.getmtime)
    if not db:
        sys.exit("--db or --latest-sim required")
    url = db if "://" in db else f"sqlite:///{db}"

    note = ""
    if a.persona:
        from simulate_v3_e2e_flow import PERSONAS  # noqa: E402  (scripts/ on path below)
        name, gender, topic, emo, event, bg = PERSONAS[a.persona]
        note = f"{name} ({gender}), topic {topic}, event: {event}. Background: {bg}"

    conv_id, turns = load_transcript(url, a.conversation)
    print(f"conversation {conv_id}: {len(turns)} turns ({sum(t['speaker'] == 'coach' for t in turns)} coach)")
    try:
        report, usage = judge_transcript(turns, note)
    except JudgeRefused as e:
        sys.exit(str(e))

    out_dir = "/tmp/v3_judge"
    os.makedirs(out_dir, exist_ok=True)
    out = f"{out_dir}/{a.name or a.persona or conv_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"conversation_id": conv_id, "usage": usage, **report.model_dump()}, f, ensure_ascii=False, indent=2)

    c = report.conversation
    print(f"\nOVERALL {c.overall}/5 | insight {c.W1_insight_own_words} choice {c.W2_real_choice} "
          f"economy {c.W3_economy_fatigue} arc {c.W4_arc_coherence} agency {c.W5_agency} | coach turns {c.total_coach_chat_turns}")
    dims = {}
    for t in report.turns:
        for k, v in t.scores.model_dump().items():
            if v:
                dims.setdefault(k, []).append(v)
    print("dimension means: " + "  ".join(f"{k.split('_')[0]}={sum(v) / len(v):.1f}" for k, v in dims.items()))
    failed = [s for s in report.stages if not s.passed]
    print(f"stages passed {len(report.stages) - len(failed)}/{len(report.stages)}" +
          (": failed " + ", ".join(f"{s.stage}({','.join(s.failure_modes)})" for s in failed) if failed else ""))
    hf = [(t.turn, h) for t in report.turns for h in t.hard_fails]
    if hf:
        print("hard fails: " + ", ".join(f"t{n}:{h}" for n, h in hf))
    print("\nTOP ISSUES")
    for i in report.top_issues:
        print(f"  {i.rank}. [{i.stage} {i.dimension} turns {i.turns}] {i.issue}\n     → {i.fix}")
    print(f"\nusage {usage} → {out}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
    main()
