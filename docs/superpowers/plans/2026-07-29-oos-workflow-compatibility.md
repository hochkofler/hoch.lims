# OOS Workflow Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make automatic OOS detection and the OOS investigation workflow operate end to end on official `senaite.core/2.x`, including an idempotent upgrade for existing sites.

**Architecture:** Keep detection and business rules in `hoch.lims`, using the existing analysis transition subscriber and guard adapter. Connect transition effects through a dedicated OOS subscriber, configure workflow expressions through GenericSetup, and apply the same expressions to installed sites through profile upgrade `1000 -> 1001`.

**Tech Stack:** Python 2.7, Plone 5.2, Dexterity, DCWorkflow, GenericSetup, Zope Component Architecture, `zc.testrunner`, `unittest2`.

## Global Constraints

- Do not modify `senaite.core`.
- Preserve the existing `OOSInvestigation` model, workflow states, permissions, histories, identifiers, and content.
- Support both official Core `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5` and historical Core `e98fb15a37fa269994e8fc81e1b60f145ae7681b`.
- Keep all implementation in `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline`.
- Every production change must follow a witnessed red-green cycle.
- Do not push, deploy to the shared base, or open a pull request.

---

### Task 1: Characterize OOS Detection

**Files:**
- Create: `src/hoch/lims/tests/test_oos_detection.py`
- Modify: `src/hoch/lims/adapters/oos_detection.py`

**Interfaces:**
- Consumes: `on_analysis_transition(analysis, event)` and SENAITE's `is_out_of_range(analysis)`.
- Produces: `_check_and_create_oos(analysis) -> OOSInvestigation or None`; creation failures propagate after logging.

- [ ] **Step 1: Add in-memory OOS detection collaborators**

Create minimal `DummyTransition`, `DummyEvent`, `DummyAnalysis`,
`DummyOOSFolder`, `DummyOOS`, `DummyPortal`, and `DummyUser` classes in
`test_oos_detection.py`. Patch and restore these module dependencies in
`setUp`/`tearDown`:

```python
self.original_is_out_of_range = detection.is_out_of_range
self.original_get_portal = detection.api.get_portal
self.original_get_uid = detection.api.get_uid
self.original_get_tool = detection.api.get_tool
self.original_get_current_user = detection.api.get_current_user
self.original_create = detection.api.create
self.original_get_id = detection.api.get_id
```

The valid fixture must expose result `"12.5"`, range
`{"min": "10", "max": "11"}`, title `"Assay"`, UID `"analysis-1"`, current
user `"analyst-1"`, an empty catalog result, and one OOS folder.

- [ ] **Step 2: Write transition-filtering and in-spec tests**

Add tests proving:

```python
def test_ignores_event_without_transition(self):
    detection.on_analysis_transition(self.analysis, DummyEvent(None))
    self.assertEqual([], self.created)

def test_ignores_unrelated_transition(self):
    detection.on_analysis_transition(
        self.analysis, DummyEvent(DummyTransition("retract")))
    self.assertEqual([], self.created)

def test_does_not_create_oos_for_in_spec_result(self):
    detection.is_out_of_range = lambda analysis: (False, False)
    detection.on_analysis_transition(
        self.analysis, DummyEvent(DummyTransition("submit")))
    self.assertEqual([], self.created)
```

- [ ] **Step 3: Write successful detection and duplicate tests**

Assert that both supported transition IDs dispatch detection, and use one
snapshot test for `submit`:

```python
oos = detection._check_and_create_oos(self.analysis)
self.assertEqual("analysis-1", oos.analysis_uid)
self.assertEqual("12.5", oos.result_value)
self.assertEqual(u"min=10, max=11", oos.specification_range)
self.assertEqual("Assay", oos.analysis_service_title)
self.assertEqual("analyst-1", oos.responsible_analyst)
self.assertEqual(30, int(oos.due_date - oos.detection_date))
self.assertEqual(1, oos.reindex_calls)
```

Set the catalog result to a brain in a separate test, call detection for a
verified analysis, and assert no object is created regardless of the existing
investigation's workflow state.

- [ ] **Step 4: Write failure-policy tests**

Add tests proving:

