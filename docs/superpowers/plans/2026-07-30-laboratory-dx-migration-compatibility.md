# Laboratory Dexterity Migration Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the official SENAITE Core `2730 -> 2731` upgrade to migrate Laboratory to Dexterity when the publication-email body has no stored value.

**Architecture:** `hoch.lims` replaces the default factory attached to Core's `ISetupSchema.email_body_sample_publication` field during add-on initialization. The replacement renders an add-on-owned copy of the publication template without Core's invalid, unused `context.laboratory` expression; Core code and stored Setup values remain unchanged.

**Tech Stack:** Python 2.7, Plone 5.2, Dexterity, zope.schema, Chameleon page templates, `plone.app.testing`, Zope testrunner.

## Global Constraints

- Keep `senaite.core` unchanged at official commit `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.
- Modify only `hoch.lims` application code, tests, templates, and documentation.
- Preserve the publication email markup, translation domain, and reserved variables.
- Execute only Core upgrade `2730 -> 2731` during application verification.
- Do not run `2731 -> 2732` until the Laboratory migration is independently verified.
- Preserve the unrelated staged change in the shared checkout at `src/hoch/lims/impress/reportview.py`.

---

### Task 1: Publication Email Default Compatibility

**Files:**
- Create: `src/hoch/lims/patches/senaitesetup.py`
- Create: `src/hoch/lims/patches/templates/email_body_sample_publication.pt`
- Modify: `src/hoch/lims/patches/__init__.py`
- Modify: `src/hoch/lims/tests/test_setup.py`

**Interfaces:**
- Consumes: `senaite.core.content.senaitesetup.ISetupSchema` and `bika.lims.api.get_view`.
- Produces: `default_email_body_sample_publication(context) -> unicode` and `apply_publication_email_default_patch() -> None`.

- [ ] **Step 1: Write the failing regression test**

Add these imports to `src/hoch/lims/tests/test_setup.py`:

```python
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import queryUtility
```

Add this test to `TestSetup`:

```python
def test_publication_email_default_renders_for_setup(self):
    setup = self.portal.restrictedTraverse("setup")
    delattr(setup, "email_body_sample_publication")
    fti = queryUtility(IDexterityFTI, name="Setup")
    field = fti.lookupSchema()["email_body_sample_publication"]

    value = field.bind(setup).default

    self.assertIn("Thank you for your analysis request", value)
    self.assertIn("$client_name", value)
    self.assertIn("$recipients", value)
    self.assertIn("$lab_name", value)
```

Use a guarded deletion if the fixture does not persist the field:

```python
if hasattr(setup, "email_body_sample_publication"):
    delattr(setup, "email_body_sample_publication")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" \
  /home/lims/hochlims/bin/test -s hoch.lims \
  -t test_publication_email_default_renders_for_setup
```

Expected: one error containing `RequestContainer` and either
`email_body_sample_publication` or `laboratory`. The failure must originate
from Core's current default factory, not test setup.

- [ ] **Step 3: Add the compatible template**

Create `src/hoch/lims/patches/templates/email_body_sample_publication.pt`:

```xml
<tal:template i18n:domain="senaite.core">
  <p i18n:translate="">
    Thank you for your analysis request.
  </p>

  <p i18n:translate="">
    Please find attached the analysis result(s) for
    <tal:client i18n:name="client_name"
      tal:content="options/client_name|default">$client_name</tal:client>
  </p>

  <p i18n:translate="">
    This report was sent to the following contacts:
  </p>

  <p>$recipients</p>

  <p i18n:translate="">
    With best regards
  </p>

  <p>$lab_name</p>

  <p i18n:translate="">
    *** This is an automatically generated email, please do not reply to this message. ***
  </p>
</tal:template>
```

- [ ] **Step 4: Implement and install the schema-field patch**

Create `src/hoch/lims/patches/senaitesetup.py`:

```python
# -*- coding: utf-8 -*-
"""Compatibility for SENAITE Setup publication-email defaults."""

from bika.lims import api
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.content.senaitesetup import ISetupSchema
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


PUBLICATION_TEMPLATE = ViewPageTemplateFile(
    "templates/email_body_sample_publication.pt")


@provider(IContextAwareDefaultFactory)
def default_email_body_sample_publication(context):
    """Render the publication body without resolving context.laboratory."""
    view = api.get_view("senaite_view", context=api.get_senaite_setup())
    if view is None:
        return u""
    return PUBLICATION_TEMPLATE(view)


def apply_publication_email_default_patch():
    """Attach the compatible factory to Core's existing schema field."""
    field = ISetupSchema["email_body_sample_publication"]
    field.defaultFactory = default_email_body_sample_publication


apply_publication_email_default_patch()
```

Add this import to `src/hoch/lims/patches/__init__.py`:

```python
import hoch.lims.patches.senaitesetup  # noqa
```

- [ ] **Step 5: Run the focused test and verify GREEN**

Run:

```bash
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" \
  /home/lims/hochlims/bin/test -s hoch.lims \
  -t test_publication_email_default_renders_for_setup
```

Expected: 1 test, 0 failures, 0 errors.

- [ ] **Step 6: Run the complete add-on suite**

Run:

```bash
PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" \
  /home/lims/hochlims/bin/test -s hoch.lims
