# -*- coding: utf-8 -*-
import json
import six
from bika.lims import api
from senaite.core.exportimport.instruments import IInstrumentAutoImportInterface
from senaite.core.exportimport.instruments import IInstrumentImportInterface
from senaite.core.exportimport.instruments.importer import ALLOWED_ANALYSIS_STATES
from senaite.core.exportimport.instruments.importer import ALLOWED_SAMPLE_STATES
from senaite.core.exportimport.instruments.importer import AnalysisResultsImporter
#from senaite.core.exportimport.instruments.parser import InstrumentResultsFileParser
from senaite.core.exportimport.instruments.parser import InstrumentCSVResultsFileParser
from senaite.core.exportimport.instruments.utils import get_instrument_import_ar_allowed_states
from senaite.core.exportimport.instruments.utils import get_instrument_import_override
from zope.interface import implementer
from zope.interface import implements
from hoch.lims import logger
import re
from datetime import datetime
from senaite.core.catalog import SAMPLE_CATALOG
from hoch.lims import messageFactory as _
import unicodedata
from senaite.core.registry import get_registry_record
from bika.lims.interfaces import IReferenceAnalysis
from bika.lims.interfaces import IRoutineAnalysis

class CustomAnalysisResultImporter(AnalysisResultsImporter):
    "Custom importer"

def extract_final_number_from_string(s):
    """Extracts the final number from a given string.
    
    Args:
        s (str): The input string."""
    match = re.search(r'(\d+)$', s)
    return match.group(1) if match else None

@implementer(IInstrumentImportInterface, IInstrumentAutoImportInterface)
class asciiResultsImporterInterface(CustomAnalysisResultImporter):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Shimadzu HPLC-PDA Nexera ASCII Importer"

    def __init__(self, context):
        self.context = context
        self.override = [False, False]
        self.allowed_sample_states = ALLOWED_SAMPLE_STATES
        self.allowed_analysis_states = ALLOWED_ANALYSIS_STATES
        
    def get_automatic_importer(self, instrument, parser, **kw):
            """Called during automated results import
            """
            # initialize the base class with the required parameters
            logger.info("Getting automatic importer for instrument: {}".format(instrument.Title()))
            super(asciiResultsImporterInterface, self).__init__(
                parser, self.context,
                override=self.override,
                allowed_sample_states=self.allowed_sample_states,
                allowed_analysis_states=self.allowed_analysis_states,
                instrument_uid=api.get_uid(instrument))
            return self

    def get_automatic_parser(self, infile):
            """Called during automated results import

            Returns the parser to be used by default for the file passed in when
            automatic results import for this instrument interface is enabled
            """
            logger.info("Getting automatic parser for file: {}".format(infile.filename))
            return asciiResultParser(infile)

    def Import(self, context, request):
            """Called from the manual import view
            """
            logger.info("Starting manual import process")
            # Get the uploaded results file
            infile = request.form.get("instrument_results_file")
            # Sample states to apply results?
            allowed_states = request.form.get("artoapply", "received")
            # The selected instrument
            instrument_uid = request.form.get("instrument", None)

            if not infile:
                return json.dumps({
                    "errors": ["No file selected", ],
                    "log": [],
                    "warns": []
                })

            # Override results?
            override = request.form.get("results_override", "nooverride")
            self.override = get_instrument_import_override(override)

            # allowed states
            self.allowed_sample_states = get_instrument_import_ar_allowed_states(
                allowed_states)

            # instrument
            instrument = api.get_object(instrument_uid)
            parser = self.get_automatic_parser(infile)
            importer = self.get_automatic_importer(instrument, parser)

            importer.process()

            return json.dumps({
                "errors": self.errors,
                "log": self.logs,
                "warns": self.warns,
            })
                
