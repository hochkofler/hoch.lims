# -*- coding: utf-8 -*-
"""Override of senaite.core's "set_analysis_conditions" modal.

senaite.core renders numeric conditions as ``<input type="number">``
without a ``step`` attribute. Browsers default that to ``step="1"``,
so the HTML5 constraint validation rejects decimal values (e.g. "2.5")
on submit. This subclass only swaps the template for a copy that adds
``step="any"`` to numeric condition inputs; all the view logic is
inherited unchanged from senaite.core.
"""

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.browser.modals.conditions import SetAnalysisConditionsView \
    as BaseSetAnalysisConditionsView


class SetAnalysisConditionsView(BaseSetAnalysisConditionsView):
    """Set analysis conditions modal with fixed numeric input step"""

    template = ViewPageTemplateFile(
        "templates/set_analysis_conditions.pt"
    )
