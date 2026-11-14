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
