from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from senaite.core.exportimport.setupdata import WorksheetImporter
from senaite.core.catalog import SETUP_CATALOG
from hoch.lims import logger

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
                category.edit(
                    SortKey=row.get('SortKey')
                )
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
        
        

