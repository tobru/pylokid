import re
import logging
from pprint import pprint
from pathlib import Path
from library.pdf_extract import PDFHandling

PATH = '/tmp/pylokid'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

PDF = PDFHandling()

for path in Path(PATH).glob('**/*.pdf'):
    file = str(path)
    f_id = re.search('.*(F[0-9]{8})_.*', file).group(1)
    pprint(PDF.extract_einsatzausdruck(file, f_id))
