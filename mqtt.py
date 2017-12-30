#!/usr/bin/env python3

""" MQTT Functions """

import logging
import paho.mqtt.client as mqtt

class MQTTClient:
    """ MQTT Client """

    def __init__(self, server, username, password):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to MQTT broker ' + server)

        try:
            self.mqtt_client = mqtt.Client('pylokid')
            self.mqtt_client.username_pw_set(username, password=password)
            self.mqtt_client.tls_set()
            self.mqtt_client.connect(server, 8883, 60)
            self.mqtt_client.loop_start()
        except Exception as err:
            self.logger.error('MQTT connection failed - exiting: ' + str(err))
            raise SystemExit(1)

        self.logger.info('MQTT connection successfull')

    def send_message(self, f_type, f_id):
        """ Publish a message over MQTT """
        self.mqtt_client.publish('pylokid/' + f_type, f_id)
