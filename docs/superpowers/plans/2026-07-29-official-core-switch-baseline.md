# Official SENAITE Core Switch Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the HOCH.LIMS characterization suite against a clean, pinned checkout of official `senaite.core/2.x` and classify every resulting incompatibility before writing compatibility code.

**Architecture:** Keep both shared source checkouts untouched. Create a disposable official-core checkout beside the existing add-on worktree and derive a second temporary test runner whose only source-path substitutions are the isolated `hoch.lims` checkout and clean official `senaite.core` checkout. Treat the first failing run as diagnostic evidence, then record failures by ownership: add-on compatibility, upstream capability, or obsolete local patch.

**Tech Stack:** Git, Python 2.7, Zope test runner, SENAITE Core 2.x.

## Global Constraints

- Work on `upgrade/senaite-core-2x-official` in `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline`.
- Use official repository `https://github.com/senaite/senaite.core.git`, branch `2.x`, pinned initially to `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.
- Do not add remotes, switch branches, stash, clean, or edit files in `/home/lims/hochlims/src/senaite.core`.
- Do not edit `/home/lims/hochlims/bin/test`.
- Do not implement compatibility behavior until the clean-core failures have been reproduced and classified.
- Do not push or open a PR.

---

### Task 1: Create the isolated official-core runner

**Files:**
- Create outside Git: `/home/lims/hochlims/worktrees/senaite-core-official-2x`
- Create outside Git: `/tmp/hoch-lims-official-core-test`

**Interfaces:**
- Consumes: shared generated runner and the official core repository
- Produces: a reproducible test command that loads isolated HOCH.LIMS and official core sources

- [ ] **Step 1: Clone the official branch without touching the shared core**

Run:

```bash
git clone --branch 2.x --single-branch \
  https://github.com/senaite/senaite.core.git \
  /home/lims/hochlims/worktrees/senaite-core-official-2x
git -C /home/lims/hochlims/worktrees/senaite-core-official-2x \
  checkout --detach ba57f85e84cea821a5c206d7f90b3ccfcaad43f5
```

Expected: detached HEAD equals the pinned SHA and the checkout is clean.

- [ ] **Step 2: Generate an isolated runner**

Copy `/home/lims/hochlims/bin/test` to
`/tmp/hoch-lims-official-core-test`, then replace:

```text
/home/lims/hochlims/src/hoch.lims/src
```

with:

```text
/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline/src
```

and replace:

```text
/home/lims/hochlims/src/senaite.core/src
```

with:

```text
/home/lims/hochlims/worktrees/senaite-core-official-2x/src
```

Preserve executable permissions.

- [ ] **Step 3: Audit source-path isolation**

Run:

```bash
rg -n "hoch\\.lims/(src|worktrees)|senaite\\.core/src|senaite-core-official" \
  /tmp/hoch-lims-official-core-test
```

Expected: add-on entries point only to the isolated add-on worktree; core
entries point only to the official-core checkout.

### Task 2: Capture the clean-core failure baseline

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Consumes: `/tmp/hoch-lims-official-core-test`
- Produces: exact failure evidence and an ownership classification

- [ ] **Step 1: Run focused time characterization**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
```

Expected: failure of `test_time_result_type_is_registered` if official core
does not register `time`; record any additional failures exactly.

- [ ] **Step 2: Run the complete add-on suite**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
```

Expected: the process completes and reports all compatibility failures. A
non-zero exit is diagnostic evidence at this stage.

- [ ] **Step 3: Classify every observed regression**

Add an official-core section to the component matrix with:

- pinned repository URL and SHA;
- focused and complete runner commands;
- exact test totals, failures, errors, and skipped counts;
- each failure mapped to one of:
  - `hoch.lims` compatibility;
  - missing general SENAITE capability suitable for upstream;
  - historical customization no longer required.

- [ ] **Step 4: Verify shared checkout preservation**

Run:

```bash
git -C /home/lims/hochlims/src/senaite.core status --short --branch
git -C /home/lims/hochlims/src/hoch.lims status --short --branch
```

Expected: the same eight historical core modifications and the same
`reportview.py` add-on modification that existed before this plan.

- [ ] **Step 5: Commit only the diagnostic record**

Run:

```bash
git diff --check
git add docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: record official core failure baseline"
```

Expected: no production-code changes in this commit.

### Task 3: Write the compatibility implementation plan

**Files:**
- Create: `docs/superpowers/plans/2026-07-29-official-core-time-compatibility.md`

**Interfaces:**
- Consumes: the classified clean-core failure baseline
- Produces: exact TDD tasks for add-on-owned compatibility and a separate upstream proposal where required

- [ ] **Step 1: Select supported extension points**

For each failing boundary, document the smallest extension point that avoids
editing core: browser override, adapter, subscriber, schema extender, or
isolated monkey patch as a last resort.

- [ ] **Step 2: Define red-green tests**

Specify tests that assert user-visible storage and formatting behavior. Do not
repeat the historical core test that derives its expected result using
`dtime.to_dt("HH:MM:SS")`, because it silently validates midnight.

- [ ] **Step 3: Separate upstream and add-on deliverables**

The plan must state which changes can ship in the HOCH.LIMS PR and which would
require a distinct SENAITE Core PR. No SENAITE Core PR is created without
explicit user approval.

- [ ] **Step 4: Commit the compatibility plan**

Run:

```bash
git add docs/superpowers/plans/2026-07-29-official-core-time-compatibility.md
git commit -m "docs: plan official core time compatibility"
```