class asciiResultParser(InstrumentCSVResultsFileParser):
        """Parse the import file and fills the raw results dictionary
        """
        def __init__(self, infile):
            InstrumentCSVResultsFileParser.__init__(self, infile)
            self._currentresultsheader = []
            self._currentanalysiskw = ''
            self._numline = 0
            self._currentsampleid = ''
            self._currentsamplename = ''
            self._currentsampletype = ''
            self._identifiers = {
                'header': "Peak#",
                'result': "Area",
                'sampletype': "Sample Type",
                'samplename': "Sample Name",
                'sampleid': "Sample ID",
            }
            logger.info("NexeraIfaParser initialized")
        
        def _parseline(self, line):
            return self.parse_TSVline(line)

        def parse_TSVline(self, line):
            """ Parses result lines
            """

            split_row = [token.strip() for token in line.split('\t')]
            _results = {'DefaultResult': self._identifiers['result']}
            
            # check if the sampleid and sampletype is identified
            if not self._currentsampleid or not self._currentsampletype:
                # if not identified, look for them
                if split_row[0] == self._identifiers['sampletype']:
                    if len(split_row) > 1:
                        self._currentsampletype = split_row[1]
                        logger.info("Current Sample Type: {}".format(self._currentsampletype))
                    else:
                        self.warn("Sample Type not found or empty",
                                numline=self._numline, line=line)
                    return 0
                elif split_row[0] == self._identifiers['samplename']:
                    if len(split_row) > 1:
                        self._currentsamplename = split_row[1]
                        logger.info("Current Sample Name: {}".format(self._currentsamplename))
                    else:
                        self.warn("Sample Name not found or empty",
                                numline=self._numline, line=line)
                    return 0
                elif split_row[0] == self._identifiers['sampleid']:
                    if len(split_row) > 1:
                        self._currentsampleid = split_row[1]
                        logger.info("Current Sample ID: {}".format(self._currentsampleid))
                    else:
                        self.warn("Sample ID not found or empty",
                                numline=self._numline, line=line)
                    return 0
                else: 
                    return 0
                
            # check for headers
            if not self._currentresultsheader:
                if self._identifiers['header'] in split_row:
                    self._currentresultsheader = split_row
                    logger.info("Current Results Header: {}".format(self._currentresultsheader))
                    return 0
                else:
                    return 0
            
            # resutls parsing
            if split_row[0].isdigit():
                logger.info("Parsing results for Sample ID: {}".format(self._currentsampleid))
                logger.info("Result Row: {}".format(split_row))
                _results.update(dict(zip(self._currentresultsheader, split_row)))

                result = _results[_results['DefaultResult']]
                column_name = _results['DefaultResult']
                result = self.zeroValueDefaultInstrumentResults(
                                                        column_name, result, line)
                _results[_results['DefaultResult']] = result
                
                self._currentanalysiskw = self.resolve_analysis_keyword()
                logger.info("Current Analysis Keyword: {}".format(self._currentanalysiskw))

                self._addRawResult(self._currentsampleid,
                                values={self._currentanalysiskw: _results},
                                override=False)
                logger.info("Added raw result for Sample ID: {} with values: {}".format(
                    self._currentsampleid, self._addRawResult))
            else:
                self._currentresultsheader = ''
                self._currentsampleid = ''
                self._currentsamplename = ''
                self._currentsampletype = ''
                return 0

        def zeroValueDefaultInstrumentResults(self, column_name, result, line):
            result = str(result)
            if result.startswith('--') or result == '' or result == 'ND':
                return 0.0

            try:
                result = float(result)
                if result < 0.0:
                    result = 0.0
            except ValueError:
                self.err(
                    "No valid number ${result} in column (${column_name})",
                    mapping={"result": result,
                            "column_name": column_name},
                    numline=self._numline, line=line)
                return
            return result
        
        def resolve_analysis_keyword(self):
            if not self._currentsampletype or not self._currentsamplename:
                return ''
            
            sampletype = 'ST'
            sampleinyection = "1A"
            if self._currentsampletype == '0:Unknown':
                sampletype = 'M'
            
            last_char_in_name = self._currentsamplename[-1]
            before_last_char_in_name = self._currentsamplename[-2]
            
            # if last char is a letter a, b or c and before last is a digit
            if last_char_in_name.upper() in ['A', 'B', 'C'] and before_last_char_in_name.isdigit():
                sampleinyection = str(before_last_char_in_name) + last_char_in_name.upper()
            else:
                logger.info("Sample Name does not conform to expected format: {}".format(self._currentsamplename))
                logger.info("Using default injection identifier: 1A")
                logger.info("Last char: {}, Before last char: {}".format(last_char_in_name, before_last_char_in_name))
                logger.info("conditions: last char is in [A, B, C]: {} and before last is digit: {}".format(
                    last_char_in_name.upper() in ['A', 'B', 'C'], before_last_char_in_name.isdigit()))
                
            return "INY_" +sampletype + "_" + sampleinyection
        
