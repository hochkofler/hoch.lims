# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims import logger
import traceback


def after_release(batch):
    """Actions to perform after batch release
    
    Args:
        batch: Batch object
    """
    try:
        from DateTime import DateTime
        
        # Set release date using direct field access
        # (avoids issues with generated setters from schema extenders)
        release_date = DateTime()
        field = batch.getField('ReleaseDate')
        if field is not None:
            field.set(batch, release_date)
        else:
            logger.warn("ReleaseDate field not found on batch {0}".format(
                batch.getId()))
        
        # Set released by (current user)
        user = api.get_current_user()
        user_id = user.getId() if user else ''
        field = batch.getField('ReleasedBy')
        if field is not None:
            field.set(batch, user_id)
        else:
            logger.warn("ReleasedBy field not found on batch {0}".format(
                batch.getId()))
        
        # Reindex batch
        batch.reindexObject()
        
        logger.info("Batch {0} released by {1}".format(
            batch.getId(), user_id))
    
    except Exception as e:
        logger.error("Error in after_release for batch {0}: {1}".format(
            batch.getId(), str(e)))
        logger.error(traceback.format_exc())
        raise
