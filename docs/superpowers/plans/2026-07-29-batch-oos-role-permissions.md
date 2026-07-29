# Batch and OOS Role Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the approved Batch and OOS workflow role matrices while preserving existing permission and business guards.

**Architecture:** Express action-specific authorization with DCWorkflow transition role guards and retain permission guards plus Python business expressions. Update the default profile for new sites and add an idempotent `1001 -> 1002` GenericSetup upgrade for installed sites.

**Tech Stack:** Python 2.7, Plone 5.2, DCWorkflow, GenericSetup, Zope security, `zc.testrunner`, `unittest2`.

## Global Constraints

- `LabManager` must have every Batch and OOS operational permission assigned to `Manager`.
- `LabManager`, `Manager`, and `RegulatoryPharmacist` retain Batch release authority.
- `Analyst` participates only in the OOS laboratory phase.
- Role membership never bypasses Batch or OOS business guards.
- An investigator cannot approve their own OOS investigation.
- No new permission IDs, workflow states, transitions, or content models.
- Official Core remains unchanged.
- Work only in `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline`.
- Follow a witnessed red-green cycle for every production change.
- Do not push, deploy to the shared base, or open a pull request.

---

### Task 1: Characterize and Configure the Installed Role Matrix

**Files:**
- Create: `src/hoch/lims/tests/test_role_permissions.py`
- Modify: `src/hoch/lims/profiles/default/rolemap.xml`
- Modify: `src/hoch/lims/profiles/default/workflows/hoch_batch_workflow/definition.xml`
- Modify: `src/hoch/lims/profiles/default/workflows/oos_investigation_workflow/definition.xml`

**Interfaces:**
- Consumes: installed `hoch_batch_workflow`,
  `oos_investigation_workflow`, and portal permission role maps.
- Produces: explicit transition `guard.roles` tuples and OOS state edit
  permission maps matching the approved matrix.

- [ ] **Step 1: Add installed-profile test helpers**

Create `TestInstalledRolePermissions(SimpleTestCase)` and helpers:

```python
BATCH_ROLES = {
    "close": ("LabManager", "Manager"),
    "release": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reopen": ("LabManager", "Manager"),
}

OOS_ROLES = {
    "start_phase1": ("Analyst", "LabManager", "Manager"),
    "escalate_phase2": ("Analyst", "LabManager", "Manager"),
    "resolve_lab_error": ("Analyst", "LabManager", "Manager"),
    "cancel": ("LabManager", "Manager"),
    "submit_for_review": ("LabManager", "Manager"),
    "approve": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reject_review": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
}


def get_workflow(self, workflow_id):
    return self.portal.portal_workflow.getWorkflowById(workflow_id)
```

Compare sorted role tuples so the test protects membership rather than XML
ordering.

- [ ] **Step 2: Write Batch transition authorization tests**

For every `BATCH_ROLES` entry assert the installed transition's
`guard.roles`. Also protect existing guard layers:

```python
release_guard = workflow.transitions["release"].guard
self.assertEqual(
    ("hoch.lims: Release Batch",),
    release_guard.permissions)
self.assertEqual(
    "python:here.guard_release_batch()",
    release_guard.expr.text)
```

Assert `close` and `reopen` retain `Modify portal content`.

- [ ] **Step 3: Write OOS transition authorization tests**

For every `OOS_ROLES` entry assert exact installed `guard.roles`. Assert all
transitions retain `hoch.lims: Transition OOSInvestigation`. Protect the
existing business expressions:

```python
expected_expressions = {
    "escalate_phase2":
        'python:here.guard_handler("escalate_phase2")',
    "submit_for_review":
        'python:here.guard_handler("submit_for_review")',
    "approve": 'python:here.guard_handler("approve")',
}
```

- [ ] **Step 4: Write OOS edit and root-permission tests**

For both `Modify portal content` and
`hoch.lims: Edit OOSInvestigation`, assert:

