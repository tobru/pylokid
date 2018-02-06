#!/usr/bin/env python3

""" E-Mail / IMAP handling """

import os
import logging
import re
import email
import email.parser
import imaplib

_EMAIL_SUBJECTS = '(OR SUBJECT "Einsatzausdruck_FW" SUBJECT "Einsatzprotokoll" UNSEEN)'

class EmailHandling:
    """ Email handling """

    def __init__(self, server, username, password, mailbox, tmp_dir):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to IMAP server %s', server)

        self.tmp_dir = tmp_dir
        try:
            self.imap = imaplib.IMAP4_SSL(server)
            self.imap.login(username, password)
            self.imap.select(mailbox, readonly=False)
        except Exception as err:
            self.logger.error('IMAP connection failed - exiting: %s', str(err))
            raise SystemExit(1)

        self.logger.info('IMAP connection successfull')

    def search_emails(self):
        """ searches for emails matching the configured subject """

        self.logger.info('Searching for messages matching the subject')
        try:
            typ, msg_ids = self.imap.search(
                None,
                _EMAIL_SUBJECTS,
            )
            if typ != 'OK':
                self.logger.error('Error searching for matching messages')
                return False
        except imaplib.IMAP4.abort as err:
            self.logger.error('IMAP search aborted - exiting: %s', str(err))
            raise SystemExit(1)

        num_messages = len(msg_ids[0].split())
        self.logger.info('Found %s matching messages', str(num_messages))

        return num_messages, msg_ids

    def store_attachments(self, msg_ids):
        """ stores the attachments to filesystem and marks message as read """

        data = {}
        for msg_id in msg_ids[0].split():
            # download message from imap
            typ, msg_data = self.imap.fetch(msg_id, '(RFC822)')

            if typ != 'OK':
                self.logger.error('Error fetching message')
                continue

            # extract attachment
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    mail = email.message_from_string(str(response_part[1], 'utf-8'))
                    subject = mail['subject']
                    f_type, f_id = self.parse_subject(subject)
                    self.logger.info('[%s] Getting attachment from "%s"', f_id, subject)
                    for part in mail.walk():
                        file_name = part.get_filename()
                        if not file_name:
                            self.logger.debug(
                                'Most probably not an attachment as no filename found'
                            )
                            continue

                        self.logger.info('[%s] Extracting attachment "%s"', f_id, file_name)

                        if bool(file_name):
                            f_type, _ = self.parse_subject(subject)
                            renamed_file_name = f_type + '_' + file_name
                            # save attachment to filesystem
                            file_path = os.path.join(self.tmp_dir, renamed_file_name)

                            self.logger.info('[%s] Saving attachment to "%s"', f_id, file_path)
                            if not os.path.isfile(file_path):
                                file = open(file_path, 'wb')
                                file.write(part.get_payload(decode=True))
                                file.close()

                            data[subject] = renamed_file_name

            # mark as seen
            self.logger.info('[%s] Marking message "%s" as seen', f_id, subject)
            self.imap.store(msg_id, '+FLAGS', '(\\Seen)')

        return data

    def parse_subject(self, subject):
        """ extract f id and type from subject """

        parsed = re.search('(.*): (F[0-9].*)', subject)
        f_type = parsed.group(1)
        f_id = parsed.group(2)

        return f_type, f_id
