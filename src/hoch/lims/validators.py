# -*- coding: utf-8 -*-
import re
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import to_utf8
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.validation import validation
from Products.validation.interfaces.IValidator import IValidator
from zope.interface import implements
from Products.Archetypes import DisplayList
from hoch.lims.interfaces import IVariablesSettingsVocabularyProvider
from bika.lims import api
from zope.component import queryAdapter

class VariablesSettingsFieldsValidator:
    """Validating VariablesSettingsField keywords.
        Applied as a subfield validator but validates entire field.
        keyword must match isUnixLikeName
        keyword must be unique in this VariablesSettingsField field
    """

    implements(IValidator)
    name = "VariablesSettingsFieldsValidator"

    def __call__(self, value, *args, **kwargs):
        instance = kwargs['instance']
        fieldname = kwargs['field'].getName()
        # do not rely on kwargs's REQUEST, cause it might be None!
        request = instance.REQUEST
        form = request.form
        variables_fields = form.get(fieldname, [])
        context = api.get_object(instance)
        translate = getToolByName(instance, 'translation_service').translate
        
        provider = queryAdapter(context, IVariablesSettingsVocabularyProvider)
        if provider:
            vocab = provider.getVocabulary()
            
        else:
            msg = _("not provider data, the context are: '%s'", context)
            instance.REQUEST[key] = msg
            return instance.REQUEST[key]
            # Fallback: intenta el método local del campo



        # We run through the validator once per form submit, and check all
        # values
        # this value in request prevents running once per subfield value.
        key = instance.id + fieldname
        if request.get(key, False):
            return True


        keywords_options = vocab
        if not keywords_options:
            instance.REQUEST[key] = to_utf8(
                translate(_("Validation failed: no keywords defined")))
            return instance.REQUEST[key]
        
        if not isinstance(keywords_options, DisplayList):
            instance.REQUEST[key] = to_utf8(
                translate(_("Validation failed: invalid keywords definition")))
            return instance.REQUEST[key]
        
        valid_keywords = [k[0] for k in keywords_options.items()]
        
        for x in range(len(variables_fields)):
            row = variables_fields[x]
            keys = row.keys()
            if 'keyword' not in keys:
                instance.REQUEST[key] = to_utf8(
                    translate(_("Validation failed: keyword is required")))
                return instance.REQUEST[key]
            if not re.match(r"^[A-Za-z\w\d\-\_]+$", row['keyword']):
                instance.REQUEST[key] = _(
                    "Validation failed: keyword contains invalid characters")
                return instance.REQUEST[key]
            
            if row['keyword'] not in valid_keywords:
                instance.REQUEST[key] = to_utf8(
                    translate(_("Validation failed: '${keyword}': invalid keyword",
                                mapping={'keyword': safe_unicode(row['keyword'])})))
                return instance.REQUEST[key]

        # keywords and titles used once only in the submitted form
        keywords = {}
        for field in variables_fields:
            if 'keyword' in field:
                if field['keyword'] in keywords:
                    keywords[field['keyword']] += 1
                else:
                    keywords[field['keyword']] = 1

        for k in [k for k in keywords.keys() if keywords[k] > 1]:
            msg = _(
                "Validation failed: '${keyword}': duplicate keyword",
                mapping={
                    'keyword': safe_unicode(k)
                })
            instance.REQUEST[key] = to_utf8(translate(msg))
            return instance.REQUEST[key]
        
        instance.REQUEST[key] = True
        return True

validation.register(VariablesSettingsFieldsValidator())