# Batch Workflow Characterization and Guard Unification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Batch close, reopen, and release behavior deterministic and ensure every release entry point applies the same safety rules.

**Architecture:** Establish `hoch.lims.workflow.batch.guards.guard_release` as the canonical release decision. Keep the existing `Batch.guard_release_batch()` method for installed workflow compatibility, but reduce it to context resolution plus delegation. Preserve the named guard adapter and workflow-module alias so old and modern SENAITE dispatch paths converge on the same implementation.

**Tech Stack:** Python 2.7, SENAITE workflow APIs, Archetypes extender fields, `unittest2`, Zope test runner.

## Global Constraints

- Work only on `upgrade/senaite-core-2x-official`.
- Do not edit SENAITE Core or mutate the shared test database.
- Do not change the installed workflow definition in this tranche; existing sites call `python:here.guard_release_batch()`.
- A releasable Batch must be closed and have an active publication containing every release sample.
- Every non-invalid release sample must be verified or published.
- Verified release samples must be within specification and have no open OOS investigation.
- Use field access for extender fields and ResultsReport `getSample`/`getContainedSamples` APIs.
- Both the legacy Batch method and guard adapter must delegate to the canonical guard.
- Validate against official and historical core matrices.

---

### Task 1: Characterize the canonical release guard

**Files:**
- Create: `src/hoch/lims/tests/test_batch_workflow.py`

**Interfaces:**
- Consumes: `guard_release(batch)`, `guard_close(batch)`, and `guard_reopen(batch)`
- Produces: executable release invariants

- [ ] **Step 1: Add focused in-memory collaborators**

Create specific Batch, Sample, Publication, Analysis, and Field collaborators
that expose the public methods used by the guard. Patch only these external
API boundaries in test setup:

```text
api.get_review_status
api.get_uid
api.get_tool
```

Restore them in teardown.

- [ ] **Step 2: Add the complete valid-release test**

Use a closed Batch, an active publication, one verified in-spec release
sample, publication membership, and an empty OOS catalog. Assert
`guard_release(batch) is True`.

- [ ] **Step 3: Add one rejection test per invariant**

Add separate tests for:

```text
Batch not closed
no ReleasePublication
no release samples
release sample not verified/published
publication missing a release sample
publication not active
verified analysis out of range
open OOS investigation
```

Each test changes one input from the valid fixture and asserts `False`.

- [ ] **Step 4: Characterize close and reopen**

Assert:

```text
guard_close(open Batch) -> True
guard_close(closed Batch) -> False
guard_reopen(closed Batch) -> True
guard_reopen(open Batch) -> False
```

- [ ] **Step 5: Run focused tests**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_batch_workflow
```

Expected: the canonical guard tests expose any incompatible publication or
field access in the current implementation.

### Task 2: Unify legacy and adapter release paths

**Files:**
- Modify: `src/hoch/lims/workflow/batch/guards.py`
- Modify: `src/hoch/lims/patches/batch.py`
- Modify: `src/hoch/lims/tests/test_batch_workflow.py`

**Interfaces:**
- Produces: one canonical release decision reached from both dispatch paths

- [ ] **Step 1: Add delegation tests**

Assert that:

- `BatchGuardAdapter(batch).guard("release")` returns the canonical decision;
- `guard_release_batch(batch)` returns the same decision;
- unrelated adapter transitions return `True`.

- [ ] **Step 2: Verify RED for legacy safety gaps**

Run the focused suite and confirm that the legacy Batch method permits at
least the out-of-spec or open-OOS fixture that the canonical guard rejects.

- [ ] **Step 3: Consolidate robust field and publication access**

In the canonical guard:

- read `ReleasePublication` and sample `Destination` through `getField`;
- obtain publication membership from `getSample()` plus
  `getContainedSamples()`;
- allow verified or published sample states;
- skip a non-final status only when `sample.isInvalid()` is true;
- apply in-spec and open-OOS checks to included release samples;
- require publication state `active`.

Reduce `guard_release_batch` to acquisition-safe Batch resolution followed by:

```python
return guards.guard_release(batch)
```

- [ ] **Step 4: Verify both dispatch paths**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_batch_workflow
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_batch_workflow
```

Expected: identical green results.

### Task 3: Characterize release effects

**Files:**
- Modify: `src/hoch/lims/tests/test_batch_workflow.py`

**Interfaces:**
- Consumes: `events.after_release(batch)`
- Produces: protected release audit fields and reindex behavior

- [ ] **Step 1: Add release-event test**

Patch `api.get_current_user` with a specific user collaborator. Call
`after_release(batch)` and assert:

- `ReleaseDate` receives a non-empty `DateTime`;
- `ReleasedBy` receives the exact user ID;
- the Batch is reindexed exactly once.

- [ ] **Step 2: Add missing-field resilience test**

Use a Batch without `ReleaseDate` and `ReleasedBy`; assert the handler still
reindexes and does not fail.

- [ ] **Step 3: Run focused tests in both matrices**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_batch_workflow
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_batch_workflow
```

Expected: all guard and event tests pass.

### Task 4: Verify and document

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Produces: exact Batch/workflow validation evidence

- [ ] **Step 1: Run both complete suites**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
```

- [ ] **Step 2: Record focused and complete counts**

Document the duplicate-guard defect, canonical ownership, covered release
invariants, event effects, and exact results.

- [ ] **Step 3: Verify hygiene and commit**

```bash
git diff --check
git add src/hoch/lims/workflow/batch/guards.py \
  src/hoch/lims/patches/batch.py \
  src/hoch/lims/tests/test_batch_workflow.py \
  docs/validation/senaite-2x-component-matrix.md
git commit -m "fix: unify batch release guards"
```
