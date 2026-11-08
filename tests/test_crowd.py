import pytest

from guildward.core.i18n import LANGS, has, missing_translations, t
from guildward.core.models import Confidence, Kind, Level, build_verdict
from guildward.intel.crowd import (
    REPORT_REASONS,
    CrowdFacts,
    Link,
    Report,
    auto_flag,
    crowd_signals,
    link_strength,
    report_score,
    reporter_weight,
)
from guildward.intel.linking import (
    SCRIPT_BANDS,
    SCRIPT_MATCH_BANDS,
    Mark,
    extract_marks,
    handle_marks,
    mark_key,
    profile_marks,
    script_marks,
)

NOW = 1_800_000_000
DAY = 86_400


def reports(*weights: float, age_days: int = 1, reason: str = "sexual") -> tuple[Report, ...]:
    return tuple(Report(w, NOW - age_days * DAY, reason) for w in weights)


def codes(f: CrowdFacts) -> set[str]:
    return {s.code for s in crowd_signals(f)}


# --- crowd -------------------------------------------------------------------------------------------------


def test_reporter_weight():
    assert reporter_weight(2, "none") == 0
    assert reporter_weight(10, "none") == 0.25
    assert reporter_weight(100, "none") == 0.6
    assert reporter_weight(800, "none") == 1.0
    assert reporter_weight(800, "flagged") == 0
    assert reporter_weight(800, "confirmed") == 0
    assert reporter_weight(800, "watch") == 0.5


def test_brigade_of_new_accounts_does_nothing():
    rs = reports(*(reporter_weight(3, "none") for _ in range(5)))
    f = CrowdFacts(1, NOW, checkers=5, reports=rs)
    assert auto_flag(f) == "none"
    assert crowd_signals(f) == []


def test_reports_alone_never_flag():
    f = CrowdFacts(1, NOW, reports=reports(1, 1, 1, 1, 1, 1))  # six old-account classmates, no other evidence
    assert auto_flag(f) == "watch"


def test_credible_reports_plus_red_checks_flag():
    f = CrowdFacts(1, NOW, checkers=6, red_checkers=2, reports=reports(1, 1, 1))
    assert auto_flag(f) == "flagged"
    sig = next(s for s in crowd_signals(f) if s.code == "crowd.flagged")
    assert sig.params["reports"] == 3 and sig.params["reason"] == "sexual"
    v = build_verdict(Kind.PERSON, crowd_signals(f), base=15, confidence=Confidence.MEDIUM)
    assert v.level is Level.YELLOW


def test_strong_link_or_network_corroborates():
    rs = reports(1, 1, 1)
    linked = CrowdFacts(1, NOW, reports=rs, links=(Link("handle", 9, "confirmed"),))
    assert auto_flag(linked) == "flagged"
    assert auto_flag(CrowdFacts(1, NOW, reports=rs, network_guilds=1)) == "flagged"
    weak = CrowdFacts(1, NOW, reports=rs, links=(Link("avatar", 9, "confirmed"),))
    assert auto_flag(weak) == "watch"


def test_watch_from_red_checks():
    assert auto_flag(CrowdFacts(1, NOW, red_checkers=3)) == "watch"
    assert auto_flag(CrowdFacts(1, NOW, red_checkers=2)) == "none"


def test_sticky_and_never_confirms():
    strong = dict(red_checkers=9, reports=reports(*[1] * 10), network_guilds=3)
    assert auto_flag(CrowdFacts(1, NOW, flag="cleared", **strong)) == "cleared"
    assert auto_flag(CrowdFacts(1, NOW, flag="confirmed")) == "confirmed"
    assert auto_flag(CrowdFacts(1, NOW, **strong)) == "flagged"
    cleared = crowd_signals(CrowdFacts(1, NOW, flag="cleared", **strong))
    assert [s.code for s in cleared] == []  # the owner's review wins over network bans too


