from senaite.core.catalog import SETUP_CATALOG
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.exportimport.setupdata import WorksheetImporter
from bika.lims import api

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