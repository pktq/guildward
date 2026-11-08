"""Local message model plumbing with a fake encoder: signals, fusion, the priority queue, busy notes, failures.

The real model is exercised by the private repo's held-out benchmark and by tools/loadtest_semantic.py.
"""

from __future__ import annotations

import asyncio
import threading
import time

import numpy as np
import pytest
from test_flows import author, fake_bot, sf

from guildward.core.models import Signal
from guildward.intel import semantic
from guildward.intel.message import analyze_message, fuse
from guildward.intel.semantic import GUARD, KID, Head, Service, to_signals

LABELS = ("msg.age_probe", "msg.isolation", "msg.secrecy")
WORDS = ("old", "app", "secret")


def head() -> Head:
    w = np.eye(3, dtype=np.float32) * 10
    return Head(LABELS, ((w, np.full(3, -5, np.float32)),), np.full(3, 0.5, np.float32), np.full(3, 0.3, np.float32),
                np.array([30, 30, 45], np.int32), {"name": "test"})


class FakeEncoder:
    """Embedding = which trigger words appear. `gate` (if set) blocks every batch until released."""

    def __init__(self, gate: threading.Event | None = None, fail: bool = False) -> None:
        self.gate, self.fail, self.batches = gate, fail, []

    def encode(self, texts):
        if self.gate is not None and texts != ["warm up"]:
            self.gate.wait(10)
        if self.fail and texts != ["warm up"]:
            raise RuntimeError("model crashed")
        if texts != ["warm up"]:
            self.batches.append(list(texts))
        return np.array([[float(w in t) for w in WORDS] for t in texts], np.float32)


def started(enc: FakeEncoder, workers: int = 1) -> Service:
    svc = Service(workers=workers, encoder=enc, head=head())
    svc.start()
    for _ in range(200):
        if svc.ready:
            return svc
        time.sleep(0.01)
    raise AssertionError(svc.stats)


@pytest.fixture(autouse=True)
def _no_global_model():
    yield
    if (svc := semantic.service()) is not None:
        svc.stop()
    semantic.install(None)


# --- signals and fusion --------------------------------------------------------------------------
def test_weight_scales_with_confidence_and_soft_hints_stay_small():
    h = head()
    (s,) = to_signals([1.0, 0, 0], h, "how old")
    assert (s.code, s.weight) == ("msg.age_probe", 30)
    (s,) = to_signals([0.5, 0, 0], h, "how old")
    assert s.weight == 18  # 60% of the category weight right at the threshold
    (s,) = to_signals([0.4, 0, 0], h, "how old")
    assert s.weight == semantic.SOFT_WEIGHT  # a hint: feeds memory, too weak to alert
    assert to_signals([0.1, 0, 0], h, "x") == ()


def test_isolation_names_the_app_or_falls_back_to_private():
    h = head()
    (s,) = to_signals([0, 1.0, 0], h, "add me on 𝓼𝓷𝓪𝓹 instead")
    assert (s.code, dict(s.params)) == ("msg.isolation", {"app": "Snapchat"})
    (s,) = to_signals([0, 1.0, 0], h, "lets talk somewhere else")
    assert s.code == "msg.isolation_private" and not s.params


def test_fuse_keeps_strongest_weight_and_rule_details():
    rule = Signal("msg.pressure", 40, severe=True)
    model = (Signal("msg.pressure", 55), Signal("msg.secrecy", 30))
    out = {s.code: s for s in fuse([rule], model)}
    assert out["msg.pressure"].weight == 55 and out["msg.pressure"].severe
    assert out["msg.multi_stage"].weight == 20  # the model added a second stage


def test_soft_hints_dont_make_a_message_multi_stage():
    out = fuse([Signal("msg.age_probe", 30)], [Signal("msg.secrecy", 8)])
    assert "msg.multi_stage" not in {s.code for s in out}


def test_analyze_message_without_model_is_rules_only():
    assert analyze_message("how old are you") == analyze_message("how old are you", ())


def test_head_roundtrip_and_example_head_loads(tmp_path):
    p = tmp_path / "h.npz"
    head().save(p)
    h2 = Head.load(p)
    assert h2.labels == LABELS and h2.meta["name"] == "test"
    ex = Head.load(semantic.head_path())
    assert len(ex.labels) == 13 and ex.layers[0][0].shape[0] == 384


# --- the queue ---------------------------------------------------------------------------------
def test_kids_checks_jump_ahead_of_waiting_guard_messages():
    gate = threading.Event()
    enc = FakeEncoder(gate)
    svc = semantic.install(started(enc, workers=1))

    async def go():
        first = svc.submit("guard first", GUARD)  # occupies the only worker
        await asyncio.wait_for(first.started.wait(), 2)
        guards = [svc.submit(f"guard {i}", GUARD) for i in range(3)]
        kids = [svc.submit(f"kid {i}", KID) for i in range(2)]
        assert svc.position(kids[1]) == 2
        gate.set()
        await asyncio.gather(*(t.future for t in [first, *guards, *kids]))

    asyncio.run(go())
    assert enc.batches[1] == ["kid 0", "kid 1", "guard 0", "guard 1", "guard 2"]


