#!/usr/bin/env python3

""" Thy pylokid main program """

import os
import re
from datetime import datetime
import asyncio
import logging
import time
import requests
import email
import email.parser
import imaplib
import aioeasywebdav
from dotenv import load_dotenv, find_dotenv
import paho.mqtt.client as mqtt
from lodur_connect import create_einsatzrapport, upload_alarmdepesche, update_einsatzrapport
import pdf_extract

_EMAIL_SUBJECTS = '(OR SUBJECT "Einsatzausdruck_FW" SUBJECT "Einsatzprotokoll" UNSEEN)'
_INTERVAL = 10

load_dotenv(find_dotenv())
imap_server = os.getenv("IMAP_SERVER")
imap_username = os.getenv("IMAP_USERNAME")
imap_password = os.getenv("IMAP_PASSWORD")
imap_mailbox = os.getenv("IMAP_MAILBOX", "INBOX")
imap_mailbox_archive = os.getenv("IMAP_MAILBOX_ARCHIVE", "Archive")
webdav_url = os.getenv("WEBDAV_URL")
webdav_username = os.getenv("WEBDAV_USERNAME")
webdav_password = os.getenv("WEBDAV_PASSWORD")
webdav_basedir = os.getenv("WEBDAV_BASEDIR")
tmp_dir = os.getenv("TMP_DIR", "/tmp")
mqtt_server = os.getenv("MQTT_SERVER")
mqtt_user = os.getenv("MQTT_USER")
mqtt_password = os.getenv("MQTT_PASSWORD")
lodur_user = os.getenv("LODUR_USER")
lodur_password = os.getenv("LODUR_PASSWORD")
lodur_base_url = os.getenv("LODUR_BASE_URL")
heartbeat_url = os.getenv("HEARTBEAT_URL")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def search_emails(imap):
    """ searches for emails matching the configured subject """
    # search for matching messages
    logger.info('Searching for messages matching the subject')
    typ, msg_ids = imap.search(
        None,
        _EMAIL_SUBJECTS,
    )
    if typ != 'OK':
        logger.error('Error searching for matching messages')
        raise

    num_messages = len(msg_ids[0].split())
    logger.info('Found ' + str(num_messages) + ' matching messages')
    return num_messages, msg_ids

def store_attachments(imap, msg_ids):
    """ stores the attachments to filesystem and marks message as read """
    data = {}
    for msg_id in msg_ids[0].split():
        # download message from imap
        typ, msg_data = imap.fetch(msg_id, '(RFC822)')

        if typ != 'OK':
            logger.error('Error fetching message')
            raise

        # extract attachment
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                mail = email.message_from_string(str(response_part[1], 'utf-8'))
                subject = mail['subject']
                logger.info('Getting attachment from: ' + subject)
                for part in mail.walk():
                    file_name = part.get_filename()
                    if not file_name:
                        logger.debug('Most probably not an attachment as no filename found')
                        continue

                    logger.info('Extracting attachment: ' + file_name)

                    if bool(file_name):
                        f_type, f_id = parse_subject(subject)
                        renamed_file_name = f_type + '_' + file_name
                        # save attachment to filesystem
                        file_path = os.path.join(tmp_dir, renamed_file_name)

                        logger.info('Saving attachment to ' + file_path)
                        if not os.path.isfile(file_path):
                            file = open(file_path, 'wb')
                            file.write(part.get_payload(decode=True))
                            file.close()

                        data[subject] = renamed_file_name

        # mark as seen
        imap.store(msg_id, '+FLAGS', '(\\Seen)')

    return data

def upload_webdav(loop, webdav, file_name, f_id):
    """ uploads a file to webdav - checks for existence before doing so """
    # upload with webdav
    remote_upload_dir = webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
    logger.info('Uploading file to WebDAV:' + remote_upload_dir)

    # create directory if not yet there
    if not loop.run_until_complete(webdav.exists(remote_upload_dir)):
        logger.info('Creating directory ' + remote_upload_dir)
        loop.run_until_complete(webdav.mkdir(remote_upload_dir))

    remote_file_path = remote_upload_dir + "/" + file_name
    if loop.run_until_complete(webdav.exists(remote_file_path)):
        logger.info('File ' + file_name + ' already exists on webdav')
    else:
        loop.run_until_complete(
            webdav.upload(os.path.join(tmp_dir, file_name), remote_file_path)
        )
        logger.info('File ' + file_name + ' uploaded')

def einsatz_exists(loop, webdav, f_id):
    """ check if an einsatz is already created """
    remote_upload_dir = webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
    if loop.run_until_complete(webdav.exists(remote_upload_dir)):
        logger.info('Einsatz exists ' + f_id)
        return True
    else:
        return False

def parse_subject(subject):
    """ extract f id and type from subject """
    parsed = re.search('(.*): (F[0-9].*)', subject)
    f_type = parsed.group(1)
    f_id = parsed.group(2)
    return f_type, f_id

