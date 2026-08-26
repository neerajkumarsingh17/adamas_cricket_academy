# ACA-OMS — Claude Code starter kit

Drop these files at the root of a fresh repository. Claude Code reads `CLAUDE.md`
automatically at the start of every session; the `docs/` folder is what it reads when a task
needs detail.

```
your-repo/
  CLAUDE.md                    <- project instructions, read automatically
  RUN.md                       <- THE EXECUTION ORDER: 43 prompts, 12 sessions
  LOCAL-SETUP.md               <- native setup: prerequisites, .env, Makefile
  PROMPTS-SETUP.md             <- START HERE: Sprint 0, four prompts
  PROMPTS.md                   <- Sprints 1-2 and the repeating pattern
  PROMPTS-PHASE1-SCREENS.md    <- the 27 Phase 1 screens
  docs/
    00-project-structure.md  <- one Django app per module, the full 37-app map
    01-data-model.md     <- every Phase 0 + Phase 1 model, field by field
    02-api-spec.md       <- endpoint list with permissions and error shapes
    03-rbac.md           <- 16 roles x 6 verbs, as seed data
    04-state-machines.md <- admission chain, 11 student statuses, document lifecycle
    05-build-sequence.md <- the 91 tasks in build order, with acceptance checks
    06-conventions.md    <- naming, migrations, testing, definition of done
```

## How to start

1. Get decisions D-01 (numbering), D-02 (duplicate rule) and D-03 (RBAC matrix) signed.
   They are listed in the tech spec. Do not skip this — the identity model is the one thing
   in this project that is genuinely expensive to change later.
2. Update `docs/01-data-model.md` section 6 with the **signed** numbering formats, and
   `docs/03-rbac.md` with the **signed** matrix. The versions in this kit are proposals.
3. Commit the kit.
4. Open Claude Code and paste the **orientation prompt** at the top of `RUN.md`. It makes
   Claude Code prove it has read the kit before writing anything.
5. Then work down `RUN.md` — it is the single ordered list of every prompt, and it says which
   file each one lives in.

5. Work one task at a time. After each, run the acceptance check named in the task row
   before moving on.

## Keeping the kit current

These docs are the handover artifact. A solo developer is a single point of failure; the
mitigation is that the project's context lives in version control rather than in one
person's head. When the data model, API or a state machine changes, update the doc in the
**same commit**. A PR that changes a serializer without updating `02-api-spec.md` is not done.
