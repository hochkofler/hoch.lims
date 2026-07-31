# LabClerk Global Worksheet Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Samples view “Create Worksheet” action available to eligible LabClerks by granting worksheet permissions on both the portal root and the worksheets folder.

**Architecture:** Expand the existing idempotent synchronizer to augment both permission contexts while preserving Core-selected roles. Add a new GenericSetup `1003 -> 1004` upgrade for already-deployed sites and verify the exact portal-root authorization used by `SamplesView.can_create_worksheet()`.

**Tech Stack:** Python 2-compatible code, Zope/Plone permissions, SENAITE Core, GenericSetup, `unittest2`, and `zope.testrunner` through `bin/test`.

## Global Constraints

- Add only `LabClerk`; preserve every existing selected role.
- Synchronize `AddWorksheet`, `EditWorksheet`, and `ManageWorksheets` on both portal root and `portal.worksheets`.
- Keep synchronization and upgrade execution idempotent.
- Do not modify the already-deployed `v1003` upgrade.
- Register a new profile upgrade from `1003` to `1004`.

---

### Task 1: Synchronize portal-root worksheet permissions

**Files:**
- Modify: `src/hoch/lims/patches/worksheet_permissions.py`
- Modify: `src/hoch/lims/tests/test_worksheet_permissions.py`
- Modify: `src/hoch/lims/tests/test_role_permissions.py`

**Interfaces:**
- Consumes: `synchronize_worksheet_permissions(portal=None)`, portal root, and `portal.worksheets`.
- Produces: both contexts selecting `LabClerk` for every item in `WORKSHEET_PERMISSIONS`.

- [ ] **Step 1: Extend the dummy portal and write failing root-context tests**

Give `DummyPortal` the same `rolesOfPermission` and `manage_permission` behavior as `DummyWorksheetFolder`. Assert both contexts:

```python
def test_adds_labclerk_to_portal_and_worksheet_permissions(self):
    worksheet_permissions.synchronize_worksheet_permissions(self.portal)
    for context in (self.portal, self.folder):
        for permission in worksheet_permissions.WORKSHEET_PERMISSIONS:
            self.assertEqual(
                (("LabClerk", "LabManager", "Manager"), 1),
                context.managed_permissions[permission])

def test_preserves_core_roles_in_both_permission_contexts(self):
    self.portal.set_roles(("LabManager", "Manager", "Owner"))
    self.folder.set_roles(("Analyst", "LabManager", "Manager"))
    worksheet_permissions.synchronize_worksheet_permissions(self.portal)
    self.assert_portal_roles_include_owner_and_labclerk()
    self.assert_folder_roles_include_analyst_and_labclerk()
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t test_worksheet_permissions`

Expected: FAIL because the portal root receives no `manage_permission` calls.

- [ ] **Step 3: Implement the minimal two-context synchronizer**

Extract a private helper and invoke it for the portal and folder:

```python
def _add_labclerk_permissions(context):
    for permission in WORKSHEET_PERMISSIONS:
        roles = set(
            info["name"]
            for info in context.rolesOfPermission(permission)
            if info["selected"])
        roles.add("LabClerk")
        context.manage_permission(
            permission, roles=tuple(sorted(roles)), acquire=1)

def synchronize_worksheet_permissions(portal=None):
    portal = portal or api.get_portal()
    _add_labclerk_permissions(portal)
    _add_labclerk_permissions(portal.worksheets)
    portal.worksheets.reindexObject()
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t test_worksheet_permissions`

Expected: all synchronization and decorator tests PASS.

- [ ] **Step 5: Add installed-site regression for the Samples authorization context**

In `test_role_permissions.py`, authenticate the test user as `LabClerk` and assert:

```python
from senaite.core.permissions.worksheet import can_add_worksheet

def test_labclerk_can_create_worksheet_from_samples_context(self):
    self.set_test_role("LabClerk")
    self.assertTrue(can_add_worksheet(self.portal))
```

