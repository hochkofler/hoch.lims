from hoch.lims.content.pharmaceuticalproduct import IPharmaceuticalProductSchema
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from senaite.core.exportimport.setupdata import WorksheetImporter
from senaite.core.catalog import SETUP_CATALOG
from hoch.lims import logger
from hoch.lims.api import validate_against_vocabulary
from hoch.lims.api import get_marketing_authorization_by_reg_num
from hoch.lims.api import get_pharmaceutical_product_by_code
from bika.lims import api
import plone.api as plone_api
from hoch.lims.content.marketingauthorization import IMarketingAuthorizationSchema
from hoch.lims.catalog import HOCHLIMS_CATALOG
from plone.dexterity.utils import createObject
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.catalog import SENAITE_CATALOG
from bika.lims.content.abstractbaseanalysis import RESULT_TYPES

class Hochlims_Custom(WorksheetImporter):
    """Import Analysis Services Hidden"""
    def edit_analysis_services(self):
        bsc = getToolByName(self.context, SETUP_CATALOG)
        sheetname = 'Analysis Services'
        worksheet = self.workbook[sheetname]
        if not worksheet:
            return
        for row in self.get_rows(3, worksheet=worksheet):
            service = self.get_object(bsc, 'AnalysisService',
                                      row.get('title'))
            if not service:
                return
            
            if row.get('Hidden'):           
                service.edit(
                    Hidden=self.to_bool(row.get('Hidden'))
                )
            
            if row.get('SortKey'):           
                service.edit(
                    SortKey=row.get('SortKey')
                )
                
            if row.get('ResultType'):
                resutltype = row.get('ResultType')
                if resutltype in RESULT_TYPES:
                    service.setResultType(row.get('ResultType'))
            
            service.reindexObject()
    
    def edit_analysis_categories(self):
        bsc = getToolByName(self.context, SETUP_CATALOG)
        sheetname = 'Analysis Categories'
        worksheet = self.workbook[sheetname]
        if not worksheet:
            return
        for row in self.get_rows(3, worksheet=worksheet):
            category = self.get_object(bsc, 'AnalysisCategory',
                                      row.get('title'))
            if not category:
                return
            
            if row.get('SortKey'):           
                category.setSortKey(row.get('SortKey'))
            category.reindexObject()
            
    def Import(self):
        """Import Analysis Services Hidden"""
        if "Analysis Services" in self.workbook.sheetnames:
            logger.info("Importing Analysis Services custom atributes")
            self.edit_analysis_services()
            logger.info("Importing Analysis Services custom atributes - DONE")
        else:
            logger.info("No 'Analysis Services' sheet found. Skipping.")
        
        if "Analysis Categories" in self.workbook.sheetnames:
            logger.info("Importing Analysys Categories custom")
            self.edit_analysis_categories()
            logger.info("Importing Analysys Categories custom - DONE")
        else:
            logger.info("No 'Analysis Categories' sheet found. Skipping.")

class Marketing_Authorization(WorksheetImporter):
    """Import Marketing Authorization"""
    
    def Import(self):
        """Import Marketing Authorization"""
        logger.info("Importing Marketing Authorization custom")
        container = self.context.MarketingAuthorizations
        separator = "-"
        
        for row in self.get_rows(3):
            reg_num = row.get("registration_number")
            if not reg_num:
                continue
            
            # check if the registration number already exists by reg_num
            if get_marketing_authorization_by_reg_num(reg_num):
                logger.error("Skipping %s: already exists" % reg_num)
                continue
            
            fields_with_vocab = [
                'dosage_form',
                'issuing_organization',
                'product_line',
                'sale_condition',
                'storage_conditions',
                'administration_route',
                'dosage_unit',
            ]
            validated = {}
            skip = False
            for field_name in fields_with_vocab:
                raw = api.safe_unicode(row.get(field_name))
                val = validate_against_vocabulary(
                    self.context,
                    IMarketingAuthorizationSchema,
                    field_name,
                    raw,
                )
                if not val:
                    logger.error(
                        "Skipping %s: invalid %s '%s'",
                        reg_num, field_name, raw
                    )
                    skip = True
                    break
                validated[field_name] = val

            if skip:
                continue
            
            raw_list_actions = row.get("therapeutic_actions", "")
            tokens = [api.safe_unicode(t.strip()) for t in raw_list_actions.split(separator) if t.strip()]
            validated_list_actions = []
            for token in tokens:
                val = validate_against_vocabulary(
                    self.context,
                    IMarketingAuthorizationSchema,
                    'therapeutic_actions',
                    token,
                )
                if not val:
                    logger.error(
                        "Skipping %s: invalid therapeutic_actions '%s'",
                        reg_num, token
                    )
                    skip = True
                    break
                validated_list_actions.append(val)

            if skip:
                continue
            
            api.create(container, "MarketingAuthorization",
                        issuing_organization=validated['issuing_organization'],
                        registration_number=reg_num,
                        trade_name=row.get("trade_name"),
                        generic_name=row.get("generic_name"),
                        concentrations=row.get("concentrations"),
                        dosage_form=validated['dosage_form'],
                        dosage_unit=validated['dosage_unit'],
                        product_line=validated['product_line'],
                        registered_presentations=row.get("registered_presentations"),
                        therapeutic_actions=validated_list_actions,
                        atq_code=row.get("atq_code"),
                        medicine_code=row.get("medicine_code"),
                        sale_condition=validated['sale_condition'],
                        storage_conditions=validated['storage_conditions'],
                        administration_route=validated['administration_route'],
                        issue_date=row.get("issue_date"),
                        expiration_date=row.get("expiration_date"),
                        shelf_life=row.get("shelf_life"),
                        holder=row.get("holder"),
                        manufacturer=row.get("manufacturer"))
            logger.info("Marketing Authorization '%s' created" % reg_num)

