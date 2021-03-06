#!/usr/bin/env python3

""" Thy pylokid main program """

import logging
import os
import time

import requests
from dotenv import find_dotenv, load_dotenv
from pushover import Client

# local classes
from library.emailhandling import EmailHandling
from library.lodur import Lodur
from library.pdftotext import PDFParsing
from library.webdav import WebDav

# Configuration
load_dotenv(find_dotenv())
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")
IMAP_CHECK_INTERVAL = os.getenv("IMAP_CHECK_INTERVAL", "10")
WEBDAV_URL = os.getenv("WEBDAV_URL")
WEBDAV_USERNAME = os.getenv("WEBDAV_USERNAME")
WEBDAV_PASSWORD = os.getenv("WEBDAV_PASSWORD")
WEBDAV_BASEDIR = os.getenv("WEBDAV_BASEDIR")
TMP_DIR = os.getenv("TMP_DIR", "/tmp")
LODUR_USER = os.getenv("LODUR_USER")
LODUR_PASSWORD = os.getenv("LODUR_PASSWORD")
LODUR_BASE_URL = os.getenv("LODUR_BASE_URL")
HEARTBEAT_URL = os.getenv("HEARTBEAT_URL")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PYLOKID_VERSION = "2.1.2"

def main():
    """ main """

    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('pylokid')
    logger.info('Starting pylokid version %s', PYLOKID_VERSION)

    # Initialize IMAP Session
    imap_client = EmailHandling(
        IMAP_SERVER,
        IMAP_USERNAME,
        IMAP_PASSWORD,
        IMAP_MAILBOX,
        TMP_DIR,
    )

    # Initialize Lodur Session
    lodur_client = Lodur(
        LODUR_BASE_URL,
        LODUR_USER,
        LODUR_PASSWORD,
    )

    # Initialize WebDav Session
    webdav_client = WebDav(
        WEBDAV_URL,
        WEBDAV_USERNAME,
        WEBDAV_PASSWORD,
        WEBDAV_BASEDIR,
        TMP_DIR,
    )

    # Initialize Pushover
    pushover = Client(
        user_key=PUSHOVER_USER_KEY,
        api_token=PUSHOVER_API_TOKEN
    )

    # Initialize PDF Parser
    pdf = PDFParsing()

    # Main Loop
    while True:
        attachments = {}
        num_messages, msg_ids = imap_client.search_emails()
        if num_messages:
            attachments = imap_client.store_attachments(msg_ids)

        if attachments:
            for subject in attachments:
                f_type, f_id = imap_client.parse_subject(subject)
                file_name = attachments[subject]

                # Upload file to cloud
                webdav_client.upload(file_name, f_id)

                # Take actions - depending on the type
                if f_type == 'Einsatzausdruck_FW':
                    logger.info('[%s] Processing type %s', f_id, f_type)
                    lodur_data = webdav_client.get_lodur_data(f_id)

                    if lodur_data:
                        logger.info(
                            '[%s] Einsatzrapport already created in Lodur', f_id
                        )
                        # Upload Alarmdepesche as it could contain more information
                        # than the first one
                        lodur_client.einsatzrapport_alarmdepesche(
                            f_id,
                            os.path.join(TMP_DIR, file_name),
                            webdav_client,
                        )

                    else:
                        ## Here we get the initial Einsatzauftrag - Time to run
                        # get as many information from PDF as possible
                        pdf_file = os.path.join(TMP_DIR, file_name)
                        pdf_data = pdf.extract_einsatzausdruck(
                            pdf_file,
                            f_id,
                        )

                        # publish Einsatz on Pushover
                        logger.info(
                            '[%s] Publishing message on Pushover', f_id
                        )
                        pushover.send_message(
                            "Einsatz {} eröffnet: {}\n\n* Ort: {}\n* Melder: {}\n* Hinweis: {}\n* {}\n\n{}\n\n{}".format(
                                f_id,
                                pdf_data['einsatz'],
                                pdf_data['ort'],
                                pdf_data['melder'].replace('\n',' '),
                                pdf_data['hinweis'],
                                pdf_data['sondersignal'],
                                pdf_data['disponierteeinheiten'],
                                pdf_data['bemerkungen'],
                            ),
                            title="Feuerwehr Einsatz",
                            url="https://www.google.com/maps/search/?api=1&query={}".format(pdf_data['ort']),
                            url_title="Ort auf Karte suchen"
                        )

                        # create new Einsatzrapport in Lodur
                        lodur_client.einsatzrapport(
                            f_id,
                            pdf_data,
                            webdav_client,
                        )

                        # upload Alarmdepesche PDF to Lodur
                        lodur_client.einsatzrapport_alarmdepesche(
                            f_id,
                            os.path.join(TMP_DIR, file_name),
                            webdav_client,
                        )

                elif f_type == 'Einsatzprotokoll':
                    logger.info('[%s] Processing type %s', f_id, f_type)

                    lodur_data = webdav_client.get_lodur_data(f_id)
                    if lodur_data:
                        # Upload Einsatzprotokoll to Lodur
                        lodur_client.einsatzrapport_alarmdepesche(
                            f_id,
                            os.path.join(TMP_DIR, file_name),
                            webdav_client,
                        )

                        # Parse the Einsatzprotokoll PDF
                        pdf_file = os.path.join(TMP_DIR, file_name)
                        pdf_data = pdf.extract_einsatzprotokoll(
                            pdf_file,
                            f_id,
                        )

                        # Update entry in Lodur with parsed PDF data
                        lodur_client.einsatzprotokoll(f_id, pdf_data, webdav_client)

                        # Einsatz finished - publish on pushover
                        logger.info(
                            '[%s] Publishing message on Pushover', f_id
                        )
                        pushover.send_message(
                            "Einsatz {} beendet".format(f_id),
                            title="Feuerwehr Einsatz beendet",
                        )

                    else:
                        logger.error(
                            '[%s] Cannot process Einsatzprotokoll as there is no Lodur ID',
                            f_id
                        )

                # This is usually a scan from the Depot printer
                elif f_type == 'Einsatzrapport':
                    logger.info('[%s] Processing type %s', f_id, f_type)

                    # Attach scan in Lodur if f_id is available
                    if f_id != None:
                        pdf_file = os.path.join(TMP_DIR, file_name)
                        lodur_client.einsatzrapport_scan(f_id, pdf_file, webdav_client)

                    logger.info(
                        '[%s] Publishing message on Pushover', f_id
                    )

                    pushover.send_message(
                        "Scan {} wurde bearbeitet und in Cloud geladen".format(f_id),
                        title="Feuerwehr Scan bearbeitet",
                    )
                else:
                    logger.error('[%s] Unknown type: %s', f_id, f_type)

        # send heartbeat
        requests.get(HEARTBEAT_URL)
        # repeat every
        logger.info('Waiting %s seconds until next check', IMAP_CHECK_INTERVAL)
        time.sleep(int(IMAP_CHECK_INTERVAL))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Byebye")