def test_decay():
    fresh = report_score(reports(1), NOW)
    assert fresh == pytest.approx(1, abs=0.01)
    assert report_score(reports(1, age_days=90), NOW) == pytest.approx(0.5)
    assert report_score(reports(1, age_days=180), NOW) == pytest.approx(0.25)
    old = CrowdFacts(1, NOW, red_checkers=2, reports=reports(1, 1, 1, age_days=200))
    assert auto_flag(old) == "none"


def test_confirmed_signals_severe():
    v = build_verdict(Kind.PERSON, crowd_signals(CrowdFacts(1, NOW, flag="confirmed")), base=15,
                      confidence=Confidence.MEDIUM)
    assert v.level is Level.RED


def test_network_and_red_check_weights():
    net = {s.code: s for s in crowd_signals(CrowdFacts(1, NOW, network_guilds=1))}["crowd.network"]
    assert (net.weight, net.severe) == (35, False)
    net2 = {s.code: s for s in crowd_signals(CrowdFacts(1, NOW, network_guilds=2))}["crowd.network"]
    assert (net2.weight, net2.severe) == (50, True)
    red = {s.code: s for s in crowd_signals(CrowdFacts(1, NOW, red_checkers=20))}["crowd.red_checks"]
    assert red.weight == 30


def test_link_signals():
    assert link_strength("handle") == "strong" and link_strength("script") == "medium"
    assert link_strength("name") == "weak"
    one_weak = CrowdFacts(1, NOW, links=(Link("name", 5, "flagged"),))
    assert crowd_signals(one_weak) == []
    two_weak = CrowdFacts(1, NOW, links=(Link("name", 5, "flagged"), Link("avatar", 5, "flagged")))
    assert codes(two_weak) == {"crowd.linked_similar"}
    unflagged = CrowdFacts(1, NOW, links=(Link("handle", 5, "watch"), Link("handle", 6, "cleared")))
    assert crowd_signals(unflagged) == []
    sig = crowd_signals(CrowdFacts(1, NOW, links=(Link("payment", 5, "confirmed"),)))[0]
    assert (sig.code, sig.weight, sig.severe, sig.params["kind"]) == ("crowd.linked", 30, True, "payment")
    assert not crowd_signals(CrowdFacts(1, NOW, links=(Link("handle", 5, "flagged"),)))[0].severe


def test_name_churn_and_deleted():
    assert codes(CrowdFacts(1, NOW, name_changes_30d=3, deleted=True)) == {"crowd.name_churn", "crowd.deleted"}
    assert codes(CrowdFacts(1, NOW, name_changes_30d=2)) == set()


# --- linking -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "value"), [
    ("add me on snap jake_2009", "snap:jake_2009"),
    ("my snap is jakesmith", "snap:jakesmith"),
    ("sc: @Jake.X", "snap:jake.x"),
    ("ѕnар: jake_09", "snap:jake_09"),
    ("lägg till mig på snap: jake_09", "snap:jake_09"),
    ("mitt snap är jakesmith", "snap:jakesmith"),
    ("snapchat - jakesmith", "snap:jakesmith"),
    ("hmu on insta jake.x", "insta:jake.x"),
    ("@jake_99 on snap", "snap:jake_99"),
    ("t.me/coolguy99 msg me there", "telegram:coolguy99"),
    ("my tele is @coolguy", "telegram:coolguy"),
    ("kik: jessy2010", "kik:jessy2010"),
    ("add me xyz_123", "discord:xyz_123"),
    ("my discord is gamerguy", "discord:gamerguy"),
    ("whatsapp me +46 70 123 45 67", "phone:701234567"),
    ("ring mig på 070-123 45 67", "phone:701234567"),
    ("email me jake.smith@gmail.com", "email:jake.smith@gmail.com"),
])
def test_handles_found(text, value):
    assert value in {m.value for m in handle_marks(text)}
    assert all(m.kind == "handle" for m in handle_marks(text))


