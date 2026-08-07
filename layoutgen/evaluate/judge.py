"""Ask a vision model which requirements are visible in which image, blind.

One question, whatever the number of arms. It used to be two - a pairwise judge and a
three-way judge, written months apart, with different schemas, different retry
behaviour and different wording in the system prompt. Two judges meant two answers to
"is this feature present", and no way to tell whether a difference between comparisons
came from the arms or from the judge.

Blinding is the whole reason this is worth doing. The images arrive labelled A, B, C
in an order fixed by the scene number, so the judge cannot know which arm it is
marking, and position cannot correlate with arm across the set.
"""

from __future__ import annotations

import itertools
import pathlib

from layoutgen.backends import llm

SYSTEM = """You audit game-layout concept images against explicit layout requirements.

You see {n} images of the same game scene, labelled {labels}, and a numbered list of
layout requirements. For each requirement, decide independently whether it is clearly
visible in each image.

Judge only what is actually depicted. "Clearly visible" means a person reading the
image could point at the thing. Do not credit a requirement because the scene is the
right genre, because the thing is implied, or because it would be easy to add. If you
cannot point at it, it is absent.

The images are unrelated attempts at the same brief - do not assume they should agree,
and do not let one image's answer influence another's.

Ignore art quality, lighting, colour and appeal entirely. You are checking presence
and arrangement, nothing else."""

LETTERS = "ABCDEFGH"


def order_for(arms: tuple[str, ...], key: int) -> list[str]:
    """Which arm is shown in which position, for this scene.

    A fixed permutation per key: the label an arm gets is unpredictable but
    reproducible, and across a set every ordering is used about equally.
    """
    perms = list(itertools.permutations(range(len(arms))))
    return [arms[i] for i in perms[key % len(perms)]]


def _schema(n_reqs: int, n_arms: int) -> dict:
    """One verdict per arm per requirement, positional.

    `present` is an array rather than named fields because the arms are not named to
    the judge - it is answering about image A, B, C, and the caller maps positions
    back to arms afterwards.
    """
    return {
        "name": "audit", "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array", "minItems": n_reqs, "maxItems": n_reqs,
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "present": {
                                "type": "array", "minItems": n_arms,
                                "maxItems": n_arms,
                                "items": {"type": "boolean"},
                                "description": "One per image, in the order shown.",
                            },
                            "note": {"type": "string"},
                        },
                        "required": ["index", "present", "note"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["requirements"],
            "additionalProperties": False,
        },
    }


def judge(reqs: list[dict], thumbs: dict[str, pathlib.Path], key: int,
          retries: int = 3) -> tuple[list[dict], list[str]] | None:
    """Mark one set of images against one checklist, and say what was shown where.

    `thumbs` maps arm to image, and its order is the order the arms are considered in;
    the order they are *shown* in is derived from `key`. Anything holding a set of
    images can call this - a scene from the golden set, or a prompt someone just typed
    into the playground - so a card's ticks mean what a stored score's ticks mean.
    """
    arms = tuple(thumbs)
    shown = order_for(arms, key)
    labels = ", ".join(LETTERS[: len(arms)])

    listing = "\n".join(f"{i + 1}. {r['label']} - {r['text']}"
                        for i, r in enumerate(reqs))
    content: list[dict] = [llm.text_part(f"REQUIREMENTS\n{listing}")]
    for pos, arm in zip(LETTERS, shown):
        content.append(llm.text_part(f"Image {pos}:"))
        content.append(llm.image_part(thumbs[arm]))
    content.append(llm.text_part(
        "For every requirement, mark presence in each image."))

    try:
        out = llm.ask(SYSTEM.format(n=len(arms), labels=labels), content,
                      _schema(len(reqs), len(arms)), retries=retries)
    except llm.LLMError:
        return None

    items = []
    for i, r in enumerate(out["requirements"]):
        if i >= len(reqs):
            break
        verdicts = dict(zip(shown, r["present"]))
        items.append({**reqs[i], "note": r.get("note", ""),
                      "present": {a: bool(verdicts.get(a)) for a in arms}})
    return items, shown
