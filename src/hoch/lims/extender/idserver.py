from datetime import datetime
from zope import interface
from bika.lims.interfaces import IIdServerVariables
from bika.lims.interfaces import IAnalysisRequest


class IDServerVariablesAdapter(object):
    """An adapter for the generation of Variables for ID Server
    """
    interface.implements(IIdServerVariables)

    def __init__(self, context):
        self.context = context

    def get_variables(self, **kw):
        # The variables map hold the values that might get into the constructed id
        yymm = datetime.now().strftime("%y%m")
        variables = {
            "month": datetime.now().strftime("%m"),
            "yymm": yymm
        }

        # Augment the variables map depending on the portal type
        if IAnalysisRequest.providedBy(self.context):
            batch = self.context.getBatch()
            batch = batch.getClientBatchID() if batch and batch.getClientBatchID() else yymm

            variables.update({
                "batch": batch
            })
            
        return variables