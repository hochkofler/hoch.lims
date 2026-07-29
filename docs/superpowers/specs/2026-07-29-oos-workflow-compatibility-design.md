# OOS Workflow Compatibility Design

## Purpose

Make the existing HOCH.LIMS Out of Specification (OOS) functionality
operational end to end on official `senaite.core/2.x`. The change covers
automatic detection, duplicate prevention, workflow guards, transition side
effects, and upgrades for existing installations.

This work preserves the existing `OOSInvestigation` Dexterity model, portal
type, identifiers, relations, workflow states, permissions, and audit data.
Model redesign and data migration are outside this block.

## Constraints

- All changes belong to `hoch.lims`; official SENAITE Core remains unchanged.
- Implementation remains on branch `upgrade/senaite-core-2x-official` in the
  isolated worktree.
- Python 2.7.18 and Plone 5.2.15 remain supported.
- New installations and upgrades from profile version `1000` must produce the
  same workflow configuration.
- The upgrade must be idempotent and preserve existing workflow history,
  permissions, states, transitions, and OOS content.
- No push, shared-base deployment, or pull request is part of this block.

## Existing Problem

HOCH.LIMS already contains:

- an analysis transition subscriber that detects out-of-range results;
- the `OOSInvestigation` content type and catalog indexes;
- an OOS guard adapter and guard functions;
- OOS workflow event functions;
- an `oos_investigation_workflow` definition.

The parts are not fully connected:

1. The OOS workflow transitions only declare permission guards. They do not
   call SENAITE's `guard_handler`, so the registered adapter and its validation
   functions do not participate in transitions.
2. The OOS event functions are not reachable through SENAITE Core's dynamic
   workflow event module loader because the portal type and local module paths
   do not match.
3. The detection subscriber catches every creation exception and returns,
   which can hide a failed compliance record while the analysis transition
   succeeds.

## Architecture

Use supported component and workflow extension points rather than injecting
HOCH modules into the `bika.lims.workflow` namespace.

The existing analysis subscriber remains responsible for OOS detection. A
new OOS transition subscriber dispatches supported transition IDs to the
existing event functions. Workflow guard expressions invoke SENAITE's public
`guard_handler`, which discovers the named HOCH guard adapter.

The default GenericSetup profile defines the desired state for new sites. A
linear `1000 -> 1001` upgrade applies only the required guard expressions to
existing workflows.

## Automatic Detection

`on_analysis_transition(analysis, event)` observes routine analysis
transitions.

- It ignores events without a transition.
- It reacts only to `submit` and `verify`.
- It calls SENAITE's range API and stops when the result is in specification.
- It requires the `OOSInvestigations` folder before attempting creation.
- It queries `hochlims_catalog` using the analysis UID and does not create a
  second investigation when one already exists.
- It creates one `OOSInvestigation` and snapshots:
  - analysis UID;
  - detection date;
  - due date, 30 calendar days after detection;
  - result value;
  - minimum and maximum specification range;
  - analysis service title;
  - responsible user ID.
- It reindexes the new investigation after the snapshot is populated.

Missing optional display values become empty strings. A missing OOS folder is
logged and does not create a partial object. Creation or persistence failures
are logged with context and re-raised so the analysis transition cannot
silently complete without the required OOS record.

Duplicate prevention is by analysis UID across all OOS states. A closed or
cancelled investigation still records that analysis occurrence and therefore
prevents a duplicate record for the same analysis.

## Workflow Guards

The following transitions use
`python:here.guard_handler("<transition_id>")`:

- `escalate_phase2`;
- `submit_for_review`;
- `approve`.

The existing `OOSInvestigationGuardAdapter` remains the single adapter entry
point. Unknown transition IDs return `True`, allowing DCWorkflow's permission
and state checks to decide them.

The canonical guard rules are:

- Phase II escalation requires a non-empty Phase I summary.
- Submission for QA review requires a conclusion, disposition, and OOS
  category.
- Approval is rejected when the current user is the recorded investigator.
  Approval remains possible when no investigator has been assigned because
  this preserves current behavior; assignment policy is outside this block.

No additional business rules are introduced for `start_phase1`,
`resolve_lab_error`, `cancel`, or `reject_review`.

## Transition Events

A subscriber for `IOOSInvestigation` and `IAfterTransitionEvent` dispatches
only these transitions:

- `start_phase1` calls `after_start_phase1`;
- `escalate_phase2` calls `after_escalate_phase2`;
- `approve` calls `after_approve`.

Events without a transition and unrelated transitions are ignored.

The effects remain:

- Phase I start records `investigation_start_date`, sets
  `investigation_phase` to `phase_1`, and reindexes.
- Phase II escalation records `phase2_start_date`, sets
  `investigation_phase` to `phase_2`, and reindexes.
- Approval records `completion_date`, records the current user ID as reviewer,
  and reindexes.

The event functions store values through the existing Dexterity attributes.
They do not alter workflow state directly; DCWorkflow owns state transitions.

## Versioned Upgrade

The default profile version advances from `1000` to `1001`.

The package registers a GenericSetup upgrade step with:

- source version `1000`;
- destination version `1001`;
- one handler dedicated to OOS workflow guard compatibility.

The handler obtains `oos_investigation_workflow`, verifies that each required
transition exists, and sets its guard expression while preserving its existing
permission and role guards. Missing workflow or transition configuration is a
hard failure with a useful identifier; silently skipping it could leave a
site non-compliant.

Running the handler a second time produces the same configuration without
adding states, transitions, permissions, or content.

## Error Handling

- Detection failures that would omit an OOS record are re-raised after
  contextual logging.
- Missing optional snapshot values do not abort detection.
- Unknown workflow transitions are ignored by the event dispatcher.
- Upgrade failures identify the missing workflow or transition and stop the
  upgrade.
- No broad exception handling is added around workflow guards or transition
  events.

## Testing

All behavior changes follow red-green-refactor.

Unit characterization covers:

- transition filtering;
- in-spec results;
- successful snapshot creation;
- duplicate prevention across OOS states;
- missing OOS folder;
- creation failures being re-raised;
- every guard acceptance and rejection condition;
- adapter delegation and unknown transitions;
- each event side effect;
- event filtering.

Integration coverage verifies:

- the workflow profile contains the three `guard_handler` expressions;
- the registered adapter is exercised through SENAITE's guard handler;
- the `1000 -> 1001` upgrade preserves permission guards while installing the
  expressions;
- a second upgrade-handler execution is a no-op;
- the OOS event subscriber is registered.

Verification gates:

1. focused OOS tests against official Core;
2. focused OOS tests against the historical Core checkout;
3. complete `hoch.lims` suite against official Core;
4. complete `hoch.lims` suite against historical Core;
5. clean official Core checkout and unchanged shared checkouts;
6. validation matrix updated with exact counts and SHAs.

## Acceptance Criteria

- An out-of-range submitted or verified routine analysis creates exactly one
  populated OOS investigation.
- Failure to create that investigation is visible to the caller.
- OOS business guards participate in real workflow evaluation.
- Transition audit fields are persisted and indexed.
- New and upgraded sites receive equivalent workflow guard configuration.
- Re-running the upgrade is safe.
- Both supported Core matrices pass all focused and complete tests.