```python
expected_edit_roles = {
    "recorded": ("Analyst", "LabManager", "Manager"),
    "phase1": ("Analyst", "LabManager", "Manager"),
    "phase2": ("LabManager", "Manager"),
    "review": ("LabManager", "Manager"),
    "closed": ("LabManager", "Manager"),
    "cancelled": ("LabManager", "Manager"),
}
```

Use `state.getPermissionInfo(permission)` and assert `acquired == 0` plus the
exact roles.

Use `self.portal.rolesOfPermission(permission)` to assert:

- `Release Batch`: `LabManager`, `Manager`, `RegulatoryPharmacist`;
- `Transition OOSInvestigation`: `Analyst`, `LabManager`, `Manager`,
  `RegulatoryPharmacist`.

- [ ] **Step 5: Run focused test and verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_role_permissions
```

Expected failures:

- transition role guards are empty;
- `Analyst` lacks the root OOS transition permission;
- `LabManager` lacks OOS edit access in `review`, `closed`, and `cancelled`.

Existing permission guards and expressions must already pass.

- [ ] **Step 6: Configure Batch transition roles**

Add these `<guard-role>` values without altering existing permissions or
expressions:

```xml
<!-- close/reopen -->
<guard-role>LabManager</guard-role>
<guard-role>Manager</guard-role>

<!-- release -->
<guard-role>LabManager</guard-role>
<guard-role>Manager</guard-role>
<guard-role>RegulatoryPharmacist</guard-role>
```

- [ ] **Step 7: Configure OOS transition roles**

Add exact `<guard-role>` elements from `OOS_ROLES` to each transition.
Preserve all permission guards and the three business expressions.

- [ ] **Step 8: Configure OOS edit and root permission roles**

In OOS states `review`, `closed`, and `cancelled`, add `LabManager` to both
managed edit permission maps. Do not add `RegulatoryPharmacist`.

In `rolemap.xml`, add:

```xml
<role name="Analyst"/>
```

to `hoch.lims: Transition OOSInvestigation`, retaining the three existing
roles.

- [ ] **Step 9: Verify GREEN on both cores**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_role_permissions
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_role_permissions
```

Expected: identical counts, 0 failures, 0 errors.

- [ ] **Step 10: Run existing Batch and OOS behavior tests**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t 'test_(batch_workflow|oos_workflow)'
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t 'test_(batch_workflow|oos_workflow)'
```

Expected: 0 failures and 0 errors. This proves role guards did not replace
business guards or transition event behavior.

- [ ] **Step 11: Commit profile authorization**

```bash
git add src/hoch/lims/profiles/default/rolemap.xml \
  src/hoch/lims/profiles/default/workflows/hoch_batch_workflow/definition.xml \
  src/hoch/lims/profiles/default/workflows/oos_investigation_workflow/definition.xml \
  src/hoch/lims/tests/test_role_permissions.py
git commit -m "fix: enforce Batch and OOS role permissions"
```

---

### Task 2: Prove Role and Business-Guard Composition

**Files:**
- Modify: `src/hoch/lims/tests/test_role_permissions.py`

**Interfaces:**
- Consumes: installed DCWorkflow transitions, real portal security manager,
  Batch release guard, and OOS approval guard.
- Produces: effective authorization evidence for representative positive,
  negative, and self-approval scenarios.

- [ ] **Step 1: Add one-role-at-a-time security helper**

Use `plone.app.testing.setRoles` and `TEST_USER_ID`:

```python
def set_test_roles(self, roles):
    setRoles(self.portal, TEST_USER_ID, list(roles))

def transition_ids(self, obj):
    return set(
        transition["id"]
        for transition in api.get_transitions_for(obj))
