from bika.lims import api

from hoch.lims.catalog.hochlims_catalog import CATALOG_ID as HOCHLIMS_CATALOG 
from senaite.patient.permissions import AddPatient
from zope.deprecation import deprecate

def get_marketingauthorization_catalog():
    """Returns the hochlims catalog
    """
    return api.get_tool(HOCHLIMS_CATALOG)


def hochlims_search(query):
    """Search the hochlims catalog
    """
    catalog = get_marketingauthorization_catalog()
    return catalog(query)