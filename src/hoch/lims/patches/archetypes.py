# -*- coding: utf-8 -*-
"""Patch Products.Archetypes.utils.Vocabulary.getValue to accept AT objects.

When a PicklistWidget renders a UIDReferenceField in view mode, AT calls
accessor() which returns Acquisition-wrapped objects, then passes them to
Vocabulary.getValue() as lookup keys.  The original implementation raises
TypeError for non-string/int keys.

This patch extracts the UID from any AT object before the lookup so the
display value is resolved correctly, without changing field.get() behaviour
or touching any jsonapi or schema extender code.
"""
from Products.Archetypes.utils import Vocabulary

_orig_getValue = Vocabulary.getValue


def _getValue(self, key, default=None):
    if not isinstance(key, (basestring, int)):
        try:
            key = key.UID()
        except AttributeError:
            return default
    return _orig_getValue(self, key, default)


Vocabulary.getValue = _getValue
