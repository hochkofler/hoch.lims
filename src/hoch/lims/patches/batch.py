# -*- coding: utf-8 -*-
"""
Monkey patch for Batch class to add workflow guard methods.

The guard_release_batch method is called via the workflow guard-expression:
    python:here.guard_release_batch()
"""

from Acquisition import aq_base
from Acquisition import aq_inner
from bika.lims import logger
from bika.lims.content.batch import Batch
from hoch.lims.workflow.batch import guards


def guard_release_batch(self):
    """Guard for release transition.

    Called via guard-expression: python:here.guard_release_batch()

    Walks the Acquisition chain to find the real Batch object,
    then validates all conditions for release.

    Returns:
        bool: True if batch can be released
    """
    # Get the real Batch object by walking the Acquisition chain
    # We use portal_type to identify the Batch (not getReleasePublication,
    # which is a schema extender method not present on aq_base)
    batch = self
    current = self
    seen = set()
    while current is not None:
        obj_id = id(aq_base(current))
        if obj_id in seen:
            break
        seen.add(obj_id)
        if getattr(aq_base(current), 'portal_type', None) == 'Batch':
            batch = current
            break
        inner = aq_inner(current)
        if inner is current or inner is None:
            break
        current = inner

    batch_id = batch.getId() if hasattr(aq_base(batch), 'getId') else repr(batch)

    # Safety check: must be a Batch
    if getattr(aq_base(batch), 'portal_type', None) != 'Batch':
        logger.info("guard_release_batch [REJECT] {0}: not a Batch (portal_type={1})".format(
            batch_id, getattr(aq_base(batch), 'portal_type', 'unknown')))
        return False

    return guards.guard_release(batch)


# Monkey patch the Batch class
Batch.guard_release_batch = guard_release_batch
