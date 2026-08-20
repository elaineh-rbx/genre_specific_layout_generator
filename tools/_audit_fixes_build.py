#!/usr/bin/env python3
"""One-shot: the Build.md findings from the three audit lanes.

Three kinds of fix. Facts that were wrong (Shooter's preset counts, a note
saying a preset does not exist when it now does). Archaeology that describes
how the document changed rather than what the system is -- chiefly the
"Build's original version" cluster, which reads like a decision log. And a
stray open design question, which moves to plan.md where open questions live.
"""
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "docs" / "LayoutGen - Build.md"

SUBS = [
    # --- facts that were wrong -------------------------------------------
    ("> Seven of Shooter's eight presets are lane networks. A prompt describing dispersed points of interest takes *Team Deathmatch* on `open-battlefield` and keeps the team bases, the cover arrays and the chokepoints, all of which it wanted.",
     "> Six of Shooter's nine presets are lane networks. A prompt describing dispersed points of interest takes *Team Deathmatch* on `open-battlefield` and keeps the team bases, the cover arrays and the chokepoints, all of which it wanted."),

    ("* **Not every shooter is a match.** The other eight presets are all competitive modes with two sides, so a solo aim-training range, a gun-testing place, or a target gallery had no preset at all and had to emit `preset: null` \u2014 a large Roblox category with nothing to land on. **Aim Trainer** is the single-player case:",
     "* **Not every shooter is a match.** The other eight presets are all competitive modes, so a solo aim-training range, a gun-testing place or a target gallery has only one row it can land on. **Aim Trainer** is that row:"),

    # --- rename history ---------------------------------------------------
    ("| `Teleporter` | point-to-point teleport (was `TravelPoint`) | mechanic |",
     "| `Teleporter` | point-to-point teleport | mechanic |"),

    ("| `Spawner` | NPC/entity/mob emitter (was NPC/mob `SpawnZone`) | mechanic |",
     "| `Spawner` | NPC/entity/mob emitter | mechanic |"),

    # --- the "Build's original version" cluster ---------------------------
    ("* **The requirement is the gate, not the enclosure.** Build's original version demanded sealed hermetic rooms, which described escape rooms specifically and excluded every open-air puzzle. A garden with a locked bridge is a puzzle.",
     "* **The requirement is the gate, not the enclosure.** Sealed hermetic rooms describe escape rooms specifically and exclude every open-air puzzle. A garden with a locked bridge is a puzzle."),

    ("* **Vehicle roads are conditional.** 15- and 30-stud streets exist so car meshes can turn. A walking-only roleplay town doesn't need them, and Build's original version wrongly demanded them of every game in the genre.",
     "* **Vehicle roads are conditional.** 15- and 30-stud streets exist so car meshes can turn. A walking-only roleplay town does not need them, so do not apply the street widths genre-wide."),

    ("* **The threat can be a region or an actor, and they're different builds.** A damaging volume needs a shape and a boundary; patrolling AI needs an origin and navigable ground. Build's original version only described the chase case and missed disaster survival entirely.",
     "* **The threat can be a region or an actor, and they're different builds.** A damaging volume needs a shape and a boundary; patrolling AI needs an origin and navigable ground. Cover both \u2014 describing only the chase case loses disaster survival."),

    ("* **Dugouts are a stadium-build feature, not a sport feature.** An informal pitch or a street court needs none of it. Build's original version required team enclosures of every sports game.",
     "* **Dugouts are a stadium-build feature, not a sport feature.** An informal pitch or a street court needs none of it, so do not require team enclosures of every sports game."),

    # --- other archaeology -------------------------------------------------
    ("**Strategy's `board-grid` is the precedent.** A tabletop board that players act on rather than move through has always been P0 with a real layout job, and nobody proposed routing chess to P5. `SET` generalises what that shape was already doing.",
     "**Strategy's `board-grid` is the precedent.** A tabletop board that players act on rather than move through is P0 with a real layout job. `SET` generalises it."),

    ("It costs nothing new. The axes are the same five `no-genre.md` has always asked, so the route is derived exactly as it is there",
     "It costs nothing new. The axes are the same five `no-genre.md` asks, so the route is derived exactly as it is there"),

    ("* **Roblox's own subgenres here are Action RPG, Open World & Survival RPG, and Turn-based RPG** \u2014 all three are presets above, and the middle one matches the bundle this doc already had under that exact name.",
     "* **Roblox's own subgenres here are Action RPG, Open World & Survival RPG, and Turn-based RPG** \u2014 all three are presets above under those exact names."),

    ("Roblox defines it as games with little to no player input, and the old rule read that as no layout job \u2014 but an idle game still has a space you watch, and most Roblox ones are a tycoon you happen to leave running.",
     "Roblox defines it as games with little to no player input, which is easy to read as no layout job \u2014 but an idle game still has a space you watch, and most Roblox ones are a tycoon you happen to leave running."),

    ("* **Roblox's own subgenres here are Animal Sim, Dress Up, Life, Morph Roleplay, and Pet Care** \u2014 all five are presets above, and building them forced two shapes and one option that did not exist. **An animal sim has no town**, so it needed `wilderness-open` and `den-shelter`; **a dress-up game has no settlement either**, just a runway and preparation booths, so it needed `stage-runway`. The genre had silently assumed a human town.",
     "* **Roblox's own subgenres here are Animal Sim, Dress Up, Life, Morph Roleplay, and Pet Care** \u2014 all five are presets above, and three of them need shapes that are not a human town. **An animal sim has no town**: it is `wilderness-open` and `den-shelter`. **A dress-up game has no settlement either**, just a runway and preparation booths, which is `stage-runway`. Do not assume housing."),

    ("* **Two of the five presets are among the largest games on the platform.** Adopt Me! and Dress to Impress are Pet Care and Dress Up respectively, so these are not fringe cases \u2014 they were simply unrepresented.",
     "* **Two of those five are among the largest games on the platform.** Adopt Me! is Pet Care and Dress to Impress is Dress Up, so neither is a fringe case."),

    # --- hedging and editorial --------------------------------------------
    ("* **Scope caveat on the cleanup volume.** It's a placed volume, so it's arguably layout, but its justification is runtime memory management. Kept here framed by *placement* \u2014 how far behind the camera it sits \u2014 rather than by the memory concern, which is Mechanics.",
     "* **The cleanup volume is specified by placement, not by the memory concern.** It is a placed volume, so it is layout; what it is *for* is runtime memory management, which is Mechanics. Specify how far behind the camera it sits and leave the rest alone."),

    ("* **Roblox files Runner as a subgenre of Obby & Platformer, not as its own genre.** Kept separate here because a runner routes P6 with elastic speed-derived spacing and shares almost none of its generation with a difficulty-chart obby.",
     "* **Roblox files Runner as a subgenre of Obby & Platformer; here it is its own genre.** A runner routes P6 with elastic speed-derived spacing and shares almost none of its generation with a difficulty-chart obby."),

    ("Whether a given game needs one is the user's pick, not a rule this document imposes \u2014 which is what the whole of Part II now assumes.",
     "Whether a given game needs one is the user's pick, not a rule this document imposes."),

    # --- the stray open question (moves to plan.md) ------------------------
    ("* **Open question on hub portals.** They're tagged `P4` because the Pipeline treats portals as zone transitions. If portals lead to genuinely separate Roblox *places* rather than zones of this build, the hub itself may be a single-zone P0 layout with teleport markers. Worth confirming.",
     "* **Hub portals are `P4` because the Pipeline treats a portal as a zone transition.** The exception is a portal leading to a genuinely separate Roblox *place* rather than to a zone of this build: that hub is a single-zone P0 layout with teleport markers, so route it P0 and say why."),
]


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    missing = [a for a, _ in SUBS if a not in text]
    for old, new in SUBS:
        text = text.replace(old, new, 1)
    BUILD.write_text(text, encoding="utf-8")
    print(f"applied {len(SUBS) - len(missing)}/{len(SUBS)}")
    for m in missing:
        print("  MISS:", m[:95])
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
