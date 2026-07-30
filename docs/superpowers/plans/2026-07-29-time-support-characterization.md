# Time Support Characterization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect HOCH.LIMS time-valued interim behavior with executable tests and fix its currently broken display formatting.

**Architecture:** Add one focused unit-test module that exercises the public HOCH.LIMS conversion and formatting boundaries without a Plone site. Keep duration conversion in `BaseCalculator`; add a small locale-aware `format_time_value` utility for display values. Record the upstream `RESULT_TYPES` dependency as a narrow characterization test so switching to an unmodified `senaite.core/2.x` exposes that missing capability explicitly.

**Tech Stack:** Python 2.7, `unittest2`, SENAITE date/time and i18n APIs, Zope test runner.

## Global Constraints

- Work only in `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline` on branch `upgrade/senaite-core-2x-official`.
- Run add-on tests through `/tmp/hoch-lims-worktree-test`; the shared runner points at the shared checkout.
- Do not modify the shared test base or the eight historical dirty files in `/home/lims/hochlims/src/senaite.core`.
- Use test-first development for the missing formatter.
- Limit this delivery to result-type registration, conversion, and display formatting; modal JavaScript and templates belong to a separate integration plan.

---

### Task 1: Characterize time conversion and upstream registration

**Files:**
- Create: `src/hoch/lims/tests/test_time_support.py`

**Interfaces:**
- Consumes: `BaseCalculator.parse_time_to_seconds(value)` and `bika.lims.content.abstractbaseanalysis.RESULT_TYPES`
- Produces: An executable record of accepted duration forms and the upstream `time` result-type dependency

- [ ] **Step 1: Add the characterization tests**

```python
# -*- coding: utf-8 -*-

import unittest2 as unittest

from bika.lims.content.abstractbaseanalysis import RESULT_TYPES
from hoch.lims.calc import BaseCalculator


class TestTimeSupport(unittest.TestCase):

    def test_time_result_type_is_registered(self):
        result_type_ids = [item[0] for item in RESULT_TYPES]
        self.assertIn("time", result_type_ids)

    def test_minutes_and_seconds_are_converted_to_seconds(self):
        self.assertEqual(
            62.0, BaseCalculator.parse_time_to_seconds("01:02"))

    def test_hours_minutes_and_seconds_are_converted_to_seconds(self):
        self.assertEqual(
            3723.0, BaseCalculator.parse_time_to_seconds("01:02:03"))

    def test_numeric_seconds_are_normalized_to_float(self):
        self.assertEqual(
            15.0, BaseCalculator.parse_time_to_seconds(15))

    def test_empty_time_has_no_value(self):
        self.assertIsNone(BaseCalculator.parse_time_to_seconds(""))
        self.assertIsNone(BaseCalculator.parse_time_to_seconds(None))

    def test_invalid_time_is_rejected(self):
        with self.assertRaises(ValueError):
            BaseCalculator.parse_time_to_seconds("invalid")


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestTimeSupport)
```

- [ ] **Step 2: Run the focused characterization tests**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Expected: six tests pass against the current test base. This task describes existing behavior and the known upstream dependency; it does not introduce production code.

- [ ] **Step 3: Commit the characterization**

```bash
git add src/hoch/lims/tests/test_time_support.py
git commit -m "test: characterize time value support"
```

### Task 2: Format time-valued interims for display

**Files:**
- Modify: `src/hoch/lims/tests/test_time_support.py`
- Modify: `src/hoch/lims/utils.py`

**Interfaces:**
- Consumes: Stored interim dictionaries with `result_type="time"` and a string `value`
- Produces: `format_time_value(value) -> str`, used by `get_formatted_interim(interim) -> str`

- [ ] **Step 1: Add the failing display-format test**

Add the import:

```python
from hoch.lims.utils import get_formatted_interim
```

Add the test method:

```python
    def test_time_interim_is_formatted_for_display(self):
        interim = {
            "result_type": "time",
            "value": "01:02:03",
        }
        self.assertEqual("01:02", get_formatted_interim(interim))
```

This catches removal or breakage of the formatter called by the real interim-display boundary.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Expected: `test_time_interim_is_formatted_for_display` errors with `NameError: global name 'format_time_value' is not defined`; the six characterization tests remain green.

- [ ] **Step 3: Add the minimal locale-aware formatter**

In `src/hoch/lims/utils.py`, add:

```python
from datetime import datetime
from senaite.core.api import dtime
from senaite.core.i18n import get_dt_format
```

Add immediately before `get_formatted_interim`:

```python
def format_time_value(value):
    """Return a stored time value using SENAITE's locale time format."""
    for source_format in ("%H:%M:%S", "%H:%M"):
        try:
            value = datetime.strptime(value, source_format)
            return dtime.date_to_string(value, get_dt_format("time"))
        except (TypeError, ValueError):
            continue
    return ""
```

Parse the HTML `time` control formats explicitly. `dtime.to_dt` is a
date/datetime parser and interprets a standalone `HH:MM:SS` string as
midnight in this stack.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Expected: seven tests pass with zero failures and zero errors.

- [ ] **Step 5: Commit the formatter**

```bash
git add src/hoch/lims/tests/test_time_support.py src/hoch/lims/utils.py
git commit -m "fix: format time-valued interim results"
```

### Task 3: Verify the add-on baseline

**Files:**
- Modify: `docs/validation/senaite-2x-component-matrix.md`

**Interfaces:**
- Consumes: Focused tests from Tasks 1 and 2 and the existing HOCH.LIMS suite
- Produces: A reproducible validation record for the data-layer time tranche

- [ ] **Step 1: Run the complete add-on suite**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 2: Check patch hygiene and repository state**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors; only the intended validation-document update is uncommitted after recording the results.

- [ ] **Step 3: Record the new time-support evidence**

Add a component-matrix row stating that the focused time tests cover:

```text
RESULT_TYPES registration; MM:SS and HH:MM:SS conversion; numeric and empty
inputs; invalid input rejection; locale-aware time interim display.
```

Record the exact focused and complete-suite counts reported by the runner.

- [ ] **Step 4: Commit the validation record**

```bash
git add docs/validation/senaite-2x-component-matrix.md
git commit -m "docs: record time support validation"
```

- [ ] **Step 5: Re-run final verification**

Run:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
git diff --check origin/2.x...HEAD
git status --short --branch
```

Expected: complete suite green, no whitespace errors, and a clean worktree ahead of `origin/2.x`.
