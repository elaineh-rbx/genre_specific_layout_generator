"""Set the skill's answer beside the router's, scene by scene.

Both answer the same question from the same prompt: `model/router.py` in two LLM calls
with no conversation, `.cursor/skills/genre-choice/` as a procedure an agent follows,
reading the genre file and its notes on the way. This prints where they agree and where
they do not.

It is deliberately not a score. Neither side is ground truth - that is what the blinded
judge over the renders is for - and the useful output is the *kind* of disagreement.
The two so far have been of one kind: the skill picking up something the prompt asked
for that the router dropped, which is worth knowing before any image is drawn.

Every block is put through `handoff.adapt` first, so an option the skill invented or a
route it got wrong shows up here rather than being counted as a difference of opinion.

    python -m layoutgen.model.compare           # every scene that has both
    python -m layoutgen.model.compare 0003      # one scene, with the option lists
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

from layoutgen import paths
from layoutgen.model import handoff
from layoutgen.model import rules as br

ROUTER = paths.ROUTING / "rules.jsonl"
SKILL = paths.ROUTING / "skill"

#: The six that belong to every genre. Worth counting on their own: they are new, and
#: they are the only picks that cannot come from a preset.
UNIVERSAL = {o.id for o in br.UNIVERSAL}


@dataclass
class Row:
    scene: str
    genre_r: str = ""
    genre_s: str = ""
    shape_r: str = ""
    shape_s: str = ""
    #: What a no-genre block says instead of a shape. Empty on every other row.
    axes: dict[str, str] = field(default_factory=dict)
    preset_r: str = ""
    preset_s: str = ""
    route_r: list[str] = field(default_factory=list)
    route_s: list[str] = field(default_factory=list)
    shared: list[str] = field(default_factory=list)
    only_skill: list[str] = field(default_factory=list)
    only_router: list[str] = field(default_factory=list)
    universal: list[str] = field(default_factory=list)
    free_text: int = 0
    problems: list[str] = field(default_factory=list)
    ok: bool = True

    @property
    def same_genre(self) -> bool:
        return self.genre_r == self.genre_s

    @property
    def same_shape(self) -> bool:
        return self.shape_r == self.shape_s

    @property
    def same_preset(self) -> bool:
        return (self.preset_r or "none") == (self.preset_s or "none")

    @property
    def no_genre(self) -> bool:
        return self.genre_s == br.NO_GENRE_NAME

    @property
    def shape_label(self) -> str:
        """What to show in the shape column, which a no-genre row fills with axes."""
        if not self.no_genre:
            return self.shape_s
        return ", ".join(self.axes.values()) or "all defaults"


def router_picks() -> dict[str, dict]:
    if not ROUTER.is_file():
        return {}
    return {r["scene"]: r for r in
            (json.loads(x) for x in ROUTER.open() if x.strip())}


def compare(scene: str, pick: dict) -> Row:
    block, source, _ = handoff.load(SKILL / f"{scene}.json")
    h = handoff.adapt(block, source=source or handoff.golden_source(scene))
    row = Row(scene=scene, ok=h.ok,
              genre_r=pick.get("genre", ""), genre_s=h.genre,
              shape_r=pick.get("shape", ""), shape_s=h.spec.get("shape") or "",
              axes=dict(h.axes),
              preset_r=pick.get("preset") or "", preset_s=h.preset,
              route_r=pick.get("route") or [], route_s=h.route,
              free_text=len(h.free_text),
              problems=[str(p) for p in h.problems])
    rp = [o for o in (pick.get("options") or []) if o]
    row.shared = [o for o in h.options if o in rp]
    row.only_skill = [o for o in h.options if o not in rp]
    row.only_router = [o for o in rp if o not in h.options]
    row.universal = [o for o in h.options if o in UNIVERSAL]
    return row


def collect(only: str = "") -> list[Row]:
    picks = router_picks()
    rows = []
    for path in sorted(SKILL.glob("*.json")):
        scene = path.stem
        if only and scene != only:
            continue
        if scene in picks:
            rows.append(compare(scene, picks[scene]))
    return rows


def _line(row: Row) -> str:
    mark = lambda same: "=" if same else "*"  # noqa: E731 - a two-character legend
    return (f"  {row.scene}  {mark(row.same_genre)} {row.genre_s[:22]:<22} "
            f"{mark(row.same_shape)} {row.shape_label[:20]:<20} "
            f"{mark(row.same_preset)} {(row.preset_s or 'none')[:20]:<20} "
            f"+{len(row.only_skill)} -{len(row.only_router)}"
            + ("" if row.ok else "  INVALID"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scene", nargs="?", default="", help="one scene, in detail")
    args = ap.parse_args()

    rows = collect(args.scene)
    if not rows:
        print("no scene has both a router pick and a skill block")
        return

    if args.scene:
        r = rows[0]
        print(f"scene {r.scene}\n")
        print(f"  genre   router {r.genre_r or '-'}\n"
              f"          skill  {r.genre_s or '-'}")
        print(f"  shape   router {r.shape_r or '-'}\n"
              f"          skill  {r.shape_label or '-'}"
              + ("   (axes, not a shape)" if r.no_genre else ""))
        print(f"  preset  router {r.preset_r or 'none'}\n"
              f"          skill  {r.preset_s or 'none'}")
        print(f"  route   router {' + '.join(r.route_r) or '-'}\n"
              f"          skill  {' + '.join(r.route_s) or '-'}")
        print(f"\n  both agreed on   {', '.join(r.shared) or '(nothing)'}")
        print(f"  only the skill   {', '.join(r.only_skill) or '(nothing)'}")
        print(f"  only the router  {', '.join(r.only_router) or '(nothing)'}")
        if r.universal:
            print(f"  universal        {', '.join(r.universal)}")
        print(f"  free text        {r.free_text} entries with no option")
        for p in r.problems:
            print(f"  problem          {p}")
        return

    print(f"{len(rows)} scenes have both. `=` agrees with the router, `*` differs;")
    print("+n options only the skill picked, -n only the router.\n")
    print("  scene  genre                    shape                  preset")
    for r in rows:
        print(_line(r))

    n = len(rows)
    same_g = sum(r.same_genre for r in rows)
    same_s = sum(r.same_shape for r in rows)
    same_p = sum(r.same_preset for r in rows)
    added = sum(len(r.only_skill) for r in rows)
    dropped = sum(len(r.only_router) for r in rows)
    uni = [o for r in rows for o in r.universal]
    bad = [r for r in rows if not r.ok]
    route_diff = sum(1 for r in rows if any(p.startswith("[route]") for p in r.problems))

    ng = [r for r in rows if r.no_genre]

    print(f"\nagreement   genre {same_g}/{n}   shape {same_s}/{n}   preset {same_p}/{n}")
    if ng:
        # The router is a fifteen-way choice and cannot produce this answer, so these
        # rows can only ever read as a disagreement. Said once, so the line above is
        # not mistaken for the skill getting them wrong.
        print(f"            {len(ng)} of those are scenes the skill calls a place rather "
              f"than a game,\n            which the router has no way to say: "
              + ", ".join(r.scene for r in ng))
    print(f"options     {added} the router did not pick, {dropped} it picked and the "
          f"skill did not")
    print(f"universal   {len(uni)} picks across {sum(1 for r in rows if r.universal)} "
          f"scenes: {', '.join(sorted(set(uni))) or '(none)'}")
    print(f"free text   {sum(r.free_text for r in rows)} entries with no option")
    print(f"validity    {n - len(bad)}/{n} adapt to a runnable spec"
          + (f"; {', '.join(r.scene for r in bad)} do not" if bad else ""))
    print(f"route       {route_diff}/{n} disagree with the document on the route")


if __name__ == "__main__":
    main()
