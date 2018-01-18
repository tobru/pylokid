#!/usr/bin/env python3

""" Thy pylokid main program """

import logging
import os
import time

import requests
from dotenv import find_dotenv, load_dotenv

# local classes
from library.emailhandling import EmailHandling
from library.lodur import Lodur
from library.mqtt import MQTTClient
from library.pdf_extract import PDFHandling
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
MQTT_SERVER = os.getenv("MQTT_SERVER")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASE_TOPIC = os.getenv("MQTT_BASE_TOPIC", "pylokid")
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
        MQTT_BASE_TOPIC,
    )

    # Initialize PDF Parser
    pdf = PDFHandling()

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

                        # publish Einsatz on MQTT
                        mqtt_client.send_message(f_type, f_id, pdf_data, pdf_file)

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

                        # Update entry in Lodur with parse PDF data
                        lodur_client.einsatzprotokoll(f_id, pdf_data, webdav_client)

                        # Einsatz finished - publish on MQTT
                        mqtt_client.send_message(f_type, f_id, pdf_data, pdf_file)
                    else:
                        logger.error(
                            '[%s] Cannot process Einsatzprotokoll as there is no Lodur ID',
                            f_id
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
