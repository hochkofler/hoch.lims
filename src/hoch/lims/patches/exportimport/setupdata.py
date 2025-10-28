from senaite.core.catalog import SETUP_CATALOG
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.exportimport.setupdata import WorksheetImporter
from senaite.core.exportimport.setupdata import Analysis_Services
from bika.lims import api
from zope.interface import implements
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFCore.utils import getToolByName
from bika.lims.utils import tmpID
from senaite.core.exportimport.setupdata import Float
from senaite.core.idserver import renameAfterCreation
from Products.CMFPlone.utils import safe_unicode
from hoch.lims import logger

def Import_sample_templates(self):
        self.load_sampletemplate_services()
        self.load_sampletemplate_partitions()

        setup = api.get_senaite_setup()
        folder = setup.sampletemplates
        sc = api.get_tool(SETUP_CATALOG)

        for row in self.get_rows(3):
            title = row.get("title")
            if not title:
                continue
            description = row.get("description") or ''
            services = self.services.get(title)
            client_title = row.get("Client_title") or "lab"
            partitions = self.partitions.get(title, [])
            if client_title == "lab":
                folder = setup.sampletemplates
            else:
                client = api.search({
                    "portal_type": "Client",
                    "getName": client_title
                }, CLIENT_CATALOG)
                if len(client) == 1:
                    folder = api.get_object(client[0])

            sampletype = self.get_object(
                sc, 'SampleType', row.get('SampleType_title'))
            samplepoint = self.get_object(
                sc, 'SamplePoint', row.get('SamplePoint_title'))

            obj = api.create(folder, "SampleTemplate", title=title, description=description)
            obj.setSampleType(sampletype)
            obj.setSamplePoint(samplepoint)
            if services:
                obj.setPartitions(partitions)
                obj.setServices(services)
                
def get_interim_fields(self):
    # preload Calculation Interim Fields sheet
    sheetname = 'Calculation Interim Fields'
    worksheet = self.workbook[sheetname]
    if not worksheet:
        return
    self.interim_fields = {}
    rows = self.get_rows(3, worksheet=worksheet)
    for row in rows:
        calc_title = row['Calculation_title']
        if calc_title not in self.interim_fields.keys():
            self.interim_fields[calc_title] = []
        self.interim_fields[calc_title].append({
            'keyword': row['keyword'],
            'title': row.get('title', ''),
            'type': row.get('result_typ', ''),
            'hidden': ('hidden' in row and row['hidden']) and True or False,
            'value': row['value'],
            'choices': str(row.get('choices', '')),
            'result_type': row.get('result_type', ''),
            'allow_empty': ('allow_empty' in row and row['allow_empty']) and True or False,
            'wide': ('wide' in row and row['wide']) and True or False,
            'unit': row['unit'] and row['unit'] or ''})
        
def load_interim_fields(self):
        # preload AnalysisService InterimFields sheet
        sheetname = 'AnalysisService InterimFields'
        worksheet = self.workbook[sheetname]
        if not worksheet:
            return
        self.service_interims = {}
        rows = self.get_rows(3, worksheet=worksheet)
        for row in rows:
            service_title = row['Service_title']
            if service_title not in self.service_interims.keys():
                self.service_interims[service_title] = []
            self.service_interims[service_title].append({
                'keyword': row['keyword'],
                'title': row.get('title', ''),
                'type': row.get('result_typ', ''),
                'hidden': ('hidden' in row and row['hidden']) and True or False,
                'value': row['value'],
                'choices': str(row.get('choices', '')),
                'result_type': row.get('result_type', ''),
                'allow_empty': ('allow_empty' in row and row['allow_empty']) and True or False,
                'wide': ('wide' in row and row['wide']) and True or False,
                'unit': row['unit'] and row['unit'] or ''})
     
