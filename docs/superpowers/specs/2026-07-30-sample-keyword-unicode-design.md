# Sample Keyword Unicode Compatibility

## Context

After the SENAITE Core profile reaches version `2754`, the samples listing
reads `getAnalysesKeywords` from sample catalog metadata and renders each
keyword as a filter chip. Legacy analysis keywords can be UTF-8 byte strings.
Core's `SamplesView.render_keyword_filter_chip` inserts the escaped byte
string into a Unicode HTML template, so Python 2 attempts an ASCII decode and
raises `UnicodeDecodeError`.

The failure occurs in the official Core samples view after catalog lookup. It
is independent of the successful Laboratory migration and of HOCH's sample
listing adapter.

## Decision

Keep `senaite.core` unchanged. Add a narrowly scoped method wrapper in
`hoch.lims` for `SamplesView.render_keyword_filter_chip`.

The wrapper converts the incoming keyword and active keyword collection with
`bika.lims.api.safe_unicode`, then delegates all URL generation, escaping,
translation, CSS, and HTML rendering to the original Core method. This keeps
the patch small and preserves Core behavior for ASCII and already-Unicode
values.

No catalog data is rewritten and no reindex is required.

## Components

- A compatibility function in `hoch.lims.patches` with the same method
  signature as Core's renderer.
- A `collective.monkeypatcher` registration that preserves and delegates to
  the original Core method.
- A regression test using a UTF-8 byte keyword such as
  `CONCENTRACIÓN`, asserting that the rendered chip is Unicode, contains the
  correct visible text, and retains a valid filter URL.

## Verification

Implementation follows a red-green cycle:

1. Add the regression test and confirm the current renderer raises
   `UnicodeDecodeError`.
2. Register the wrapper and confirm the focused test passes.
3. Run the complete `hoch.lims` test suite.
4. Transfer only the tested implementation commit to the shared test
   checkout while preserving the staged `reportview.py` change.
5. Restart all three clients.
6. Request `/test/samples/view/folderitems` through HTTP and confirm it no
   longer returns 500.
7. Confirm no new samples-listing traceback appears in the client logs.

## Rollback

The compatibility change is code-only. Rollback consists of restoring the
previous `hoch.lims` commit and restarting the clients. It does not mutate
catalogs or content.
