# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims import logger
from hoch.lims.catalog import HOCHLIMS_CATALOG


def _get_field_value(obj, field_name, default=None):
    """Read an extender field without relying on generated accessors."""
    field = obj.getField(field_name)
    if field is None:
        return default
    return field.get(obj)


def guard_release(batch):
    """Validate that batch can be released.
    
    Logs the reason for rejection to help with debugging.
    
    Returns:
        bool: True if batch can be released
    """
    batch_id = batch.getId() if hasattr(batch, 'getId') else repr(batch)
    
    # 1. Must be in closed state
    status = api.get_review_status(batch)
    if status != 'closed':
        logger.info("guard_release [REJECT] Batch {0}: status is '{1}', must be 'closed'".format(
            batch_id, status))
        return False
    
    # 2. Must have a release publication selected
    release_pub = _get_field_value(batch, "ReleasePublication")
    if not release_pub:
        logger.info("guard_release [REJECT] Batch {0}: no ReleasePublication selected".format(
            batch_id))
        return False
    
    # 3. Get batch "release" samples
    batch_samples = batch.getAnalysisRequests()
    release_samples = [s for s in batch_samples
                       if _get_field_value(s, "Destination") == "release"]
    
    if not release_samples:
        logger.info("guard_release [REJECT] Batch {0}: no samples with Destination='release'".format(
            batch_id))
        return False
    
    # 4. Verify publication contains all release samples
    primary = release_pub.getSample()
    contained = release_pub.getContainedSamples() or []
    pub_samples = ([primary] if primary else []) + list(contained)
    pub_sample_uids = set([api.get_uid(s) for s in pub_samples])
    release_sample_uids = set([api.get_uid(s) for s in release_samples])
    
    missing = release_sample_uids - pub_sample_uids
    if missing:
        logger.info("guard_release [REJECT] Batch {0}: publication missing {1} release sample(s)".format(
            batch_id, len(missing)))
        return False
    
    # 5. All non-invalid release samples must be final
    valid_statuses = ["verified", "published"]
    for sample in release_samples:
        sample_status = api.get_review_status(sample)
        if sample_status not in valid_statuses and not sample.isInvalid():
            logger.info("guard_release [REJECT] Batch {0}: sample {1} is '{2}', must be verified or published".format(
                batch_id, sample.getId(), sample_status))
            return False
    
    # 6. All release samples must be in spec
    for sample in release_samples:
        if not is_sample_in_spec(sample):
            logger.info("guard_release [REJECT] Batch {0}: sample {1} is out of specification".format(
                batch_id, sample.getId()))
            return False
    
    # 7. No open OOS investigations for release samples
    for sample in release_samples:
        if _has_open_oos(sample):
            logger.info(
                "guard_release [REJECT] Batch {0}: sample {1} has open "
                "OOS investigation(s)".format(batch_id, sample.getId()))
            return False

    # 8. Publication must be active
    pub_status = api.get_review_status(release_pub)
    if pub_status != 'active':
        logger.info("guard_release [REJECT] Batch {0}: publication status is '{1}', must be 'active'".format(
            batch_id, pub_status))
        return False
    
    logger.info("guard_release [ALLOW] Batch {0}: all conditions met".format(batch_id))
    return True


def is_sample_in_spec(sample):
    """Check if all analyses in sample are within specification.
    
    Returns:
        bool: True if all analyses are in spec
    """
    analyses = sample.getAnalyses(full_objects=True)
    
    for analysis in analyses:
        if api.get_review_status(analysis) != 'verified':
            continue
        if analysis.isOutOfRange():
            logger.warn("Analysis {0} is out of range for sample {1}".format(
                analysis.getId(), sample.getId()))
            return False
    
    return True


def _has_open_oos(sample):
    """Check if sample has any open OOS investigations.

    Returns:
        bool: True if there are open (non-closed/cancelled) OOS investigations
    """
    sample_uid = api.get_uid(sample)
    try:
        catalog = api.get_tool(HOCHLIMS_CATALOG)
        open_oos = catalog(
            portal_type="OOSInvestigation",
            oos_sample_uid=sample_uid,
            review_state=["recorded", "phase1", "phase2", "review"],
        )
        return len(open_oos) > 0
    except Exception:
        # If catalog not available yet, don't block
        return False


def guard_close(batch):
    """Guard for close transition."""
    return api.get_review_status(batch) == 'open'


def guard_reopen(batch):
    """Guard for reopen transition."""
    return api.get_review_status(batch) == 'closed'
