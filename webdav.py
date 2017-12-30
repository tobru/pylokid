#!/usr/bin/env python3

""" WebDav Functions """

import os
from datetime import datetime
import logging
import asyncio
import aioeasywebdav

class WebDav:
    """ WebDav Client """

    def __init__(self, url, username, password, webdav_basedir, tmp_dir):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to WebDAV server: ' + url)

        self.loop = asyncio.get_event_loop()
        self.webdav_basedir = webdav_basedir
        self.tmp_dir = tmp_dir
        try:
            self.webdav = aioeasywebdav.connect(
                url,
                username=username,
                password=password,
            )
        except:
            self.logger.error('WebDav connection failed - exiting')

        self.logger.info('WebDav connection successfull')

    def upload(self, file_name, f_id):
        """ uploads a file to webdav - checks for existence before doing so """

        # upload with webdav
        remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
        self.logger.info('Uploading file to WebDAV:' + remote_upload_dir)

        # create directory if not yet there
        if not self.loop.run_until_complete(self.webdav.exists(remote_upload_dir)):
            self.logger.info('Creating directory ' + remote_upload_dir)
            self.loop.run_until_complete(self.webdav.mkdir(remote_upload_dir))

        remote_file_path = remote_upload_dir + "/" + file_name
        if self.loop.run_until_complete(self.webdav.exists(remote_file_path)):
            self.logger.info('File ' + file_name + ' already exists on webdav')
        else:
            self.loop.run_until_complete(
                self.webdav.upload(
                    os.path.join(self.tmp_dir, file_name),
                    remote_file_path,
                )
            )
            self.logger.info('File ' + file_name + ' uploaded')

    def einsatz_exists(self, f_id):
        """ check if an einsatz is already created """

        remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
        if self.loop.run_until_complete(self.webdav.exists(remote_upload_dir)):
            self.logger.info('Einsatz exists ' + f_id)
            return True
        else:
            return False

    def store_lodur_id(self, lodur_id, f_id):
        """ stores assigned lodur_id on webdav """

        file_name = f_id + '_lodurid.txt'
        file_path = os.path.join(self.tmp_dir, file_name)
        if not os.path.isfile(file_path):
            file = open(file_path, 'w')
            file.write(str(lodur_id))
            file.close()
            self.logger.info('Stored Lodur ID locally in: ' + file_path)
            self.upload(file_name, f_id)
        else:
            self.logger.info('Lodur ID already available locally in: ' + file_path)

    def get_lodur_id(self, f_id):
        """ gets lodur_id if it exists """

        file_name = f_id + '_lodurid.txt'
        file_path = os.path.join(self.tmp_dir, file_name)

        # first check if we already have it locally - then check on webdav
        if os.path.isfile(file_path):
            with open(file_path, 'r') as content:
                lodur_id = content.read()
                self.logger.info('Found Lodur ID for ' + f_id + ' locally: ' + lodur_id)
                return lodur_id
        else:
            remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
            remote_file_path = remote_upload_dir + '/' + file_name
            if self.loop.run_until_complete(self.webdav.exists(remote_file_path)):
                self.loop.run_until_complete(self.webdav.download(remote_file_path, file_path))
                with open(file_path, 'r') as content:
                    lodur_id = content.read()
                    self.logger.info('Found Lodur ID for ' + f_id + ' on WebDAV: ' + lodur_id)
                    return lodur_id
            else:
                self.logger.info('No Lodur ID found for ' + f_id)
                return False
