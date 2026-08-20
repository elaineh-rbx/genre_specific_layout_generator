# Agent arm — reason in prose, never encode the config

You are one of many agents producing the **reasoning stage** of the `agent` arm. Decide
each scene by reading the skills and write a prose layout blob. Do **not** write JSON and
do not try to satisfy a schema. A separate call through the LLM Gateway will transcribe
your prose into strict structured JSON after you finish.

That separation is the contract being tested:

1. the subagent reasons with tools and the full skill files;
2. the subagent hands off a prose decision;
3. the gateway encodes that already-made decision as JSON.

If you write structured JSON, stages 1 and 3 collapse back together and the arm is invalid.

Repository: `/home/builder/workspace/genre_specific_layout_generator`

## Read these once, at the start — not once per scene

1. `.cursor/skills/layout-intake/SKILL.md` — which layout concerns need resolution.
2. `.cursor/skills/uprez-prompt/SKILL.md` — how context becomes image-ready spatial prose.
3. `.cursor/skills/genre-choice/SKILL.md` — the classification workflow.
4. `.cursor/skills/genre-choice/shapes.md` — the shared shape catalogue. Every shape in
   it is reachable from every genre. A genre's typical list is presentation, not a
   restriction.
5. `.cursor/skills/genre-choice/options.md` — the shared option catalogue. Read it on
   demand when the selected genre and the universal six do not cover a spatial request;
   take the canonical ID and route, but write scene-specific text.
6. `.cursor/skills/scope-reduce-default/SKILL.md` — the no-question reduction pass for
   requests that need more than one buildable frame at their gameplay grain.
7. `.cursor/skills/layout-blob/SKILL.md` — the prose handoff contract. In particular,
   follow its ten-section order, canonical IDs in backticks, and prose targets.

Then, per scene, read the one file under `.cursor/skills/genre-choice/genres/` for the
genre you land on, and `.cursor/skills/genre-choice/no-genre.md` if you conclude the
prompt has no genre. Re-read a genre file only when you move to a genre you have not
already read. Consult `options.md` only when that prompt needs an option outside the
loaded genre and universal rows.

## Per scene

Your shard file lists scene IDs, one per line. Work them **in order, one at a time**, and
write each result to disk before starting the next so partial progress survives.

1. Read `results/routing/agent_input/<SCENE>.json`. It carries the author's original
   prompt in `source` and their replies to the intake questions in `answers`. Read the
   whole file freely — the other systems' configs, including the label this arm is scored
   against, are deliberately not in it, so there is nothing here to avoid. Do not go
   looking for them in `results/routing/answered/`.
2. Use `layout-intake` to identify layout-changing questions. Preserve supplied intake
   answers as `author`. Copy every supplied `field`, `ask`, and `answer` string verbatim:
   do not translate, paraphrase, shorten, or rename them. For any necessary unanswered
   question, choose the narrowest grounded answer and mark it `agent_inferred`.
3. Decide and record the full-request configuration by following `genre-choice`, then
   complete `layout-intake`'s handoff: genre, shape, options, placements, concrete
   components, render order, scale, theme, and full route. Do not scope these decisions
   while you are still collecting them.
4. At the end, after the full-request sections are complete, follow
   `scope-reduce-default` on that assembled handoff. In `## Scope reduction result`,
   preserve the unchanged full-request decision and record its complete zone/active
   result. If it fired, the active zone must include all executable shape, config,
   placement, component, render-order, scale, theme, and route information; a modifier
   named in `route_cleared` remains provenance rather than executable route.
5. Last, follow `uprez-prompt` to write `## Final scoped image prompt`. If scope
   reduction did not fire, this prompt describes the full request. If it fired, it
   describes **only the active zone**. Deferred zones must not leak into this prompt
   positively or negatively. This exact final section is the only scene body accepted by
   both isometric and top-down prompt assembly.
6. There is no user to interview. Never imply that an agent-inferred answer came from the
   author.
7. Write `results/routing/agent_blob/<SCENE>.md` as prose beginning with
   `# Agent decision`, followed by the ten sections required by `layout-blob/SKILL.md`:
   Clarifications resolved; Genre; Shape and preset; Config requirements; Layout
   requirements; Layout components; Render order; Scale, theme, and pipeline cost; Scope
   reduction result; Final scoped image prompt.

The decision is the self-contained artifact the gateway transcribes. Name canonical shape,
option, order, and route IDs in backticks. Spell genre and preset names exactly as the
genre file does. Include every scene-specific layout component and count the later JSON
needs; the gateway may transcribe what you wrote but may not invent what you omitted. The
final scoped image prompt must combine the original message and intake answers with the
end-of-decision scope result; answers override conflicting source details. The builder
copies that section verbatim after transcription, and rendering accepts no other scene
body.

## Do not

- Do not read `results/routing/blob/`, `results/routing/agent/`,
  `results/routing/agent_spec/`, or `docs/`. The skill files are your source, and those
  directories hold other systems' answers.
- Do not emit JSON, a JSON code fence, or a field-value dump disguised as prose.
- Do not skip a scene because it is thin. `"make a hide and seek map"` is a real prompt
  with a real answer; decide it and say what you assumed.
- Do not stop early. Finish every scene in your shard.

## Report back

One line per scene: `<SCENE> prose blob written`. Nothing else — the decisions belong in
each `.md` artifact, not in your final message.
