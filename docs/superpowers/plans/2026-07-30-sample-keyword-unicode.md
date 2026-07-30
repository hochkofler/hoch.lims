# Sample Keyword Unicode Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the SENAITE samples listing from raising `UnicodeDecodeError` when cataloged analysis keywords are UTF-8 byte strings.

**Architecture:** Keep the official `senaite.core` checkout unchanged. Register a focused `collective.monkeypatcher` wrapper in `hoch.lims` that converts the keyword and active-keyword collection with `bika.lims.api.safe_unicode`, then delegates rendering and URL construction to Core's preserved method.

**Tech Stack:** Python 2.7, Plone 5.2, SENAITE Core 2.x, ZCML, `collective.monkeypatcher`, `unittest2`, `plone.app.testing`.

## Global Constraints

- Keep `senaite.core` at the official commit `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`; do not modify Core.
- Do not mutate or reindex catalog data in this change.
- Preserve Core behavior for ASCII strings and Unicode strings.
- Preserve the unrelated staged change in shared `src/hoch/lims/impress/reportview.py`; its cached diff SHA-256 is `726c4403f9751d8bdd0da3e40541a635f829b2482b8406d01b5c0aac736de8c2`.
- Run package tests with `--path "$PWD/src"` so the isolated worktree is imported instead of the shared checkout.
- Deploy only after the isolated worktree passes the focused and complete test suites.

---

### Task 1: Regression Test and Compatibility Wrapper

**Files:**
- Create: `src/hoch/lims/patches/sample_keywords.py`
- Modify: `src/hoch/lims/patches/configure.zcml`
- Create: `src/hoch/lims/tests/test_sample_keyword_unicode.py`

**Interfaces:**
- Consumes: Core method `SamplesView.render_keyword_filter_chip(self, keyword, active_keywords)` and the preserved method name `_old_render_keyword_filter_chip`.
- Produces: `hoch.lims.patches.sample_keywords.render_keyword_filter_chip(self, keyword, active_keywords) -> unicode`.

- [ ] **Step 1: Write the failing integration test**

Create `src/hoch/lims/tests/test_sample_keyword_unicode.py`:

```python
# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.tests.base import SIMPLE_TESTING
from senaite.core.browser.samples.view import SamplesView


class TestSampleKeywordUnicode(unittest.TestCase):

    layer = SIMPLE_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def test_non_ascii_byte_keyword_renders_filter_chip(self):
        view = SamplesView(self.portal, self.request)
        keyword = u"CONCENTRACIÓN".encode("utf-8")

        chip = view.render_keyword_filter_chip(keyword, [keyword])

        self.assertIsInstance(chip, unicode)
        self.assertIn(u"<code>CONCENTRACIÓN</code>", chip)
        self.assertIn(u'class="analysis-keyword-filter active"', chip)
        self.assertIn(u"samples_column_filters=", chip)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSampleKeywordUnicode)
```

- [ ] **Step 2: Run the focused test and verify the production failure**

Run:

```bash
/home/lims/hochlims/bin/test \
  --path "$PWD/src" \
  -s hoch.lims \
  -t test_non_ascii_byte_keyword_renders_filter_chip
```

Expected: one error with `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3`, originating from Core's Unicode HTML template formatting.

- [ ] **Step 3: Add the minimal normalization wrapper**

Create `src/hoch/lims/patches/sample_keywords.py`:

```python
# -*- coding: utf-8 -*-

from bika.lims import api


def render_keyword_filter_chip(self, keyword, active_keywords):
    """Render cataloged analysis keywords safely as Unicode.

    Legacy catalog metadata can contain UTF-8 byte strings. Normalize the
    renderer inputs and leave all chip behavior to the original Core method.
    """
    keyword = api.safe_unicode(keyword)
    active_keywords = [
        api.safe_unicode(active_keyword)
        for active_keyword in active_keywords
    ]
    return self._old_render_keyword_filter_chip(keyword, active_keywords)
```

- [ ] **Step 4: Register the wrapper and preserve the Core method**

Append this registration before `</configure>` in
`src/hoch/lims/patches/configure.zcml`:

```xml
  <monkey:patch
    description="Render non-ASCII sample analysis keywords"
    class="senaite.core.browser.samples.view.SamplesView"
    original="render_keyword_filter_chip"
    preserveOriginal="True"
    replacement=".sample_keywords.render_keyword_filter_chip" />
```

- [ ] **Step 5: Run the focused test and verify it passes**

Run:

```bash
/home/lims/hochlims/bin/test \
  --path "$PWD/src" \
  -s hoch.lims \
  -t test_non_ascii_byte_keyword_renders_filter_chip
```

Expected: `Ran 1 test` and `OK`.