def store_lodur_id(loop, webdav, lodur_id, f_id):
    """ stores assigned lodur_id on webdav """
    file_name = f_id + '_lodurid.txt'
    file_path = os.path.join(tmp_dir, file_name)
    if not os.path.isfile(file_path):
        file = open(file_path, 'w')
        file.write(str(lodur_id))
        file.close()
        logger.info('Stored Lodur ID locally in: ' + file_path)
        upload_webdav(loop, webdav, file_name, f_id)
    else:
        logger.info('Lodur ID already available locally in: ' + file_path)

def get_lodur_id(loop, webdav, f_id):
    """ gets lodur_id if it exists """
    file_name = f_id + '_lodurid.txt'
    file_path = os.path.join(tmp_dir, file_name)

    # first check if we already have it locally - then check on webdav
    if os.path.isfile(file_path):
        with open(file_path, 'r') as content:
            lodur_id = content.read()
            logger.info('Found Lodur ID for ' + f_id + ' locally: ' + lodur_id)
            return lodur_id
    else:
        remote_upload_dir = webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
        remote_file_path = remote_upload_dir + '/' + file_name
        if loop.run_until_complete(webdav.exists(remote_file_path)):
            loop.run_until_complete(webdav.download(remote_file_path, file_path))
            with open(file_path, 'r') as content:
                lodur_id = content.read()
                logger.info('Found Lodur ID for ' + f_id + ' on WebDAV: ' + lodur_id)
                return lodur_id
        else:
            logger.info('No Lodur ID found for ' + f_id)
            return False

def main():
    """ main """

    # MQTT connection
    logger.info('Connecting to MQTT broker ' + mqtt_server)
    mqtt_client = mqtt.Client('pylokid')
    mqtt_client.username_pw_set(mqtt_user, password=mqtt_password)
    mqtt_client.tls_set()
    mqtt_client.connect(mqtt_server, 8883, 60)
    mqtt_client.loop_start()

    # imap connection
    logger.info('Connecting to IMAP server ' + imap_server)
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(imap_username, imap_password)
    imap.select(imap_mailbox, readonly=False)

    # webdav connection
    logger.info('Connecting to WebDAV server ' + webdav_url)
    loop = asyncio.get_event_loop()
    webdav = aioeasywebdav.connect(
        webdav_url,
        username=webdav_username,
        password=webdav_password,
    )

    while True:
        attachments = {}
        num_messages, msg_ids = search_emails(imap)
        if num_messages > 0:
            attachments = store_attachments(imap, msg_ids)

        if len(attachments) > 0:
            for subject in attachments:
                f_type, f_id = parse_subject(subject)
                file_name = attachments[subject]
                upload_webdav(loop, webdav, file_name, f_id)

                # Take actions - depending on the type
                if f_type == 'Einsatzausdruck_FW':
                    lodur_id = get_lodur_id(loop, webdav, f_id)
                    if lodur_id:
                        logger.info(
                            'Einsatzrapport ' + f_id + ' already created in Lodur: ' + lodur_id
                        )
                        # Upload Alarmdepesche as it could contain more information than the first one
                        upload_alarmdepesche(
                            lodur_user,
                            lodur_password,
                            lodur_base_url,
                            lodur_id,
                            file_name,
                            os.path.join(tmp_dir, file_name),
                        )
                    else:
                        # this is real - publish Einsatz on MQTT
                        # TODO publish more information about the einsatz - coming from the PDF
                        mqtt_client.publish('pylokid/' + f_type, f_id)

                        # get as many information from PDF as possible
                        pdf_data = pdf_extract.extract_einsatzausdruck(
                            os.path.join(tmp_dir, file_name),
                            f_id,
                        )

                        # create new Einsatzrapport in Lodur
                        logger.info('Creating Einsatzrapport in Lodur for ' + f_id)
                        lodur_id = create_einsatzrapport(
                            lodur_user,
                            lodur_password,
                            lodur_base_url,
                            f_id,
                            pdf_data,
                        )
                        logger.info('Sent data to Lodur. Assigned Lodur ID: ' + lodur_id)
                        # store lodur id in webdav
                        store_lodur_id(loop, webdav, lodur_id, f_id)

                        logger.info(
                            'Uploading PDF for ' + f_id + ' to Lodur Einsatzrapport ' + lodur_id
                        )
                        upload_alarmdepesche(
                            lodur_user,
                            lodur_password,
                            lodur_base_url,
                            lodur_id,
                            file_name,
                            os.path.join(tmp_dir, file_name),
                        )
                elif f_type == 'Einsatzprotokoll':
                    # Einsatz finished - publish on MQTT
                    mqtt_client.publish('pylokid/' + f_type, f_id)

                    lodur_id = get_lodur_id(loop, webdav, f_id)
                    if lodur_id:
                        logger.info('Uploading Einsatzprotokoll to Lodur')
                        upload_alarmdepesche(
                            lodur_user,
                            lodur_password,
                            lodur_base_url,
                            lodur_id,
                            file_name,
                            os.path.join(tmp_dir, file_name),
                        )
                        pdf_data = pdf_extract.extract_einsatzprotokoll(
                            os.path.join(tmp_dir, file_name),
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
        requests.get(heartbeat_url)
        # repeat every
        time.sleep(_INTERVAL)

if __name__ == '__main__':
    main()
