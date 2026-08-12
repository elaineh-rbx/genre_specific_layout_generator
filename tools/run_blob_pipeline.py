"""Run the front half of the new pipeline over the golden set.

Three model calls per scene - uprez, blob, decouple - and every intermediate is written
out beside the spec. Keeping them is the point rather than a convenience: when a render
comes back wrong the only useful question is which stage lost it, and that is answerable
from the scene prompt and the blob or not at all.

Stage 4 is deliberately not run here. `layoutgen.pipeline.mapper` is a pure function of
the spec, so the prompts are recomputed at render time instead of stored - a stored
prompt would go stale the moment a wrapper in `prompts.py` changed, and then the file
would disagree with what was actually sent.

Writes `results/routing/blob/<scene>.json`, one per scene, and skips any that already
have one unless `--force`.

Usage:
    python tools/run_blob_pipeline.py --limit 5
    python tools/run_blob_pipeline.py --workers 12
    python tools/run_blob_pipeline.py --only P0002,P0099 --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402
from layoutgen.backends import llm                                # noqa: E402
from layoutgen.model import blob                                  # noqa: E402
from layoutgen.pipeline import mapper                             # noqa: E402
from layoutgen.pipeline.golden import _manifest                   # noqa: E402

OUT = paths.ROUTING / "blob"


def served_by() -> str:
    """Which service and model answered, for the record."""
    if llm.PROVIDER == "gateway":
        from layoutgen.backends import gateway
        return f"gateway/{gateway.ENV}/{gateway.MODEL}"
    return f"azure/{llm.DEPLOYMENT}"


def version() -> str:
    """A short hash of everything that decides what these three calls produce.

    Editing a skill silently changes the output of every scene run after the edit, and a
    batch that straddles one is half of each with nothing on disk to say so. Recording
    the version makes that visible, and `--stale` makes it fixable without re-running
    six hundred scenes that were already current.

    The service and model are part of it for the same reason: a batch half-answered
    through Azure and half through the gateway is not one batch, and nothing else on disk
    would say which scene came from where.
    """
    h = hashlib.sha256()
    for part in (blob.skill("uprez-prompt"), blob.skill("layout-blob"),
                 blob.DECOUPLE_SYSTEM, blob.vocabulary(), served_by(),
                 # How the user message is assembled counts too: folding the intake
                 # answers in changed every scene's input without touching a skill, and
                 # a version that ignored it would call the old specs current.
                 blob.clarified("PROBE", [{"field": "f", "ask": "q", "answer": "a"}])):
        h.update(part.encode())
    return h.hexdigest()[:12]


#: The intake's questions as the author resolved them, written by `answer_questions.py`.
#: The router's arm was given these, so withholding them here would make the comparison a
#: test of who had more information rather than of what each did with it.
ANSWERED = paths.ROUTING / "answered"


def answers_for(scene: str) -> list[dict]:
    path = ANSWERED / f"{scene}.json"
    if not path.is_file():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    return [a for a in (d.get("answers") or []) if (a.get("answer") or "").strip()]


def run_one(scene: str, source: str, keep_uprez: str = "") -> dict:
    """All three stages for one scene, with the failing stage named if one fails.

    `keep_uprez` supplies a body already on disk instead of calling stage 1 again. It is
    for a re-run that changed how the config is decided and not how the prompt is
    rewritten: the uprez skill is unchanged, so a fresh call would return a differently
    worded body for the same instructions, and every config difference measured afterwards
    would be confounded by a body that also moved. Holding it fixed also drops a third of
    the calls. The version stamp still covers the uprez skill, so a spec written this way
    is honest about which instructions produced it.
    """
    said = answers_for(scene)
    # Built once and used twice: uprez turns it into the scene, and the blob stage reads
    # it for genre. Two calls assembling the same text separately is two chances to drift.
    enriched = blob.clarified(source, said)
    rec: dict = {"scene": scene, "source": source, "answers": said,
                 "scene_prompt": "", "blob": "",
                 "spec": None, "stage": "uprez", "status": "ok", "error": "",
                 "pipeline_version": version(), "served_by": served_by(),
                 "reused_uprez": bool(keep_uprez)}
    try:
        rec["scene_prompt"] = keep_uprez.strip() or blob.uprez(enriched)
        if not rec["scene_prompt"]:
            rec.update(status="no-space",
                       error="uprez found no describable world or layout")
            return rec
        rec["stage"] = "blob"
        # The original message goes in alongside the scene prompt: genre is decided here
        # and uprez has already removed the rules and economy that decide it. The
        # clarifications come with it, since a rule the author confirmed is genre evidence
        # exactly as much as one they wrote first time.
        rec["blob"] = blob.describe(rec["scene_prompt"], enriched)
        if not rec["blob"]:
            rec.update(status="error", error="blob stage returned nothing")
            return rec
        rec["stage"] = "decouple"
        rec["spec"] = blob.decouple(rec["blob"], rec["scene_prompt"])
        # Copied in, not asked for: the scene prompt is the body of both image prompts,
        # and a model asked to echo a paragraph it was given will eventually tidy it.
        # Carrying it on the spec makes the spec the whole input to stage 4.
        rec["spec"]["scene_prompt"] = rec["scene_prompt"]
        rec["stage"] = "done"
        # The mapper is not stored, but it is exercised: an order the spec asks for that
        # nothing can carve should surface here rather than at render time.
        built = mapper.build(rec["spec"])
        rec["order"] = built["order"]
        rec["first"] = built["first"]
        rec["mapper_notes"] = built["notes"]
    except Exception as exc:                                      # noqa: BLE001
        rec.update(status="error", error=f"{type(exc).__name__}: {exc}")
    return rec


def renormalise() -> None:
    """Re-apply `blob.normalise` to every spec on disk. No model calls.

    The relations `normalise` enforces are between fields that are already written down,
    so tightening one is not a reason to pay for six hundred scenes again - the fix
    applies to what is on disk. Anything it changes is appended to that spec's `notes`,
    which is where the record of the repair belongs.
    """
    changed = 0
    for path in sorted(OUT.glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("status") != "ok" or not rec.get("spec"):
            continue
        # The derived fields count as part of the record: a mapper rule can change the
        # order without touching the spec, and a stored order that disagrees with what
        # the mapper now computes is worse than no stored order at all.
        before = json.dumps([rec["spec"], rec.get("order"), rec.get("first"),
                             rec.get("mapper_notes")], sort_keys=True)
        rec["spec"] = blob.normalise(rec["spec"])
        rec["spec"]["scene_prompt"] = rec.get("scene_prompt", "")
        built = mapper.build(rec["spec"])
        rec["order"], rec["first"] = built["order"], built["first"]
        rec["mapper_notes"] = built["notes"]
        after = json.dumps([rec["spec"], rec["order"], rec["first"],
                            rec["mapper_notes"]], sort_keys=True)
        if after != before:
            changed += 1
            path.write_text(json.dumps(rec, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    print(f"renormalised {changed} specs in {OUT}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--renormalise", action="store_true",
                    help="re-apply the spec's own consistency rules to what is already "
                         "on disk, without calling the model")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated scene ids")
    ap.add_argument("--force", action="store_true",
                    help="redo scenes that already have a spec")
    ap.add_argument("--stale", action="store_true",
                    help="redo only scenes whose spec predates the current skill text")
    ap.add_argument("--keep-uprez", action="store_true",
                    help="reuse the scene prompt already on disk instead of calling stage "
                         "1 again, so a re-run that changed how the config is decided does "
                         "not also move the body")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if args.renormalise:
        renormalise()
        return
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    now = stamp = version()

    todo: list[tuple[str, str, str]] = []
    stale = kept = 0
    for scene, m in sorted(_manifest().items()):
        if only and scene not in only:
            continue
        existing = OUT / f"{scene}.json"
        old: dict = {}
        if existing.is_file():
            try:
                old = json.loads(existing.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                old = {}
        if existing.is_file() and not args.force:
            if not args.stale:
                continue
            if old.get("pipeline_version") == now:
                continue
            stale += 1
        source = (m.get("source_prompt") or "").strip()
        if not source:
            continue
        # Only a body that a *successful* run produced is worth keeping; reusing one from
        # a record that failed at uprez would hand the blob stage an empty string.
        body = ((old.get("scene_prompt") or "") if args.keep_uprez
                and old.get("status") == "ok" else "")
        kept += bool(body)
        todo.append((scene, source, body))
    if args.limit:
        todo = todo[: args.limit]

    print(f"skill version {now}"
          + (f"  ({stale} stale specs to refresh)" if args.stale else ""), flush=True)
    print(f"{len(todo)} scenes through "
          + (f"blob -> decouple, reusing {kept} scene prompts" if args.keep_uprez
             else "uprez -> blob -> decouple")
          + f" via {llm.DEPLOYMENT} ({args.workers} workers)", flush=True)

    lock, done, t0 = threading.Lock(), 0, time.monotonic()
    tally = {"ok": 0, "no-space": 0, "error": 0}

    def worker(item: tuple[str, str, str]) -> None:
        nonlocal done
        scene, source, body = item
        rec = run_one(scene, source, keep_uprez=body)
        with lock:
            done += 1
            tally[rec["status"]] = tally.get(rec["status"], 0) + 1
            (OUT / f"{scene}.json").write_text(
                json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
            if rec["status"] == "ok":
                s = rec["spec"]
                note = f"  {rec['first']}-first"
                print(f"  [{done}/{len(todo)}] {scene}  {s['genre']} / "
                      f"{s['shape'] or '(no shape)'}  {len(s['options'])} opts"
                      f"{note}", flush=True)
            else:
                print(f"  [{done}/{len(todo)}] {scene}  {rec['status']} "
                      f"at {rec['stage']}: {rec['error'][:90]}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for _ in pool.map(worker, todo):
            pass

    dt = time.monotonic() - t0
    print(f"\n{tally['ok']} ok, {tally['no-space']} no-space, {tally['error']} error "
          f"in {dt / 60:.1f} min ({tally['ok'] / dt * 60 if dt else 0:.1f} scenes/min)")
    print(f"specs in {OUT}")

    # The skills are read from disk on every call, so editing one mid-run changes the
    # instructions half way through while every record still carries the version stamped
    # at the start. That produces a spec set that looks uniform and is not, which is worse
    # than a set that is visibly stale. Cheap to detect, so never assume it did not happen.
    if (now := version()) != stamp:
        print(f"\n*** WARNING: the pipeline version changed during this run, "
              f"{stamp} -> {now}.\n*** A skill or prompt was edited while it was running, "
              f"so these specs were not all\n*** produced by the same instructions. "
              f"Re-run with --force before trusting them.")


if __name__ == "__main__":
    main()