- [ ] **Step 6: Run the complete addon suite**

Run:

```bash
/home/lims/hochlims/bin/test --path "$PWD/src" -s hoch.lims
```

Expected: 96 tests, zero failures and zero errors.

- [ ] **Step 7: Review and commit the tested implementation**

Run:

```bash
git diff --check
git diff -- src/hoch/lims/patches/configure.zcml \
  src/hoch/lims/patches/sample_keywords.py \
  src/hoch/lims/tests/test_sample_keyword_unicode.py
git add src/hoch/lims/patches/configure.zcml \
  src/hoch/lims/patches/sample_keywords.py \
  src/hoch/lims/tests/test_sample_keyword_unicode.py
git commit -m "fix: render Unicode sample keywords"
```

Expected: the commit contains only the wrapper, its ZCML registration, and its regression test.

---

### Task 2: Test-Environment Deployment and Runtime Verification

**Files:**
- Create in shared checkout: `src/hoch/lims/patches/sample_keywords.py`
- Modify in shared checkout: `src/hoch/lims/patches/configure.zcml`
- Create in shared checkout: `src/hoch/lims/tests/test_sample_keyword_unicode.py`
- Preserve unchanged: `src/hoch/lims/impress/reportview.py`

**Interfaces:**
- Consumes: the verified implementation commit from Task 1.
- Produces: a running test site whose `/test/samples/view/folderitems` endpoint renders non-ASCII keyword chips without HTTP 500.

- [ ] **Step 1: Capture and verify the shared checkout safety state**

Run from `/home/lims/hochlims/src/hoch.lims`:

```bash
git status --short --branch
git diff --cached -- src/hoch/lims/impress/reportview.py | sha256sum
```

Expected: `reportview.py` remains staged and the hash is
`726c4403f9751d8bdd0da3e40541a635f829b2482b8406d01b5c0aac736de8c2`.

- [ ] **Step 2: Transfer only the tested files into the shared checkout**

Apply the exact Task 1 commit patch to the shared checkout, limited to:

```text
src/hoch/lims/patches/configure.zcml
src/hoch/lims/patches/sample_keywords.py
src/hoch/lims/tests/test_sample_keyword_unicode.py
```

Do not unstage, edit, or include `src/hoch/lims/impress/reportview.py`.

- [ ] **Step 3: Commit only the compatibility paths**

Run from `/home/lims/hochlims/src/hoch.lims`:

```bash
git commit --only \
  src/hoch/lims/patches/configure.zcml \
  src/hoch/lims/patches/sample_keywords.py \
  src/hoch/lims/tests/test_sample_keyword_unicode.py \
  -m "fix: render Unicode sample keywords"
```

Expected: the new compatibility files are committed while `reportview.py` remains staged and absent from the new commit.

- [ ] **Step 4: Re-verify the preserved staged change**

Run:

```bash
git status --short
git diff --cached -- src/hoch/lims/impress/reportview.py | sha256sum
git show --stat --oneline HEAD
```

Expected: `reportview.py` is still staged with hash
`726c4403f9751d8bdd0da3e40541a635f829b2482b8406d01b5c0aac736de8c2`,
and the commit contains only the three compatibility paths.

- [ ] **Step 5: Restart all Zope clients**

Run:

```bash
supervisorctl -s http://127.0.0.1:9001 -u admin -p admin restart \
  hochlims_zeoclient1 hochlims_zeoclient2 hochlims_zeoclient3
```

Expected: all three processes restart successfully and report `RUNNING`.

- [ ] **Step 6: Verify the samples endpoint through authenticated HTTP**

Request the endpoint with the configured test administrator credentials:

```bash
curl --fail --silent --show-error \
  --user 'admin:<configured-test-password>' \
  --output /tmp/hochlims-samples-folderitems.json \
  --write-out '%{http_code}\n' \
  http://127.0.0.1:8080/test/samples/view/folderitems
```

Expected: HTTP `200`; the response is saved for inspection and no longer returns the previous HTTP 500.

- [ ] **Step 7: Confirm runtime output and logs**

Run:

```bash
python -m json.tool /tmp/hochlims-samples-folderitems.json >/dev/null
rg -n "UnicodeDecodeError|render_keyword_filter_chip" \
  /home/lims/hochlims/var/log/instance*.log
```

Expected: the response is valid JSON and no new post-restart traceback for `render_keyword_filter_chip` appears. Historical matches may remain and must be distinguished by timestamp.

- [ ] **Step 8: Record the result without reindexing**

Report the focused/full test counts, HTTP status, client state, and log result.
Explicitly note that this block did not reindex catalogs; catalog normalization
and a controlled reindex remain a separate follow-up.
