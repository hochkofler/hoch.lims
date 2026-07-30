# Calculation Interim Merge Characterization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect the HOCH.LIMS `setCalculation` contract before any refactoring or upstream-core migration removes its compatibility patch.

**Architecture:** Exercise the add-on replacement function directly with small in-memory collaborators. Verify persisted snapshot fields, merge ownership, ordering, and copy isolation without requiring a Plone site. Run the same tests against official and historical core matrices so the patch has one stable add-on-owned contract.

**Tech Stack:** Python 2.7, `unittest2`, HOCH.LIMS compatibility patch, Zope test runner.

## Global Constraints

- Work only on `upgrade/senaite-core-2x-official`.
- Do not change production behavior during characterization.
- Derive expected interim dictionaries as literals.
- Do not assert implementation details that are not part of persisted behavior.
- Validate with both `/tmp/hoch-lims-official-core-test` and `/tmp/hoch-lims-worktree-test`.
- Do not edit SENAITE Core.

---

### Task 1: Characterize calculation snapshots and interim ownership

**Files:**
- Create: `src/hoch/lims/tests/test_calculation_interims.py`

**Interfaces:**
- Consumes: `hoch.lims.patches.analysis.setCalculation(self, value)`
- Produces: regression coverage for calculation snapshots and interim merging

- [ ] **Step 1: Add in-memory collaborators**

Create:

```python
class DummyField(object):

    def __init__(self):
        self.value = None

    def set(self, context, value):
        self.value = value


class DummyCalculation(object):

    def UID(self):
        return "calculation-uid"

    def getMinifiedFormula(self):
        return "[Temperature] * 2"

    def getPythonImports(self):
        return [{"module": "math", "function": "sqrt"}]

    def getVersion(self):
        return 7

    def getInterimFields(self):
        return self.interims


class DummyAnalysis(object):

    def __init__(self, interims):
        self.interims = interims
        self.fields = {
            name: DummyField()
            for name in (
                "CalculationUID", "CalculationFormula",
                "CalculationImports", "CalculationVersion")
        }

    def getField(self, name):
        return self.fields[name]

    def getInterimFields(self):
        return self.interims

    def setInterimFields(self, interims):
        self.interims = interims
```

If `api.get_version` requires a different public version accessor, add only
that accessor to `DummyCalculation`.

- [ ] **Step 2: Test snapshot fields**

Call `setCalculation(analysis, calculation)` and assert literal values:

```python
self.assertEqual(
    "calculation-uid", analysis.fields["CalculationUID"].value)
self.assertEqual(
    "[Temperature] * 2", analysis.fields["CalculationFormula"].value)
self.assertEqual(
    '[{"function": "sqrt", "module": "math"}]',
    analysis.fields["CalculationImports"].value)
self.assertEqual(7, analysis.fields["CalculationVersion"].value)
```

- [ ] **Step 3: Test shared-field ownership**

Use a calculation interim and service interim with the same keyword. Assert
that service values win for:

```text
value, hidden, report, unit, title, wide
```

Assert that calculation values remain authoritative for:

```text
choices, result_type, allow_empty
```

- [ ] **Step 4: Test ordering and exclusivity**

Assert that calculation interims appear first in calculation order, followed
by service-only interims, and that a shared keyword appears exactly once.

- [ ] **Step 5: Test copy isolation**

After linking, mutate the source calculation and service dictionaries. Assert
that the analysis snapshot remains unchanged.

- [ ] **Step 6: Test unlink behavior**

Call `setCalculation(analysis, None)` and assert the four calculation snapshot
fields are cleared while existing interims remain unchanged.

- [ ] **Step 7: Add explicit suite discovery**

```python
def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestCalculationInterims)
```

### Task 2: Verify both core matrices

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Consumes: the characterization tests from Task 1
- Produces: recorded evidence that the contract is independent of the core fork

- [ ] **Step 1: Run focused tests against official core**

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_calculation_interims
```

Expected: all characterization tests pass.

- [ ] **Step 2: Run focused tests against historical core**

```bash
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_calculation_interims
```

Expected: identical test count and result.

- [ ] **Step 3: Run both complete suites**

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: both suites pass with zero failures and errors.

- [ ] **Step 4: Record exact evidence and commit**

Record focused and complete counts in the component matrix, then:

```bash
git diff --check
git add src/hoch/lims/tests/test_calculation_interims.py \
  docs/validation/senaite-2x-component-matrix.md
git commit -m "test: characterize calculation interim merging"
```