```python
def test_missing_oos_folder_does_not_create_partial_record(self):
    self.portal.pop("OOSInvestigations")
    self.assertIsNone(detection._check_and_create_oos(self.analysis))
    self.assertEqual([], self.created)

def test_creation_failure_is_propagated(self):
    def fail_create(container, portal_type):
        raise RuntimeError("cannot persist OOS")
    detection.api.create = fail_create
    with self.assertRaises(RuntimeError):
        detection._check_and_create_oos(self.analysis)
```

- [ ] **Step 5: Run focused tests and verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_oos_detection
```

Expected: the snapshot test fails because `_check_and_create_oos` returns
`None`; the creation failure test fails because the exception is swallowed.
Filtering and duplicate characterization may already pass.

- [ ] **Step 6: Implement the minimal detection contract**

Change `_check_and_create_oos` to return the created object:

```python
oos.reindexObject()
logger.info(...)
return oos
```

Limit the `try` block to creation and snapshot persistence, retain contextual
logging, and re-raise:

```python
except Exception as error:
    logger.error(
        "Failed to create OOS Investigation for analysis %s: %s",
        analysis_uid, str(error))
    raise
```

Do not change the range API, duplicate query, due-date rule, or snapshot
fields.

- [ ] **Step 7: Run focused tests and verify GREEN on both cores**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_oos_detection
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_oos_detection
```

Expected: identical test counts, 0 failures, 0 errors.

- [ ] **Step 8: Commit detection**

```bash
git add src/hoch/lims/adapters/oos_detection.py \
  src/hoch/lims/tests/test_oos_detection.py
git commit -m "fix: make OOS detection observable"
```

---

### Task 2: Connect OOS Guards and Transition Events

**Files:**
- Create: `src/hoch/lims/tests/test_oos_workflow.py`
- Modify: `src/hoch/lims/adapters/oos_detection.py`
- Modify: `src/hoch/lims/adapters/configure.zcml`
- Modify: `src/hoch/lims/profiles/default/workflows/oos_investigation_workflow/definition.xml`

**Interfaces:**
- Consumes: `OOSInvestigationGuardAdapter.guard(transition)`, functions in `hoch.lims.workflow.oos.guards`, and functions in `hoch.lims.workflow.oos.events`.
- Produces: `on_oos_transition(investigation, event) -> None`, dispatching supported after-transition effects.

- [ ] **Step 1: Add guard and event collaborators**

In `test_oos_workflow.py`, define `DummyInvestigation`, `DummyUser`,
`DummyTransition`, and `DummyEvent`. The investigation exposes the existing
guard accessors, mutable audit attributes, and `reindexObject`.

Patch `guards.api.get_current_user`, `guards.api.get_id`,
`events.api.get_current_user`, and `events.api.get_id`, restoring them with
`addCleanup`.

- [ ] **Step 2: Characterize every guard**

Add independent tests proving:

- escalation rejects an empty Phase I summary and accepts a populated one;
- review rejects each missing value independently: conclusion, disposition,
  and OOS category;
- review accepts when all three are populated;
- approval rejects the investigator as current user;
- approval accepts a different reviewer;
- approval accepts when the investigator is empty;
- the adapter delegates known transition IDs and permits unknown ones.

- [ ] **Step 3: Characterize event effects and dispatch filtering**

Test each existing event function for its timestamp, phase/reviewer value, and
one reindex call. Then specify the dispatcher:

```python
def test_oos_dispatcher_ignores_missing_and_unrelated_transitions(self):
    detection.on_oos_transition(self.investigation, DummyEvent(None))
    detection.on_oos_transition(
        self.investigation, DummyEvent(DummyTransition("cancel")))
    self.assertEqual(0, self.investigation.reindex_calls)

def test_oos_dispatcher_routes_supported_transitions(self):
    for transition_id in ("start_phase1", "escalate_phase2", "approve"):
        investigation = DummyInvestigation()
        detection.on_oos_transition(
            investigation, DummyEvent(DummyTransition(transition_id)))
        self.assertEqual(1, investigation.reindex_calls)
```

- [ ] **Step 4: Add installed-workflow guard-expression test**

Using `SimpleTestCase`, obtain:

```python
workflow = self.portal.portal_workflow.getWorkflowById(
    "oos_investigation_workflow")
```

For `escalate_phase2`, `submit_for_review`, and `approve`, assert:

```python
self.assertEqual(
    'python:here.guard_handler("{}")'.format(transition_id),
    workflow.transitions[transition_id].guard.expr.text)
self.assertIn(
    "hoch.lims: Transition OOSInvestigation",
    workflow.transitions[transition_id].guard.permissions)
```

