# -*- coding: utf-8 -*-
from zope.interface import implementer
from bika.lims.interfaces import IAddSampleObjectInfo
from bika.lims import api
from bika.lims import logger

@implementer(IAddSampleObjectInfo)
class BatchProductSampleTypeFilter(object):
    """Dynamic filter for SampleTypes based on the Batch's product or matrix authorization."""

    def __init__(self, obj):
        self.obj = obj

    def get_object_info_with_record(self, record):
        # Aplicar solo si el objeto es un Batch
        if self.obj.portal_type != "Batch":
            return {}
        logger.info("todo el objeto es:'%s'", self.obj)
        
        product_uid = getattr(self.obj, "Product", None)
        logger.info("The product UID is: '%s'", product_uid)
        if not product_uid:
            # Lote sin producto → materias primas
            logger.info("Batch without product: returning generic SampleTypes")
            return {
                "filter_queries": {
                    "SampleType": {
                        # Muestra SampleTypes sin matriz o matrices sin MA
                        "getSampleMatrixUID": ["", None],
                        "is_active": True,
                    }
                }
            }

        product = api.get_object_by_uid(product_uid)
        # Si tiene producto, obtenemos su MA
        
        ma = product.getMarketingAuthorization()
        if not ma:
            logger.info("Product without MA: no filter by matrix authorization")
            return {}
        
        ma_uid = api.get_uid(ma)
        matrices = api.search({
            "portal_type": "SampleMatrix",
            "getMarketingAuthorizationUID": ma_uid,
        })
        matrices = matrices[:1]
        logger.info("Sample matrices: '%s'", matrices)
        
        matrix_uids = [b.UID for b in matrices]

        # Filtramos SampleTypes que tengan una matriz con esa MA
        
        queries = {
            "SampleType": {
                "marketingauthorization_uid_for_sampletype": [ma_uid],
                "is_active": True,
            }
        }

        logger.info(
            
            "Filtering SampleTypes for Batch '%s' by MA '%s' (%s)", self.obj.Title(), ma.Title(), ma_uid
        )
        obj_2 = api.search({"portal_type": "SampleType"})[0].getObject()
        catalog = api.get_catalogs_for(obj_2)
        logger.info("Catalog are: '%s'", catalog)
        logger.info("indexes '%s'", sorted(catalog[0].indexes()))
        return {"filter_queries": queries}
