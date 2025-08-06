from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from senaite.core.exportimport.setupdata import WorksheetImporter
from senaite.core.catalog import SETUP_CATALOG
from hoch.lims import logger
from hoch.lims.api import validate_against_vocabulary
from hoch.lims.api import get_marketing_authorization_by_reg_num
from bika.lims import api
from hoch.lims.content.marketingauthorization import IMarketingAuthorizationSchema
from plone.dexterity.utils import createObject

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
            ]
            validated = {}
            skip = False
            for field_name in fields_with_vocab:
                raw = row.get(field_name)
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
            tokens = [t.strip() for t in raw_list_actions.split(separator) if t.strip()]
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
                        dosage_form=validated['dosage_form'],
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
                       
        
        

