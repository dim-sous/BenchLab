# The failures the rules were written after

`CLAUDE.md` states the rules. This file keeps the incidents, because a rule without its incident
degrades into a slogan. Each entry states what was observed, with the lines; what it means is the
rule's job. Labels are stable: add new ones, never renumber.

Its rules come from its siblings too, which keep their own incidents: DeePC-Sandbox (`[D…]`, its
`docs/project/failures.md`), BESS-Optimization-Platform (`[B…]`) and RCWS (`[A…]`).

## [L1] A branch deleted after its merge failed (2026-11-14)

Closing branch 2b, one command merged DeePC-Sandbox #19 and then deleted its branch, here and
on GitHub. The merge failed (`GraphQL: Base branch was modified. Review and try the merge
again.`), the command went on, and GitHub closed the PR when its branch went. Nothing was lost:
the commits were still in the local repository; the branch was pushed again at `c52f99f`, the PR
reopened and merged (`eafdf77`). Rule: a merge's result is read (the PR's state) before its
branch is deleted, in a step of its own.

## [L2] A project could not change without Benchlab changing (2026-11-15)

Measured after branch 2c (Benchlab `v0.4.0`, DeePC-Sandbox `e3b1f06`), on the developer's
question whether a project can change without Benchlab changing, as it can without numpy
changing:

- A piece hands the page series, drawn as lines against x, and numbers, and nothing else
  (`benchlab/record/__init__.py:6`, `benchlab/figure/chart.py:3`). A setting is one of six kinds
  (`benchlab/record/config.py:86`). The declaration (`benchlab/project.py:30`) gives a project no
  way to add a part of the page.
- DeePC takes numpy by a range (`numpy>=2.4.2`) and Benchlab at an exact tag raised by hand
  (`tag = "v0.4.0"`). Each of 2a, 2b and 2c needed a DeePC PR (#18, #19, #20). #20 was DeePC's
  copy of the page's 136 words, a 160-line file identical but for its comments to the toy's, and
  the lines that declare, test and describe it (13 files, +229 −90).
- `docs/design.md` §4 planned one test per project that its pieces plug in. DeePC holds 1,727
  lines of tests of the Lab, of its 3,354 test lines, importing the Lab's insides
  (`benchlab.lab.app`, `form`, `state`, `view`, `words`).

The developer: "this is the same kind of mistake we made when we were first developing the lab
for the RCWS repo" (RCWS [A9]: "the record layer is a narrow pipe between a rich computation and
a fixed figure"). Rule: `CLAUDE.md`, "RunLab is used like numpy"; the direction:
`docs/design.md` §10.
