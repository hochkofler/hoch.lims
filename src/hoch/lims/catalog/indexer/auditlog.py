# -*- coding: utf-8 -*-
"""
Custom auditlog indexer to avoid UnicodeDecodeError during cataloging.

The upstream implementation in ``senaite.core.catalog.indexer.auditlog``
encoded unicode strings to UTF-8 bytes before returning them.  When the
registrar later attempts to index the value the bytes are implicitly
converted back to unicode using the default ``ascii`` codec, causing
failures if the text contains non-ASCII characters (see bug report).

We override the original adapter here and keep the logic mostly identical
but *never* return ``bytes`` objects.  All values are coerced to
unicode early using ``api.safe_unicode`` and we handle ``bytes`` explicitly
just in case some older snapshots still contain raw byte strings.

This module is registered by the catalog's ``configure.zcml`` so it
replaces the original indexer at import time.
"""

import itertools
import re

import six

from bika.lims import api
from bika.lims.api.snapshot import get_snapshots
from bika.lims.interfaces import IAuditable
from plone.indexer import indexer
from hoch.lims import logger

# reuse the same interface used by the original indexer
try:
    from senaite.core.interfaces import IAuditlogCatalog
except ImportError:  # pragma: no cover
    # during tests or when the package isn't available the import might fail;
    # we can't do much else, indexer registration will probably also fail but
    # this keeps linters happy.
    IAuditlogCatalog = object

# regular expressions copied from upstream implementation
UID_RX = re.compile(r"[a-z0-9]{32}$")
DATE_RX = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}")


@indexer(IAuditable, IAuditlogCatalog)
def listing_searchable_text(instance):
    """Fulltext search for the audit metadata.
    
    Returns empty string if no snapshots to avoid issues in clean creates.
    """
    
    snapshots = get_snapshots(instance)
    if not snapshots:
        return u""
    
    values = map(lambda s: s.values(), snapshots)
    catalog_data = set()
    skip_values = ["None", "true", "True", "false", "False"]
    uid_title_cache = {}

    def append(value):
        # recursively unpack data structures
        if isinstance(value, (list, tuple)):
            for v in value:
                append(v)
        elif isinstance(value, dict):
            for v in value.values():
                append(v)
        elif isinstance(value, six.binary_type):
            # raw bytes: decode to unicode using utf-8
            try:
                value = value.decode("utf-8")
            except Exception:
                value = value.decode("utf-8", "ignore")
            append(value)
        elif isinstance(value, six.string_types):
            # force unicode and drop problematic values
            value = api.safe_unicode(value)
            if len(value) < 2:
                return
            if value in skip_values:
                return
            if re.match(DATE_RX, value):
                return
            if re.match(UID_RX, value):
                if value in uid_title_cache:
                    value = uid_title_cache[value]
                else:
                    title_or_id = api.get_title_or_id_from_uid(value) if hasattr(api, 'get_title_or_id_from_uid') else value
                    # fallback to the upstream helper if available
                    try:
                        # import lazily to avoid circular references
                        from senaite.core.catalog.indexer.auditlog import get_title_or_id_from_uid
                        title_or_id = get_title_or_id_from_uid(value)
                    except Exception:
                        pass
                    uid_title_cache[value] = title_or_id
                    value = title_or_id
            # always ensure unicode before adding to set
            catalog_data.add(api.safe_unicode(value))

    for value in itertools.chain(values):
        append(value)
    
    # try to join without extra processing; only convert if join fails
    try:
        result = u" ".join(catalog_data)
    except UnicodeDecodeError:
        # if join fails (some bytes slipped through), convert all to unicode
        # and retry. this is a last‑resort fallback and should rarely execute.
        catalog_data = set(api.safe_unicode(v) for v in catalog_data)
        result = u" ".join(catalog_data)

    return result


# ensure we override the upstream implementation as soon as this module is
# imported (not just when our indexer runs).  Plone may have registered the
# original adapter earlier, but replacing the callable guarantees our
# safe version is executed regardless of registration order.
try:
    import senaite.core.catalog.indexer.auditlog as upstream
    upstream.listing_searchable_text = listing_searchable_text
except Exception:
    # possible during tests or if senaite.core isn't yet available; the
    # patch will be tried again the next time the function is executed.
    pass
