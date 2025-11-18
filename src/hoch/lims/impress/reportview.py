# -*- coding: utf-8 -*-

from senaite.impress.analysisrequest.reportview import \
    MultiReportView as BaseMultiReportView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile as PT
from bika.lims import api
from senaite.core.api.dtime import to_DT
from hoch.lims.utils import get_formatted_interim

class MultiReportView(BaseMultiReportView):
    """Controller view for multi-reports
    """
    JS_TEMPLATE = PT("templates/js.pt")
    CSS_TEMPLATE = PT("templates/css.pt")
    CONTROLS_TEMPLATE = PT("templates/controls.pt")
    HEADER_TEMPLATE = PT("templates/header.pt")
    INFO_TEMPLATE = PT("templates/info.pt")
    ALERTS_TEMPLATE = PT("templates/alerts.pt")
    SUMMARY_TEMPLATE = PT("templates/summary.pt")
    RESULTS_TEMPLATE = PT("templates/results.pt")
    RESULTS_TRANSPOSED_TEMPLATE = PT("templates/results_transposed.pt")
    INTERPRETATIONS_TEMPLATE = PT("templates/interpretations.pt")
    REMARKS_TEMPLATE = PT("templates/remarks.pt")
    ATTACHMENTS_TEMPLATE = PT("templates/attachments.pt")
    SIGNATURE_TEMPLATE = PT("templates/signatures.pt")
    DISCREETER_TEMPLATE = PT("templates/discreeter.pt")
    FOOTER_TEMPLATE = PT("templates/footer.pt")
    BATCH_DATA_TEMPLATE = PT("templates/batch_data.pt")
    SAMPLE_DATA_TEMPLATE = PT("templates/sample_data.pt")
    INSTRUMENT_DATA_TEMPLATE = PT("templates/instrument_data.pt")
    REFERENCE_SAMPLE_DATA_TEMPLATE = PT("templates/reference_samples_data.pt")
    STERILITY_REPORT_TEMPLATE = PT("templates/sterility_report.pt")
    LAL_REPORT_TEMPLATE = PT("templates/lal_report.pt")
    MICROBIAL_TITRATION_REPORT_TEMPLATE = PT("templates/microbial_titration_report.pt")

    def __init__(self, context, collection, request):
        super(MultiReportView, self).__init__(collection, request)

    @property
    def primary_sample(self):
        """Primary sample of the collection
        """
        if len(self.collection) == 0:
            raise ValueError("No reports in collection!")
        return self.collection[0]
    
    def to_date(self, value):
        """Convert a value to a date string
        """
        return to_DT(value)
    
    def render_template(self, context, template_name, **kw):
        """Render a template with the given context and options
        """
        template = PT("templates/%s.pt" % template_name)
        if template is None:
            raise ValueError("Template '%s' not found!" % template_name)
        return template(context, **kw)
    
    def render_batch_data(self, context, **kw):
        """Render the batch data template with the given context and options
        """
        return self.BATCH_DATA_TEMPLATE(context, **kw)
    
    def render_sample_data(self, context, **kw):
        """Render the sample data template with the given context and options
        """
        return self.SAMPLE_DATA_TEMPLATE(context, **kw)
    
    def render_instrument_data(self, context, **kw):
        """Render the instrument data template with the given context and options
        """
        return self.INSTRUMENT_DATA_TEMPLATE(context, **kw)
    
    def render_reference_sample_data(self, context, **kw):
        """Render the reference sample data template with the given context and options
        """
        return self.REFERENCE_SAMPLE_DATA_TEMPLATE(context, **kw)
    
    def render_sterility_report(self, context, **kw):
        """Render the sterility report template with the given context and options
        """
        return self.STERILITY_REPORT_TEMPLATE(context, **kw)
    
    def render_lal_report(self, context, **kw):
        """Render the lal report template"""
        return self.LAL_REPORT_TEMPLATE(context, **kw)
    
    def render_microbial_titration_report(self, context, **kw):
        """Render microbial titration report"""
        return self.MICROBIAL_TITRATION_REPORT_TEMPLATE(context, **kw)

    def formatted_interim(self, interim, dmk="."):
        return get_formatted_interim(interim, dmk)

    @property
    def decimal_mark(self):
        return self.aq_parent.getDecimalMark()

class SingleReportView(MultiReportView):
    """Controller view for single-reports
    """
    def __init__(self, context, model, request):
        super(SingleReportView, self).__init__(context, [model], request)
