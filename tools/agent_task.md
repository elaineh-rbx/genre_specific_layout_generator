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
5. `.cursor/skills/layout-blob/SKILL.md` — the prose handoff contract. In particular,
   follow its nine-section order, canonical IDs in backticks, and prose targets.

Then, per scene, read the one file under `.cursor/skills/genre-choice/genres/` for the
genre you land on, and `.cursor/skills/genre-choice/no-genre.md` if you conclude the
prompt has no genre. Re-read a genre file only when you move to a genre you have not
already read.

## Per scene

Your shard file lists scene IDs, one per line. Work them **in order, one at a time**, and
write each result to disk before starting the next so partial progress survives.

1. Read `results/routing/agent_input/<SCENE>.json`. It carries the author's original
   prompt in `source`, their replies to the intake questions in `answers`, and the
   already-fixed uprezzed body in `scene_prompt`. Read the whole file freely — the other
   systems' configs, including the label this arm is scored against, are deliberately not
   in it, so there is nothing here to avoid. Do not go looking for them in
   `results/routing/answered/`.
2. Use `layout-intake` to identify layout-changing questions. Preserve supplied intake
   answers as `author`; for any necessary unanswered question, choose the narrowest
   grounded answer and mark it `agent_inferred`.
3. Decide the configuration by following `genre-choice`, then express the complete
   decision by following `layout-blob`. The enriched image prompt incorporates both kinds
   of resolved answers.
4. There is no user to interview. Never imply that an agent-inferred answer came from the
   author.
5. Write `results/routing/agent_blob/<SCENE>.md` as prose, with this exact outer shape:

   - `# Scene prompt` followed by the `scene_prompt` text verbatim.
   - `# Agent decision` followed by the nine sections required by
     `layout-blob/SKILL.md`: Clarifications resolved; Enriched image prompt; Genre; Shape
     and preset; Config requirements; Layout requirements; Layout components; Render
     order; Scale, theme, and pipeline cost.

The scene-prompt section makes the prose artifact self-contained. The decision section is
what the gateway transcribes. Name canonical shape, option, order, and route IDs in
backticks. Spell genre and preset names exactly as the genre file does. Include every
scene-specific layout component and count the later JSON needs; the gateway may transcribe
what you wrote but may not invent what you omitted. The enriched image prompt must combine
the original message and intake answers into the final image-ready spatial description;
answers override conflicting details from the original message.

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
