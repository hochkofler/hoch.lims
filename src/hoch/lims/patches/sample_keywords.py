# -*- coding: utf-8 -*-

from cgi import escape as html_escape

from bika.lims import _
from bika.lims import api
from senaite.core.i18n import translate as t


def render_keyword_filter_chip(self, keyword, active_keywords):
    """Render cataloged analysis keywords safely as Unicode.

    Legacy catalog metadata can contain UTF-8 byte strings. Normalize the
    renderer inputs and leave all chip behavior to the original Core method.
    """
    keyword = api.safe_unicode(keyword)
    active_keywords = [
        api.safe_unicode(active_keyword)
        for active_keyword in active_keywords
    ]
    href = api.safe_unicode(
        html_escape(self.get_keyword_filter_url(keyword), quote=True))
    if keyword in active_keywords:
        title = t(_("Remove this analysis from the filter"))
        css = "analysis-keyword-filter active"
        style = "text-decoration:none;font-weight:bold"
    else:
        title = t(_("Filter samples by this analysis"))
        css = "analysis-keyword-filter"
        style = "text-decoration:none"
    title = api.safe_unicode(html_escape(api.safe_unicode(title), quote=True))
    return (
        u'<a href="{href}" class="{css}" '
        u'title="{title}" style="{style}">'
        u'<code>{keyword}</code></a>'
    ).format(href=href, css=css, title=title, style=style,
             keyword=api.safe_unicode(html_escape(keyword)))
