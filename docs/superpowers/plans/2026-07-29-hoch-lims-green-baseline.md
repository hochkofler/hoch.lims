# HOCH LIMS Green Test Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing `hoch.lims` test baseline reproducible and green
without changing production behavior.

**Architecture:** Keep the current functional addon untouched. Adapt the
existing vocabulary tests to the `zc.testrunner` test protocol, remove the
invalid Zope-product installation attempt for the package-only JSON API addon,
and document the exact component matrix used by the shared test environment.

**Tech Stack:** Python 2.7, Plone 5.2.15, `unittest2`,
`plone.app.testing`, `zc.testrunner`, SENAITE 2.x.

## Global Constraints

- Work only in
  `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline`.
- Keep `senaite.core` unmodified.
- Do not include the preserved local `reportview.py` change.
- Do not change workflows, catalogs, contents, permissions, or runtime
  behavior in this phase.
- Use the worktree-specific `/tmp/hoch-lims-worktree-test` runner created
  below as the acceptance command.
- Do not create a GitHub PR in this phase.

---

### Task 0: Create a worktree-specific test runner

**Files:**

- Generate: `/tmp/hoch-lims-worktree-test` (not committed)

**Interfaces:**

- Consumes: `/home/lims/hochlims/bin/test` and its resolved dependency paths
- Produces: the same runner with only the `hoch.lims` import path redirected
  to the isolated worktree

- [ ] **Step 1: Copy the generated runner**

Run:

```bash
cp /home/lims/hochlims/bin/test /tmp/hoch-lims-worktree-test
```

- [ ] **Step 2: Redirect only the addon source path**

Run:

```bash
sed -i 's#/home/lims/hochlims/src/hoch.lims/src#/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline/src#' /tmp/hoch-lims-worktree-test
```

- [ ] **Step 3: Verify runner isolation**

Run:

```bash
rg -n "hoch\\.lims/src|hoch-lims-senaite-baseline/src" /tmp/hoch-lims-worktree-test
```

Expected: one match for
`/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline/src` and no match
for `/home/lims/hochlims/src/hoch.lims/src`.

### Task 1: Make vocabulary tests discoverable

**Files:**

- Modify: `src/hoch/lims/tests/test_vocabulary.py`

**Interfaces:**

- Consumes: `hoch.lims.patches.analysisrequest.getProcessesVocabulary`
- Produces: a `unittest2.TestCase` suite discoverable by `zc.testrunner`

- [ ] **Step 1: Verify the existing discovery failure**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_vocabulary
```

Expected: exit code `1` with
`Module hoch.lims.tests.test_vocabulary does not define any tests`.

- [ ] **Step 2: Convert the five free functions into unittest methods**

Add:

```python
import unittest2 as unittest
```

Wrap the existing five test functions in:

```python
class TestProcessesVocabulary(unittest.TestCase):
```

Rename each function signature from:

```python
def test_name():
```

to:

```python
def test_name(self):
```

Do not change their inputs or assertions.

- [ ] **Step 3: Register an explicit test suite**

Append:

```python
def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestProcessesVocabulary)
```

- [ ] **Step 4: Verify focused discovery and behavior**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_vocabulary
```

Expected: 5 tests run, 0 failures, 0 errors, exit code `0`.

- [ ] **Step 5: Commit the test discovery repair**

```bash
git add src/hoch/lims/tests/test_vocabulary.py
git commit -m "test: repair vocabulary test discovery"
```

### Task 2: Remove the invalid JSON API product installation

**Files:**

- Modify: `src/hoch/lims/tests/base.py`

**Interfaces:**

- Consumes: `senaite.jsonapi` ZCML and its Python package registration
- Produces: a Plone test layer that loads the JSON API without trying to
  install a non-product through `zope.installProduct`

- [ ] **Step 1: Reproduce the layer warning**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_jsonapi_registered
```

Expected: output contains `Could not install product senaite.jsonapi`.

- [ ] **Step 2: Remove only the invalid installation call**

Delete this line from `SimpleTestLayer.setUpZope`:

```python
zope.installProduct(app, "senaite.jsonapi")
```

Keep:

```python
import senaite.jsonapi
self.loadZCML(package=senaite.jsonapi)
```

The package registers routes through ZCML/Python imports and does not expose
a legacy Zope product requiring `zope.installProduct`.

- [ ] **Step 3: Verify the JSON API endpoint**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_jsonapi_registered
```

