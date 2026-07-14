# -*- coding: utf-8 -*-
from bika.lims import api
from plone.indexer import indexer
from hoch.lims.interfaces import IOOSInvestigation


@indexer(IOOSInvestigation)
def oos_analysis_uid(instance):
    return instance.getAnalysisUid() or ""


@indexer(IOOSInvestigation)
def oos_sample_uid(instance):
    """Computed index: navigates from analysis to sample"""
    analysis = instance.getAnalysis()
    if analysis:
        sample = analysis.getRequest()
        if sample:
            return api.get_uid(sample)
    return ""


@indexer(IOOSInvestigation)
def oos_batch_uid(instance):
    """Computed index: navigates from analysis to sample to batch"""
    analysis = instance.getAnalysis()
    if analysis:
        sample = analysis.getRequest()
        if sample:
            batch = sample.getBatch() if hasattr(sample, "getBatch") else None
            if batch:
                return api.get_uid(batch)
    return ""


@indexer(IOOSInvestigation)
def oos_category(instance):
    return instance.getOosCategory() or ""


@indexer(IOOSInvestigation)
def oos_detection_date(instance):
    return instance.getDetectionDate() or None


@indexer(IOOSInvestigation)
def oos_due_date(instance):
    return instance.getDueDate() or None


@indexer(IOOSInvestigation)
def oos_disposition(instance):
    return instance.getDisposition() or ""


@indexer(IOOSInvestigation)
def oos_investigation_phase(instance):
    return instance.getInvestigationPhase() or ""