def import_analysis_services(self):
    # Only Change line Method=defaultmethod,
    # And add line Instrument = defaultinstrument,
        self.load_interim_fields()
        folder = self.context.bika_setup.bika_analysisservices
        bsc = getToolByName(self.context, SETUP_CATALOG)
        for row in self.get_rows(3):
            if not row['title']:
                continue

            obj = _createObjectByType("AnalysisService", folder, tmpID())
            MTA = {
                'days': self.to_int(row.get('MaxTimeAllowed_days', 0), 0),
                'hours': self.to_int(row.get('MaxTimeAllowed_hours', 0), 0),
                'minutes': self.to_int(row.get('MaxTimeAllowed_minutes', 0), 0),
            }
            category = self.get_object(
                bsc, 'AnalysisCategory', row.get('AnalysisCategory_title'))
            department = self.get_object(
                bsc, 'Department', row.get('Department_title'))
            container = self.get_object(
                bsc, 'SampleContainer', row.get('Container_title'))
            preservation = self.get_object(
                bsc, 'SamplePreservation', row.get('Preservation_title'))

            # Analysis Service - Method considerations:
            # One Analysis Service can have 0 or n Methods associated (field
            # 'Methods' from the Schema).
            # If the Analysis Service has at least one method associated, then
            # one of those methods can be set as the defualt method (field
            # '_Method' from the Schema).
            #
            # To make it easier, if a DefaultMethod is declared in the
            # Analysis_Services spreadsheet, but the same AS has no method
            # associated in the Analysis_Service_Methods spreadsheet, then make
            # the assumption that the DefaultMethod set in the former has to be
            # associated to the AS although the relation is missing.
            defaultmethod = self.get_object(
                bsc, 'Method', row.get('DefaultMethod_title'))
            methods = self.get_methods(row['title'], defaultmethod)
            if not defaultmethod and methods:
                defaultmethod = methods[0]

            # Analysis Service - Instrument considerations:
            # By default, an Analysis Services will be associated automatically
            # with several Instruments due to the Analysis Service - Methods
            # relation (an Instrument can be assigned to a Method and one Method
            # can have zero or n Instruments associated). There is no need to
            # set this assignment directly, the AnalysisService object will
            # find those instruments.
            # Besides this 'automatic' behavior, an Analysis Service can also
            # have 0 or n Instruments manually associated ('Instruments' field).
            # In this case, the attribute 'AllowInstrumentEntryOfResults' should
            # be set to True.
            #
            # To make it easier, if a DefaultInstrument is declared in the
            # Analysis_Services spreadsheet, but the same AS has no instrument
            # associated in the AnalysisService_Instruments spreadsheet, then
            # make the assumption the DefaultInstrument set in the former has
            # to be associated to the AS although the relation is missing and
            # the option AllowInstrumentEntryOfResults will be set to True.
            defaultinstrument = self.get_object(
                bsc, 'Instrument', row.get('DefaultInstrument_title'))
            instruments = self.get_instruments(row['title'], defaultinstrument)
            allowinstrentry = True if instruments else False
            if not defaultinstrument and instruments:
                defaultinstrument = instruments[0]

            # The manual entry of results can only be set to false if the value
            # for the attribute "InstrumentEntryOfResults" is False.
            allowmanualentry = True if not allowinstrentry else row.get(
                'ManualEntryOfResults', True)

            # Analysis Service - Calculation considerations:
            # By default, the AnalysisService will use the Calculation associated
            # to the Default Method (the field "UseDefaultCalculation"==True).
            # If the Default Method for this AS doesn't have any Calculation
            # associated and the field "UseDefaultCalculation" is True, no
            # Calculation will be used for this AS ("_Calculation" field is
            # reserved and should not be set directly).
            #
            # To make it easier, if a Calculation is set by default in the
            # spreadsheet, then assume the UseDefaultCalculation has to be set
            # to False.
            deferredcalculation = self.get_object(
                bsc, 'Calculation', row.get('Calculation_title'))
            usedefaultcalculation = False if deferredcalculation else True
            _calculation = deferredcalculation if deferredcalculation else \
                (defaultmethod.getCalculation() if defaultmethod else None)

            obj.edit(
                title=row['title'],
                ShortTitle=row.get('ShortTitle', row['title']),
                description=row.get('description', ''),
                Keyword=row['Keyword'],
                PointOfCapture=row['PointOfCapture'].lower(),
                Category=category,
                Department=department,
                Unit=row['Unit'] and row['Unit'] or None,
                Precision=row['Precision'] and str(row['Precision']) or '0',
                ExponentialFormatPrecision=str(self.to_int(
                    row.get('ExponentialFormatPrecision', 7), 7)),
                LowerDetectionLimit='%06f' % self.to_float(
                    row.get('LowerDetectionLimit', '0.0'), 0),
                UpperDetectionLimit='%06f' % self.to_float(
                    row.get('UpperDetectionLimit', '1000000000.0'), 1000000000.0),
                DetectionLimitSelector=self.to_bool(
                    row.get('DetectionLimitSelector', 0)),
                MaxTimeAllowed=MTA,
                Price="%02f" % Float(row['Price']),
                BulkPrice="%02f" % Float(row['BulkPrice']),
                VAT="%02f" % Float(row['VAT']),
                Method=defaultmethod,
                Methods=methods,
                ManualEntryOfResults=allowmanualentry,
                InstrumentEntryOfResults=allowinstrentry,
                Instrument = defaultinstrument,
                Instruments=instruments,
                Calculation=_calculation,
                UseDefaultCalculation=usedefaultcalculation,
                DuplicateVariation="%02f" % Float(row['DuplicateVariation']),
                Accredited=self.to_bool(row['Accredited']),
                InterimFields=hasattr(self, 'service_interims') and self.service_interims.get(
                    row['title'], []) or [],
                Separate=self.to_bool(row.get('Separate', False)),
                Container=container,
                Preservation=preservation,
                CommercialID=row.get('CommercialID', ''),
                ProtocolID=row.get('ProtocolID', '')
            )
            obj.unmarkCreationFlag()
            renameAfterCreation(obj)
            notify(ObjectInitializedEvent(obj))
        self.load_result_options()
        self.load_service_uncertainties()
        
