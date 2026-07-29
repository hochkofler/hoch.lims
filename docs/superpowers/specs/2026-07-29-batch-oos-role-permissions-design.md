# Batch and OOS Role Permissions Design

## Purpose

Define and enforce a testable role matrix for pharmaceutical Batch and OOS
workflow actions in HOCH.LIMS on official `senaite.core/2.x`.

The design preserves existing portal types, workflow states, permission IDs,
histories, content, and business guards. It adds transition-level role
restrictions where the existing global permissions are too broad.

## Constraints

- `LabManager` has the same operational authority as `Manager` throughout
  Batch and OOS workflows.
- `RegulatoryPharmacist` retains Batch release authority and participates in
  OOS review actions.
- `Analyst` participates only in the laboratory investigation stage.
- Existing data-validation guards remain mandatory in addition to role
  authorization.
- An investigator cannot approve their own OOS investigation regardless of
  role.
- No new permission IDs or content models are introduced.
- Official SENAITE Core remains unchanged.
- New and upgraded sites must receive equivalent authorization.

## Existing Problem

The root role map grants:

- Batch release to `Manager`, `LabManager`, and `RegulatoryPharmacist`;
- all OOS transitions to `Manager`, `LabManager`, and
  `RegulatoryPharmacist`.

The OOS workflow currently uses the same transition permission for every
action. This makes it impossible to express that an `Analyst` can advance the
laboratory phase while a `RegulatoryPharmacist` participates only in review
actions. `Analyst` must first receive the shared transition permission; the
per-transition role guards then restrict that permission to the three
laboratory-stage actions.

OOS state permissions already distinguish editing stages, but no automated
tests prove the effective transition or edit authorization for each role.

## Architecture

Use DCWorkflow transition role guards for action-specific authorization.
Permission guards and business guard expressions remain in place, so a
transition is allowed only when all configured layers agree:

```text
workflow state
and permission guard
and transition role guard
and business guard expression
```

The default workflow profiles define the desired state for new sites. A
linear GenericSetup upgrade from `1001` to `1002` applies only role guards to
existing workflows and preserves guard permissions and expressions.

## Batch Role Matrix

| Action | Analyst | LabManager | Manager | RegulatoryPharmacist |
| --- | --- | --- | --- | --- |
| View Batch | Yes | Yes | Yes | Yes |
| Modify open Batch | No | Yes | Yes | No |
| Close Batch | No | Yes | Yes | No |
| Reopen Batch | No | Yes | Yes | No |
| Release Batch | No | Yes | Yes | Yes |

`LabManager` retains `hoch.lims: Release Batch`. The root role map therefore
does not change.

The release transition continues to require both:

- `hoch.lims: Release Batch`;
- the canonical Batch release guard that validates state, publication,
  samples, specifications, and open OOS investigations.

## OOS Transition Matrix

| Transition | Analyst | LabManager | Manager | RegulatoryPharmacist |
| --- | --- | --- | --- | --- |
| `start_phase1` | Yes | Yes | Yes | No |
| `escalate_phase2` | Yes | Yes | Yes | No |
| `resolve_lab_error` | Yes | Yes | Yes | No |
| `cancel` | No | Yes | Yes | No |
| `submit_for_review` | No | Yes | Yes | No |
| `approve` | No | Yes | Yes | Yes |
| `reject_review` | No | Yes | Yes | Yes |

`LabManager` and `Manager` are equivalent in every OOS transition.

The existing business guards remain authoritative:

- escalation requires the Phase I summary;
- review submission requires conclusion, disposition, and OOS category;
- approval rejects the recorded investigator as current reviewer.

Possessing an allowed role does not bypass these requirements.

## OOS Edit and View Matrix

All authenticated users retain the existing view permission in every OOS
state.

