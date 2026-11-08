"""The local message model: catches risky messages by meaning, not exact wording.

multilingual-e5-small (8-bit ONNX, ~118 MB) turns a message into a 384-number embedding on this server's CPU;
a small classifier head (weights in the loaded rule set, like the rules) turns that into a probability per
`msg.*` category. Text goes in, numbers come out: nothing is stored and nothing leaves the machine. The only
network use is the one-time model download from Hugging Face, checked against a pinned size and SHA-256.

The model never runs on the discord.py event loop. One shared ONNX session serves a pool of worker threads
(onnxruntime releases the GIL), one per core. Requests are micro-batched (up to MAX_BATCH, or what arrives
within BATCH_WAIT) from two queues: kids' checks always go first, Guard's background server messages after.
Guard requests may be shed under load (rules still run on them); kids' checks never are.

If the model can't be downloaded or loaded, everything keeps working on rules only and the owner dashboard
shows why.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import os
import re
import threading
import time
import urllib.request
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from guildward.core.models import Signal
from guildward.core.text import fold, normalize
from guildward.intel.behavior import age_disclosure

log = logging.getLogger(__name__)

REPO = "Xenova/multilingual-e5-small"
REVISION = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"  # pinned: a new upload must not change behaviour silently
FILES = {  # local name: (path in repo, bytes, sha256)
    "model_quantized.onnx": ("onnx/model_quantized.onnx", 118_308_185,
                             "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193"),
    "tokenizer.json": ("tokenizer.json", 17_082_730,
                       "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"),
}
MAX_TOKENS = 128  # Discord messages are short; longer ones are cut, which mostly keeps the opening ask
MAX_BATCH = 32
BATCH_WAIT = 0.004  # seconds a worker waits for more requests before running a partial batch
KID, GUARD = 0, 1
GUARD_MAX_QUEUE = 512  # Guard requests beyond this are shed (rules-only), never kids' checks
GUARD_MAX_WAIT = 5.0  # a Guard request older than this when picked up is shed
BUSY_AFTER = 3.0  # a kid's check not started by then gets a "busy, you're next" note
CEILING = 60.0  # only a real failure gets here: then rules-only, clearly marked
SOFT_WEIGHT = 8  # below-threshold hints: too weak to alert, but they feed memory and pattern tracking

_APP_NAMES = (("Snapchat", r"snap ?chat|snap|sc"), ("Instagram", r"insta(?:gram)?|ig"), ("Telegram", r"telegram|tele"),
              ("WhatsApp", r"whats ?app|wa"), ("Kik", r"kik"), ("TikTok", r"tik ?tok"), ("Signal", r"signal"))
_APP_RX = [(name, re.compile(rf"(?<![a-zåäö])(?:{rx})(?![a-zåäö])")) for name, rx in _APP_NAMES]


# --- download --------------------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def ensure_files(cache: Path, on_progress: Callable[[str], None] | None = None) -> dict[str, Path]:
    """Download the model once into `cache`; verify size + sha256 every start. Raises on any mismatch."""
    cache.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for name, (remote, size, sha) in FILES.items():
        path = cache / name
        if path.exists() and path.stat().st_size == size and _sha256(path) == sha:
            out[name] = path
            continue
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{remote}"
        part = path.with_suffix(path.suffix + ".part")
        log.info("downloading %s (%.0f MB) from %s", name, size / 1e6, url)
        req = urllib.request.Request(url, headers={"User-Agent": "guildward-model-fetch"})
        with urllib.request.urlopen(req, timeout=60) as r, part.open("wb") as f:
            done, next_mark = 0, 0.1
            while chunk := r.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done / size >= next_mark:
                    msg = f"{name}: {done / size:.0%}"
                    log.info("model download %s", msg)
                    if on_progress:
                        on_progress(msg)
                    next_mark += 0.1
        if part.stat().st_size != size or _sha256(part) != sha:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"{name}: size/sha256 mismatch after download (expected {size} bytes, {sha[:12]}…)")
        part.replace(path)
        out[name] = path
    return out


# --- encoder + head --------------------------------------------------------------------------------
class Encoder:
    """Text -> L2-normalised e5 embeddings. Thread-safe: one session, many callers."""

    def __init__(self, model: Path, tokenizer: Path, *, threads: int = 1) -> None:
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._np = np
        self.tok = Tokenizer.from_file(str(tokenizer))
        self.tok.enable_truncation(MAX_TOKENS)
        self.tok.no_padding()
        self.pad_id = self.tok.token_to_id("<pad>") or 1
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads  # parallelism comes from the worker threads, one core each
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(model), opts, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}

    def encode(self, texts: Sequence[str]) -> Any:
        np = self._np
        # e5 wants the "query: " prefix; folding undoes fancy fonts and look-alike letters before tokenising.
        encs = self.tok.encode_batch([f"query: {fold(x)}" for x in texts])
        n = max(len(e.ids) for e in encs)
        ids = np.full((len(encs), n), self.pad_id, dtype=np.int64)
        mask = np.zeros((len(encs), n), dtype=np.int64)
        for i, e in enumerate(encs):
            ids[i, : len(e.ids)] = e.ids
            mask[i, : len(e.ids)] = 1
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        hidden = self.session.run(None, feed)[0]  # (batch, tokens, 384)
        m = mask[..., None].astype(np.float32)
        emb = (hidden * m).sum(1) / np.maximum(m.sum(1), 1e-9)  # mean pooling over real tokens
        return emb / np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)


@dataclass(frozen=True)
class Head:
    """Small classifier over embeddings: dense layers, ReLU between, sigmoid out (one-vs-rest per category)."""

    labels: tuple[str, ...]
    layers: tuple[tuple[Any, Any], ...]  # (W, b) with W shaped (in, out)
    thresholds: Any  # alert at p >= threshold
    soft: Any  # hint at soft <= p < threshold
    weights: Any  # signal weight at full confidence, per label
    meta: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Head:
        import numpy as np

        with np.load(path, allow_pickle=False) as z:
            n = int(z["n_layers"])
            layers = tuple((z[f"W{i}"].astype(np.float32), z[f"b{i}"].astype(np.float32)) for i in range(n))
            meta = {k[5:]: str(z[k]) for k in z.files if k.startswith("meta_")}
            return cls(tuple(str(x) for x in z["labels"]), layers, z["thresholds"].astype(np.float32),
                       z["soft"].astype(np.float32), z["weights"].astype(np.int32), meta)

    def save(self, path: Path) -> None:
        import numpy as np

        arrays: dict[str, Any] = {"labels": np.array(self.labels), "n_layers": np.array(len(self.layers)),
                                  "thresholds": self.thresholds, "soft": self.soft, "weights": self.weights}
        for i, (w, b) in enumerate(self.layers):
            arrays[f"W{i}"], arrays[f"b{i}"] = w, b
        arrays.update({f"meta_{k}": np.array(v) for k, v in self.meta.items()})
        np.savez_compressed(path, **arrays)

    def predict(self, emb: Any) -> Any:
        import numpy as np

        x = emb
        for i, (w, b) in enumerate(self.layers):
            x = x @ w + b
            if i < len(self.layers) - 1:
                x = np.maximum(x, 0)
        return 1.0 / (1.0 + np.exp(-x))


def head_path() -> Path | None:
    """The loaded rule set's head (private in production, the public example otherwise). None = no head."""
    from guildward.intel.rules import rules

    p = getattr(rules(), "SEMANTIC_HEAD", None)
    return Path(p) if p else None


