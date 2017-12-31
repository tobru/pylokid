#!/usr/bin/env python3

""" Thy pylokid main program """

import logging
import os
import time

import requests
from dotenv import find_dotenv, load_dotenv

# local classes
from emailhandling import EmailHandling
from lodur import Lodur
from mqtt import MQTTClient
from pdf_extract import PDFHandling
from webdav import WebDav

# TODO replace by IMAP idle
_INTERVAL = 10

# Configuration
load_dotenv(find_dotenv())
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")
WEBDAV_URL = os.getenv("WEBDAV_URL")
WEBDAV_USERNAME = os.getenv("WEBDAV_USERNAME")
WEBDAV_PASSWORD = os.getenv("WEBDAV_PASSWORD")
WEBDAV_BASEDIR = os.getenv("WEBDAV_BASEDIR")
TMP_DIR = os.getenv("TMP_DIR", "/tmp")
MQTT_SERVER = os.getenv("MQTT_SERVER")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
LODUR_USER = os.getenv("LODUR_USER")
LODUR_PASSWORD = os.getenv("LODUR_PASSWORD")
LODUR_BASE_URL = os.getenv("LODUR_BASE_URL")
HEARTBEAT_URL = os.getenv("HEARTBEAT_URL")

def main():
    """ main """

    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('pylokid')

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

    # Initialize MQTT Sessions
    mqtt_client = MQTTClient(
        MQTT_SERVER,
        MQTT_USER,
        MQTT_PASSWORD,
    )

    # Initialize PDF Parser
    pdf = PDFHandling()

    while True:
        attachments = {}
        num_messages, msg_ids = imap_client.search_emails()
        if num_messages:
            attachments = imap_client.store_attachments(msg_ids)

        if attachments:
            for subject in attachments:
                f_type, f_id = imap_client.parse_subject(subject)
                file_name = attachments[subject]
                webdav_client.upload(file_name, f_id)

                # Take actions - depending on the type
                if f_type == 'Einsatzausdruck_FW':
                    lodur_id = webdav_client.get_lodur_id(f_id)
                    if lodur_id:
                        logger.info(
                            'Einsatzrapport ' + f_id + ' already created in Lodur: ' + lodur_id
                        )
                        # Upload Alarmdepesche as it could contain more information than the first one
                        lodur_client.einsatzrapport_alarmdepesche(
                            lodur_id,
                            os.path.join(TMP_DIR, file_name),
                        )
                    else:
                        # this is real - publish Einsatz on MQTT
                        # TODO publish more information about the einsatz - coming from the PDF
                        mqtt_client.send_message(f_type, f_id)

                        # get as many information from PDF as possible
                        pdf_data = pdf.extract_einsatzausdruck(
                            os.path.join(TMP_DIR, file_name),
                            f_id,
                        )

                        # create new Einsatzrapport in Lodur
                        logger.info('Creating Einsatzrapport in Lodur for ' + f_id)
                        lodur_id = lodur_client.einsatzrapport(
                            f_id,
                            pdf_data,
                        )
                        # store lodur id in webdav
                        webdav_client.store_lodur_id(lodur_id, f_id)

                        # upload Alarmdepesche to Lodur
                        lodur_client.einsatzrapport_alarmdepesche(
                            lodur_id,
                            os.path.join(TMP_DIR, file_name),
                        )
                elif f_type == 'Einsatzprotokoll':
                    # Einsatz finished - publish on MQTT
                    mqtt_client.send_message(f_type, f_id)

                    lodur_id = webdav_client.get_lodur_id(f_id)
                    if lodur_id:
                        logger.info('Uploading Einsatzprotokoll to Lodur')
                        lodur_client.einsatzrapport_alarmdepesche(
                            lodur_id,
                            os.path.join(TMP_DIR, file_name),
                        )
                        pdf_data = pdf.extract_einsatzprotokoll(
                            os.path.join(TMP_DIR, file_name),
                            f_id,
                        )
                        # only update when parsing was successfull
                        if pdf_data:
                            logger.info('Updating Einsatzrapport with data from PDF - not yet implemented')
                        else:
                            logger.info('Updating Einsatzrapport not possible - PDF parsing failed')
                    else:
                        logger.error('Cannot process Einsatzprotokoll as there is no Lodur ID')
                else:
                    logger.error('Unknown type: ' + f_type)

        # send heartbeat
        requests.get(HEARTBEAT_URL)
        # repeat every
        time.sleep(_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Byebye")