def test_guard_is_shed_under_load_kids_never(monkeypatch):
    monkeypatch.setattr(semantic, "GUARD_MAX_QUEUE", 2)
    gate = threading.Event()
    svc = semantic.install(started(FakeEncoder(gate)))

    async def go():
        t0 = svc.submit("busy", GUARD)
        await asyncio.wait_for(t0.started.wait(), 2)
        got = [svc.submit("g", GUARD) for _ in range(4)]
        kids = [svc.submit("k", KID) for _ in range(50)]
        gate.set()
        return got, kids

    got, kids = asyncio.run(go())
    assert got.count(None) == 2 and svc.stats.shed == 2
    assert all(k is not None for k in kids)


def test_busy_kid_check_gets_place_in_line_then_full_result():
    gate = threading.Event()
    svc = semantic.install(started(FakeEncoder(gate)))
    places: list[int] = []

    async def go():
        blocker = svc.submit("blocker", KID)
        await asyncio.wait_for(blocker.started.wait(), 2)

        async def note(place: int) -> None:
            places.append(place)
            gate.set()

        return await semantic.kid_check(["how old r u"], on_wait=note, busy_after=0.05)

    res = asyncio.run(go())
    assert places == [1]
    assert res.status == "ok" and res.signals[0][0].code == "msg.age_probe"


def test_model_crash_answers_rules_only_marked_unfinished():
    semantic.install(started(FakeEncoder(fail=True)))
    res = asyncio.run(semantic.kid_check(["how old"]))
    assert res.unfinished and res.signals == ((),)


def test_hung_model_hits_the_ceiling_not_forever():
    semantic.install(started(FakeEncoder(threading.Event())))  # never released
    t0 = time.monotonic()
    res = asyncio.run(semantic.kid_check(["how old"], busy_after=0.05, ceiling=0.3))
    assert res.unfinished and time.monotonic() - t0 < 2


def test_no_model_installed_is_plain_rules():
    res = asyncio.run(semantic.kid_check(["how old"]))
    assert res.status == "off" and not res.unfinished
    assert semantic.status()["state"] == "off"


def test_failed_load_keeps_running_on_rules(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise OSError("no network")

    monkeypatch.setattr(semantic, "ensure_files", boom)
    svc = semantic.install(Service(cache=tmp_path, workers=1, head=head()))
    svc.start()
    for _ in range(200):
        if svc.stats.state == "failed":
            break
        time.sleep(0.01)
    assert svc.status()["state"] == "failed" and "no network" in svc.status()["detail"]
    assert asyncio.run(semantic.kid_check(["how old"])).unfinished


# --- kid flow ------------------------------------------------------------------------------------
def test_model_hint_feeds_the_kids_memory_and_unfinished_note():
    semantic.install(started(FakeEncoder()))
    bot = fake_bot()
    groomer = sf(20, 7)
    v = asyncio.run(flows_check(bot, ["keep it a secret from everyone"], groomer))
    assert any(s.code == "msg.secrecy" for s in v.signals)  # rules miss this wording; the model doesn't
    assert bot.pocket.store.val("SELECT COUNT(*) FROM pair_signals WHERE code='msg.secrecy'") >= 1

    semantic.install(started(FakeEncoder(fail=True)))
    v = asyncio.run(flows_check(bot, ["hello"], groomer))
    assert any(s.code == "ai.unfinished" for s in v.signals)


def flows_check(bot, texts, uid):
    from guildward.bot import flows

    return flows.check_message(bot, sf(800, 1), "en", texts, author=author(uid), memory_key=uid)


def test_guard_check_feeds_the_engine():
    semantic.install(started(FakeEncoder()))
    (sigs,) = asyncio.run(semantic.guard_check(["dont tell, its our secret"]))
    assert {s.code for s in sigs} == {"msg.secrecy"}


def test_guard_engine_alerts_on_what_only_the_model_saw():
    from test_guard import KID, NEW, World

    w = World()
    w.join(KID)
    w.join(NEW)
    w.say(KID, "hi im 12 lol")
    w.t += 5
    w.mid += 1
    ev = semantic_event(w, NEW, "you know the drill, nobody hears about our chats", KID.id,
                        (Signal("msg.secrecy", 45), Signal("msg.isolation_private", 30)))
    outs = w.engine.on_message(ev)
    assert [o.kind for o in outs].count("alert") == 1
    assert {o["code"] for o in w.store.q("SELECT code FROM observations WHERE user_id=?", NEW.id)} >= {
        "msg.secrecy", "msg.isolation_private", "msg.multi_stage"}


def semantic_event(w, m, text, reply, model):
    from test_guard import G

    from guildward.guard.engine import MessageEvent

    return MessageEvent(G, 7, w.mid, m, text, w.t, reply_to=reply, channel_name="general", model=model)