```

Create real `OOSInvestigation` objects under
`self.portal.OOSInvestigations` with `api.create`. Populate Phase I summary,
conclusion, disposition, and category before testing guarded later stages.

- [ ] **Step 2: Write effective initial OOS authorization test**

For a fresh `recorded` investigation, set each role independently and assert:

| Role | `start_phase1` visible |
| --- | --- |
| Analyst | Yes |
| LabManager | Yes |
| Manager | Yes |
| RegulatoryPharmacist | No |

The test must call `api.get_transitions_for` rather than inspect guard roles.

- [ ] **Step 3: Write effective review authorization test**

Move a populated investigation to `review` as `LabManager`. Then test each
reviewer role independently:

| Role | `approve` | `reject_review` |
| --- | --- | --- |
| Analyst | No | No |
| LabManager | Yes | Yes |
| Manager | Yes | Yes |
| RegulatoryPharmacist | Yes | Yes |

Set the investigator to a different user for the positive cases.

- [ ] **Step 4: Write self-approval composition test**

For each of `LabManager`, `Manager`, and `RegulatoryPharmacist`, make the
current test user the recorded investigator and assert `approve` is absent
while `reject_review` remains available. Then set a different investigator
and assert `approve` becomes available.

- [ ] **Step 5: Protect Batch business-guard composition**

Use a real installed Batch transition object and the existing in-memory valid
Batch collaborators from `test_batch_workflow` only if they can be adapted
without copying production logic. Otherwise test the real guard handler
directly:

```python
self.assertFalse(
    guards.guard_release(batch_with_open_oos))
self.assertTrue(
    guards.guard_release(valid_batch))
```

Combine this with the installed release transition assertions from Task 1:
an allowed role and a valid business guard are both necessary.

- [ ] **Step 6: Run focused tests**

Run both matrices:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_role_permissions
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_role_permissions
```

If real transition setup exposes a product defect, apply
`superpowers:systematic-debugging`, identify the root cause, and add the
smallest production correction under a new red-green cycle.

- [ ] **Step 7: Commit effective authorization tests**

```bash
git add src/hoch/lims/tests/test_role_permissions.py
git commit -m "test: verify effective workflow authorization"
```

---

### Task 3: Add the Idempotent `1001 -> 1002` Upgrade

**Files:**
- Create: `src/hoch/lims/upgrades/v1002.py`
- Modify: `src/hoch/lims/upgrades/configure.zcml`
- Modify: `src/hoch/lims/profiles/default/metadata.xml`
- Modify: `src/hoch/lims/tests/test_upgrades.py`

**Interfaces:**
- Consumes: installed Batch/OOS workflows and portal permission mappings.
- Produces: `v1002.upgrade(portal_setup) -> None`, applying transition roles
  and OOS edit maps while preserving permission and expression guards.

- [ ] **Step 1: Extend upgrade test fixtures**

Generalize `DummyPortal`, `DummyWorkflowTool`, `DummyWorkflow`,
`DummyTransition`, and add `DummyState`.

Each transition uses the real `Guard` initialized with a permission and,
where applicable, an expression. Each state records calls to:

```python
state.setPermission(permission, acquired, roles)
state.getPermissionInfo(permission)
```

The portal records `manage_permission(permission, roles, acquire)` calls and
returns configured mappings through `rolesOfPermission`.

- [ ] **Step 2: Write exact upgrade tests**

Add tests proving:

- every Batch transition receives `BATCH_ROLES`;
- every OOS transition receives `OOS_ROLES`;
- existing `guard.permissions`, `guard.expr.text`, and `guard.groups` remain
  unchanged;
- `review`, `closed`, and `cancelled` edit permissions become
  `("LabManager", "Manager")`, acquired false;
- the root OOS transition permission becomes
  `("Analyst", "LabManager", "Manager", "RegulatoryPharmacist")`;
- Batch release permission is not modified;
- a second execution has an identical snapshot.

Add separate useful-error tests for a missing:

- Batch workflow;
- OOS workflow;
- transition;
- state;
- required managed permission.

