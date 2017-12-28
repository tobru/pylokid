#!/usr/bin/env python3

import io
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import HTMLConverter,TextConverter,XMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

def concatenate_to_multiline_string(data, start, end):
    res = ''
    counter = start
    while counter <= end:
        res += data[counter] + '\n'
        counter += 1
    return res

def convert(file):
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

    convertedPDF = output.getvalue()

    infile.close()
    converter.close()
    output.close()
    return convertedPDF

def get_einsatzausdruck(file):
    """ extracts as many information from the parsed Einsatzausdruck as possible """

    splited = convert(file).splitlines()
    # sometimes the "second part - below map" doesnt start at the same index
    # depending on the lenght of the bemerkungen
    # therefore we compute a simple offset for the second part
    # TODO: make it better
    second_part_offset = 29 - splited.index('Disponierte Einheiten')
    data = {
        'auftrag': splited[14],
        'datum': splited[15],
        'zeit': splited[16],
        'melder': concatenate_to_multiline_string(splited,18,19),
        'erfasser': splited[20],
        'bemerkungen': concatenate_to_multiline_string(splited,23,28),
        'einsatz': splited[34-second_part_offset],
        'ort': splited[37-second_part_offset],
        'strasse': splited[38-second_part_offset],
        #'objekt': splited[],
        'hinweis': splited[50-second_part_offset]
    }
    return data

def get_einsatzprotokoll(file):
    """ extracts as many information from the parsed Einsatzprotokoll as possible """

    splited = convert(file).splitlines()
    data = {
        'auftrag': splited[26],
        'datum': splited[25],
        'angelegt': splited[28],
        'disposition': splited[30],
        'ausgerueckt': splited[32],
        'anort': splited[33],
    }
    return data
