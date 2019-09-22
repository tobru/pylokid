import re
import logging
from pprint import pprint
from pathlib import Path
from library.pdftotext import PDFParsing

PATH = '/home/tobru/Documents/Feuerwehr/Stab/Fourier/Einsatzdepeschen/2019'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

PDF = PDFParsing()

for path in Path(PATH).glob('**/Einsatzausdruck*.pdf'):
    file = str(path)
    print(file)
    f_id = re.search('.*(F[0-9]{8})_.*', file).group(1)
    print(f_id)
    pprint(PDF.extract_einsatzausdruck(file, f_id))

"""
for path in Path(PATH).glob('**/Einsatzprotokoll*.pdf'):
    file = str(path)
    print(file)
    f_id = re.search('.*(F[0-9]{8})_.*', file).group(1)
    print(f_id)
    pprint(PDF.extract_einsatzprotokoll(file, f_id))
"""
