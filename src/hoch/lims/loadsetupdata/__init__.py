# -*- coding: utf-8 -*-
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
from hoch.lims.config import VARIABLES
from senaite.core.idserver import renameAfterCreation

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
            
            result_type_keys = [rt[0] for rt in RESULT_TYPES]
            if row.get('ResultType'):
                resutltype = row.get('ResultType')
                if resutltype in result_type_keys:
                    service.setResultType(row.get('ResultType'))
                else:
                    logger.info("result type '%s' not admited. admited results: '%s'", resutltype, result_type_keys)
            
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
        bsc = getToolByName(self.context, SETUP_CATALOG)
        
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
            
            batch_labels_titles = row.get("BatchLabels").split(",")
            batch_labels = []
            for batch_label_title in batch_labels_titles:
                batch_label = self.get_object(bsc, 'BatchLabel',
                                      batch_label_title)
                if batch_label:
                    batch_labels.append(api.get_uid(batch_label))
            
            # create the batch
            obj = api.create(
                client, "Batch",
                Client = client,
                title = batch_id,
                BatchID = batch_id,
                ClientBatchID = batch_id,
                BatchDate =  row.get("BatchDate"),
                BatchLabels = batch_labels,
                ManufactureDate = row.get("ManufactureDate"),
                ReleasedBatchSize = row.get("ReleasedBatchSize"),
                BatchSize = api.to_int(row.get("BatchSize", 1000),1000),
                Product = product,
                Description = product.Description(),
                Remarks = row.get("Remarks"),
            )
            logger.info("Batch '%s' created" % obj)
            obj.unmarkCreationFlag()
            renameAfterCreation(obj)
            notify(ObjectInitializedEvent(obj))
            
class Instruments_Methods(WorksheetImporter):
    def Import(self):
        logger.info("Importing instrument methods worksheet")
        bsc = getToolByName(self.context, SETUP_CATALOG)
        method_instruments = {}
        for row in self.get_rows(3):
            method = self.get_object(bsc, 'Method',
                                      row.get('method_title'))
            if not method:
                continue
            
            instrument = self.get_object(bsc, 'Instrument',
                                      row.get('Instrument_title'))
            if not instrument:
                continue
            
            method_uid = api.get_uid(method)
            instrument_uid = api.get_uid(instrument)
            if method_uid not in method_instruments:
                method_instruments[method_uid] = [instrument_uid]
            else:
                method_instruments[method_uid].append(instrument_uid)
    
        for method_uid, instruments_uids in method_instruments.items():
            method = api.get_object_by_uid(method_uid)
            logger.info("setting instruments '%s' to method: '%s'", instruments_uids, method)
            method.setInstruments(instruments_uids)

class Methods_Calculations(WorksheetImporter):
    def Import(self):
        logger.info("Importing methods calculations worksheet")
        bsc = getToolByName(self.context, SETUP_CATALOG)
        method_calculations = {}
        for row in self.get_rows(3):
            method = self.get_object(bsc, 'Method',
                                      row.get('method_title'))
            if not method:
                continue
            
            calculation = self.get_object(bsc, 'Calculation',
                                      row.get('calculation_title'))
            if not calculation:
                continue
            
            method_uid = api.get_uid(method)
            calculation_uid = api.get_uid(calculation)
            if method_uid not in method_calculations:
                method_calculations[method_uid] = [calculation_uid]
            else:
                method_calculations[method_uid].append(calculation_uid)
    
        for method_uid, calculation_uids in method_calculations.items():
            method = api.get_object_by_uid(method_uid)
            logger.info("setting instruments '%s' to method: '%s'", calculation_uids, method)
            method.setCalculations(calculation_uids)
            