```

Expected: 95 tests, 0 failures, 0 errors.

- [ ] **Step 7: Check and commit the implementation**

Run:

```bash
git diff --check
git status --short
git add src/hoch/lims/patches/__init__.py \
  src/hoch/lims/patches/senaitesetup.py \
  src/hoch/lims/patches/templates/email_body_sample_publication.pt \
  src/hoch/lims/tests/test_setup.py
git commit -m "fix: render Setup publication default during migration"
```

Expected: one implementation commit containing only the four listed files.

---

### Task 2: Test-Environment Deployment and Migration Verification

**Files:**
- Read: `/home/lims/hochlims/src/hoch.lims/src/hoch/lims/impress/reportview.py`
- Read: `/var/local/plone-5.2/hochlims/client1/event.log`
- Read: `/var/local/plone-5.2/hochlims/client2/event.log`
- Read: `/var/local/plone-5.2/hochlims/client3/event.log`
- No new source file is produced by this task.

**Interfaces:**
- Consumes: the tested implementation commit from Task 1 and the shared test site's Core profile at `2730`.
- Produces: a test site with profile version `2731` and a Dexterity `setup/laboratory` object, or a fully reported transactional rollback.

- [ ] **Step 1: Record and protect the shared checkout state**

Run:

```bash
git -C /home/lims/hochlims/src/hoch.lims status --short --branch
git -C /home/lims/hochlims/src/hoch.lims diff --cached -- \
  src/hoch/lims/impress/reportview.py
```

Expected: the pre-existing staged `reportview.py` change is present. Save the
output for comparison and do not unstage, amend, or include it in any commit.

- [ ] **Step 2: Transfer the tested implementation commit**

Determine the implementation commit:

```bash
HOCH_IMPL_COMMIT="$(git log -1 --format=%H)"
```

From `/home/lims/hochlims/src/hoch.lims`, cherry-pick only that implementation
commit. If Git refuses because of the staged user change, stop and report it;
do not stash or reset user work.

```bash
git cherry-pick "$HOCH_IMPL_COMMIT"
```

Then verify:

```bash
git status --short --branch
git diff --cached -- src/hoch/lims/impress/reportview.py
git -C /home/lims/hochlims/src/senaite.core status --short --branch
git -C /home/lims/hochlims/src/senaite.core rev-parse HEAD
```

Expected: `reportview.py` remains staged and unchanged from Step 1; Core is
clean at `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.

- [ ] **Step 3: Restart all Zope clients**

Use Supervisor's authenticated loopback endpoint to restart `client1`,
`client2`, and `client3`, then check their status. Do not restart ZEO.

```bash
supervisorctl -s http://127.0.0.1:9001 \
  -u admin -p admin restart \
  hochlims_zeoclient1 hochlims_zeoclient2 hochlims_zeoclient3
supervisorctl -s http://127.0.0.1:9001 \
  -u admin -p admin status \
  hochlims_zeoclient1 hochlims_zeoclient2 hochlims_zeoclient3
```

Expected: all three clients reach `RUNNING`, and each event log records
`Ready to handle requests`.

- [ ] **Step 4: Verify the patch is active before touching the profile**

Run a read-only Zope script against `/test` that:

```python
from senaite.core.content.senaitesetup import ISetupSchema
from hoch.lims.patches.senaitesetup import (
    default_email_body_sample_publication)

field = ISetupSchema["email_body_sample_publication"]
assert field.defaultFactory is default_email_body_sample_publication
setup = app.restrictedTraverse("test/setup")
assert "Thank you for your analysis request" in field.bind(setup).default
```

Expected: both assertions pass without committing a transaction.

- [ ] **Step 5: Confirm the pre-migration state**

Run a read-only Zope script against `/test` and assert:

```python
site.portal_setup.getLastVersionForProfile("senaite.core:default") == ("2730",)
api.is_at_content(site.setup.laboratory)
```

Also record critical Laboratory values: ID, title, supervisor UID, accreditation
reference, email, phone, and tax number.

Expected: profile `2730` and an Archetypes Laboratory.

- [ ] **Step 6: Execute only `2730 -> 2731` through GenericSetup**

In the authenticated GenericSetup upgrade page:

```text
http://192.168.64.128/test/portal_setup/manage_upgrades?profile_id=senaite.core:default
```

Select only `2730 -> 2731` (“Migrate Laboratory to Dexterity”) and execute it.
Do not use QuickInstaller and do not select later steps.

Expected: the request completes without `AttributeError`,
`PTRuntimeError`, or proxy timeout.

- [ ] **Step 7: Verify committed migration state**

Run a read-only Zope script and assert:

```python
site.portal_setup.getLastVersionForProfile("senaite.core:default") == ("2731",)
not api.is_at_content(site.setup.laboratory)
site.setup.laboratory.portal_type == "Laboratory"
```

Compare the critical Laboratory values recorded in Step 5. Search all three
event logs from the execution timestamp for:

```text
Convert Laboratory to Dexterity [DONE]
```

and confirm there is no migration traceback.

- [ ] **Step 8: Stop at the verification checkpoint**

Report the profile version, Laboratory implementation type, preserved values,
test results, and relevant log evidence. Do not execute `2731 -> 2732` until
the user approves continuation.
