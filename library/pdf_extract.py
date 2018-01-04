#!/usr/bin/env python3

""" extracts data from ELZ PDFs """

import io
import logging
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

class PDFHandling:
    """ PDF handling like parsing """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # less logging for pdfminer - more is not needed
        logger_doc = logging.getLogger('pdfminer.pdfdocument')
        logger_doc.setLevel(logging.WARNING)
        logger_page = logging.getLogger('pdfminer.pdfpage')
        logger_page.setLevel(logging.WARNING)
        logger_interp = logging.getLogger('pdfminer.pdfinterp')
        logger_interp.setLevel(logging.WARNING)
        logger_psparser = logging.getLogger('pdfminer.psparser')
        logger_psparser.setLevel(logging.WARNING)
        logger_cmapdb = logging.getLogger('pdfminer.cmapdb')
        logger_cmapdb.setLevel(logging.WARNING)
        logger_pdfparser = logging.getLogger('pdfminer.pdfparser')
        logger_pdfparser.setLevel(logging.WARNING)

    def concatenate_to_multiline_string(self, data, start, end):
        """ concatenates multiple lines to a single multiline string """

        res = ''
        counter = start
        while counter <= end:
            res += data[counter] + '\n'
            counter += 1
        return res

    def convert(self, file):
        """ converts the PDF to a multiline string """

        pagenums = set()
        manager = PDFResourceManager()
        codec = 'utf-8'
        caching = True

        output = io.StringIO()
        converter = TextConverter(manager, output, codec=codec, laparams=LAParams())

        interpreter = PDFPageInterpreter(manager, converter)
        infile = open(file, 'rb')

        for page in PDFPage.get_pages(infile, pagenums, caching=caching, check_extractable=True):
            interpreter.process_page(page)

        converted_pdf = output.getvalue()

        infile.close()
        converter.close()
        output.close()
        return converted_pdf

    def extract_einsatzausdruck(self, file, f_id):
        """ extracts as many information from the parsed Einsatzausdruck as possible """

        converted = self.convert(file)
        splited = converted.splitlines()

        self.logger.debug('[%s] Parsed PDF raw: %s', f_id, converted)

        # search some well-known words for later positional computation
        try:
            index_erfasser = splited.index('Erfasser')
            index_auftrag = splited.index('Auftrag')
            index_bemerkungen = splited.index('Bemerkungen')
            index_dispo = splited.index('Disponierte Einheiten')
            index_einsatz = splited.index('Einsatz')
            index_hinweis = splited.index('Hinweis')
            index_maps = splited.index('Google Maps')
        except IndexError:
            self.logger.error('[%s] PDF file does not look like a Einsatzausdruck', f_id)
            return False

        # the PDF parsing not always produces the same output
        # let's define the already known output
        if index_bemerkungen == 6:
            # get length of bemerkungen field
            # it lives between the line which contains 'Bemerkungen' and
            # the line 'Disponierte Einheiten'
            length_bemerkungen = index_auftrag - index_bemerkungen - 1
            erfasser = splited[index_dispo - 2]
            # sometimes there is just a phone number for the field melder but on
            # the second line, so the lines vary for erfasser and melder
            if index_dispo - index_erfasser == 10:
                melder = splited[index_dispo - 4] + ', ' + splited[index_dispo - 3]
            else:
                melder = splited[index_dispo - 4]
        elif index_bemerkungen == 21 or index_bemerkungen == 22:
            length_bemerkungen = index_dispo - index_bemerkungen - 1
            erfasser = splited[index_bemerkungen - 2]
            if index_bemerkungen - index_erfasser == 10:
                melder = splited[index_bemerkungen - 4] + ', ' + splited[index_bemerkungen - 3]
            else:
                melder = splited[index_bemerkungen - 4]
        else:
            self.logger.error('[%s] Unknown parser output', f_id)
            return False

        # sanity check to see if we can correlate the f_id
        auftrag = splited[index_erfasser + 2]
        if f_id == auftrag:
            self.logger.info('[%s] ID matches in PDF', f_id)
        else:
            self.logger.error('[%s] ID does not match in PDF: "%s"', f_id, auftrag)
            return False



        # try to find out if there is a hinweis
        # if yes, the difference between the indexes is 4, else it's shorter
        if index_maps - index_hinweis == 4:
            hinweis = splited[index_hinweis+2]
        else:
            hinweis = ''

        data = {
            'auftrag': auftrag,
            'datum': splited[index_erfasser + 3],
            'zeit': splited[index_erfasser + 4],
            'melder': melder,
            'erfasser': erfasser,
            'bemerkungen': self.concatenate_to_multiline_string(
                splited,
                index_bemerkungen + 1,
                index_bemerkungen + length_bemerkungen
            ).rstrip(),
            'einsatz': splited[index_einsatz - 6],
            'sondersignal': splited[index_einsatz - 5],
            'ort': splited[index_einsatz - 3].title(),
            'strasse': splited[index_einsatz - 2].title(),
            #'objekt': splited[],
            'hinweis': hinweis,
        }
        return data

    def extract_einsatzprotokoll(self, file, f_id):
        """ extracts as many information from the parsed Einsatzprotokoll as possible """

        splited = self.convert(file).splitlines()

        # sanity check to see if we can correlate the f_id
        if f_id == splited[26]:
            self.logger.info('[%s] ID matches in PDF', f_id)
        else:
            self.logger.error('[%s] ID does not match in PDF', f_id)
            return False

        data = {
            'auftrag': splited[26],
            'datum': splited[25],
            'angelegt': splited[28],
            'disposition': splited[30],
            'ausgerueckt': splited[32],
            'anort': splited[33],
        }
        return data