class AnalysisService_SubInstruments(WorksheetImporter):
    def Import(self):
        logger.info("Importing subinstruments for analysis services")
        bsc = getToolByName(self.context, SETUP_CATALOG)
        services_subinstruments = {}
        for row in self.get_rows(3):
            service = self.get_object(bsc, 'AnalysisService',
                                      row.get('service_title'))
            if not service:
                continue
            
            subinstrument = self.get_object(bsc, 'Instrument',
                                      row.get('subinstrument_title'))
            if not subinstrument:
                continue
            
            is_default_subinstrument = row.get('default') and True or False
            
            service_uid = api.get_uid(service)
            if service_uid not in services_subinstruments:
                services_subinstruments[service_uid] = {}
                services_subinstruments[service_uid]["instruments"]=[]
                services_subinstruments[service_uid]["defaults"]=[]
                services_subinstruments[service_uid]["allowed"] = self.getSubInstrumentAllowed(service)
            
            if subinstrument in services_subinstruments[service_uid]["allowed"]:
                services_subinstruments[service_uid]["instruments"].append(subinstrument)
                if is_default_subinstrument:
                    services_subinstruments[service_uid]["defaults"].append(subinstrument)
            else:
                logger.info("SubInstrument: '%s' not allowed, allowed instruments are: '%s'", row.get('subinstrument_title'), services_subinstruments[service_uid]["allowed"])

        for service_uid, subinstruments in services_subinstruments.items():
            service = api.get_object_by_uid(service_uid)
            service.setSubInstrumentsAllowed(subinstruments["instruments"])
            if subinstruments["defaults"]:   
                service.setSubInstruments(subinstruments["defaults"])
                
    def getSubInstrumentAllowed(self, service):
        sub_instruments = []
        instruments_asigned = service.getInstruments()
        # When methods are selected, display only instruments from the methods
        methods = service.getMethods()
        for method in methods:
            for instrument in method.getInstruments():
                if instrument in sub_instruments or instrument in instruments_asigned:
                    continue
                sub_instruments.append(instrument)

        if not methods:
            # query all available instruments when no methods are selected
            sub_instruments = self.query_available_instruments()
        
        return sub_instruments

class AnalysisService_Conditions(WorksheetImporter):
    def Import(self):
        logger.info("Importing conditions for analysis services")
        bsc = getToolByName(self.context, SETUP_CATALOG)
        services_conditions = {}
        for row in self.get_rows(3):
            service = self.get_object(bsc, 'AnalysisService',
                                      row.get('Service_title'))
            if not service:
                continue
            
            condition_title = row.get('title')
            if not condition_title:
                continue
            
            condition_type = row.get('type')
            if not condition_type or condition_type not in ['text','number','checkbox','select','file']:
                continue
            
            service_uid = api.get_uid(service)
            if service_uid not in services_conditions:
                services_conditions[service_uid] = {}
                services_conditions[service_uid][condition_title] = {
                    "title": condition_title,
                    "description": row.get('description'),
                    "type": condition_type,
                    "choices": row.get('choices'),
                    "default": row.get('default'),
                    "required": row.get('required') and True or False,
                    "report": row.get('report') and True or False,
                }
        
        for service_uid, condition_titles in services_conditions.items():
            conditions = []
            for condition_title, condition in condition_titles.items():
                conditions.append(condition)
            services_conditions[service_uid]["conditions"] = conditions
            
            service = api.get_object_by_uid(service_uid)
            logger.info("setting conditions '%s' to service: '%s'", conditions, service)
            actual_conditions = service.getConditions()
            conditions_to_add = []
            for actual_condition in actual_conditions:
                if actual_condition['title'] not in condition_titles:
                    conditions_to_add.append(actual_condition)
            
            conditions_to_add = conditions_to_add + conditions
            service.setConditions(conditions_to_add)
            service.reindexObject()