@pytest.mark.parametrize(("text", "value"), [
    ("send it to $jakepay23", "cashapp:jakepay23"),
    ("cashapp $cashmoney please", "cashapp:cashmoney"),
    ("paypal.me/johnny22", "paypal:johnny22"),
    ("venmo @john-doe-5", "venmo:john-doe-5"),
])
def test_payment_tags_found(text, value):
    assert [(m.kind, m.value) for m in handle_marks(text)] == [("payment", value)]


@pytest.mark.parametrize("text", [
    "add me in game", "add me back pls", "add me rn", "add me on roblox", "oh snap that's cool", "my snap is down",
    "do you have snap or insta", "ig its fine", "ig u right", "insta is better than tiktok", "i dc at 9.30",
    "it costs $5", "add my $nap", "i have 12 345 678 robux", "born 2010-05-12", "i got 1000 streaks on snap lol",
    "lägg till mig på snap", "gaming session tonight", "send me a $50 gift card",
])
def test_no_false_handles(text):
    assert handle_marks(text) == []


SCRIPT = ("hey you seem really mature for your age, i dont usually talk to people like this but you are different. "
          "do you have snap so we can talk more privately")


def shared_bands(a: str, b: str) -> int:
    return len(set(script_marks(a)) & set(script_marks(b)))


@pytest.mark.parametrize("variant", [
    SCRIPT,
    SCRIPT.upper() + "!!",
    SCRIPT.replace("hey you", "hey emma, you"),
    SCRIPT.replace("really", "so"),
    SCRIPT.replace("you are", "you're").replace("snap", "insta"),
])
def test_script_small_edits_match(variant):
    assert shared_bands(SCRIPT, variant) >= SCRIPT_MATCH_BANDS


@pytest.mark.parametrize("other", [
    "anyone want to play minecraft tonight i have a new server with my friends from school",
    "you seem really nice, do you want to play roblox with me and my friends later today",
    "do you have snap so we can talk later about the homework for tomorrow",
    "you seem really mature for a kid your age my mom says",
])
def test_unrelated_messages_dont_match(other):
    assert shared_bands(SCRIPT, other) < SCRIPT_MATCH_BANDS


def test_script_marks_shape():
    marks = script_marks(SCRIPT)
    assert len(marks) == SCRIPT_BANDS and all(m.kind == "script" for m in marks)
    assert marks[0].value.startswith("b0:")
    assert script_marks("hi wanna play later") == []


def test_extract_marks_combines_and_dedupes():
    marks = extract_marks(SCRIPT + " my snap is jake_09, snap: jake_09")
    assert [m for m in marks if m.kind == "handle"] == [Mark("handle", "snap:jake_09")]
    assert sum(m.kind == "script" for m in marks) == SCRIPT_BANDS
    assert extract_marks("") == []


def test_profile_marks():
    marks = profile_marks("jake_smith2009", "Jaaake Smith", "a_1f2e3d")
    assert marks == [Mark("avatar", "a_1f2e3d"), Mark("name", "jakesmith")]
    assert profile_marks("gamer_boy_2010", "xXShadowXx", None) == []
    assert profile_marks("bob", None, None) == []


def test_mark_key():
    m = Mark("handle", "snap:jake_09")
    k = mark_key(b"secret", m)
    assert k == mark_key(b"secret", Mark("handle", "snap:jake_09"))
    assert len(k) == 32 and "jake" not in k
    assert k != mark_key(b"other", m) and k != mark_key(b"secret", Mark("payment", "snap:jake_09"))


# --- i18n --------------------------------------------------------------------------------------------------


def test_i18n_complete():
    assert missing_translations() == []
    keys = ["crowd.confirmed", "crowd.flagged", "crowd.watch", "crowd.network", "crowd.red_checks",
            "crowd.linked", "crowd.linked_similar", "crowd.name_churn", "crowd.deleted"]
    keys += [f"crowd.reason.{r}" for r in REPORT_REASONS]
    params = {"reports": 12, "count": 3}
    for k in keys:
        assert has(k)
        for lang in LANGS:
            text = t(k, lang, **params)
            assert "{" not in text and text != k