- [ ] **Step 3: Run upgrade test and verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_upgrades
```

Expected: import failure for absent `hoch.lims.upgrades.v1002`.

- [ ] **Step 4: Implement role constants and transition updates**

Create `v1002.py` with literal matrices matching the specification:

```python
BATCH_TRANSITION_ROLES = {
    "close": ("LabManager", "Manager"),
    "release": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reopen": ("LabManager", "Manager"),
}
OOS_TRANSITION_ROLES = {
    "start_phase1": ("Analyst", "LabManager", "Manager"),
    "escalate_phase2": ("Analyst", "LabManager", "Manager"),
    "resolve_lab_error": ("Analyst", "LabManager", "Manager"),
    "cancel": ("LabManager", "Manager"),
    "submit_for_review": ("LabManager", "Manager"),
    "approve": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
    "reject_review": (
        "LabManager", "Manager", "RegulatoryPharmacist"),
}
OOS_EDIT_STATES = ("review", "closed", "cancelled")
OOS_EDIT_PERMISSIONS = (
    "Modify portal content",
    "hoch.lims: Edit OOSInvestigation",
)
OOS_TRANSITION_PERMISSION = (
    "hoch.lims: Transition OOSInvestigation")
```

For each transition, verify existence and call:

```python
transition.guard.changeFromProperties({
    "guard_roles": ";".join(roles),
})
```

Only `guard_roles` is supplied, preserving permissions, expressions, and
groups.

- [ ] **Step 5: Implement state and root-permission updates**

For each required OOS state and edit permission:

```python
if permission not in workflow.permissions:
    raise ValueError(
        "Missing managed permission {} in {}".format(
            permission, workflow_id))
state.setPermission(
    permission, 0, ("LabManager", "Manager"))
```

Set the portal permission explicitly:

```python
portal.manage_permission(
    OOS_TRANSITION_PERMISSION,
    roles=(
        "Analyst",
        "LabManager",
        "Manager",
        "RegulatoryPharmacist",
    ),
    acquire=0)
```

- [ ] **Step 6: Register version `1002`**

Add to `upgrades/configure.zcml`:

```xml
<genericsetup:upgradeStep
    title="Enforce Batch and OOS role permissions"
    description="Apply the HOCH workflow authorization matrix"
    source="1001"
    destination="1002"
    handler="hoch.lims.upgrades.v1002.upgrade"
    profile="hoch.lims:default"
    />
```

Change default profile metadata to `<version>1002</version>`.

- [ ] **Step 7: Verify GREEN on both cores**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_upgrades
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_upgrades
```

Expected: identical counts, 0 failures, 0 errors.

- [ ] **Step 8: Commit the upgrade**

```bash
git add src/hoch/lims/profiles/default/metadata.xml \
  src/hoch/lims/tests/test_upgrades.py \
  src/hoch/lims/upgrades/configure.zcml \
  src/hoch/lims/upgrades/v1002.py
git commit -m "feat: upgrade workflow role permissions"
```

---

### Task 4: Validate and Record Permission Compatibility

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Consumes: focused authorization/upgrade tests and complete addon suites.
- Produces: reproducible evidence for both Core matrices.

- [ ] **Step 1: Run focused permission block on both cores**

Run:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t 'test_(role_permissions|upgrades)'
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t 'test_(role_permissions|upgrades)'
```

Record exact counts, failures, errors, and skips.

- [ ] **Step 2: Run complete suites**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Record exact counts for both matrices.

- [ ] **Step 3: Update the validation matrix**

Add a `Batch and OOS role permissions` section documenting:

- the approved role matrices;
- `LabManager` parity with `Manager`;
- retained Batch release authority;
- role and business-guard composition;
- profile version `1002`;
- `1001 -> 1002` idempotency and preserved guards;
- exact focused and complete test counts.

- [ ] **Step 4: Commit validation evidence**

```bash
git add docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: record workflow permission compatibility"
```

- [ ] **Step 5: Apply verification-before-completion**

Freshly run both complete suites, `git diff --check origin/2.x...HEAD`, and
status checks for:

- feature worktree;
- clean official Core checkout;
- shared addon with only its pre-existing staged report change;
- historical Core with only its eight pre-existing local changes.
