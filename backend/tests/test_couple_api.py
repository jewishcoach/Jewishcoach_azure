"""
Couple process: invite link, privacy of the shared screens, the hold before כמ"ז, cancel/delete, pilot gate.
"""
import json
import sys
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db, utc_now  # noqa: E402
import app.models  # noqa: E402,F401
from app.api.chat_v2 import save_v2_state  # noqa: E402
from app.dependencies import get_current_user  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Conversation, CoupleMember, CoupleSession, User  # noqa: E402
from app.services import couple_notifications as notify  # noqa: E402
from app.services import couple_service as cs  # noqa: E402


DISCOVERY_DONE = {
    "event_description": "מוצאי שבת — עם איתי — הוא שוב לא ענה לי",
    "emotions": ["כעס", "פחד"],
    "thought": "אני לבד בזה",
    "action_actual": "הרמתי את הקול",
    "emotion_desired": "רוגע",
    "action_desired": "לדבר בשקט",
    "pattern": "כשלא עונים לי, אני מרימה את הקול ודורשת תשובות",
    "paradigm": "ככה זה אצלי — אם לא אלחץ, לא ישמעו אותי",
    "stance": {
        "reality_belief": "אני מאמינה שאם לא אלחם על המקום שלי, ישכחו אותי",
        "short": "אם לא אלחם, ישכחו אותי",
        "activation_trigger": "כשמתעלמים ממני",
        "gains": ["שומעים אותי"],
        "losses": ["ריחוק"],
    },
}


def _state(step, cd, couple):
    return {"current_step": step, "saturation_score": 0.0, "collected_data": dict(cd), "messages": [],
            "couple": couple}


class Ctx:
    def __init__(self):
        # one shared in-memory connection: TestClient runs endpoints in other threads
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.current = None
        app.dependency_overrides[get_db] = self._get_db
        app.dependency_overrides[get_current_user] = lambda: self.current
        self.client = TestClient(app)

    def _get_db(self):
        yield self.db

    def user(self, email=None, is_admin=False):
        u = User(clerk_id=f"clerk_{uuid.uuid4().hex[:10]}", email=email or f"{uuid.uuid4().hex[:8]}@test.com",
                 is_admin=is_admin, created_at=utc_now())
        self.db.add(u)
        self.db.commit()
        return u

    def as_(self, user):
        self.current = user
        return self.client

    def set_state(self, conversation_id, step, cd):
        conv = self.db.get(Conversation, conversation_id)
        conv.v2_state = _state(step, cd, (conv.v2_state or {}).get("couple"))
        self.db.commit()


@pytest.fixture
def ctx(monkeypatch):
    pilot = f"pilot_{uuid.uuid4().hex[:6]}@test.com"
    monkeypatch.setenv("COUPLE_PILOT_EMAILS", pilot)
    limiter.enabled = False
    c = Ctx()
    c.pilot_email = pilot
    c.sent = []  # emails are recorded, never sent
    monkeypatch.setattr(notify, "_send", lambda to, subject, lines: c.sent.append((to.email, subject, lines)))
    yield c
    limiter.enabled = True
    app.dependency_overrides.clear()
    c.db.close()
    c.engine.dispose()


def _open(ctx, title="הוויכוח על ההוצאות, מוצאי שבת"):
    a = ctx.user(email=ctx.pilot_email)
    r = ctx.as_(a).post("/api/couple/sessions", json={"event_title": title, "display_name": "נועה", "gender": "female"})
    assert r.status_code == 200, r.text
    return a, r.json()


def _join(ctx, token, name="איתי", gender="male"):
    b = ctx.user()
    r = ctx.as_(b).post(f"/api/couple/invites/{token}/accept", json={"display_name": name, "gender": gender})
    assert r.status_code == 200, r.text
    return b, r.json()


def test_pilot_gate(ctx):
    outsider = ctx.user()
    assert ctx.as_(outsider).get("/api/couple/enabled").json() == {"can_start": False}
    r = ctx.as_(outsider).post("/api/couple/sessions", json={"event_title": "ויכוח", "display_name": "x"})
    assert r.status_code == 404
    admin = ctx.user(is_admin=True)
    assert ctx.as_(admin).get("/api/couple/enabled").json() == {"can_start": True}


