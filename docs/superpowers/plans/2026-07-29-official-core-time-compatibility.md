# Official Core Time Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve HOCH.LIMS `time` analysis and interim behavior while running against an unmodified official `senaite.core/2.x`.

**Architecture:** Put all temporary compatibility code behind one focused `hoch.lims.patches.time_support` module. Extend legacy result-type vocabularies at add-on load time because the Archetypes fields expose no registration hook; override the named modern interim vocabulary through ZCML. Wrap only the two core display methods that need time-specific formatting, and override the edit-analysis modal with a HOCH-owned subclass/template until the general capability is accepted upstream.

**Tech Stack:** Python 2.7, Archetypes `DisplayList`, Zope Component Architecture, Five browser pages, Page Templates, JavaScript, `unittest2`, Zope test runner.

## Global Constraints

- Develop only on `upgrade/senaite-core-2x-official` in the isolated HOCH.LIMS worktree.
- Validate with `/tmp/hoch-lims-official-core-test` against official core SHA `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.
- Do not edit either SENAITE Core checkout.
- Keep time storage compatible with HTML controls: `HH:MM` or `HH:MM:SS`.
- Derive expected formatted values as literals; do not use `dtime.to_dt` to calculate test expectations.
- Keep the compatibility module removable: no domain model or persistent-data migration is introduced.
- Treat an isolated monkey patch as the last resort only where legacy Archetypes fields provide no supported registration hook.
- Do not create the separate SENAITE Core PR without explicit user approval.

---

### Task 1: Register `time` in legacy and modern vocabularies

**Files:**
- Create: `src/hoch/lims/patches/time_support.py`
- Modify: `src/hoch/lims/patches/__init__.py`
- Modify: `src/hoch/lims/overrides.zcml`
- Modify: `src/hoch/lims/tests/test_time_support.py`

**Interfaces:**
- Produces: `TIME_RESULT_TYPE`, `TimeResultTypesVocabulary`, and idempotent `enable_time_result_type()`
- Consumes: legacy `ResultType` and `InterimFieldsField`, plus the named modern result-types vocabulary

- [ ] **Step 1: Strengthen the failing registration tests**

Add tests that assert observable vocabulary results:

```python
from bika.lims.browser.fields.interimfieldsfield import InterimFieldsField
from bika.lims.content.abstractbaseanalysis import ResultType
from hoch.lims.patches.time_support import TimeResultTypesVocabulary

    def test_time_is_available_for_analysis_results(self):
        self.assertIn("time", list(ResultType.vocabulary))

    def test_time_is_available_for_legacy_interims(self):
        field = InterimFieldsField("Interims")
        vocabulary = field.subfield_vocabularies["result_type"]
        self.assertIn("time", list(vocabulary))

    def test_time_is_available_for_modern_interims(self):
        vocabulary = TimeResultTypesVocabulary()(None)
        self.assertIn("time", [term.value for term in vocabulary])
```

Remove the constant-only `RESULT_TYPES` assertion after these consumer-level
tests exist.

- [ ] **Step 2: Verify RED against official core**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
```

Expected: the three vocabulary tests fail because `time` is absent.

- [ ] **Step 3: Implement idempotent legacy vocabulary extension**

Create `hoch.lims.patches.time_support` with:

```python
from bika.lims import _
from bika.lims.browser.fields.interimfieldsfield import InterimFieldsField
from bika.lims.content import abstractbaseanalysis
from Products.Archetypes.public import DisplayList
from senaite.core.config import vocabularies as config_vocabularies
from senaite.core.schema.vocabulary import to_simple_vocabulary
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory

TIME_RESULT_TYPE = ("time", _("Time"))


def append_time(items):
    if "time" in [item[0] for item in items]:
        return tuple(items)
    return tuple(items) + (TIME_RESULT_TYPE,)


def enable_time_result_type():
    abstractbaseanalysis.RESULT_TYPES = append_time(
        abstractbaseanalysis.RESULT_TYPES)
    abstractbaseanalysis.ResultType.vocabulary = DisplayList(
        abstractbaseanalysis.RESULT_TYPES)

    vocabulary = InterimFieldsField._properties[
        "subfield_vocabularies"]["result_type"]
    if "time" not in list(vocabulary):
        vocabulary.add("time", _("Time"))

    config_vocabularies.RESULT_TYPES = append_time(
        config_vocabularies.RESULT_TYPES)


@implementer(IVocabularyFactory)
class TimeResultTypesVocabulary(object):

    def __call__(self, context):
        return to_simple_vocabulary(
            append_time(config_vocabularies.RESULT_TYPES))


enable_time_result_type()
```

Import the module from `patches/__init__.py`. In `overrides.zcml`, register
`TimeResultTypesVocabulary` with the existing name
`senaite.core.vocabularies.resulttypes`.

- [ ] **Step 4: Verify GREEN on official and historical cores**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Expected: all focused tests pass in both matrices; repeated initialization
does not duplicate the `time` entry.

- [ ] **Step 5: Commit**

```bash
git add src/hoch/lims/patches/time_support.py \
  src/hoch/lims/patches/__init__.py \
  src/hoch/lims/overrides.zcml \
  src/hoch/lims/tests/test_time_support.py
git commit -m "fix: register time result types outside core"
```

### Task 2: Format time results and listing interims

**Files:**
- Modify: `src/hoch/lims/patches/time_support.py`
- Modify: `src/hoch/lims/tests/test_time_support.py`