def import_Analysis_Specifications(self):
        """change all bucket[parent][title][resultsrange]"""
        bucket = {}
        client_catalog = getToolByName(self.context, CLIENT_CATALOG)
        setup_catalog = getToolByName(self.context, SETUP_CATALOG)
        # collect up all values into the bucket
        for row in self.get_rows(3):
            field = row.get("Title", False)
            if not field:
                field = row.get("title", False)
                if not field:
                    continue
            parent = row["Client_title"] if row["Client_title"] else "lab"
            st = row["SampleType_title"] if row["SampleType_title"] else ""
            service = self.resolve_service(row)

            if parent not in bucket:
                bucket[parent] = {}
            if field not in bucket[parent]:
                bucket[parent][field] = {"sampletype": st, "resultsrange": []}
            resultsrange_dict = {
                "keyword": service.getKeyword(),
                "min": row.get("min", ""),
                "max": row.get("max", ""),
                "max_operator": 'lt' if row.get("max_operator", 'leq') == '<' else 'leq',
                "min_operator": 'gt' if row.get("min_operator", 'geq') == '>' else 'geq',
                "warn_min": row.get("warn_min", ""),
                "warn_max": row.get("warn_max", ""),
                "hidemin": row.get("hidemin", ""),
                "hidemax": row.get("hidemax", ""),
                "rangecomment": row.get("rangecomment", ""),
                "min_panic": row.get("min_panic", ""),
                "max_panic": row.get("max_panic", ""),
                }
            logger.info("Result range dict %s", resultsrange_dict)
            bucket[parent][field]["resultsrange"].append(resultsrange_dict)
                
        # write objects.
        for parent in bucket.keys():
            for field in bucket[parent]:
                if parent == "lab":
                    folder = self.context.bika_setup.bika_analysisspecs
                else:
                    proxy = client_catalog(
                        portal_type="Client", getName=safe_unicode(parent))[0]
                    folder = proxy.getObject()
                st = bucket[parent][field]["sampletype"]
                resultsrange = bucket[parent][field]["resultsrange"]
                if st:
                    st_uid = setup_catalog(
                        portal_type="SampleType", title=safe_unicode(st))[0].UID
                obj = _createObjectByType("AnalysisSpec", folder, tmpID())
                obj.edit(title=field)
                obj.setResultsRange(resultsrange)
                if st:
                    obj.setSampleType(st_uid)
                obj.unmarkCreationFlag()
                renameAfterCreation(obj)
                notify(ObjectInitializedEvent(obj))