class quantitativeResultsImportInterface(CustomAnalysisResultImporter):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Shimadzu HPLC-PDA Nexera Quantitive Result Importer"

    def __init__(self, context):
        self.context = context
        self.override = [False, False]
        self.allowed_sample_states = ALLOWED_SAMPLE_STATES
        self.allowed_analysis_states = ALLOWED_ANALYSIS_STATES
        
    def get_automatic_importer(self, instrument, parser, **kw):
            """Called during automated results import
            """
            # initialize the base class with the required parameters
            logger.info("Getting automatic importer for instrument: {}".format(instrument.Title()))
            super(quantitativeResultsImportInterface, self).__init__(
                parser, self.context,
                override=self.override,
                allowed_sample_states=self.allowed_sample_states,
                allowed_analysis_states=self.allowed_analysis_states,
                instrument_uid=api.get_uid(instrument))
            return self

    def get_automatic_parser(self, infile):
            """Called during automated results import

            Returns the parser to be used by default for the file passed in when
            automatic results import for this instrument interface is enabled
            """
            logger.info("Getting automatic parser for file: {}".format(infile.filename))
            return quantitiveResultParser(infile)

    def Import(self, context, request):
            """Called from the manual import view
            """
            logger.info("Starting manual import process")
            # Get the uploaded results file
            infile = request.form.get("instrument_results_file")
            # Sample states to apply results?
            allowed_states = request.form.get("artoapply", "received")
            # The selected instrument
            instrument_uid = request.form.get("instrument", None)

            if not infile:
                return json.dumps({
                    "errors": ["No file selected", ],
                    "log": [],
                    "warns": []
                })

            # Override results?
            override = request.form.get("results_override", "nooverride")
            self.override = get_instrument_import_override(override)

            # allowed states
            self.allowed_sample_states = get_instrument_import_ar_allowed_states(
                allowed_states)

            # instrument
            instrument = api.get_object(instrument_uid)
            parser = self.get_automatic_parser(infile)
            importer = self.get_automatic_importer(instrument, parser)

            importer.process()

            return json.dumps({
                "errors": self.errors,
                "log": self.logs,
                "warns": self.warns,
            })
            
class quantitiveResultParser(InstrumentCSVResultsFileParser):
        """Parse the import file and fills the raw results dictionary
        """
        def __init__(self, infile):
            InstrumentCSVResultsFileParser.__init__(self, infile)
            self._currentresultsheader = []
            self._currentanalysiskw = ''
            self._numline = 0
            self._currentsampleid = ''
            self._currentsamplename = ''
            self._currentsampletype = ''
            self._identifiers = {
                'header': "Peak#",
                'result': "Conc.",
                'sampletype': "Sample Type",
                'samplename': "Sample Name",
                'sampleid': "Sample ID",
            }
            self._mapped_interim = {
                    "Area": "area",
                    "Ret. Time": "ret_time",
                    "NTP(USP)":"ntp_usp",
                    "Vial#":"vial_number",
                }
            self._missing_headers = []
            self._mapped_api_samples = {}
            self._important_headers = ['Sample ID', 'Sample Name', 'Sample Type', 'Date Acquired', 'Conc.']
            logger.info("NexeraIfaParser initialized")
        
        def _parseline(self, line):
            return self.parse_TSVline(line)

        def parse_TSVline(self, line):
            """ Parses result lines
            """

            split_row = [token.strip() for token in line.split('\t')]
            _results = {'DefaultResult': self._identifiers['result']}
            
            # ID# 1
            if split_row[0] == 'ID#':
                return 0
            # Name	CBDV - cannabidivarin
            elif split_row[0] == 'Name':
                if split_row[1]:
                    self._currentpeakname = split_row[1]
                    return 0
                else:
                    self.warn("Peak Name not found or empty",
                            numline=self._numline, line=line)
            
            # Data Filename	Sample Name	Sample ID	Sample Type	Level#
            elif 'Sample ID' in split_row:
                
                split_row.insert(0, '#')
                self._currentresultsheader = split_row
                self._missing_headers = [h for h in self._important_headers if h not in self._currentresultsheader]
                if self._missing_headers:
                    self.err("Missing important headers: {}".format(self._missing_headers),
                                numline=self._numline, line=line) 
                return 0
            
            # 1	QC PREP A_QC PREP A_009.lcd	QC PREP
            elif split_row[0].isdigit() and not self._missing_headers:
                _results.update(dict(zip(self._currentresultsheader, split_row)))
                
                date_acquired = _results.get('Date Acquired', '').strip()
                # mount_translations = {
                #     "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
                #     "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
                #     "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
                # }          

                
                # for es, en in mount_translations.items():
                #     date_acquired = date_acquired.replace(es, en)
                    
                formats = (
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%d-%b-%y %I:%M:%S %p",
                    "%d-%b-%y %I:%M:%S %p",
                )

                da = next(
                    (
                        datetime.strptime(date_acquired, fmt)
                        for fmt in formats
                        if _safe_parse(date_acquired, fmt)
                    ),
                    None
                )

                if not da:
                    self.err(
                        "Invalid Output Time format %s" % date_acquired,
                        numline=self._numline
                    )
                    return 0
                self._header['Output Date'] = da
                self._header['Output Time'] = da
                result = _results[_results['DefaultResult']]
                column_name = _results['DefaultResult']
                _results['DateTime'] = da
                result = self.zeroValueDefaultInstrumentResults(
                    column_name, result, line)
                
                if not result:
                    #logger.info("Result is zero or invalid, skipping entry for Sample ID: {}".format(result))
                    return 0
                
                #logger.info("Result Row: {}".format(_results))
                default_number = extract_final_number_from_string(_results['Sample Name'])
                if not default_number:
                    self.err("Could not extract default number from Sample Name: {}".format(_results['Sample Name']),
                            numline=self._numline, line=line)
                    return 0
                _results['number_line'] = default_number

                _results[_results['DefaultResult']] = result
                
                for key, new_key in self._mapped_interim.items():
                    _results[new_key] = _results.get(key)
                
                _results['api_name'] = self._currentpeakname
                self._currentanalysiskw = self.resolve_analysis_keyword(_results)
                self._currentsampleid = _results['Sample ID']
                
                peak_key = self._currentsampleid + "-" + self._currentpeakname
                if peak_key in self._mapped_api_samples:
                    self._current_partition = self._mapped_api_samples[peak_key]
                else:
                    normalized_peak_name = normalize_text(self._currentpeakname)
                    self._current_partition = get_sid_from_api(self._currentsampleid, normalized_peak_name)
                    self._mapped_api_samples[peak_key] = self._current_partition
                    logger.info("current partition id info %s", self._current_partition)

                self._addRawResult(self._current_partition or self._currentsampleid,
                                values={self._currentanalysiskw: _results},
                                override=False)
                logger.info("Added raw result for Sample ID: {}, keyword: {} with result: {}".format(
                        self._currentsampleid, self._currentanalysiskw, result))

        def zeroValueDefaultInstrumentResults(self, column_name, result, line):
            result = str(result)
            if result.startswith('--') or result == '' or result == 'ND':
                return 0.0

            try:
                result = float(result)
                if result < 0.0:
                    result = 0.0
            except ValueError:
                self.err(
                    "No valid number ${result} in column (${column_name})",
                    mapping={"result": result,
                            "column_name": column_name},
                    numline=self._numline, line=line)
                return
            return result
        
        def resolve_analysis_keyword(self, results_line):
            if not results_line['Sample Type'] or not results_line['number_line']:
                return ''
            
            sample_type = results_line['Sample Type']
            if sample_type.startswith('Standard'):
                sample_type_abrev = 'ST'
            else:
                sample_type_abrev = 'UNK'
                
            default_number_str = str(results_line['number_line']).zfill(2)
            return "CONC_" +sample_type_abrev + "_" + default_number_str