- [ ] **Step 5: Run focused tests and verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_oos_workflow
```

Expected: dispatcher tests fail because `on_oos_transition` is absent, and
the installed-workflow tests fail because the guard expressions are absent.
Existing direct guard/event characterization must pass.

- [ ] **Step 6: Add the OOS event dispatcher**

In `oos_detection.py`, import the local event module and implement:

```python
OOS_EVENT_HANDLERS = {
    "start_phase1": oos_events.after_start_phase1,
    "escalate_phase2": oos_events.after_escalate_phase2,
    "approve": oos_events.after_approve,
}


def on_oos_transition(investigation, event):
    transition = event.transition
    if not transition:
        return
    handler = OOS_EVENT_HANDLERS.get(transition.getId())
    if handler:
        handler(investigation)
```

Register it in `adapters/configure.zcml`:

```xml
<subscriber
    for="hoch.lims.interfaces.IOOSInvestigation
         Products.DCWorkflow.interfaces.IAfterTransitionEvent"
    handler=".oos_detection.on_oos_transition"
    />
```

- [ ] **Step 7: Add workflow guard expressions for new installations**

Under the permission guard of each required transition add:

```xml
<guard-expression>
  python:here.guard_handler("TRANSITION_ID")
</guard-expression>
```

Use exactly `escalate_phase2`, `submit_for_review`, and `approve`. Preserve the
existing permission guard and every state/transition property.

- [ ] **Step 8: Run focused tests and verify GREEN on both cores**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_oos_workflow
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_oos_workflow
```

Expected: identical counts, 0 failures, 0 errors.

- [ ] **Step 9: Commit workflow wiring**

```bash
git add src/hoch/lims/adapters/configure.zcml \
  src/hoch/lims/adapters/oos_detection.py \
  src/hoch/lims/profiles/default/workflows/oos_investigation_workflow/definition.xml \
  src/hoch/lims/tests/test_oos_workflow.py
git commit -m "fix: connect OOS workflow guards and events"
```

---

### Task 3: Add the Idempotent `1000 -> 1001` Upgrade

**Files:**
- Create: `src/hoch/lims/upgrades/configure.zcml`
- Create: `src/hoch/lims/upgrades/v1001.py`
- Create: `src/hoch/lims/tests/test_upgrades.py`
- Modify: `src/hoch/lims/configure.zcml`
- Modify: `src/hoch/lims/profiles/default/metadata.xml`

**Interfaces:**
- Consumes: a GenericSetup `portal_setup` tool and installed
  `oos_investigation_workflow`.
- Produces: `upgrade(portal_setup) -> None`, setting three guard expressions
  without replacing existing permission or role guards.

- [ ] **Step 1: Write upgrade unit fixtures**

In `test_upgrades.py`, define `DummyPortalSetup`, `DummyContext`,
`DummyWorkflowTool`, `DummyWorkflow`, and `DummyTransition`. Use the real
`Products.DCWorkflow.Guard.Guard` for each transition and initialize its
permission guard:

```python
guard = Guard()
guard.changeFromProperties({
    "guard_permissions":
        "hoch.lims: Transition OOSInvestigation",
})
```

`DummyPortalSetup._getImportContext(PROFILE_ID).getSite()` returns a portal
whose `portal_workflow` provides `getWorkflowById`.

- [ ] **Step 2: Write upgrade behavior tests**

Add tests proving:

```python
def test_upgrade_adds_guard_expressions_and_preserves_permissions(self):
    v1001.upgrade(self.portal_setup)
    for transition_id in v1001.GUARDED_TRANSITIONS:
        guard = self.workflow.transitions[transition_id].guard
        self.assertEqual(
            'python:here.guard_handler("{}")'.format(transition_id),
            guard.expr.text)
        self.assertEqual(
            ("hoch.lims: Transition OOSInvestigation",),
            guard.permissions)

def test_upgrade_is_idempotent(self):
    v1001.upgrade(self.portal_setup)
    first = self.snapshot()
    v1001.upgrade(self.portal_setup)
    self.assertEqual(first, self.snapshot())
```

Also assert `ValueError` containing `oos_investigation_workflow` when the
workflow is absent and `ValueError` containing the transition ID when one
required transition is absent.