Extend the existing local-permission test to assert `LabClerk` is selected on both `self.portal` and `self.portal.worksheets` for all three permissions.

- [ ] **Step 6: Run unit and integration tests**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t 'test_worksheet_permissions|test_role_permissions'`

Expected: PASS with zero failures and zero errors.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/hoch/lims/patches/worksheet_permissions.py src/hoch/lims/tests/test_worksheet_permissions.py src/hoch/lims/tests/test_role_permissions.py
git commit -m "fix: grant LabClerk global worksheet permissions"
```

---

### Task 2: Upgrade deployed sites to profile version 1004

**Files:**
- Create: `src/hoch/lims/upgrades/v1004.py`
- Modify: `src/hoch/lims/upgrades/configure.zcml`
- Modify: `src/hoch/lims/profiles/default/metadata.xml`
- Modify: `src/hoch/lims/tests/test_upgrades.py`

**Interfaces:**
- Consumes: expanded `synchronize_worksheet_permissions(portal)` from Task 1.
- Produces: `hoch.lims.upgrades.v1004.upgrade(portal_setup) -> None`; registered `1003 -> 1004` path.

- [ ] **Step 1: Write failing upgrade-1004 tests**

Import `v1004`; ensure the dummy portal records root and folder permission changes; add the case to `test_suite()`:

```python
def test_v1004_restores_global_and_local_permissions(self):
    v1004.upgrade(self.portal_setup)
    self.assertEqual([v1004.PROFILE_ID], self.portal_setup.profile_ids)
    for context in (self.portal, self.portal.worksheets):
        for permission in v1004.WORKSHEET_PERMISSIONS:
            self.assertIn(
                "LabClerk",
                context.managed_permissions[permission][0])

def test_v1004_is_idempotent(self):
    v1004.upgrade(self.portal_setup)
    first = self.snapshot()
    v1004.upgrade(self.portal_setup)
    self.assertEqual(first, self.snapshot())
```

- [ ] **Step 2: Run upgrade tests and verify RED**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t test_upgrades`

Expected: ERROR because `hoch.lims.upgrades.v1004` does not exist.

- [ ] **Step 3: Implement and register upgrade 1004**

Create `v1004.py` with the same focused upgrade entrypoint as `v1003`:

```python
from hoch.lims.patches.worksheet_permissions import WORKSHEET_PERMISSIONS
from hoch.lims.patches.worksheet_permissions import synchronize_worksheet_permissions

PROFILE_ID = "profile-hoch.lims:default"

def upgrade(portal_setup):
    context = portal_setup._getImportContext(PROFILE_ID)
    synchronize_worksheet_permissions(context.getSite())
```

Register `source="1003"`, `destination="1004"`, handler `hoch.lims.upgrades.v1004.upgrade`, and change default profile metadata from `1003` to `1004`.

- [ ] **Step 4: Run upgrade tests and verify GREEN**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t 'test_upgrades|test_worksheet_permissions|test_role_permissions'`

Expected: PASS with zero failures and zero errors.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/hoch/lims/upgrades/v1004.py src/hoch/lims/upgrades/configure.zcml src/hoch/lims/profiles/default/metadata.xml src/hoch/lims/tests/test_upgrades.py
git commit -m "fix: upgrade global worksheet permissions"
```

---

### Task 3: Final regression verification

**Files:**
- Verify only.

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: evidence for focused authorization and complete package compatibility.

- [ ] **Step 1: Run the focused regression suite**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims -t 'test_worksheet_permissions|test_upgrades|test_role_permissions'`

Expected: zero failures and zero errors.

- [ ] **Step 2: Run the complete package suite**

Run: `/home/lims/hochlims/bin/test --path=/tmp/hochlims-labclerk-global/src -s hoch.lims`

Expected: zero failures and zero errors.

- [ ] **Step 3: Validate the branch diff**

Run: `git diff --check origin/2.x...HEAD`

Expected: no output.

Run: `git status --short`

Expected: no output.
