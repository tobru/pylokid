#!/usr/bin/env python3

""" Gotify Functions """

import logging
import json
from urllib.parse import urljoin
import requests

class GotifyClient:
    """ Gotify Client """

    def __init__(self, url, token):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Gotify URL %s', url)

        self.url = url
        self.token = token

    def send_message(self, f_type, f_id, pdf_data=None, pdf_file=None):
        """ Publish a message over Gotify """

        requestURL = urljoin(self.url, '/message?token=' + self.token)

        try:
            resp = requests.post(requestURL, json={
                'title': 'Einsatz ' + f_id,
                'message': f_type,
                'priority': 5
            })
        except requests.exceptions.RequestException as err:
            self.logger.error('[%s] Could not connect to Gotify server: %e', f_id, err)

        # Print request result if server returns http error code
        if resp.status_code is not requests.codes.ok:
            self.logger.error('[%s] Could not send message to Gotify server: %e', f_id, bytes.decode(resp.content))