class Pharmaceutical_Product(WorksheetImporter):
    """Import Pharmaceutical products"""
    
    def Import(self):
        """Import Pharmaceutical products"""
        logger.info("Importing Pharmaceutical products")
        container = self.context.PharmaceuticalProducts
        
        for row in self.get_rows(3):
            code = row.get("code")
            if not code:
                continue
            
            # check if the product code already exists by prod_code
            if get_pharmaceutical_product_by_code(code):
                logger.error("Skipping %s: already exists" % code)
                continue
            
            # check if the marketing authorization exists
            reg_num = api.safe_unicode(row.get("registration_number"))
            if not reg_num:
                logger.error("Skipping %s: no marketing authorization provided" % code)
                continue
            
            reg_num_obj = get_marketing_authorization_by_reg_num(reg_num)
            if not reg_num_obj:
                logger.error("Skipping %s: marketing authorization '%s' not found" % (code, reg_num))
                continue
            
            fields_with_vocab = [
                'primary_presentation',
                'secundary_presentation',
            ]
            validated = {}
            skip = False
            for field_name in fields_with_vocab:
                raw = api.safe_unicode(row.get(field_name))
                val = validate_against_vocabulary(
                    self.context,
                    IPharmaceuticalProductSchema,
                    field_name,
                    raw,
                )
                if not val:
                    logger.error(
                        "Skipping %s: invalid %s '%s'",
                        reg_num, field_name, raw
                    )
                    skip = True
                    break
                validated[field_name] = val

            if skip:
                continue
            
            # create the product
            obj = api.create(
                container, "PharmaceuticalProduct",
                code=api.safe_unicode(code),
                name=api.safe_unicode(row.get("name")),
                presentation=api.safe_unicode(row.get("presentation")),
                primary_presentation=validated['primary_presentation'],
                dosage_unit_per_primary_presentation=self.to_int(row.get("dosage_unit_per_primary_presentation"),0),
                secundary_presentation=validated['secundary_presentation'],
                dosage_unit_per_secundary_presentation=self.to_int(row.get("dosage_unit_per_secundary_presentation"),0),
            )
            logger.info("Pharmaceutical Product created '%s'", code)
            
            obj.setMarketingAuthorization(reg_num_obj)
            obj.reindexObject()
                       

class Batch(WorksheetImporter):
    """Import Batch"""
    
    def Import(self):
        """Import Batch"""
        logger.info("Importing Batch custom")
        client_cat = api.get_tool(CLIENT_CATALOG)
        product_cat = api.get_tool(HOCHLIMS_CATALOG)
        senaite_cat = api.get_tool(SENAITE_CATALOG)
        for row in self.get_rows(3):
            batch_id = row.get("BatchID")
            if not batch_id:
                continue
            client_title = row.get("Client_title")
            if not client_title:
                continue
            client = client_cat(portal_type="Client",
                                getName=client_title)[0].getObject()
            if not client:
                logger.error("Skipping %s: client '%s' not found" % (batch_id, client_title))
                continue
            # check if the batch already exists
            batch = senaite_cat(portal_type="Batch",
                                getClientBatchID=batch_id)
            if batch:
                logger.error("Skipping %s: already exists" % batch_id)
                continue
            product_code = row.get("Product_code")
            if not product_code:
                logger.error("Skipping %s: no product code provided" % batch_id)
                continue
            product = get_pharmaceutical_product_by_code(product_code)
            if not product:
                logger.error("Skipping %s: product '%s' not found" % (batch_id, product_code))
                continue
            # create the batch
            obj = api.create(
                client, "Batch",
                Client = client,
                title = batch_id,
                BatchID = batch_id,
                ClientBatchID = batch_id,
                BatchDate =  row.get("BatchDate"),
                ManufactureDate = row.get("ManufactureDate"),
                ReleasedBatchSize = row.get("ReleasedBatchSize"),
                Product = product,
                Remarks = row.get("Remarks"),
            )
            logger.info("Batch '%s' created" % obj.__dict__)
            
