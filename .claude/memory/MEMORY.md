# Benchlab: where the work stands

Start here in a new session. Updated 2026-11-13, at the end of the design session (a cloud
session; the work continues in VS Code on the developer's computer).

## Where it stands

- **Design approved** and pushed: `docs/design.md`. It holds every decision, each marked by who
  made it: the developer (what the page shows, decided after driving it) or Claude (how it is
  built, with the reason).
- **Mockup** the developer drove (two rounds, real DeePC and Hydrofoil runs):
  https://claude.ai/artifact/7Ay5aQm2F6FyxJhKa4frbb (private to the developer).
- **Branch 1 planned and approved**: `docs/plan-branch-1.md`. Benchlab's core is DeePC's
  `devkit/{record,figure,terminal,lab}` moved here unchanged, except for the four ties to DeePC
  the plan names, and DeePC is moved onto it with every record and still identical. To be
  implemented from VS Code. Nothing is built yet: this repository holds only documents.

## Next

1. Implement `docs/plan-branch-1.md`: PR A here (branch `core-from-deepc`), PR B in DeePC. Every
   git write only on the developer's word, at hand-off.
2. Branch 2: the page as designed (tree, runs in their own processes, words as cells, no hovers),
   with Benchlab's own test project. Then Hydrofoil moves (with its naming pass), the shared
   calculations, BESS, old runs and Re-fly (`docs/design.md` §8).

## How the developer works

- **Every question goes through AskUserQuestion**, never as text at the end of a message
  (2026-11-13: "WHEN I ASK QUESTION TO WHICH I EXPECT ANSWERS, ALWAYS USE THE ASKTHEUSER TOOL").
  This also belongs in `~/.claude/CLAUDE.md` on each of their computers; they chose to add it
  there themselves.
- **Not a software engineer**: "take every last one of my answer with a grain of salt". What the
  page shows is theirs, settled only after driving it. How it is built is Claude's, said with
  its reason. Push back when an answer costs more than it looks, and write the cost beside the
  decision (`docs/design.md` §3, decision 5, is the example).
- The siblings' rules hold here too: propose, then plan mode, then build. No multi-agent fan-out
  without asking first. Hand off in the Lab. No git write without their word.

## Measured on 2026-11-13 (cloud machine, 4 CPUs, defaults)

- Lines in the four shared layers per project: DeePC 4,486, Hydrofoil 1,798, BESS 5,312, RCWS
  10,294.
- DeePC `closed_loop` 77 s wall per default run; its λ_g sweep (1, 10, 100) 160 s for 3 runs one
  after another. Hydrofoil takeoff 0.7 to 1.2 s per run. `uv run hydrofoil settings flight`
  0.56 to 0.59 s warm, 2.2 s cold.
- Labels that are code names: 64 of Hydrofoil's 70 settings, 8 of DeePC `open_loop`'s 13. Each
  is renamed when its project moves (`docs/design.md` decision 5).