- [ ] **Step 3: Run upgrade tests and verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_upgrades
```

Expected: import error because `hoch.lims.upgrades.v1001` does not exist.

- [ ] **Step 4: Implement the upgrade handler**

Create `v1001.py`:

```python
from hoch.lims import logger

PROFILE_ID = "profile-hoch.lims:default"
WORKFLOW_ID = "oos_investigation_workflow"
GUARDED_TRANSITIONS = (
    "escalate_phase2",
    "submit_for_review",
    "approve",
)


def upgrade(portal_setup):
    context = portal_setup._getImportContext(PROFILE_ID)
    portal = context.getSite()
    workflow = portal.portal_workflow.getWorkflowById(WORKFLOW_ID)
    if workflow is None:
        raise ValueError("Missing workflow: {}".format(WORKFLOW_ID))
    for transition_id in GUARDED_TRANSITIONS:
        transition = workflow.transitions.get(transition_id)
        if transition is None:
            raise ValueError(
                "Missing transition {} in {}".format(
                    transition_id, WORKFLOW_ID))
        expression = 'python:here.guard_handler("{}")'.format(
            transition_id)
        transition.guard.changeFromProperties({
            "guard_expr": expression,
        })
    logger.info("Installed OOS workflow guard expressions")
```

Directly changing only `guard_expr` preserves the existing permissions, roles,
and groups because `Guard.changeFromProperties` ignores unspecified keys.

- [ ] **Step 5: Register and include the upgrade**

Create `upgrades/configure.zcml`:

```xml
<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:genericsetup="http://namespaces.zope.org/genericsetup"
    i18n_domain="hoch.lims">
  <genericsetup:upgradeStep
      title="Enable the HOCH OOS workflow"
      description="Connect OOS workflow guards for SENAITE 2.x"
      source="1000"
      destination="1001"
      handler="hoch.lims.upgrades.v1001.upgrade"
      profile="hoch.lims:default"
      />
</configure>
```

Add `<include package=".upgrades" />` to the package includes in
`hoch/lims/configure.zcml`, and change the default profile metadata version to
`1001`.

- [ ] **Step 6: Verify upgrade registration and behavior GREEN**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_upgrades
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_upgrades
```

Expected: identical counts, 0 failures, 0 errors. ZCML setup of the test layer
also proves the upgrade directive is valid.

- [ ] **Step 7: Commit the upgrade**

```bash
git add src/hoch/lims/configure.zcml \
  src/hoch/lims/profiles/default/metadata.xml \
  src/hoch/lims/tests/test_upgrades.py \
  src/hoch/lims/upgrades/configure.zcml \
  src/hoch/lims/upgrades/v1001.py
git commit -m "feat: add OOS workflow upgrade step"
```

---

### Task 4: Validate and Record the OOS Block

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Consumes: all OOS focused tests and the complete `hoch.lims` suite.
- Produces: reproducible compatibility evidence for both Core matrices.

- [ ] **Step 1: Run the complete official-Core suite**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
```

Expected: all tests pass with 0 failures and 0 errors. Record exact test and
skip counts.

- [ ] **Step 2: Run the complete historical-Core suite**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: the same test count, 0 failures, and 0 errors. Record exact counts.

- [ ] **Step 3: Update the validation matrix**

Add an `OOS detection and workflow` section documenting:

- the disconnected guard and event root cause;
- the public subscriber/guard-handler architecture;
- focused counts for detection, workflow, and upgrades on both cores;
- full-suite counts on both cores;
- profile version `1001` and upgrade idempotency;
- the explicit creation-failure policy;
- confirmation that official Core remains unchanged.

- [ ] **Step 4: Commit validation evidence**

```bash
git add docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: record OOS compatibility results"
```

- [ ] **Step 5: Apply verification-before-completion**

Freshly run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
git diff --check origin/2.x...HEAD
git status --short --branch
git -C /home/lims/hochlims/worktrees/senaite-core-official-2x \
  status --short --branch
git -C /home/lims/hochlims/src/hoch.lims status --short --branch
git -C /home/lims/hochlims/src/senaite.core status --short --branch
```

Expected:

- both suites have 0 failures and 0 errors;
- the feature worktree is clean;
- official Core is clean at `ba57f85e8`;
- the shared addon still has only its pre-existing staged
  `src/hoch/lims/impress/reportview.py` change;
- historical Core still has only its eight pre-existing local changes.
