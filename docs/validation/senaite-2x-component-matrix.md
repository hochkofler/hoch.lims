# SENAITE 2.x Validation Matrix

Date: 2026-07-29

## Runtime

- Python: 2.7.18
- Plone: 5.2.15

## Components

| Component | Branch | SHA |
| --- | --- | --- |
| hoch.lims source baseline | 2.x | 664b2956228ffa94615c99ce0dcea499fdbb2c67 |
| senaite.core | hoch-prod | e98fb15a37fa269994e8fc81e1b60f145ae7681b |
| senaite.lims | 2.x | 0e487baf128dbfd9444048334ffa6f176b0dd8d2 |
| senaite.app.listing | 2.x | 3d0a603e1976a2516988051381b0418da1e2e9ea |
| senaite.app.spotlight | 2.x | 6212658fbafae22d1f74dee5ca1e1745098af0b4 |
| senaite.app.supermodel | 2.x | 03cc81a7d799135d19676129d30a8ca6512777a8 |
| senaite.impress | 2.x | 01d5380aa1e574e27c843536bd04d4df3e2b32d8 |
| senaite.jsonapi | 2.x | 0139af663f23c773dff5e4c4367ac5a47a44c9d8 |

## Test runner

The generated shared runner hard-codes the original `hoch.lims` checkout.
Tests in the isolated worktree therefore use a temporary copy at:

```text
/tmp/hoch-lims-worktree-test
```

Only these two entries differ from the shared runner:

```text
/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline/src
```

They replace the original addon source and test paths. All SENAITE components,
eggs, runtime settings, and runner arguments remain unchanged.

## Baseline result

Command:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Result:

- 13 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0;
- no `Could not install product senaite.jsonapi` message.

## Interpretation

This matrix records the pre-adaptation characterization environment. The
`senaite.core` entry is intentionally the historical `hoch-prod` fork and is
not the target matrix. The official-core phase will replace it with a pinned
official `senaite.core/2.x` SHA and record a second matrix.

The core checkout contains eight uncommitted historical customizations. Tests
in this phase characterize existing behavior; they do not establish
compatibility with a clean official core.

## Time-support characterization

Focused command:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims -t test_time_support
```

Focused result:

- 7 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

Coverage:

- `time` registration in `RESULT_TYPES`;
- `MM:SS` and `HH:MM:SS` conversion to seconds;
- numeric and empty inputs;
- invalid conversion input rejection;
- locale-aware display of a time-valued interim.

Complete-suite result after the formatter correction:

- 20 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

The registration test intentionally depends on the historical core patch. It
must fail when the clean official core is first introduced, identifying the
capability that must be supplied upstream or through a supported add-on hook.

## Official core failure baseline

Official source:

```text
https://github.com/senaite/senaite.core.git
branch: 2.x
SHA: ba57f85e84cea821a5c206d7f90b3ccfcaad43f5
checkout: /home/lims/hochlims/worktrees/senaite-core-official-2x
```

The isolated runner `/tmp/hoch-lims-official-core-test` replaces both source
paths:

```text
hoch.lims -> /home/lims/hochlims/worktrees/hoch-lims-senaite-baseline/src
senaite.core -> /home/lims/hochlims/worktrees/senaite-core-official-2x/src
```

Focused command:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims -t test_time_support
```

Focused result:

- 7 tests;
- 1 failure;
- 0 errors;
- 0 skipped;
- non-zero exit code.

Complete command:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
```

Complete result:

- 20 tests;
- 1 failure;
- 0 errors;
- 0 skipped;
- non-zero exit code.

The sole observed regression is
`TestTimeSupport.test_time_result_type_is_registered`: official core exposes
`numeric`, `string`, `text`, selection types, `date`, and `datetime`, but not
`time`.

Classification: **missing general SENAITE capability suitable for upstream**.
Time is a general analysis/interim result type rather than a HOCH-specific
domain concept. HOCH.LIMS may carry an isolated compatibility layer while an
upstream change is proposed, but the durable owner should be SENAITE Core.

No other failure is exposed by the current 20-test suite. This is not evidence
that the other historical core changes are obsolete; each still requires
behavioral characterization before removal.
