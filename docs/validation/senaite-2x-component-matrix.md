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

## Official core time compatibility result

HOCH.LIMS now supplies the temporary compatibility layer without modifying
official core `ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`.

Coverage added:

- legacy AnalysisService result vocabulary;
- legacy and modern interim vocabularies;
- time conversion and locale-aware formatting;
- delegation of non-time analysis and interim formatting;
- modal result and interim time controls;
- server-side interim submission normalization.

Final official-core command:

```bash
/tmp/hoch-lims-official-core-test -s hoch.lims
```

Result:

- 29 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

Final historical-core command:

```bash
/tmp/hoch-lims-worktree-test -s hoch.lims
```

Result:

- 29 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

The Page Template is compiled and rendered in the integration layer for both
result and interim cases. The environment has no JavaScript runtime such as
Node.js, so JavaScript syntax was not independently checked by a JS parser;
the server-side normalization protects interim persistence independently of
the client synchronizer.

## Calculation interim merge characterization

Focused commands:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_calculation_interims
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_calculation_interims
```

Each matrix reports:

- 6 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

The tests protect:

- calculation UID, formula, imports, and version snapshots;
- service ownership of `value`, `hidden`, `report`, `unit`, `title`, and
  `wide` for shared interims;
- calculation ownership of `choices`, `result_type`, and `allow_empty`;
- calculation-first and service-only ordering;
- one record per shared keyword;
- deep-copy isolation from source dictionaries;
- unlink behavior.

Complete-suite result after adding the characterization:

| Matrix | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Official core `ba57f85e8` | 35 | 0 | 0 | 0 |
| Historical core `e98fb15` plus local patches | 35 | 0 | 0 | 0 |

The matching results establish that this merge behavior is owned and supplied
by `hoch.lims`; it does not require the historical SENAITE Core checkout.

## Batch workflow characterization

Focused commands:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t test_batch_workflow
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t test_batch_workflow
```

Each matrix reports:

- 15 tests;
- 0 failures;
- 0 errors;
- 0 skipped;
- exit code 0.

The characterization found two release implementations with different
behavior. The workflow profile invokes the legacy
`Batch.guard_release_batch()` expression, while `BatchGuardAdapter` invokes
`workflow.batch.guards.guard_release()`. Before unification, the legacy path
did not reject out-of-specification samples or open OOS investigations, and
the adapter path rejected samples already in the `published` state.

Both entry points now converge on the canonical guard while the legacy method
retains its acquisition-safe Batch lookup for compatibility with installed
workflow definitions. No GenericSetup workflow migration is required by this
change.

The tests protect these release invariants:

- the Batch is closed;
- a release publication is selected and active;
- at least one Batch sample has `Destination` set to `release`;
- every release sample belongs to the selected publication;
- every non-invalid release sample is verified or published;
- verified analyses are within specification;
- no release sample has an open OOS investigation.

They also protect close/reopen state guards, adapter delegation, and the
post-release audit behavior that records `ReleaseDate` and `ReleasedBy` and
reindexes the Batch. Missing optional audit fields do not abort the event.

Complete-suite result after guard unification:

| Matrix | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Official core `ba57f85e8` | 50 | 0 | 0 | 0 |
| Historical core `e98fb15` plus local patches | 50 | 0 | 0 | 0 |

The matching results establish that the Batch release rules and compatibility
bridge are supplied by `hoch.lims`; they do not require a modification to
official SENAITE Core.

## OOS detection and workflow

The existing OOS implementation contained the content type, catalog,
automatic analysis subscriber, guard adapter, workflow guard functions, and
transition event functions, but the workflow was not connected end to end:

- `escalate_phase2`, `submit_for_review`, and `approve` had permission guards
  but did not invoke SENAITE's `guard_handler`;
- the local OOS event module was not reachable through Core's portal-type
  module dispatcher;
- automatic detection swallowed persistence failures after logging them.

HOCH.LIMS now uses public extension points without modifying or injecting
modules into SENAITE Core:

- the analysis subscriber continues to detect out-of-range results on
  `submit` and `verify`;
- creation is idempotent by analysis UID and snapshots the result, range,
  service, responsible user, detection date, and 30-day due date;
- persistence failures are logged and re-raised instead of silently omitting
  the compliance record;
- the three business transitions use `guard_handler` and therefore exercise
  the existing named OOS guard adapter;
- a dedicated `IAfterTransitionEvent` subscriber dispatches Phase I, Phase II,
  and approval audit effects.

Focused results:

| Focus | Official core `ba57f85e8` | Historical core `e98fb15` |
| --- | ---: | ---: |
| OOS detection | 9 passed | 9 passed |
| OOS guards and events | 15 passed | 15 passed |
| Profile upgrade | 4 passed | 4 passed |

The default profile is now version `1001`. The registered
`1000 -> 1001` GenericSetup upgrade changes only the guard expressions of the
three required transitions. Tests prove that it preserves permission guards,
rejects incomplete installed workflows with an identifying error, and
produces the same configuration when executed a second time.

Complete-suite result:

| Matrix | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Official core `ba57f85e8` | 78 | 0 | 0 | 0 |
| Historical core `e98fb15` plus local patches | 78 | 0 | 0 | 0 |

The matching results establish that OOS detection, workflow validation,
transition auditing, and installed-site migration are owned by `hoch.lims`
and operate without an official Core change.

## Batch and OOS role permissions

The default profile and installed-site upgrade now apply the approved role
matrix consistently:

- Batch close and reopen: `LabManager`, `Manager`;
- Batch release: `LabManager`, `Manager`, `RegulatoryPharmacist`;
- OOS Phase I start, Phase II escalation, and lab-error resolution:
  `Analyst`, `LabManager`, `Manager`;
- OOS cancel and review submission: `LabManager`, `Manager`;
- OOS approval and review rejection: `LabManager`, `Manager`,
  `RegulatoryPharmacist`.

`LabManager` has the same OOS edit access as `Manager` in review and terminal
states. `RegulatoryPharmacist` can perform the review decisions but does not
receive general edit access. The existing business guard still prevents an
investigator from approving their own investigation regardless of role.

The profile is now version `1002`. The registered `1001 -> 1002`
GenericSetup upgrade updates transition roles while preserving guard
permissions, expressions, and groups; updates both OOS edit permissions in
review, closed, and cancelled states; and installs the global OOS transition
permission roles. It rejects incomplete workflow installations and is
idempotent.

Focused command:

```bash
/tmp/hoch-lims-official-core-test \
  -s hoch.lims -t 'test_(role_permissions|upgrades)'
/tmp/hoch-lims-worktree-test \
  -s hoch.lims -t 'test_(role_permissions|upgrades)'
```

Focused result:

| Matrix | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Official core `ba57f85e8` | 20 | 0 | 0 | 0 |
| Historical core `e98fb15` plus local patches | 20 | 0 | 0 | 0 |

This includes nine integration tests that verify effective workflow actions
for each role, including the self-approval prohibition, and eleven upgrade
tests covering versions `1000 -> 1001` and `1001 -> 1002`.

Complete-suite result:

| Matrix | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Official core `ba57f85e8` | 94 | 0 | 0 | 0 |
| Historical core `e98fb15` plus local patches | 94 | 0 | 0 | 0 |

The official Core checkout remains unmodified; the permission policy,
workflow configuration, tests, and installed-site migration are all supplied
by `hoch.lims`.
