#!/usr/bin/env python3

""" WebDav Functions """

import os
import json
from datetime import datetime
import logging
import asyncio
import aioeasywebdav

class WebDav:
    """ WebDav Client """

    def __init__(self, url, username, password, webdav_basedir, tmp_dir):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to WebDAV server %s', url)

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
            self.logger.error('WebDAV connection failed - exiting')

        self.logger.info('WebDAV connection successfull')

    def upload(self, file_name, f_id):
        """ uploads a file to webdav - checks for existence before doing so """

        # upload with webdav
        remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
        self.logger.info('[%s] Uploading file to WebDAV "%s"', f_id, remote_upload_dir)

        # create directory if not yet there
        if not self.loop.run_until_complete(self.webdav.exists(remote_upload_dir)):
            self.logger.info('[%s] Creating directory "%s"', f_id, remote_upload_dir)
            self.loop.run_until_complete(self.webdav.mkdir(remote_upload_dir))

        remote_file_path = remote_upload_dir + "/" + file_name
        if self.loop.run_until_complete(self.webdav.exists(remote_file_path)):
            self.logger.info('[%s] File "%s" already exists on WebDAV', f_id, file_name)
        else:
            self.loop.run_until_complete(
                self.webdav.upload(
                    os.path.join(self.tmp_dir, file_name),
                    remote_file_path,
                )
            )
            self.logger.info('[%s] File "%s" uploaded', f_id, file_name)

    def einsatz_exists(self, f_id):
        """ check if an einsatz is already created """

        remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
        if self.loop.run_until_complete(self.webdav.exists(remote_upload_dir)):
            self.logger.info('[%s] Einsatz exists on WebDAV', f_id)
            return True
        else:
            return False

    def store_lodur_data(self, f_id, lodur_data):
        """ stores lodur data on webdav """

        file_name = f_id + '_lodur.json'
        file_path = os.path.join(self.tmp_dir, file_name)

        file = open(file_path, 'w')
        file.write(json.dumps(lodur_data))
        file.close()

        self.logger.info('[%s] Stored Lodur data locally in %s', f_id, file_path)
        self.upload(file_name, f_id)

    def get_lodur_data(self, f_id):
        """ gets lodur data if it exists """

        file_name = f_id + '_lodur.json'
        file_path = os.path.join(self.tmp_dir, file_name)

        # first check if we already have it locally - then check on webdav
        if os.path.isfile(file_path):
            with open(file_path, 'r') as content:
                lodur_data = json.loads(content.read())
                self.logger.info('[%s] Found Lodur data locally', f_id)
                return lodur_data
        else:
            remote_upload_dir = self.webdav_basedir + "/" + str(datetime.now().year) + "/" + f_id
            remote_file_path = remote_upload_dir + '/' + file_name
            if self.loop.run_until_complete(self.webdav.exists(remote_file_path)):
                self.loop.run_until_complete(self.webdav.download(remote_file_path, file_path))
                with open(file_path, 'r') as content:
                    lodur_data = json.loads(content.read())
                    self.logger.info('[%s] Found Lodur data on WebDAV', f_id)
                    return lodur_data
            else:
                self.logger.info('[%s] No existing Lodur data found', f_id)
                return False