def to_signals(probs: Sequence[float], head: Head, text: str) -> tuple[Signal, ...]:
    """Probabilities -> Signals. Weight scales with confidence: 60% of the category weight at the threshold,
    100% at p=1. Between soft and threshold: a small hint that only feeds memory/patterns."""
    out: list[Signal] = []
    for code, p, thr, soft, w in zip(head.labels, probs, head.thresholds, head.soft, head.weights, strict=True):
        p, thr = float(p), float(thr)
        if p >= thr:
            weight = round(int(w) * (0.6 + 0.4 * (p - thr) / max(1e-6, 1.0 - thr)))
        elif p >= float(soft):
            weight = min(SOFT_WEIGHT, int(w) // 3)
        else:
            continue
        if weight <= 0:
            continue
        if code == "msg.age_probe" and "?" not in text and age_disclosure(text) is not None:
            continue  # "hi im 13" states the sender's own age; the model mistakes it for asking
        params: dict[str, str | int] = {}
        if code == "msg.isolation":
            app = _app_in(text)
            if app is None:
                code = "msg.isolation_private"  # "somewhere else" with no app named: same stage, no {app} to fill
            else:
                params["app"] = app
        out.append(Signal(code, weight, MappingProxyType(params)))
    best: dict[str, Signal] = {}
    for s in out:
        if s.code not in best or s.weight > best[s.code].weight:
            best[s.code] = s
    return tuple(best.values())


def _app_in(text: str) -> str | None:
    s = normalize(text)
    return next((name for name, rx in _APP_RX if rx.search(s)), None)


# --- inference service -----------------------------------------------------------------------------
class Ticket:
    """One text waiting for the model. Lives on the event loop that submitted it."""

    __slots__ = ("enqueued", "future", "loop", "prio", "started", "text")

    def __init__(self, text: str, prio: int, loop: asyncio.AbstractEventLoop) -> None:
        self.text, self.prio, self.loop = text, prio, loop
        self.enqueued = time.monotonic()
        self.future: asyncio.Future[tuple[Signal, ...] | None] = loop.create_future()
        self.started = asyncio.Event()


def _post(t: Ticket, fn: Callable[..., Any], *args: Any) -> None:
    """Hand a result back to the ticket's event loop from a worker thread (a closed loop is ignored)."""
    with contextlib.suppress(RuntimeError):
        t.loop.call_soon_threadsafe(fn, *args)


def _resolve(t: Ticket, value: Any, exc: BaseException | None = None) -> None:
    if t.future.done():
        return
    if exc is not None:
        t.future.set_exception(exc)
    else:
        t.future.set_result(value)


@dataclass
class Stats:
    state: str = "off"  # off | downloading | loading | ready | failed
    detail: str = ""
    workers: int = 0
    batches: int = 0
    texts: int = 0
    shed: int = 0
    errors: int = 0
    busy_notes: int = 0
    last_ms: float = 0.0
    recent_ms: deque[float] = field(default_factory=lambda: deque(maxlen=500))
    head: str = ""


class Service:
    """Model + worker threads + the two-priority queue. `encoder`/`head` may be injected (tests)."""

    def __init__(self, *, cache: Path = Path("data/models"), workers: int | None = None,
                 encoder: Any = None, head: Head | None = None) -> None:
        self.cache = cache
        self.n_workers = max(1, workers or os.cpu_count() or 1)
        self.encoder, self.head = encoder, head
        self.stats = Stats()
        self._cv = threading.Condition()
        self._q: tuple[deque[Ticket], deque[Ticket]] = (deque(), deque())
        self._threads: list[threading.Thread] = []
        self._stop = False

    # lifecycle
    def start(self) -> None:
        """Load in the background (download on first start); workers start once the model is ready."""
        if self.stats.state != "off":
            return
        self.stats.state = "loading"
        threading.Thread(target=self._load, name="guildward-model-load", daemon=True).start()

    def _load(self) -> None:
        try:
            if self.head is None:
                hp = head_path()
                if hp is None:
                    raise RuntimeError("the loaded rule set has no SEMANTIC_HEAD")
                self.head = Head.load(hp)
            if self.encoder is None:
                missing = [n for n, (_, size, _) in FILES.items()
                           if not (self.cache / n).exists() or (self.cache / n).stat().st_size != size]
                if missing:
                    self.stats.state = "downloading"
                files = ensure_files(self.cache, lambda m: setattr(self.stats, "detail", m))
                self.stats.state, self.stats.detail = "loading", ""
                self.encoder = Encoder(files["model_quantized.onnx"], files["tokenizer.json"])
            self.encoder.encode(["warm up"])
        except Exception as e:
            self.stats.state, self.stats.detail = "failed", f"{type(e).__name__}: {e}"[:300]
            log.warning("message model unavailable, running on rules only: %s", self.stats.detail)
            self._fail_waiting(e)
            return
        self.stats.head = self.head.meta.get("name", "")
        for i in range(self.n_workers):
            th = threading.Thread(target=self._work, name=f"guildward-model-{i}", daemon=True)
            th.start()
            self._threads.append(th)
        self.stats.workers = self.n_workers
        self.stats.state = "ready"
        log.info("message model ready: %s, head %s, %d worker threads", REPO, self.stats.head or "?", self.n_workers)

    def stop(self) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()

    @property
    def ready(self) -> bool:
        return self.stats.state == "ready"

    @property
    def accepting(self) -> bool:
        return self.stats.state in ("downloading", "loading", "ready")

    # queue
    def submit(self, text: str, prio: int) -> Ticket | None:
        """Queue one text (call from the event loop). None = not taken (model off/failed, or Guard shed)."""
        if not self.accepting:
            return None
        t = Ticket(text, prio, asyncio.get_running_loop())
        with self._cv:
            if prio == GUARD and len(self._q[GUARD]) >= GUARD_MAX_QUEUE:
                self.stats.shed += 1
                return None
            self._q[prio].append(t)
            self._cv.notify()
        return t

    def position(self, t: Ticket) -> int:
        """1-based place among kids' checks still waiting; 0 once it has started."""
        with self._cv:
            for i, x in enumerate(self._q[KID]):
                if x is t:
                    return i + 1
        return 0

    def waiting(self) -> tuple[int, int]:
        with self._cv:
            return len(self._q[KID]), len(self._q[GUARD])

    def _take(self) -> list[Ticket]:
        """Oldest kids' checks first, then oldest Guard messages; stale Guard requests are shed."""
        batch: list[Ticket] = []
        kid, guard = self._q
        while kid and len(batch) < MAX_BATCH:
            batch.append(kid.popleft())
        now = time.monotonic()
        while guard and len(batch) < MAX_BATCH:
            t = guard.popleft()
            if now - t.enqueued > GUARD_MAX_WAIT:
                self.stats.shed += 1
                _post(t, _resolve, t, None)
                continue
            batch.append(t)
        return batch

    def _work(self) -> None:
        while True:
            with self._cv:
                while not self._stop and not (self._q[KID] or self._q[GUARD]):
                    self._cv.wait()
                if self._stop:
                    return
                if len(self._q[KID]) + len(self._q[GUARD]) < MAX_BATCH:
                    self._cv.wait(BATCH_WAIT)  # let a burst fill the batch; others may grab it meanwhile
                batch = self._take()
            if not batch:
                continue
            for t in batch:
                _post(t, t.started.set)
            t0 = time.perf_counter()
            try:
                probs = self.head.predict(self.encoder.encode([t.text for t in batch]))
                results = [to_signals(p, self.head, t.text) for p, t in zip(probs, batch, strict=True)]
            except Exception as e:
                self.stats.errors += 1
                self.stats.detail = f"{type(e).__name__}: {e}"[:300]
                log.exception("message model batch failed")
                for t in batch:
                    _post(t, _resolve, t, None, e)
                continue
            ms = (time.perf_counter() - t0) * 1000
            self.stats.batches += 1
            self.stats.texts += len(batch)
            self.stats.last_ms = ms
            self.stats.recent_ms.append(ms)
            for t, r in zip(batch, results, strict=True):
                _post(t, _resolve, t, r)

    def _fail_waiting(self, e: BaseException) -> None:
        with self._cv:
            waiting = [*self._q[KID], *self._q[GUARD]]
            self._q[KID].clear()
            self._q[GUARD].clear()
        for t in waiting:
            _post(t, _resolve, t, None, e)

    def status(self) -> dict[str, Any]:
        s = self.stats
        kid, guard = self.waiting() if self.accepting else (0, 0)
        recent = sorted(s.recent_ms)
        return {"state": s.state, "detail": s.detail, "model": REPO, "head": s.head, "workers": s.workers,
                "texts": s.texts, "shed": s.shed, "errors": s.errors, "busy_notes": s.busy_notes,
                "queue_kids": kid, "queue_guard": guard,
                "batch_ms_p50": round(recent[len(recent) // 2], 1) if recent else None}


# --- the calls the bot makes -----------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Result:
    signals: tuple[tuple[Signal, ...], ...]  # per text; empty tuples when the model didn't run
    status: str  # ok | off (no model on this server) | failed (model should have run but didn't finish)

    @property
    def unfinished(self) -> bool:
        return self.status == "failed"


_service: Service | None = None


def service() -> Service | None:
    return _service


def install(svc: Service | None) -> Service | None:
    """Make `svc` the process-wide model (the bot calls this at startup; tests inject fakes)."""
    global _service
    _service = svc
    return svc


def status() -> dict[str, Any]:
    return _service.status() if _service else {"state": "off", "detail": "not started", "model": REPO}


async def kid_check(texts: Sequence[str], *, on_wait: Callable[[int], Awaitable[None]] | None = None,
                    busy_after: float = BUSY_AFTER, ceiling: float = CEILING) -> Result:
    """Model signals for a kid's check. Never dropped for load: if it hasn't started after `busy_after`
    seconds, `on_wait(place_in_line)` lets the caller show "busy, you're next". Only a failure, or the
    `ceiling` passing, gives up (status "failed": the caller shows rules only, marked)."""
    svc = _service
    empty = tuple(() for _ in texts)
    if svc is None or not texts:
        return Result(empty, "off")
    if not svc.accepting:
        return Result(empty, "failed" if svc.stats.state == "failed" else "off")
    tickets = [svc.submit(x, KID) for x in texts]
    if any(t is None for t in tickets):
        return Result(empty, "failed")
    ts: list[Ticket] = [t for t in tickets if t is not None]
    deadline = time.monotonic() + ceiling
    started = asyncio.ensure_future(asyncio.gather(*(t.started.wait() for t in ts)))
    try:
        await asyncio.wait_for(asyncio.shield(started), busy_after)
    except TimeoutError:
        last = -1
        while not started.done() and on_wait is not None and time.monotonic() < deadline:
            place = min((p for p in (svc.position(t) for t in ts) if p), default=0)
            if place and place != last:
                last = place
                svc.stats.busy_notes += 1
                try:
                    await on_wait(place)
                except Exception:  # a failed "busy" edit must not lose the check itself
                    log.warning("busy note failed", exc_info=True)
            await asyncio.wait([started], timeout=min(5.0, max(0.0, deadline - time.monotonic())))
    finally:
        if not started.done():
            started.cancel()
    try:
        out = await asyncio.wait_for(asyncio.gather(*(t.future for t in ts)), max(0.0, deadline - time.monotonic()))
    except Exception:
        log.warning("message model did not finish a kid's check; answering with rules only", exc_info=True)
        return Result(empty, "failed")
    return Result(tuple(r or () for r in out), "ok")


async def guard_check(texts: Sequence[str]) -> tuple[tuple[Signal, ...], ...]:
    """Model signals for Guard's background messages. Shed under load: then just empty (rules still run)."""
    svc = _service
    if svc is None or not svc.ready or not texts:
        return tuple(() for _ in texts)
    tickets = [svc.submit(x, GUARD) for x in texts]
    out: list[tuple[Signal, ...]] = []
    for t in tickets:
        if t is None:
            out.append(())
            continue
        try:
            out.append(await asyncio.wait_for(t.future, GUARD_MAX_WAIT + 10) or ())
        except Exception:
            out.append(())
    return tuple(out)
