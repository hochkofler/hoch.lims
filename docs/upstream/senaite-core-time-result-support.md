# SENAITE Core: Time Result Support

## Purpose

Add `time` as a general analysis and interim result type in
`senaite.core/2.x`. This capability is not specific to HOCH.LIMS and belongs
upstream.

## Required core changes

- Add `time` to both legacy Archetypes and modern result-type vocabularies.
- Add `time` to the legacy interim-fields vocabulary.
- Accept `HH:MM` and `HH:MM:SS` in default-result validation.
- Parse standalone time values explicitly. `dtime.to_dt("01:02:03")` resolves
  to midnight in the current stack and must not be used for this purpose.
- Format time-valued analysis results and listing interims with the locale
  time format.
- Render analysis results and interims as `<input type="time" step="1">` in
  the edit-analysis modal.
- Synchronize time-only controls with persisted form fields when no date input
  exists.

## Test requirements

Tests must use independently derived literals:

```text
stored: 01:02:03
default localized display: 01:02
```

Do not calculate the expected value through the same parser under test. The
historical local core test used `dtime.to_dt` for both implementation and
expectation and therefore accepted the incorrect value `00:00`.

Coverage must include:

- legacy AnalysisService result vocabulary;
- modern result vocabulary;
- legacy and modern interim vocabularies;
- `HH:MM` and `HH:MM:SS`;
- invalid values;
- analysis result display;
- interim listing display;
- modal rendering;
- modal submission and persistence.

## HOCH.LIMS extraction

Until the minimum supported official core contains the capability, HOCH.LIMS
provides a compatibility module and a browser-layer modal override. Once the
upstream implementation is available, remove:

- `hoch.lims.patches.time_support`;
- its ZCML monkey patches and vocabulary override;
- `hoch.lims.browser.analysis`;
- the copied modal template and JavaScript.

Keep the HOCH-facing behavioral tests and run them against the new minimum
core before removing the compatibility layer.