| State | Analyst edit | LabManager edit | Manager edit | RegulatoryPharmacist edit |
| --- | --- | --- | --- | --- |
| `recorded` | Yes | Yes | Yes | No |
| `phase1` | Yes | Yes | Yes | No |
| `phase2` | No | Yes | Yes | No |
| `review` | No | Yes | Yes | No |
| `closed` | No | Yes | Yes | No |
| `cancelled` | No | Yes | Yes | No |

This makes `LabManager` equivalent to `Manager` as requested. A
`RegulatoryPharmacist` can approve or reject through workflow transitions but
does not receive general content-edit permission.

Both `Modify portal content` and
`hoch.lims: Edit OOSInvestigation` must reflect this matrix. Transition
permissions do not implicitly grant edit access.

## Profile Configuration

Each Batch and OOS transition receives explicit `<guard-role>` entries for
the roles allowed by the matrices.

The root role map for `hoch.lims: Transition OOSInvestigation` includes
`Analyst`, `LabManager`, `Manager`, and `RegulatoryPharmacist`. This shared
permission is necessary for the permission guard; transition role guards
provide the action-specific restriction.

Existing elements are preserved:

- permission guards;
- guard expressions;
- transition destinations;
- action metadata;
- workflow state permissions.

OOS state permission maps are changed only where needed to make
`LabManager` equivalent to `Manager` in `review`, `closed`, and `cancelled`.
No workflow state or transition is added or removed.

## Versioned Upgrade

The default profile version advances from `1001` to `1002`.

The `1001 -> 1002` upgrade:

1. obtains `hoch_batch_workflow` and `oos_investigation_workflow`;
2. verifies every governed transition and state exists;
3. assigns the exact role tuple for each transition while preserving its
   permission, group, and expression guards;
4. updates the two OOS edit permission maps in `review`, `closed`, and
   `cancelled` to include both `LabManager` and `Manager`;
5. adds `Analyst` to the portal-level OOS transition permission while
   retaining `LabManager`, `Manager`, and `RegulatoryPharmacist`;
6. leaves the Batch release permission role map unchanged;
7. logs the applied authorization matrix.

Missing workflow, transition, state, or managed permission configuration is a
hard failure containing the missing identifier.

Running the handler a second time produces the same roles and permission maps
without adding workflow objects or changing histories or content.

## Testing

All changes follow red-green-refactor.

Profile characterization verifies:

- exact role guards for every Batch and OOS transition;
- preservation of permission guards and business expressions;
- exact OOS edit permission maps for each state;
- root `Release Batch` permission still includes `LabManager`, `Manager`, and
  `RegulatoryPharmacist`.
- root `Transition OOSInvestigation` permission includes `Analyst`,
  `LabManager`, `Manager`, and `RegulatoryPharmacist`.

Effective authorization tests use real installed workflows and users assigned
one role at a time. They verify positive and negative transition availability
for `Analyst`, `LabManager`, `Manager`, and `RegulatoryPharmacist`.

Composition tests prove:

- a permitted role is still rejected when a Batch or OOS business guard
  fails;
- an investigator with `LabManager`, `Manager`, or
  `RegulatoryPharmacist` cannot approve their own investigation;
- a different allowed reviewer can approve.

Upgrade tests verify:

- exact role assignment;
- preservation of existing permission and expression guards;
- edit-map updates;
- useful failures for incomplete workflows;
- identical state after a second execution.

Both focused and complete suites run against official and historical Core.

## Acceptance Criteria

- `LabManager` can perform every Batch and OOS action available to `Manager`.
- `LabManager` retains Batch release authority.
- `Analyst` can conduct Phase I but cannot submit for review or review OOS.
- `RegulatoryPharmacist` can release Batch and review OOS without receiving
  general OOS edit access.
- Business guards cannot be bypassed by role membership.
- Self-approval remains prohibited.
- New and upgraded sites enforce the same matrices.
- The `1001 -> 1002` upgrade is safe to repeat.
- Both Core matrices pass focused and complete verification.
