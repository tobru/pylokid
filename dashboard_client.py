#!/usr/bin/env python3

""" The dashboard client """

import os
import logging
import subprocess

from dotenv import find_dotenv, load_dotenv
import paho.mqtt.client as mqtt

# Configuration
load_dotenv(find_dotenv())
MQTT_SERVER = os.getenv("MQTT_SERVER")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_BASE_TOPIC = os.getenv("MQTT_BASE_TOPIC", "pylokid")
TMP_DIR = os.getenv("TMP_DIR", "/tmp")

# Initialization
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger('dashboard')

PIDS = {}

def on_connect(client, userdata, flags, rc):
    LOGGER.info("Connected to MQTT with result code %s", str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("pylokid/#")

def on_message(client, userdata, msg):
    topic_detail = msg.topic.split("/")
    f_id = topic_detail[2]
    if topic_detail[1] == 'Einsatzausdruck_FW' and topic_detail[3] == 'pdf':
        LOGGER.info("[%s] New Einsatzausdruck received", f_id)
        file_name = TMP_DIR + "/dashboard_" + f_id + ".pdf"
        file = open(file_name, "wb")
        file.write(msg.payload)
        file.close()

        if f_id in PIDS:
            LOGGER.info(
                "[%s] Einsatzausdruck already being displayed with PID %s",
                f_id,
                str(PIDS[f_id])
            )
        else:
            LOGGER.info("[%s] Displaying Einsatzausdruck with xpdf", f_id)
            # TODO turn on TV with cec-client
            process = subprocess.Popen(
                ["/usr/bin/xpdf", "-z", "width", "-fullscreen", file_name],
                env=dict(os.environ, DISPLAY=":0")
            )
            PIDS[f_id] = process.pid
    elif topic_detail[1] == 'Einsatzprotokoll':
        LOGGER.info("[%s] New Einsatzprotokoll received", f_id)
        if f_id in PIDS:
            LOGGER.info("[%s] Killing xpdf PID %s", f_id, str(PIDS[f_id]))
            os.kill(PIDS[f_id], 9)
            PIDS.pop(f_id)
        else:
            LOGGER.info("[%s] No xpdf PID found", f_id)
    else:
        LOGGER.info("[%s] Unknown", topic_detail[1])

def main():
    """ main """

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.username_pw_set(MQTT_USER, password=MQTT_PASSWORD)
    mqtt_client.tls_set()
    mqtt_client.connect(MQTT_SERVER, 8883, 60)
    mqtt_client.loop_forever()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Byebye")
