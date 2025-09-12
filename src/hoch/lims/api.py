from bika.lims import api

from hoch.lims.catalog.hochlims_catalog import CATALOG_ID as HOCHLIMS_CATALOG
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.schema import getFieldsInOrder
from hoch.lims import logger

def get_marketingauthorization_catalog():
    """Returns the hochlims catalog
    """
    return api.get_tool(HOCHLIMS_CATALOG)


def hochlims_search(query):
    """Search the hochlims catalog
    """
    catalog = get_marketingauthorization_catalog()
    return catalog(query)

def get_marketing_authorization_by_reg_num(reg_num):
    """Get a Marketing Authorization by its registration number.
    """
    index_name = "mktauth_registration_number"
    brains = hochlims_search({index_name: reg_num})
    if brains:
        return brains[0].getObject()
    return None

def get_pharmaceutical_product_by_code(code):
    """Get a Pharmaceutical Product by its code.
    """
    index_name = "product_code"
    brains = hochlims_search({index_name: code})
    if brains:
        return brains[0].getObject()
    return None

def validate_against_vocabulary(context, schema, field_name, raw_value):
        """
        Checks that raw_value is in the vocabulary defined in the schema
        for field_name. Returns term.value if it exists, or throws Invalid.
        """
        for fname, field in getFieldsInOrder(schema):
            if fname == field_name:
                break
        else:
            logger.error("The field '%s' does not exist in the schema" % field_name)
            return

        source_name = getattr(field, "vocabularyName", None) or getattr(field.value_type, "vocabularyName", None)
        if not source_name:
            logger.error("The field '%s' does not have a source defined" % field_name)
            return
        if not isinstance(source_name, str):
            logger.error("The source for field '%s' must be a string" % field_name)
            return
        
        factory = getUtility(IVocabularyFactory, source_name)
        vocabulary = factory(context)
        term = None
        if raw_value in vocabulary:
            term = vocabulary.getTerm(raw_value)
            return term.value
        
        if term is None:
            valid = ", ".join([t.token for t in vocabulary])
            logger.info(
                "The value '%s' is not valid for field '%s'. Valid values are: %s" %
                (raw_value, field_name, valid)
            )
            return

        return term.value