# -*- coding: utf-8 -*-
"""
Monkey patch for Batch class to add workflow guard methods.

The guard_release_batch method is called via the workflow guard-expression:
    python:here.guard_release_batch()
"""

from Acquisition import aq_base
from Acquisition import aq_inner
from bika.lims import api
from bika.lims import logger
from bika.lims.content.batch import Batch


def _get_field_value(obj, field_name, default=None):
    """Safely get a schema extender field value.
    
    Schema extender fields are not on aq_base, so we use getField().
    """
    field = obj.getField(field_name)
    if field is None:
        return default
    return field.get(obj)


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

    # 1. Must be in closed state
    status = api.get_review_status(batch)
    if status != 'closed':
        logger.info("guard_release_batch [REJECT] {0}: status='{1}', need 'closed'".format(
            batch_id, status))
        return False

    # 2. Must have a release publication selected
    # Use getField() to access schema extender fields
    release_pub = _get_field_value(batch, 'ReleasePublication')
    if not release_pub:
        logger.info("guard_release_batch [REJECT] {0}: no ReleasePublication selected".format(
            batch_id))
        return False

    # 3. Get batch "release" samples
    # Destination is also a schema extender field - use getField()
    batch_samples = batch.getAnalysisRequests()
    release_samples = [s for s in batch_samples
                       if _get_field_value(s, 'Destination') == 'release']

    if not release_samples:
        logger.info("guard_release_batch [REJECT] {0}: no samples with Destination='release'".format(
            batch_id))
        return False

    # 4. All release samples must be verified
    valid_status = ['verified', 'published']
    for sample in release_samples:
        sample_status = api.get_review_status(sample)
        if sample_status not in valid_status and not sample.isInvalid():
            logger.info("guard_release_batch [REJECT] {0}: sample {1} is '{2}'".format(
                batch_id, sample.getId(), sample_status))
            return False

    # 5. Publication must contain all release samples
    # ResultsReport uses getSample() for primary and getContainedSamples() for all
    pub_primary = release_pub.getSample()
    metadata = release_pub.getMetadata()
    logger.info("guard_release_batch [INFO] {0}: metadata={1}".format(
        batch_id, metadata))
    pub_contained = release_pub.getContainedSamples() or []
    pub_samples = ([pub_primary] if pub_primary else []) + list(pub_contained)
    pub_uids = set(api.get_uid(s) for s in pub_samples if s)
    release_uids = set(api.get_uid(s) for s in release_samples)
    missing = release_uids - pub_uids
    if missing:
        logger.info("guard_release_batch [REJECT] {0}: publication missing {1} samples".format(
            batch_id, len(missing)))
        logger.info("pub samples {0}, release samples {1}".format(pub_samples, release_samples))
        return False

    # 6. Publication must be active
    pub_status = api.get_review_status(release_pub)
    if pub_status != 'active':
        logger.info("guard_release_batch [REJECT] {0}: publication status='{1}'".format(
            batch_id, pub_status))
        return False

    logger.info("guard_release_batch [ALLOW] {0}: all conditions met".format(batch_id))
    return True


# Monkey patch the Batch class
Batch.guard_release_batch = guard_release_batch
