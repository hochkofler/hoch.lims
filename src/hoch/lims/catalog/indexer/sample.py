from plone.indexer import indexer
from bika.lims.interfaces import IAnalysisRequest
from hoch.lims import logger

@indexer(IAnalysisRequest)
def sample_destination(instance):
    """Indexer for sample destination (extender field)
    """
    field = instance.Schema().getField("Destination")
    if not field:
        return None
    return field.get(instance)