class Calculations_python_imports(WorksheetImporter):
    """Import Calculations python imports"""
    
    def Import(self):
        """Import Calculations python imports"""
        logger.info("Importing Calculations python imports custom")
        bsc = getToolByName(self.context, SETUP_CATALOG)
        for row in self.get_rows(3):
            calculation = self.get_object(bsc, 'Calculation',
                                      row.get('Calculation_title'))
            if not calculation:
                continue
            
            python_module = row.get('python_module')
            python_function = row.get('python_function')
            if not python_function or not python_module:
                continue
            
            python_import = {
                'module': python_module,
                'function': python_function
            }
            
            calculation.setPythonImports([python_import])
            calculation.reindexObject()
            logger.info("Calculation '%s' python imports updated", calculation.Title())

class Reference_Samples_Concentration(WorksheetImporter):
    """Importer for reference samples concentrations"""
    def Import(self):
        bsc = getToolByName(self.context, SENAITE_CATALOG)
        for row in self.get_rows(3):
            reference_sample = self.get_object(bsc, 'ReferenceSample',
                                       row.get('id', ''))
            if not reference_sample:
                continue
            
            reference_sample.edit(
                Concentration = row.get('Concentration',''),
                ConcentrationUnit=row.get('ConcentrationUnit',''),
                Sensitivity=row.get('Sensitivity',''),
                SensitivityUnit=row.get('SensitivityUnit','')
            )
            reference_sample.reindexObject()
            
class Sample_Matrices_Variables(WorksheetImporter):
    """Importador optimizado para variables de matrices de muestra"""
    sample_matrices_data = {}
    
    def process_row(self, row, bsc):
        """Procesa una fila individual del worksheet"""
        samplematrix_title = row.get('samplematrix_title')
        service_title = row.get('service_title')
        parameter = row.get('parameter')
        value_str = row.get('value')
        unit = row.get('unit')
        
        # Validaciones básicas
        if not all([samplematrix_title, service_title, parameter, value_str]):
            logger.warning(u"Fila omitida: datos incompletos")
            return
            
        value = (api.to_float(value_str, 0), unit)
            
        # Obtener objetos
        samplematrix = self.get_object(bsc,'SampleMatrix', samplematrix_title)
        service = self.get_object(bsc,'AnalysisService', service_title)
        
        if not samplematrix or not service:
            logger.warning(u"Objeto no encontrado: %s o %s", samplematrix_title, service_title)
            return
            
        # Almacenar datos en estructura eficiente
        samplematrix_uid = samplematrix.UID()
        service_uid = service.UID()
        
        if samplematrix_uid not in self.sample_matrices_data:
            self.sample_matrices_data[samplematrix_uid] = {
                'obj': samplematrix,
                'services': {}
            }
            
        if service_uid not in self.sample_matrices_data[samplematrix_uid]['services']:
            self.sample_matrices_data[samplematrix_uid]['services'][service_uid] = {}
            
        self.sample_matrices_data[samplematrix_uid]['services'][service_uid][parameter] = value
    
    def save_data(self):
        """Guarda los datos procesados en las matrices de muestra"""
        for sm_uid, data in self.sample_matrices_data.items():
            samplematrix = data['obj']
            variables_data = []
            
            for service_uid, parameters in data['services'].items():
                for param_name, param_value in parameters.items():
                    variables_data.append({
                        'parameter': param_name,
                        'service': service_uid,
                        'value': param_value[0],
                        'unit': param_value[1],
                    })
            
            # Actualizar la matriz de muestra
            samplematrix.variables_table = variables_data
            logger.info("Actualizada matriz de muestra: %s", samplematrix.Title())
    
    def Import(self):
        """Método principal de importación"""
        logger.info("Iniciando importación de variables de matrices de muestra")
        bsc = getToolByName(self.context, 'senaite_catalog_setup')
        # Procesar todas las filas
        for row in self.get_rows(3):  # Empezar desde la fila 3
            self.process_row(row, bsc)
        
        # Guardar todos los datos
        self.save_data()
        
        logger.info("Importación completada: %d matrices actualizadas", 
                   len(self.sample_matrices_data))
              
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