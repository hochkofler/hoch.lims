# -*- coding: utf-8 -*-
"""Compatibility for SENAITE Setup publication-email defaults."""

from bika.lims import api
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.content.senaitesetup import ISetupSchema
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


PUBLICATION_TEMPLATE = ViewPageTemplateFile(
    "templates/email_body_sample_publication.pt")


@provider(IContextAwareDefaultFactory)
def default_email_body_sample_publication(context):
    """Render the publication body without resolving context.laboratory."""
    view = api.get_view("senaite_view", context=api.get_senaite_setup())
    if view is None:
        return u""
    return PUBLICATION_TEMPLATE(view)


def apply_publication_email_default_patch():
    """Attach the compatible factory to Core's existing schema field."""
    field = ISetupSchema["email_body_sample_publication"]
    field.defaultFactory = default_email_body_sample_publication


apply_publication_email_default_patch()