def test_open_seeds_a_v3_conversation_at_the_shared_title(ctx):
    a, opened = _open(ctx)
    conv = ctx.db.get(Conversation, opened["conversation_id"])
    assert conv.user_id == a.id
    assert conv.v2_state["ux_version"] == 3
    assert conv.v2_state["couple"] == {"session_id": opened["session_id"], "role": "inviter",
                                       "event_title": "הוויכוח על ההוצאות, מוצאי שבת"}
    assert conv.v2_state["collected_data"]["topic"] == "אירוע זוגי: הוויכוח על ההוצאות, מוצאי שבת"
    assert a.gender == "female"  # saved to the profile so the coach addresses her correctly
    session = ctx.db.get(CoupleSession, opened["session_id"])
    assert session.invite_token_hash == cs.hash_token(opened["invite_token"])  # only the hash is stored


def test_invite_shows_only_name_and_title_and_is_single_use(ctx):
    a, opened = _open(ctx)
    token = opened["invite_token"]
    assert ctx.as_(a).get(f"/api/couple/invites/{token}").json()["state"] == "own"
    assert ctx.as_(a).post(f"/api/couple/invites/{token}/accept", json={"display_name": "x"}).status_code == 409

    b = ctx.user()
    preview = ctx.as_(b).get(f"/api/couple/invites/{token}").json()
    assert preview == {"state": "valid", "inviter_name": "נועה", "inviter_gender": "female",
                       "event_title": "הוויכוח על ההוצאות, מוצאי שבת"}
    r = ctx.as_(b).post(f"/api/couple/invites/{token}/accept", json={"display_name": "איתי", "gender": "male"})
    assert r.status_code == 200
    joined = r.json()
    conv_b = ctx.db.get(Conversation, joined["conversation_id"])
    assert conv_b.user_id == b.id and conv_b.v2_state["couple"]["role"] == "invitee"
    assert ctx.as_(b).get(f"/api/couple/invites/{token}").json()["state"] == "joined"

    stranger = ctx.user()
    assert ctx.as_(stranger).get(f"/api/couple/invites/{token}").json() == {"state": "used"}
    assert ctx.as_(stranger).post(f"/api/couple/invites/{token}/accept", json={"display_name": "y"}).status_code == 409
    assert ctx.as_(stranger).get(f"/api/couple/sessions/{opened['session_id']}").status_code == 404
    assert ctx.as_(stranger).get(f"/api/couple/invites/not-a-token").status_code == 404


def test_expired_and_renewed_invite(ctx):
    a, opened = _open(ctx)
    session = ctx.db.get(CoupleSession, opened["session_id"])
    session.invite_expires_at = utc_now() - timedelta(minutes=1)
    ctx.db.commit()
    b = ctx.user()
    assert ctx.as_(b).get(f"/api/couple/invites/{opened['invite_token']}").json() == {"state": "expired"}
    assert ctx.as_(b).post(f"/api/couple/invites/{opened['invite_token']}/accept",
                           json={"display_name": "איתי"}).status_code == 410
    renewed = ctx.as_(a).post(f"/api/couple/sessions/{opened['session_id']}/invite").json()["invite_token"]
    assert ctx.as_(b).get(f"/api/couple/invites/{opened['invite_token']}").status_code == 404  # old link dead
    assert ctx.as_(b).get(f"/api/couple/invites/{renewed}").json()["state"] == "valid"