Expected: test passes with exit code `0` and output does not contain
`Could not install product senaite.jsonapi`.

- [ ] **Step 4: Run the full addon suite**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: 13 tests run, 0 failures, 0 errors, exit code `0`, and no failed
JSON API installation message.

- [ ] **Step 5: Commit the layer repair**

```bash
git add src/hoch/lims/tests/base.py
git commit -m "test: load senaite jsonapi without product install"
```

### Task 3: Document the effective component matrix

**Files:**

- Create: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**

- Consumes: exact Git SHAs and effective runtime versions
- Produces: the reproducible baseline reference for subsequent official-core
  work

- [ ] **Step 1: Create the validation document**

Write:

```markdown
# SENAITE 2.x Validation Matrix

Date: 2026-07-29

## Runtime

- Python: 2.7.18
- Plone: 5.2.15

## Components

| Component | Branch | SHA |
| --- | --- | --- |
| hoch.lims | upgrade/senaite-core-2x-official | 664b2956228ffa94615c99ce0dcea499fdbb2c67 |
| senaite.core | hoch-prod | e98fb15a37fa269994e8fc81e1b60f145ae7681b |
| senaite.lims | 2.x | 0e487baf128dbfd9444048334ffa6f176b0dd8d2 |
| senaite.app.listing | 2.x | 3d0a603e1976a2516988051381b0418da1e2e9ea |
| senaite.app.spotlight | 2.x | 6212658fbafae22d1f74dee5ca1e1745098af0b4 |
| senaite.app.supermodel | 2.x | 03cc81a7d799135d19676129d30a8ca6512777a8 |
| senaite.impress | 2.x | 01d5380aa1e574e27c843536bd04d4df3e2b32d8 |
| senaite.jsonapi | 2.x | 0139af663f23c773dff5e4c4367ac5a47a44c9d8 |

## Interpretation

This matrix records the pre-adaptation characterization environment. The
`senaite.core` entry is intentionally the historical `hoch-prod` fork and is
not the target matrix. The next phase replaces it with a pinned official
`senaite.core/2.x` SHA and records a second matrix.

The core checkout contains eight uncommitted historical customizations. Tests
in this phase characterize the existing behavior; they do not establish
compatibility with a clean official core.
```

- [ ] **Step 2: Verify every recorded SHA**

Run `git rev-parse HEAD` in each component checkout and compare every result
with the table. Any mismatch must be corrected in the document before commit.

- [ ] **Step 3: Check the document for placeholders**

Run:

```bash
rg -n "TBD|TODO|FIXME|XXX" docs/validation/senaite-2x-component-matrix.md
```

Expected: no matches.

- [ ] **Step 4: Commit the matrix**

```bash
git add docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: record senaite test baseline matrix"
```

### Task 4: Verify and hand off the green baseline

**Files:**

- Verify: `src/hoch/lims/tests/test_vocabulary.py`
- Verify: `src/hoch/lims/tests/base.py`
- Verify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**

- Consumes: all Phase 1 changes
- Produces: a reviewed commit series ready to transfer to the shared test base

- [ ] **Step 1: Run the full suite from a clean process**

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: exit code `0`, 13 tests, 0 failures, 0 errors.

- [ ] **Step 2: Verify repository scope**

Run:

```bash
git status --short
git diff origin/2.x...HEAD --stat
git diff origin/2.x...HEAD -- src/hoch/lims
```

Expected:

- clean worktree;
- only the specification, plan, two test-infrastructure files, and validation
  matrix differ from `origin/2.x`;
- no production module changes.

- [ ] **Step 3: Verify the shared core remains untouched**

Run:

```bash
git -C /home/lims/hochlims/src/senaite.core status --short
```

Expected: exactly the eight pre-existing historical modifications and no new
files or changes attributable to this phase.

- [ ] **Step 4: Record handoff**

Report:

- worktree path;
- branch and commit list;
- full test result;
- remaining warnings;
- confirmation that no changes have yet been transferred to the shared test
  base and no PR has been created.
