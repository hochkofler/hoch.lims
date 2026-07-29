# HOCH LIMS Adaptation to Official SENAITE Core 2.x

## Purpose

Adapt the existing `hoch.lims` addon to the official `senaite.core/2.x`
branch while preserving its current data models and functional behavior.

Reengineering `hoch.lims` and introducing new domain models are explicitly
outside this project's scope. They will be evaluated only after the addon
works against a clean official core and has sufficient regression coverage.

## Safety and isolation

- All implementation takes place in the dedicated worktree
  `/home/lims/hochlims/worktrees/hoch-lims-senaite-baseline`.
- The implementation branch is `upgrade/senaite-core-2x-official`, created
  from `origin/2.x` at `664b2956228ffa94615c99ce0dcea499fdbb2c67`.
- The existing local `MultiReportView.getContactByUsername` change remains
  outside the adaptation branch until a characterization test proves it is
  required.
- `senaite.core` must remain clean. No addon behavior may be implemented by
  editing core files.
- Changes return to the shared test base only after they pass the worktree
  verification gates.
- A GitHub PR is created only after the shared test base also passes.

## Delivery strategy

The project is divided into independently verifiable phases. Each phase ends
with tests and a reviewable commit boundary.

### Phase 1: reproducible green baseline

1. Fix discovery of all five vocabulary tests under `zc.testrunner`.
2. Diagnose and correct the `Could not install product senaite.jsonapi`
   failure in the test layer.
3. Record the exact repository SHAs and effective dependency matrix.
4. Preserve existing behavior; do not change production functionality.

Exit conditions:

- `/home/lims/hochlims/bin/test -s hoch.lims` returns exit code `0`;
- all intended test modules and test cases execute;
- the test setup does not report a failed `senaite.jsonapi` installation;
- the dependency matrix is documented and reproducible.

### Phase 2: characterization coverage

Add regression tests before modifying each critical subsystem:

1. calculations and interims;
2. result types, including `time`;
3. consumables and subinstruments;
4. Batch close, reopen, and release;
5. OOS detection and workflow;
6. role-based permissions;
7. catalogs, mappings, indexes, and searches;
8. worksheets and listings;
9. Shimadzu/Nexera imports;
10. setup import/export;
11. critical Impress reports.

Tests must assert externally observable behavior and persisted data, not
implementation details of existing monkey patches.

### Phase 3: official core switch

1. Pin the official `senaite.core/2.x` SHA selected for validation.
2. Pin compatible SHAs for `senaite.lims`, listing, spotlight, supermodel,
   impress, and jsonapi.
3. Build without reusing production `parts`, `develop-eggs`, or generated
   artifacts.
4. Run the characterization suite and classify every regression by subsystem.

The Unicode `get_link` correction already present upstream is not copied into
the addon.

### Phase 4: addon-only compatibility

Adapt subsystems in this order:

1. moved imports, interfaces, and public utilities;
2. test layers and registrations;
3. catalogs, indexers, and mappings;
4. contents, extenders, and behaviors;
5. analysis datamanager, calculations, and interims;
6. `time` results implemented entirely in `hoch.lims`;
7. samples, batches, workflows, worksheets, and listings;
8. setup import/export and Nexera;
9. Impress reports;
10. OOS.

For each integration:

- prefer a public adapter, subscriber, view, behavior, datamanager, or
  documented hook;
- encapsulate private compatibility APIs when no public alternative exists;
- do not copy a core method wholesale unless characterization demonstrates
  there is no smaller extension point;
- stop and redesign if implementation appears to require modifying core.

### Phase 5: versioned upgrades

`hoch.lims` will use Plone GenericSetup upgrade steps before any persistent
catalog, workflow, permission, content, or data change is introduced.

The installed profile currently uses version `1000`. New transitions will be
linear and explicit, for example:

```text
1000 -> 1001  establish official-core compatibility
1001 -> 1002  migrate time-result configuration
1002 -> 1003  update workflows and permissions
1003 -> 1004  update catalog mappings and indexes
```

The exact boundaries are determined by the implementation commits. Each step
must:

- have one coherent migration responsibility;
- be idempotent;
- check for existing objects, indexes, mappings, roles, and configuration;
- process large object sets in bounded batches;
- log progress and a useful failure location;
- avoid profile reinstallation as a migration mechanism;
- have tests for the first run and a second no-op run.

Upgrade order in an environment is:

```text
backup
-> official SENAITE component upgrades
-> hoch.lims upgrades
-> catalog and relationship reconciliation
-> functional acceptance
-> restart and repeated verification
```

## Data compatibility

The adaptation preserves current portal types, UIDs, identifiers, relations,
workflow histories, permissions, and audit data wherever upstream migrations
allow it.

No model migration is introduced solely for code cleanliness. If official
SENAITE migrations convert a dependency from Archetypes to Dexterity,
`hoch.lims` adapters and extenders are updated around the official migration
and verified against representative data.

## Error handling and recoverability

- Upgrade handlers fail loudly rather than silently skipping required work.
- Batch migrations record progress and permit safe restart.
- No material migration runs without a verified backup.
- A failed acceptance run is recovered by restoring the test database, not by
  attempting ad-hoc reverse mutations.
- The production procedure includes explicit rollback and restore evidence.

## Testing gates

Every behavior change follows red-green-refactor:

1. add a failing characterization or regression test;
2. confirm it fails for the intended reason;
3. implement the minimum addon-only change;
4. run the focused test;
5. run the complete `hoch.lims` suite;
6. run relevant SENAITE suites;
7. inspect `senaite.core` and confirm it is clean.

Migration acceptance also verifies:

- the second upgrade run performs no destructive or duplicate work;
- object and catalog counts reconcile;
- UIDs and relations remain valid;
- workflows and permissions work by role;
- critical instrument imports and reports match expected outputs;
- backup and restore complete successfully.

## Deliverables

- one reviewable `hoch.lims` adaptation branch;
- pinned component matrix;
- repaired and expanded test suite;
- addon-only implementation of required custom behavior;
- GenericSetup upgrade chain and upgrade tests;
- representative database migration evidence;
- validation and rollback documentation;
- no changes to `senaite.core`.

