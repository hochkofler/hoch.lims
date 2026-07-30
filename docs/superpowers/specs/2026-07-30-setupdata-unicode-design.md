# Setup Data Unicode Compatibility

## Context

The `hoch-prod` branch of `senaite.core` diverges from official Core 2.x by
two effective changes. It converts the `title` value to Unicode while
importing the `Instrument_Types` and `Sample_Conditions` worksheets.

Those changes avoid failures when titles contain UTF-8 characters, but they
do not belong in a maintained Core fork. HOCH.LIMS already overrides Core
setup-data importers through `collective.monkeypatcher` in
`hoch.lims.patches.exportimport`.

## Decision

Keep `senaite.core` at the official commit
`ba57f85e84cea821a5c206d7f90b3ccfcaad43f5`. Move the two Unicode title
normalizations into HOCH.LIMS as targeted overrides of:

- `senaite.core.exportimport.setupdata.Instrument_Types.Import`
- `senaite.core.exportimport.setupdata.Sample_Conditions.Import`

Each replacement retains Core's existing row filtering, containers, portal
types, and description behavior. It changes only the argument passed as
`title`, using `bika.lims.api.safe_unicode(title)`.

## Components

- Two replacement functions in
  `hoch.lims.patches.exportimport.setupdata`.
- Two registrations in
  `hoch.lims.patches.exportimport.configure.zcml`, using
  `ignoreOriginal="True"` as the existing HOCH setup-data patches do.
- Regression tests that pass UTF-8 titles through both importers and assert
  that `api.create` receives Unicode titles and the original descriptions.

## Scope

- Normalize titles only; descriptions are intentionally unchanged.
- Do not modify `senaite.core`.
- Do not change existing product data or run a reindex.
- Keep import behavior unchanged for empty titles: rows without a title are
  skipped.

## Verification

1. Add focused failing tests for both importers with UTF-8 titles.
2. Add the overrides and confirm the focused tests pass.
3. Run the complete HOCH.LIMS suite.
4. Test the overrides from a clean worktree based on `origin/2.x`.

## Rollback

The change only affects future setup-data imports. Removing the two HOCH
override registrations and restarting clients restores official Core import
behavior; no catalog or content rollback is needed.