def test_mirror_opens_only_after_both_approved_and_shows_only_approved_lines(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid = opened["session_id"]

    # not ready before the end of discovery
    assert ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror/draft").status_code == 409
    ctx.set_state(opened["conversation_id"], "S11", DISCOVERY_DONE)
    draft = ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror/draft").json()
    ids = [line["id"] for line in draft["lines"]]
    assert ids == ["emotions", "thought", "action", "desired_emotion", "desired_action",
                   "pattern", "paradigm", "stance", "trigger", "gains", "losses"]
    assert draft["lines"][0]["text"] == "כעס, פחד"
    assert all("איתי" not in line["text"] for line in draft["lines"])  # the event telling is never a line

    submitted = [dict(line) for line in draft["lines"]]
    submitted[1]["visible"] = False  # hide the thought
    submitted[2]["text"] = "הרמתי את הקול  ויצאתי מהחדר"  # edit the action
    submitted.append({"id": "event_description", "text": "injected"})  # unknown ids are dropped
    r = ctx.as_(a).post(f"/api/couple/sessions/{sid}/mirror", json={"lines": submitted})
    assert r.status_code == 200 and r.json()["me"]["mirror_done"] and not r.json()["mirror_open"]

    # B still sees nothing of A
    assert ctx.as_(b).get(f"/api/couple/sessions/{sid}/mirror").status_code == 409
    status_b = ctx.as_(b).get(f"/api/couple/sessions/{sid}").json()
    assert status_b["partner"]["mirror_done"] is True and status_b["mirror_open"] is False
    assert "lines" not in json.dumps(status_b) and "הרמתי" not in json.dumps(status_b, ensure_ascii=False)

    ctx.set_state(joined["conversation_id"], "S11", {
        "emotions": ["הצפה"], "action_actual": "יצאתי מהחדר", "pattern": "כשצועקים עליי, אני שותק ויוצא",
        "stance": {"short": "אם אגיב, זה רק יחמיר", "activation_trigger": "כשמרימים עליי את הקול",
                   "gains": ["שקט"]},
    })
    draft_b = ctx.as_(b).get(f"/api/couple/sessions/{sid}/mirror/draft").json()
    assert ctx.as_(b).post(f"/api/couple/sessions/{sid}/mirror", json={"lines": draft_b["lines"]}).json()["mirror_open"]

    screen_a = ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror").json()
    screen_b = ctx.as_(b).get(f"/api/couple/sessions/{sid}/mirror").json()
    assert screen_a["me"] == screen_b["partner"] and screen_b["me"] == screen_a["partner"]
    a_lines = {line["id"]: line["text"] for line in screen_b["partner"]["lines"]}
    assert "thought" not in a_lines and "event_description" not in a_lines
    assert a_lines["action"] == "הרמתי את הקול ויצאתי מהחדר"
    assert screen_b["partner"]["name"] == "נועה" and screen_a["partner"]["gender"] == "male"
    assert "messages" not in json.dumps(screen_a) and "collected_data" not in json.dumps(screen_a)

    # approvals are frozen once the screen opened
    assert ctx.as_(a).post(f"/api/couple/sessions/{sid}/mirror", json={"lines": []}).status_code == 409
    assert ctx.as_(a).get(f"/api/couple/sessions/{sid}").json()["mirror_seen"] is True


def test_hold_before_kamaz_until_the_mirror_opens(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid, conv_a = opened["session_id"], opened["conversation_id"]
    ctx.set_state(conv_a, "S11", DISCOVERY_DONE)

    r = ctx.as_(a).post("/api/chat/v2/stage-intro", json={"conversation_id": conv_a, "target_macro_stage": "kamaz"})
    assert r.status_code == 409 and r.json()["detail"] == {"code": "couple_waiting"}

    # whatever path writes a later step, the saved conversation stays at S11
    state = dict(ctx.db.get(Conversation, conv_a).v2_state)
    state["current_step"] = "S12"
    save_v2_state(conv_a, state, ctx.db)
    assert ctx.db.get(Conversation, conv_a).v2_state["current_step"] == "S11"

    for m in ctx.db.get(CoupleSession, sid).members:
        m.mirror, m.mirror_at = [], utc_now()
    ctx.db.commit()
    assert not cs.waiting_for_mirror(ctx.db, conv_a)
    state = dict(ctx.db.get(Conversation, conv_a).v2_state)
    state["current_step"] = "S12"
    save_v2_state(conv_a, state, ctx.db)
    assert ctx.db.get(Conversation, conv_a).v2_state["current_step"] == "S12"


def test_cancel_releases_the_hold_and_closes_the_link(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid = opened["session_id"]
    assert cs.waiting_for_mirror(ctx.db, opened["conversation_id"])
    status = ctx.as_(b).post(f"/api/couple/sessions/{sid}/cancel").json()
    assert status["status"] == "cancelled"
    assert not cs.waiting_for_mirror(ctx.db, opened["conversation_id"])
    assert not cs.waiting_for_mirror(ctx.db, joined["conversation_id"])
    assert ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror").status_code == 409
    assert ctx.as_(a).get(f"/api/couple/invites/{opened['invite_token']}").status_code == 404


def test_deleting_a_conversation_ends_the_process_and_removes_the_shared_lines(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid = opened["session_id"]
    ctx.set_state(opened["conversation_id"], "S11", DISCOVERY_DONE)
    draft = ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror/draft").json()
    ctx.as_(a).post(f"/api/couple/sessions/{sid}/mirror", json={"lines": draft["lines"]})

    assert ctx.as_(a).delete(f"/api/chat/conversations/{opened['conversation_id']}").status_code == 200
    member = ctx.db.query(CoupleMember).filter(CoupleMember.session_id == sid, CoupleMember.role == "inviter").one()
    assert member.mirror is None and member.conversation_id is None
    assert ctx.db.get(CoupleSession, sid).status == "cancelled"
    assert ctx.as_(b).get(f"/api/couple/sessions/{sid}").json()["status"] == "cancelled"


def test_safety_hold_keeps_screens_closed_and_hides_progress_from_the_partner(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid = opened["session_id"]
    for m in ctx.db.get(CoupleSession, sid).members:
        m.mirror, m.mirror_at = [], utc_now()
        if m.role == "invitee":
            m.safety_hold_at = utc_now()
    ctx.db.commit()
    status_a = ctx.as_(a).get(f"/api/couple/sessions/{sid}").json()
    assert status_a["mirror_open"] is False
    assert status_a["partner"]["mirror_done"] is False  # looks like the partner simply hasn't finished
    assert ctx.as_(a).get(f"/api/couple/sessions/{sid}/mirror").status_code == 409


def test_commitment_screen(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    sid = opened["session_id"]
    done = {**DISCOVERY_DONE, "renewal_belief": "אני מאמינה שקולי נשמע גם בשקט", "new_action": "לבקש זמן ולדבר",
            "commitment": "אני מבקשת להתאמן על הקושי…"}
    for conv_id, user in ((opened["conversation_id"], a), (joined["conversation_id"], b)):
        ctx.set_state(conv_id, "S15", done)
        lines = ctx.as_(user).get(f"/api/couple/sessions/{sid}/commitment/draft").json()["lines"]
        assert [line["id"] for line in lines] == ["new_stance", "new_action", "request"]
        ctx.as_(user).post(f"/api/couple/sessions/{sid}/commitment", json={"lines": lines})
    screen = ctx.as_(a).get(f"/api/couple/sessions/{sid}/commitment").json()
    assert screen["partner"]["lines"][0]["text"] == "אני מאמינה שקולי נשמע גם בשקט"


def test_approved_lines_keeps_draft_order_and_drops_hidden_or_cleared():
    draft = [{"id": "emotions", "text": "כעס"}, {"id": "pattern", "text": "דפוס"}, {"id": "trigger", "text": "כפתור"}]
    submitted = [{"id": "trigger", "text": "  כפתור   שלי "}, {"id": "emotions", "visible": False},
                 {"id": "pattern", "text": ""}, {"id": "other", "text": "x"}]
    assert cs.approved_lines(submitted, draft, 300) == [{"id": "trigger", "text": "כפתור שלי"}]


def test_pattern_line_is_shown_in_first_person():
    state = {"current_step": "S11", "collected_data": {
        "pattern": "להגיב בחוסר סבלנות ובהגנה כשאת מרגישה שלא מקשיבים לך או מתעלמים מהחשיבות שלך",
        "action_actual": "אמרתי לו שזו הבעיה שלך",  # the member's own quote stays as written
        "stance": {"gains": ["שקט"]}}}
    lines = {line["id"]: line["text"] for line in cs.mirror_draft(state)}
    assert lines["pattern"] == "להגיב בחוסר סבלנות ובהגנה כשאני מרגישה שלא מקשיבים לי או מתעלמים מהחשיבות שלי"
    assert lines["action"] == "אמרתי לו שזו הבעיה שלך"
    assert cs._first_person("להסביר את הצורך שלי") == "להסביר את הצורך שלי"  # the object marker "את" is kept


def test_sessions_list_tells_whether_my_part_started(ctx):
    a, opened = _open(ctx)
    assert ctx.as_(a).get("/api/couple/sessions").json()[0]["me"]["step"] == "S0"
    conv = ctx.db.get(Conversation, opened["conversation_id"])
    conv.current_phase = "S2"
    ctx.db.commit()
    assert ctx.as_(a).get("/api/couple/sessions").json()[0]["me"]["step"] == "S2"


def test_status_emails_go_to_the_waiting_partner_without_any_content(ctx):
    a, opened = _open(ctx)
    b, joined = _join(ctx, opened["invite_token"])
    assert ctx.sent[-1][0] == a.email and "איתי הצטרף" in ctx.sent[-1][1]
    sid = opened["session_id"]
    ctx.set_state(opened["conversation_id"], "S11", DISCOVERY_DONE)
    ctx.set_state(joined["conversation_id"], "S11", DISCOVERY_DONE)
    for user in (a, b):
        lines = ctx.as_(user).get(f"/api/couple/sessions/{sid}/mirror/draft").json()["lines"]
        ctx.as_(user).post(f"/api/couple/sessions/{sid}/mirror", json={"lines": lines})
    to, subject, body = ctx.sent[-1]
    assert to == a.email and subject == "מסך השיתוף שלכם פתוח"  # A approved first and is the one waiting
    text = subject + " ".join(body)
    assert "הוויכוח" not in text and "כעס" not in text  # no title, no lines