def get_ar_by_arid(arid):
    query = {"getId": arid, "review_state": ALLOWED_SAMPLE_STATES}
    ar = api.search(query, SAMPLE_CATALOG)
    if not ar or len(ar) == 0:
        return None
    
    return api.get_object(ar[0])
    
def get_analyses_by_sid(arid):

    ar = get_ar_by_arid(arid)
    analyses = [analysis.getObject() for analysis in ar.getAnalyses()]
    return list(filter(is_analysis_allowed, analyses))
        
def is_analysis_allowed(analysis):
    """Filter analyses that match the import criteria
    """
    # Routine Analyses must be in the allowed WF states
    status = api.get_workflow_status_of(analysis)
    if status in ALLOWED_ANALYSIS_STATES:
        return True
    return False 

def get_sid_from_api(sid, api_name):
    ar = get_ar_by_arid(sid)
    if not ar:
        return
    
    descendants = ar.getDescendants()
    if not descendants:
        return sid
    
    part = next((part.getId() for part in descendants if normalize_text(part.getSampleTypeTitle()) == api_name), None)
    logger.info("Partitionn that have the peak name '%s' is '%s'", api_name, part)
    return part
    
def normalize_text(text):
    if isinstance(text, str):
        text = text.decode('utf-8', 'ignore')
    text = text.upper()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(
        c for c in text
        if unicodedata.category(c) != 'Mn'
    )
    text = re.sub(r'[^A-Z0-9]+', '_', text)
    text = text.strip('_')

    return text

def _safe_parse(value, fmt):
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError as err:
        logger.info(err)
        #logger.info("%s, Ok format: %s for datetime 14/12/2026 12:46:35 PM is: '%s'", err, fmt, datetime.strftime(datetime(2026,1,13,4,2,9), fmt))
        return False