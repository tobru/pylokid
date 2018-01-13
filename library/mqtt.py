#!/usr/bin/env python3

""" MQTT Functions """

import logging
import json
import paho.mqtt.client as mqtt

class MQTTClient:
    """ MQTT Client """

    def __init__(self, server, username, password, base_topic):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to MQTT broker %s', server)

        try:
            self.mqtt_client = mqtt.Client('pylokid')
            self.mqtt_client.username_pw_set(username, password=password)
            self.mqtt_client.tls_set()
            self.mqtt_client.connect(server, 8883, 60)
            self.mqtt_client.loop_start()
        except Exception as err:
            self.logger.error('MQTT connection failed - exiting: %s', str(err))
            raise SystemExit(1)

        self.logger.info('MQTT connection successfull')
        self.base_topic = base_topic

    def send_message(self, f_type, f_id, pdf_data=None, pdf_file=None):
        """ Publish a message over MQTT """

        topic = "{0}/{1}/".format(self.base_topic, f_id)
        self.logger.info('[%s] Publishing information on MQTT topic %s*', f_id, topic)

        if f_type == 'Einsatzausdruck_FW':
            try:
                self.mqtt_client.publish(topic + 'typ', 'Einsatzauftrag')
                self.mqtt_client.publish(topic + 'json', json.dumps(pdf_data))

                ## Publish the PDF blob
                pdf_fh = open(pdf_file, 'rb')
                pdf_binary = pdf_fh.read()
                self.mqtt_client.publish(topic + 'pdf', bytes(pdf_binary))
            except IndexError as err:
                self.logger.info('[%s] Cannot publish information: %s', f_id, err)
        elif f_type == 'Einsatzprotokoll':
            self.mqtt_client.publish(topic + 'typ', 'Einsatzprotokoll')