class Dosage_Forms(WorksheetImporter):
    """Import Dosage Forms"""
    
    def Import(self):
        """Import Dosage Forms"""
        logger.info("Importing Dosage Forms custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            
            plone_api.portal.set_registry_record(
                "hoch.lims.dosage_forms",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.dosage_forms",
                default=[]
            )
            logger.info("this is new dosage forms: %s" % actual_values)
            
class Dosage_Units(WorksheetImporter):
    """Import Dosage Units"""
    
    def Import(self):
        """Import Dosage Units"""
        logger.info("Importing Dosage Units custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            
            plone_api.portal.set_registry_record(
                "hoch.lims.dosage_units",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.dosage_units",
                default=[]
            )
            logger.info("this is new dosage units: %s" % actual_values)

class Regulatory_Authorities(WorksheetImporter):
    """Import Regulatory Authorities"""
    
    def Import(self):
        """Import Regulatory Authorities"""
        logger.info("Importing Regulatory Authorities custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.regulatory_authorities",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.regulatory_authorities",
                default=[]
            )
            logger.info("this is new regulatory authorities: %s" % actual_values)
            
class Product_Lines(WorksheetImporter):
    """Import Product Lines"""
    
    def Import(self):
        """Import Product Lines"""
        logger.info("Importing Product Lines custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.product_lines",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.product_lines",
                default=[]
            )
            logger.info("this is new product lines: %s" % actual_values)

class Therapeutic_Indications(WorksheetImporter):
    """Import Therapeutic Indications"""
    
    def Import(self):
        """Import Therapeutic Indications"""
        logger.info("Importing Therapeutic Indications custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.therapeutic_indications",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.therapeutic_indications",
                default=[]
            )
            logger.info("this is new therapeutic indications: %s" % actual_values)

class Sale_Conditions(WorksheetImporter):
    """Import Sale Conditions"""
    
    def Import(self):
        """Import Sale Conditions"""
        logger.info("Importing Sale Conditions custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.sale_conditions",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.sale_conditions",
                default=[]
            )
            logger.info("this is new sale conditions: %s" % actual_values)

class Storage_Conditions(WorksheetImporter):
    """Import Storage Conditions"""
    
    def Import(self):
        """Import Storage Conditions"""
        logger.info("Importing Storage Conditions custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.storage_conditions",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.storage_conditions",
                default=[]
            )
            logger.info("this is new storage conditions: %s" % actual_values)

class Administration_Routes(WorksheetImporter):
    """Import Administration Routes"""
    
    def Import(self):
        """Import Administration Routes"""
        logger.info("Importing Administration Routes custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.administration_routes",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.administration_routes",
                default=[]
            )
            logger.info("this is new administration routes: %s" % actual_values)

class Primary_Presentation(WorksheetImporter):
    """Import Primary Presentation"""
    
    def Import(self):
        """Import Primary Presentation"""
        logger.info("Importing Primary Presentation custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.primary_presentations",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.primary_presentations",
                default=[]
            )
            logger.info("this is new primary presentations: %s" % actual_values)

class Secundary_Presentation(WorksheetImporter):
    """Import Secundary Presentation"""
    
    def Import(self):
        """Import Secundary Presentation"""
        logger.info("Importing Secundary Presentation custom")
        
        new_vocab = []
        for row in self.get_rows(3):
            key = row.get("key")
            value = row.get("value")
            if key and value:
                new_vocab.append({u'key': api.safe_unicode(key), u'value': api.safe_unicode(value)})
        
        if new_vocab:
            plone_api.portal.set_registry_record(
                "hoch.lims.secundary_presentations",
                new_vocab
            )
            
            actual_values = api.get_registry_record(
                "hoch.lims.secundary_presentations",
                default=[]
            )
            logger.info("this is new secundary presentations: %s" % actual_values)