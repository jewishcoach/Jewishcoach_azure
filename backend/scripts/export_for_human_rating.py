"""
Export simulated transcripts to one self-contained HTML page for HUMAN rating (judge calibration).
The judge's scores are NOT shown (no anchoring). The page saves ratings as a JSON download.
Run from backend/:
    .venv/bin/python scripts/export_for_human_rating.py --map /tmp/r3_map.txt --out /tmp/v3_rating.html
Compare afterwards:
    .venv/bin/python scripts/export_for_human_rating.py --compare ~/Downloads/bsd_ratings.json --judge-prefix r3_
"""
import argparse, html, json, os, sys

sys.path.insert(0, os.getcwd())
from app.bsd_v2.eval.judge import load_transcript

QUESTIONS = [
    ("overall", "ציון כללי לשיחה — עד כמה זה אימון BSD טוב?"),
    ("method", "נאמנות לשיטה — המאמן עשה את מה שהשלב דורש?"),
    ("client_words", "המילים של המתאמן — בלי פרשנות, בלי להאכיל בכפית"),
    ("warmth", "חום ונוכחות — נשמע כמו מאמן אנושי?"),
    ("economy", "קצב — בלי חזרות מיותרות ובלי עייפות"),
]

PAGE = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>דירוג שיחות BSD</title>
<style>
body{font-family:Heebo,Arial,sans-serif;background:#f6f4f0;color:#2d4658;max-width:860px;margin:auto;padding:24px;line-height:1.6}
h2{margin-top:48px;border-top:3px solid #03ffe6;padding-top:16px}
.turn{border-radius:12px;padding:10px 14px;margin:8px 0;white-space:pre-wrap}
.coach{background:#fff;box-shadow:0 0 4px rgba(0,0,0,.08)}
.client{background:#d6fffa;margin-right:60px}
.card{background:#efe7ff;margin-right:60px;font-size:.92em}
.meta{font-size:.78em;color:#7a8b97}
.form{background:#fff;border:2px solid #9747ff;border-radius:12px;padding:14px;margin:16px 0}
.q{margin:8px 0} .q label{margin-left:12px}
textarea{width:100%;min-height:60px}
button{background:#9747ff;color:#fff;border:0;border-radius:10px;padding:12px 24px;font-size:1em;cursor:pointer}
</style></head><body>
<h1>דירוג שיחות אימון BSD</h1>
<p>שלום, ותודה שהסכמת לעזור.</p>
<p>לפניך שיחות בין <b>מאמן AI</b> שמאמן בשיטת BSD לבין <b>מתאמנים מדומים</b> (דמויות שנבנו לבדיקה —
אין כאן אנשים אמיתיים). בממשק המתאמן ממלא חלק מהשלבים בכרטיסים — הם מסומנים בסגול.</p>
<p>נשמח שתקרא כל שיחה ותדרג 1–5 (<b>5 = מה שמאמן BSD מעולה היה כותב</b>), ותכתוב בהערות מה הכי הפריע ומה היה טוב.
אין צורך לדרג את כולן — גם כמה שיחות יעזרו מאוד.</p>
<p>בסוף לחץ <b>"שמור דירוגים"</b> — יירד קובץ <code>bsd_ratings.json</code>. שלח אותו בחזרה למי ששלח לך את הקישור.
(הדירוגים נשמרים רק בדפדפן שלך עד שתלחץ.)</p>
__BODY__
<p><button onclick="save()">שמור דירוגים</button></p>
<script>
function save(){const out={};document.querySelectorAll('.form').forEach(f=>{const id=f.dataset.id;out[id]={};
f.querySelectorAll('input:checked').forEach(i=>out[id][i.name.split('|')[1]]=+i.value);
out[id].note=f.querySelector('textarea').value;});
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));
a.download='bsd_ratings.json';a.click();}
</script></body></html>"""


def render(persona: str, turns: list) -> str:
    sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
    from simulate_v3_e2e_flow import PERSONAS  # noqa: E402
    name, gender, topic, emo, event, bg = PERSONAS.get(persona, (persona, "", "", "", "", ""))
    parts = [f"<h2>{html.escape(name)} — {html.escape(topic)}</h2><p class='meta'>{html.escape(bg)}</p>"]
    for t in turns:
        cls = "coach" if t["speaker"] == "coach" else ("card" if t["card"] else "client")
        who = "מאמן" if t["speaker"] == "coach" else ("כרטיס" if t["card"] else "מתאמן")
        meta = f'<div class="meta">[{t["turn"]}] {who}' + (f' · {t["stage"]}' if t["stage"] else "") + "</div>"
        parts.append(f'<div class="turn {cls}">{meta}{html.escape(t["text"])}</div>')
    form = [f'<div class="form" data-id="{html.escape(persona)}"><b>הדירוג שלך</b>']
    for key, label in QUESTIONS:
        radios = "".join(f'<label><input type="radio" name="{persona}|{key}" value="{v}">{v}</label>' for v in range(1, 6))
        form.append(f'<div class="q">{label}<br>{radios}</div>')
    form.append('<div class="q">הערות (מה הכי הפריע / הכי טוב):<br><textarea></textarea></div></div>')
    return "\n".join(parts + form)


def export(map_path: str, out: str):
    body = []
    for line in open(map_path):
        persona, db = line.split()
        _, turns = load_transcript(f"sqlite:///{db}")
        body.append(render(persona, turns))
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__BODY__", "\n".join(body)))
    print(f"{len(body)} conversations → {out}")


def compare(ratings_path: str, prefix: str):
    """Human vs judge: per persona and the mean absolute gap per question."""
    human = json.load(open(ratings_path))
    key_map = {"overall": ("conversation", "overall"), "economy": ("conversation", "W3_economy_fatigue")}
    dim_map = {"method": "D1_method", "client_words": "D2_client_words", "warmth": "D7_warmth"}
    gaps = {q: [] for q, _ in QUESTIONS}
    for persona, h in human.items():
        path = f"/tmp/v3_judge/{prefix}{persona}.json"
        if not os.path.exists(path):
            continue
        j = json.load(open(path))
        row = []
        for q, _ in QUESTIONS:
            if q in key_map:
                jv = j[key_map[q][0]][key_map[q][1]]
            else:
                vals = [t["scores"][dim_map[q]] for t in j["turns"] if t["scores"][dim_map[q]]]
                jv = round(sum(vals) / len(vals), 1) if vals else None
            hv = h.get(q)
            if hv and jv:
                gaps[q].append(abs(hv - jv))
            row.append(f"{q}: you {hv} / judge {jv}")
        print(f"{persona:14} " + " | ".join(row))
    print("\nmean |human - judge|: " + "  ".join(f"{q}={sum(v)/len(v):.2f}" for q, v in gaps.items() if v))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", help="lines: '<persona> <sqlite path>'")
    ap.add_argument("--out", default="/tmp/v3_rating.html")
    ap.add_argument("--compare", help="bsd_ratings.json downloaded from the page")
    ap.add_argument("--judge-prefix", default="r3_")
    a = ap.parse_args()
    if a.compare:
        compare(a.compare, a.judge_prefix)
    else:
        export(a.map, a.out)
