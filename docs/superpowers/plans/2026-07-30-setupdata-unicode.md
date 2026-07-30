# Setup Data Unicode Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the two UTF-8 setup-data title normalizations from the `hoch-prod` Core branch into HOCH.LIMS, so production can run official SENAITE Core unchanged.

**Architecture:** Register two narrowly scoped `collective.monkeypatcher` replacements in HOCH's existing export-import patch package. Each replacement copies the matching official Core importer flow and changes only the value passed to `api.create(..., title=...)`, normalizing it with `api.safe_unicode`.

**Tech Stack:** Python 2.7, Plone 5.2, SENAITE Core 2.x, HOCH.LIMS, ZCML, `collective.monkeypatcher`, `unittest2`.

## Global Constraints

- Keep `senaite.core` at official commit `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`; do not modify Core.
- Match only the two effective `hoch-prod` changes: Unicode titles for `InstrumentType` and `SampleCondition` setup-data imports.
- Preserve description values without normalization.
- Preserve Core behavior for rows without a title: skip them without creating content.
- Do not alter existing content, indexes, or catalogs.
- Run tests with `/home/lims/hochlims/bin/test --path "$PWD/src" -s hoch.lims` from the isolated worktree.

---

### Task 1: Characterize and Implement Setup-Data Import Overrides

**Files:**
- Modify: `src/hoch/lims/patches/exportimport/configure.zcml`
- Modify: `src/hoch/lims/patches/exportimport/setupdata.py`
- Create: `src/hoch/lims/tests/test_setupdata_unicode.py`

**Interfaces:**
- Consumes: `senaite.core.exportimport.setupdata.Instrument_Types.Import(self)` and `Sample_Conditions.Import(self)`.
- Produces: `import_instrument_types(self) -> None` and `import_sample_conditions(self) -> None` in `hoch.lims.patches.exportimport.setupdata`.

- [ ] **Step 1: Write the failing regression tests**

Create `src/hoch/lims/tests/test_setupdata_unicode.py`:

```python
# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.patches.exportimport import setupdata


class DummySetup(object):

    instrumenttypes = object()
    sampleconditions = object()


class DummyContext(object):

    setup = DummySetup()


class DummyImporter(object):

    def __init__(self, rows):
        self.context = DummyContext()
        self.rows = rows

    def get_rows(self, start_row):
        return self.rows


class TestSetupDataUnicode(unittest.TestCase):

    def setUp(self):
        self.created = []
        self.original_create = setupdata.api.create
        setupdata.api.create = self.create

    def tearDown(self):
        setupdata.api.create = self.original_create

    def create(self, container, portal_type, **kwargs):
        self.created.append((container, portal_type, kwargs))

    def test_instrument_type_title_is_unicode(self):
        importer = DummyImporter([{
            "title": u"Espectrómetro Óptico".encode("utf-8"),
            "description": "unchanged",
        }])

        setupdata.import_instrument_types(importer)

        container, portal_type, kwargs = self.created[0]
        self.assertIs(importer.context.setup.instrumenttypes, container)
        self.assertEqual("InstrumentType", portal_type)
        self.assertIsInstance(kwargs["title"], unicode)
        self.assertEqual(u"Espectrómetro Óptico", kwargs["title"])
        self.assertEqual("unchanged", kwargs["description"])

    def test_sample_condition_title_is_unicode_and_empty_title_is_skipped(self):
        importer = DummyImporter([
            {"title": "", "description": "ignored"},
            {
                "title": u"Condición Térmica Óptima".encode("utf-8"),
                "description": "unchanged",
            },
        ])

        setupdata.import_sample_conditions(importer)

        self.assertEqual(1, len(self.created))
        container, portal_type, kwargs = self.created[0]
        self.assertIs(importer.context.setup.sampleconditions, container)
        self.assertEqual("SampleCondition", portal_type)
        self.assertIsInstance(kwargs["title"], unicode)
        self.assertEqual(u"Condición Térmica Óptima", kwargs["title"])
        self.assertEqual("unchanged", kwargs["description"])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSetupDataUnicode)
```

