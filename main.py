#!/usr/bin/env python3

""" Thy pylokid main program """

import os
import re
import datetime
import asyncio
import logging
import time
import email
import email.parser
import imaplib
from datetime import datetime
import aioeasywebdav
from dotenv import load_dotenv, find_dotenv
import paho.mqtt.client as mqtt

_EMAIL_SUBJECTS = '(OR SUBJECT "Einsatzausdruck_FW" SUBJECT "Einsatzprotokoll" UNSEEN)'

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_attachments(mqtt_client):
    # imap connection
    logger.info('Connecting to IMAP server ' + imap_server)
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(imap_username, imap_password)
    imap.select(imap_mailbox, readonly=False)

    # search for matching messages
    logger.info('Searching for messages matching the subject')
    typ, msg_ids = imap.search(
        None,
        _EMAIL_SUBJECTS,
    )
    if typ != 'OK':
        print('Error searching for matching messages')
        raise

    logger.info('Found ' + str(len(msg_ids[0].split())) + ' matching messages')

    for msg_id in msg_ids[0].split():
        subject = str()
        f_id = str()

        # download message
        typ, msg_data = imap.fetch(msg_id, '(RFC822)')

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(str(response_part[1],'utf-8'))
                subject = msg["subject"]
                # extract F id from subject
                f_id = re.search('.*: (F[0-9].*)',subject).group(1)

        logger.info('Processing message: ' + subject)
        logger.info('Detected F ID: ' + f_id)

        mqtt_client.publish("pylokid/einsatz/" + f_id, subject)

        # Mark as seen
        imap.store(msg_id, '+FLAGS', '(\\Seen)')

        # extract attachment from body
        mail = email.message_from_string(str(msg_data[0][1],'utf-8'))

        for part in mail.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            file_name = part.get_filename()

            logger.info('Extracting attachment: ' + file_name)

            if bool(file_name):
                # save attachment to filesystem
                file_path = os.path.join(tmp_dir, file_name)

                logger.info('Saving attachment to ' + file_path)
                if not os.path.isfile(file_path):
                    print(file_name)
                    file = open(file_path, 'wb')
                    file.write(part.get_payload(decode=True))
                    file.close()

                upload_attachment(file_path, file_name, f_id)


def upload_attachment(file, file_name, f_id):
    # webdav connection
    logger.info('Connecting to WebDAV server ' + webdav_url)
    loop = asyncio.get_event_loop()
    webdav = aioeasywebdav.connect(
        webdav_url,
        username=webdav_username,
        password=webdav_password,
    )

    # upload with webdav
    upload_dir = webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
    logger.info('Uploading attachment to ' + upload_dir)

    # create directory if not yet there
    if not loop.run_until_complete(webdav.exists(upload_dir)):
        logger.info('Creating directory ' + upload_dir)
        loop.run_until_complete(webdav.mkdir(upload_dir))

    remote_file_path = upload_dir + "/" + file_name
    if loop.run_until_complete(webdav.exists(remote_file_path)):
        logger.info('File ' + file_name + ' already uploaded')
    else:
        loop.run_until_complete(
            webdav.upload(file, remote_file_path)
        )
        logger.info('File ' + file_name + ' uploaded')

def on_connect(client, userdata, flags, rc):
    logger.info('Connected to MQTT with result code ' + str(rc))

def main():
    """ main """

    logger.info('Connecting to MQTT broker ' + mqtt_server)

    client = mqtt.Client('pylokid')
    client.on_connect = on_connect
    client.username_pw_set(mqtt_user, password=mqtt_password)
    client.tls_set()
    client.connect(mqtt_server, 8883, 60)
    client.loop_start()

    while True:
        get_attachments(client)
        time.sleep(60)

if __name__ == '__main__':
    main()
