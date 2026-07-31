# LabClerk global worksheet permissions

## Problem

The `1003` upgrade grants `LabClerk` the worksheet add, edit, and manage
permissions on the `worksheets` folder. SENAITE's Samples view uses a
different authorization context when it builds the collective “Create
Worksheet” action: `SamplesView.can_create_worksheet()` checks `Add Worksheet`
on the portal root.

Production evidence shows that `fzabala` has all three permissions on
`worksheets`, but not on the portal root. Consequently, the worksheet-folder
controls are authorized while the collective action in the Samples view is
hidden.

## Required behavior

`LabClerk` must have `Add Worksheet`, `Edit Worksheet`, and
`Manage Worksheets` on both the portal root and the `worksheets` folder.
Existing selected roles must be preserved in both contexts. A LabClerk viewing
eligible received samples with unassigned analyses must see the collective
“Create Worksheet” action.

## Design

The existing `synchronize_worksheet_permissions(portal=None)` function will
iterate over two permission contexts: the portal root and
`portal.worksheets`. For each of the three worksheet permissions, it will
retain every selected role and add only `LabClerk`. The worksheet folder will
continue to be reindexed; the portal root does not require reindexing for
authorization.

The runtime decorator will keep calling the same synchronization function
after SENAITE recalculates its worksheet permissions. Profile setup will also
continue calling it, so both contexts remain consistent after configuration
changes and profile imports.

Because deployed sites are already registered at profile version `1003`, a
new idempotent GenericSetup upgrade `1003 -> 1004` will execute the expanded
synchronizer. The default profile version will become `1004`; `v1003` will
not be modified retroactively.

## Testing

Tests will be written before production changes and will demonstrate that:

- all three permissions gain `LabClerk` on the portal root and folder;
- existing roles remain selected in both contexts;
- repeated synchronization is idempotent;
- the Samples view authorization becomes true for an eligible LabClerk;
- the `1004` upgrade repairs a site at `1003`; and
- the installed-site integration test verifies both authorization contexts.

The focused regression tests and the complete `hoch.lims` suite will run
after the implementation.

## Deployment

Deploy the updated `2.x` package, restart all Zope clients, and run the
pending `hoch.lims` upgrade on each site. Production must report profile
version `1004`, with `LabClerk` selected for the three permissions on both
the portal root and `worksheets`.