- [ ] **Step 2: Run the tests and confirm they fail because the replacements do not exist**

Run:

```bash
/home/lims/hochlims/bin/test \
  --path "$PWD/src" \
  -s hoch.lims \
  -t test_setupdata_unicode
```

Expected: errors stating that `setupdata` has no attribute
`import_instrument_types` and `import_sample_conditions`.

- [ ] **Step 3: Implement the two minimal replacement functions**

Append these functions to `src/hoch/lims/patches/exportimport/setupdata.py`:

```python
def import_instrument_types(self):
    container = self.context.setup.instrumenttypes
    for row in self.get_rows(3):
        title = row.get("title")
        if not title:
            continue
        api.create(container, "InstrumentType",
                   title=api.safe_unicode(title),
                   description=row.get("description"))


def import_sample_conditions(self):
    container = self.context.setup.sampleconditions
    for row in self.get_rows(3):
        title = row.get("title")
        if not title:
            continue
        description = row.get("description")
        api.create(container, "SampleCondition",
                   title=api.safe_unicode(title),
                   description=description)
```

- [ ] **Step 4: Register the replacements in ZCML**

Append before `</configure>` in
`src/hoch/lims/patches/exportimport/configure.zcml`:

```xml
    <monkey:patch
    description="Unicode InstrumentType setup-data titles"
    class="senaite.core.exportimport.setupdata.Instrument_Types"
    original="Import"
    ignoreOriginal="True"
    replacement=".setupdata.import_instrument_types" />

    <monkey:patch
    description="Unicode SampleCondition setup-data titles"
    class="senaite.core.exportimport.setupdata.Sample_Conditions"
    original="Import"
    ignoreOriginal="True"
    replacement=".setupdata.import_sample_conditions" />
```

- [ ] **Step 5: Run focused tests and then the full HOCH.LIMS suite**

Run:

```bash
/home/lims/hochlims/bin/test \
  --path "$PWD/src" \
  -s hoch.lims \
  -t test_setupdata_unicode

/home/lims/hochlims/bin/test --path "$PWD/src" -s hoch.lims
```

Expected: focused tests pass; complete suite has zero failures and zero errors.

- [ ] **Step 6: Review and commit only the compatibility change**

Run:

```bash
git diff --check
git diff -- src/hoch/lims/patches/exportimport/configure.zcml \
  src/hoch/lims/patches/exportimport/setupdata.py \
  src/hoch/lims/tests/test_setupdata_unicode.py
git add src/hoch/lims/patches/exportimport/configure.zcml \
  src/hoch/lims/patches/exportimport/setupdata.py \
  src/hoch/lims/tests/test_setupdata_unicode.py
git commit -m "fix: normalize setup data titles"
```

Expected: the commit contains only the two importer overrides, their ZCML
registration, and the regression tests.

---

### Task 2: Verify Official Core Has No HOCH-Specific Diff

**Files:**
- Verify only: `/home/lims/hochlims/src/senaite.core`

**Interfaces:**
- Consumes: official Core ref `origin/2.x` at `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.
- Produces: evidence that the production Core source can remain official and the Unicode import behavior is supplied by HOCH.LIMS.

- [ ] **Step 1: Compare the official Core checkout to the approved ref**

Run:

```bash
git -C /home/lims/hochlims/src/senaite.core status --short
git -C /home/lims/hochlims/src/senaite.core rev-parse HEAD
git -C /home/lims/hochlims/src/senaite.core diff --stat ba57f85e84cea821a5c206d7f90b3ccfcaad43f5
```

Expected: clean status, HEAD equal to `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`, and no diff.

- [ ] **Step 2: Record the handoff condition**

Record that deployment requires the HOCH.LIMS compatibility commit plus the
official Core checkout. Do not deploy `origin/hoch-prod` for this behavior.
