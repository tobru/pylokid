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

        splited = self.convert(file).splitlines()

        # sanity check to see if we can correlate the f_id
        if f_id == splited[14]:
            self.logger.info('[%s] ID found in PDF', f_id)
        else:
            self.logger.error('[%s] ID not found in PDF', f_id)
            return False

        # search some well-known words for later positional computation
        try:    
            index_bemerkungen = splited.index('Bemerkungen')
            index_dispo = splited.index('Disponierte Einheiten')
            index_hinweis = splited.index('Hinweis')
        except IndexError:
            self.logger.error('[%s] PDF file doesn\'t look like a Einsatzausdruck', f_id)
            return False

        # get length of bemerkungen field
        # it lives between the line which contains 'Bemerkungen' and
        # the line 'Disponierte Einheiten'
        length_bemerkungen = index_dispo - index_bemerkungen - 1

        data = {
            'auftrag': splited[14],
            'datum': splited[15],
            'zeit': splited[16],
            'melder': self.concatenate_to_multiline_string(splited, 18, 19),
            'erfasser': splited[20],
            'bemerkungen': self.concatenate_to_multiline_string(
                splited,
                index_bemerkungen,
                index_bemerkungen + length_bemerkungen
            ),
            'einsatz': splited[index_dispo+5],
            'plzort': splited[index_dispo+8].title(),
            'strasse': splited[index_dispo+9].title(),
            #'objekt': splited[],
            'hinweis': splited[index_hinweis+2]
        }
        return data

    def extract_einsatzprotokoll(self, file, f_id):
        """ extracts as many information from the parsed Einsatzprotokoll as possible """

        splited = self.convert(file).splitlines()

        # sanity check to see if we can correlate the f_id
        if f_id == splited[26]:
            self.logger.info('[%s] ID found in PDF', f_id)
        else:
            self.logger.error('[%s] ID not found in PDF', f_id)
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
