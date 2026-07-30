# Laboratory Dexterity Migration Compatibility

## Context

The official `senaite.core` upgrade step `2730 -> 2731` migrates the
Archetypes Laboratory object to Dexterity. While the new object is inserted,
`plone.app.linkintegrity` inspects the modified SENAITE Setup object and reads
its `email_body_sample_publication` RichText field.

When that field has no stored value, the Core default factory renders
`email_body_sample_publication.pt`. The template evaluates the unused
expression `context.laboratory`. Its rendering context is a
`RequestContainer`, which does not expose that attribute, so the upgrade is
aborted with `AttributeError`.

The effective Dexterity FTI registrations for `Laboratory` and `Setup` were
verified and point to their correct Core schemas. No `hoch.lims` module
participates in the failing traceback.

## Decision

Keep `senaite.core` unchanged at the official `2.x` commit. Add a narrowly
scoped compatibility patch in `hoch.lims` that replaces only
`default_email_body_sample_publication` with an equivalent factory backed by
a local template that omits the invalid and unused `context.laboratory`
expression.

The replacement preserves the existing email markup, translation domain, and
reserved publication variables. It does not alter stored Setup values,
Laboratory data, the migration implementation, or any other Core defaults.

## Components

- A local publication-email template containing the same functional content
  as Core without the unused Laboratory lookup.
- A replacement context-aware default factory in the existing
  `hoch.lims.patches` package.
- ZCML registration using the add-on's established monkey-patch mechanism.
- A regression test that reads the default value through the real Setup
  Dexterity schema and proves it renders without raising an exception.

## Verification

Implementation follows a red-green cycle:

1. Add the regression test and confirm it fails with the current Core factory.
2. Add the minimal compatibility factory and template.
3. Confirm the focused test and the complete `hoch.lims` suite pass.
4. Deploy the isolated branch to the test buildout and restart all clients.
5. Execute only Core upgrade step `2730 -> 2731`.
6. Verify the registered profile version is `2731`, `setup/laboratory` is
   Dexterity, migrated Laboratory values remain present, and no migration
   traceback was logged.

The subsequent Core repair step `2731 -> 2732` remains separate and will only
be run after these checks pass.

## Rollback

If application verification fails, stop the clients, restore the deployed
add-on checkout to the prior commit, restart the clients, and leave the Core
profile at `2730`. A failed upgrade request is transactional and must not be
treated as successful unless the profile version and migrated object are both
verified.