**Interfaces:**
- Consumes: `format_time_value(value)` from `hoch.lims.utils`
- Produces: wrappers that delegate every non-time value unchanged to the original core methods

- [ ] **Step 1: Add failing wrapper tests**

Create minimal analysis and view doubles and test:

```python
    def test_time_analysis_result_uses_hoch_formatter(self):
        analysis = DummyTimeAnalysis("01:02:03")
        self.assertEqual("01:02", format_analysis_result(analysis, None))

    def test_time_listing_interim_uses_hoch_formatter(self):
        view = DummyAnalysesView()
        interim = {"result_type": "time", "value": "01:02:03"}
        self.assertEqual("01:02", format_listing_interim(view, None, interim))
```

Also test that non-time inputs invoke a sentinel original callable exactly
once and return its value.

- [ ] **Step 2: Verify RED**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
```

Expected: imports fail because the wrapper functions do not exist.

- [ ] **Step 3: Implement narrow wrappers**

Add:

```python
from hoch.lims.utils import format_time_value


def format_analysis_result(self, *args, **kwargs):
    if self.getResultType() == "time":
        return format_time_value(self.getResult())
    return self._old_getFormattedResult(*args, **kwargs)


def format_listing_interim(self, interim):
    if interim.get("result_type") == "time":
        return format_time_value(interim.get("value"))
    return self._old_get_formatted_interim(interim)
```

Register both with `monkey:patch` in `patches/configure.zcml`, targeting
`AbstractAnalysis.getFormattedResult` and `AnalysesView.get_formatted_interim`
with `preserveOriginal="True"`. The preservation handler exposes the originals
as `_old_getFormattedResult` and `_old_get_formatted_interim`.

- [ ] **Step 4: Verify both matrices and commit**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Expected: focused tests pass in both matrices.

Commit:

```bash
git add src/hoch/lims/patches/time_support.py \
  src/hoch/lims/patches/configure.zcml \
  src/hoch/lims/tests/test_time_support.py
git commit -m "fix: format time results outside core"
```

### Task 3: Supply time controls in the analysis edit modal

**Files:**
- Create: `src/hoch/lims/browser/analysis/edit.py`
- Create: `src/hoch/lims/browser/analysis/templates/edit_analysis.pt`
- Create: `src/hoch/lims/browser/analysis/static/edit_analysis.js`
- Create: `src/hoch/lims/browser/analysis/configure.zcml`
- Modify: `src/hoch/lims/browser/configure.zcml`
- Modify: `src/hoch/lims/tests/test_time_support.py`

**Interfaces:**
- Consumes: official `EditAnalysisForm`
- Produces: `HochEditAnalysisForm` registered as `edit_analysis_modal` on `IHochLims`

- [ ] **Step 1: Add modal behavior tests**

Using the existing integration layer, render an editable time-result analysis
and assert:

```python
self.assertIn('type="time" name="Result"', rendered)
self.assertIn('step="1"', rendered)
self.assertNotIn('type="text" name="Result"', rendered)
```

Render a time interim and assert that it has a visible `type="time"` input and
a hidden input carrying the same keyword. Submit `01:02:03` and assert the
analysis/interim stores exactly `01:02:03`.

- [ ] **Step 2: Verify RED against official core**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
```

Expected: official modal renders the generic text control or lacks the
time-interim control.

- [ ] **Step 3: Add the scoped browser override**

Subclass official `EditAnalysisForm` only to set a HOCH-owned
`ViewPageTemplateFile`. Copy the pinned official template and JavaScript into
the add-on, then apply only these changes:

- render analysis result type `time` as `<input type="time" step="1">`;
- exclude `time` from the generic text-result condition;
- render time interims with visible and hidden inputs;
- let the JavaScript synchronizer support a time-only input when no date input
  exists.

Register the page for `*`, name `edit_analysis_modal`, permission
`senaite.core.permissions.FieldEditAnalysisResult`, and layer
`hoch.lims.interfaces.IHochLims`.

- [ ] **Step 4: Verify modal and complete suites**

Run:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: all tests pass in both matrices.

- [ ] **Step 5: Commit**

```bash
git add src/hoch/lims/browser/analysis \
  src/hoch/lims/browser/configure.zcml \
  src/hoch/lims/tests/test_time_support.py
git commit -m "fix: edit time results outside core"
```

### Task 4: Document upstream extraction and final evidence

**Files:**
- Create: `docs/upstream/senaite-core-time-result-support.md`
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Produces: an upstream-ready change description without creating a PR

- [ ] **Step 1: Document the upstream patch**

Specify the general core changes:

- add `time` to legacy and modern result vocabularies;
- accept `time` in default-result validation;
- parse `HH:MM[:SS]` explicitly for result and interim display;
- render and submit time controls in listings and the edit modal;
- test literals such as `01:02`, never expectations derived through the same
  parser.

State that the add-on compatibility module and modal override can be removed
after the minimum supported official core contains the feature.

- [ ] **Step 2: Record final validation**

Record exact focused and complete-suite totals for both core matrices in the
component matrix.

- [ ] **Step 3: Run final verification**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
git diff --check origin/2.x...HEAD
git status --short --branch
```

Expected: both suites green, clean patch hygiene, and a clean worktree.

- [ ] **Step 4: Commit**

```bash
git add docs/upstream/senaite-core-time-result-support.md \
  docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: prepare upstream time support extraction"
```
