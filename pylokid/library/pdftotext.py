#!/usr/bin/env python3

""" extracts data from ELZ PDFs using Poppler pdftotext """

import subprocess
import logging


class PDFParsing:
    """ PDF parsing """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("PDF parsing based on pdftotext loaded")

    def extract(self, f_id, file, datafields):

        self.logger.info("[%s] parsing PDF file %s", f_id, file)

        data = {}

        for field, coordinate in datafields.items():

            # x-coordinate of the crop area top left corner
            x = coordinate["xMin"]

            # y-coordinate of the crop area top left corner
            y = coordinate["yMin"]

            # width of crop area in pixels
            w = coordinate["xMax"] - coordinate["xMin"]

            # height of crop area in pixels
            h = coordinate["yMax"] - coordinate["yMin"]

            self.logger.debug(
                "[%s] Computed command for field %s: %s",
                f_id,
                field,
                "pdftotext -f 1 -l 1 -x {} -y {} -W {} -H {}".format(x, y, w, h),
            )

            scrapeddata = subprocess.Popen(
                [
                    "/usr/bin/pdftotext",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    "-x",
                    str(x),
                    "-y",
                    str(y),
                    "-W",
                    str(w),
                    "-H",
                    str(h),
                    file,
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            stdout, _ = scrapeddata.communicate()

            ## TODO: fixup some fields (lowercase, remove unnecessary \n)
            if "edit" in coordinate and coordinate["edit"] == "title":
                data[field] = stdout.rstrip().title()
            else:
                data[field] = stdout.rstrip()

        # sanity check to see if we can correlate the f_id
        if f_id == data["auftrag"]:
            self.logger.debug("[%s] ID matches in PDF", f_id)
            return data
        else:
            self.logger.error(
                '[%s] ID does not match in PDF: "%s"', f_id, data["auftrag"]
            )
            return False

    def extract_einsatzausdruck(self, file, f_id):
        """ extracts information from Einsatzausdruck using external pdftotext """

        self.logger.debug("[%s] Parsing PDF: %s", f_id, file)

        # Get them using 'pdftotext -bbox'
        # y = row
        # x = column: xMax 450 / 590 means full width
        coordinates = {
            "auftrag": {
                "xMin": 70,
                "yMin": 47,
                "xMax": 120,
                "yMax": 58,
            },
            "datum": {
                "xMin": 190,
                "yMin": 47,
                "xMax": 239,
                "yMax": 58,
            },
            "zeit": {
                "xMin": 190,
                "yMin": 59,
                "xMax": 215,
                "yMax": 70,
            },
            "melder": {
                "xMin": 304,
                "yMin": 47,
                "xMax": 446,
                "yMax": 70,
                "edit": "title",
            },
            "erfasser": {
                "xMin": 448,
                "yMin": 59,
                "xMax": 478,
                "yMax": 70,
            },
            # big field until "Disponierte Einheiten"
            "bemerkungen": {
                "xMin": 28,
                "yMin": 112,
                "xMax": 590,
                "yMax": 350,
            },
            "disponierteeinheiten": {
                "xMin": 28,
                "yMin": 366,
                "xMax": 450,
                "yMax": 376,
            },
            "einsatz": {
                "xMin": 76,
                "yMin": 690,
                "xMax": 450,
                "yMax": 703,
            },
            "sondersignal": {
                "xMin": 76,
                "yMin": 707,
                "xMax": 450,
                "yMax": 721,
            },
            "ort": {
                "xMin": 76,
                "yMin": 732,
                "xMax": 590,
                "yMax": 745,
            },
            "hinweis": {
                "xMin": 76,
                "yMin": 773,
                "xMax": 450,
                "yMax": 787,
            },
        }

        return self.extract(f_id, file, coordinates)

    def extract_einsatzprotokoll(self, file, f_id):
        """ extracts information from Einsatzprotokoll using external pdftotext """

        self.logger.debug("[%s] Parsing PDF: %s", f_id, file)

        # Get them using 'pdftotext -bbox'
        # y = row
        # x = column: xMax 450 / 590 means full width
        coordinates = {
            "auftrag": {
                "xMin": 192,
                "yMin": 132,
                "xMax": 238,
                "yMax": 142,
            },
            "angelegt": {
                "xMin": 192,
                "yMin": 294,
                "xMax": 226,
                "yMax": 304,
            },
            "dispo": {
                "xMin": 192,
                "yMin": 312,
                "xMax": 226,
                "yMax": 322,
            },
            "ausgerueckt": {
                "xMin": 192,
                "yMin": 331,
                "xMax": 226,
                "yMax": 341,
            },
            "vorort": {
                "xMin": 192,
                "yMin": 348,
                "xMax": 226,
                "yMax": 358,
            },
        }

        return self.extract(f_id, file, coordinates)
