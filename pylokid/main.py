#!/usr/bin/env python3

""" Thy pylokid main program """

import logging
import os
import time

import requests
from importlib.metadata import version
from dotenv import find_dotenv, load_dotenv
from pushover import Client

# local classes
from pylokid.library.emailhandling import EmailHandling
from pylokid.library.lodur import Lodur
from pylokid.library.pdftotext import PDFParsing
from pylokid.library.webdav import WebDav

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
LODUR_USER = os.getenv("LODUR_USER")
LODUR_PASSWORD = os.getenv("LODUR_PASSWORD")
LODUR_BASE_URL = os.getenv("LODUR_BASE_URL")
HEARTBEAT_URL = os.getenv("HEARTBEAT_URL")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")


def main():
    """main"""

    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("pylokid")
    logger.info("Starting pylokid version %s", version("pylokid"))

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

    # Initialize Pushover
    pushover = Client(user_key=PUSHOVER_USER_KEY, api_token=PUSHOVER_API_TOKEN)

    # Initialize PDF Parser
    pdf = PDFParsing()

    # Main Loop
    logger.info("** Starting to process E-Mails **")
    while True:

        # Search for matchting E-Mails
        msg_ids = imap_client.search_emails()

        for msg, subject in msg_ids.items():
            logger.info("Processing IMAP message ID %s", msg)
            file_name = imap_client.store_attachment(msg)

            # If the message couldn't be parsed, skip to next message
            if not file_name:
                pass

            # Figure out event type and F ID by parsing the subject
            f_type, f_id = imap_client.parse_subject(subject)

            # Upload extracted attachment to cloud
            webdav_client.upload(file_name, f_id)

            # Take actions - depending on the type
            if f_type == "Einsatzausdruck_FW":
                logger.info("[%s] Processing type %s", f_id, f_type)

                # Check if the PDF isn't already parsed
                if webdav_client.get_lodur_data(f_id, "_pdf.json"):
                    logger.info("[%s] PDF already parsed", f_id)
                else:
                    # Extract information from PDF
                    pdf_data = pdf.extract_einsatzausdruck(
                        os.path.join(TMP_DIR, file_name),
                        f_id,
                    )

                    # publish Einsatz on Pushover
                    logger.info("[%s] Publishing message on Pushover", f_id)
                    pushover.send_message(
                        "<b>{}</b>\n\n* Ort: {}\n* Melder: {}\n* Hinweis: {}\n* {}\n\n{}\n\n{}".format(
                            pdf_data["einsatz"],
                            pdf_data["ort"],
                            pdf_data["melder"].replace("\n", " "),
                            pdf_data["hinweis"],
                            pdf_data["sondersignal"],
                            pdf_data["bemerkungen"],
                            pdf_data["disponierteeinheiten"],
                        ),
                        title="Feuerwehr Einsatz - {}".format(f_id),
                        url="https://www.google.com/maps/search/?api=1&query={}".format(
                            pdf_data["ort"]
                        ),
                        url_title="Ort auf Karte suchen",
                        html=1,
                    )

                    # Upload extracted data to cloud
                    webdav_client.store_data(f_id, f_id + "_pdf.json", pdf_data)

                if webdav_client.get_lodur_data(f_id):
                    logger.info("[%s] Lodur data already retrieved", f_id)
                    # Marking message as seen, no need to reprocess again
                    imap_client.mark_seen(msg, f_id)
                else:
                    # Retrieve data from Lodur
                    lodur_id = lodur_client.get_einsatzrapport_id(f_id)
                    if lodur_id:
                        logger.info(
                            "[%s] Einsatzrapport available in Lodur with ID %s",
                            f_id,
                            lodur_id,
                        )
                        logger.info(
                            "%s?modul=36&what=144&event=%s&edit=1",
                            LODUR_BASE_URL,
                            lodur_id,
                        )

                        lodur_data = lodur_client.retrieve_form_data(lodur_id)
                        webdav_client.store_data(f_id, f_id + "_lodur.json", lodur_data)

                        # upload Alarmdepesche PDF to Lodur
                        lodur_client.upload_alarmdepesche(
                            f_id,
                            os.path.join(TMP_DIR, file_name),
                            webdav_client,
                        )

                        # Marking message as seen, no need to reprocess again
                        imap_client.mark_seen(msg, f_id)
                    else:
                        logger.warn("[%s] Einsatzrapport NOT found in Lodur", f_id)

            elif f_type == "Einsatzprotokoll":

                lodur_id = webdav_client.get_lodur_data(f_id)["event_id"]
                pdf_data = webdav_client.get_lodur_data(f_id, "_pdf.json")
                logger.info(
                    "[%s] Processing type %s with Lodur ID %s",
                    f_id,
                    f_type,
                    lodur_id,
                )

                # Retrieve Lodur data again and store it in Webdav
                lodur_data = lodur_client.retrieve_form_data(lodur_id)
                webdav_client.store_data(f_id, f_id + "_lodur.json", lodur_data)

                if (
                    "aut_created_report" in lodur_data
                    and lodur_data["aut_created_report"] == "finished"
                ):
                    logger.info("[%s] Record in Lodur ready to be updated", f_id)

                    # Upload Einsatzprotokoll to Lodur
                    lodur_client.upload_alarmdepesche(
                        f_id,
                        os.path.join(TMP_DIR, file_name),
                        webdav_client,
                    )

                    # Update entry in Lodur
                    lodur_client.einsatzprotokoll(
                        f_id, lodur_data, pdf_data, webdav_client
                    )

                    # Correct time on AdF to round up to one hour
                    # curl 'https://lodur-zh.ch/urdorf/tunnel.php?modul=36&what=1082'
                    # -H 'Referer: https://lodur-zh.ch/urdorf/index.php?modul=36&what=145&event=3485&edit=1'
                    # -H 'Cookie: PHPSESSID=85pnahp3q83apv7qsbi8hrj5g7'
                    # --data-raw 'dtv_d=03&dtv_m=04&dtv_y=2021&dtb_d=03&dtb_m=04&dtb_y=2021&ztv_h=18&ztv_m=26&ztb_h=19&ztb_m=26'
                    # ztb_m -> same as ztv_m

                    # Einsatz finished - publish on pushover
                    logger.info("[%s] Publishing message on Pushover", f_id)
                    pushover.send_message(
                        "Einsatz beendet",
                        title="Feuerwehr Einsatz beendet - {}".format(f_id),
                    )

                    # Marking message as seen, no need to reprocess again
                    imap_client.mark_seen(msg, f_id)

                else:
                    logger.warn(
                        "[%s] Record in Lodur NOT ready yet to be updated", f_id
                    )

            # This is usually a scan from the Depot printer
            elif f_type == "Einsatzrapport":

                logger.info("[%s] Processing type %s", f_id, f_type)

                # Attach scan in Lodur if f_id is available
                # f_id can be empty when scan was misconfigured
                if f_id != None and len(f_id) > 8:
                    lodur_id = webdav_client.get_lodur_data(f_id)["event_id"]
                    # Retrieve Lodur data again and store it in Webdav
                    lodur_data = lodur_client.retrieve_form_data(lodur_id)
                    webdav_client.store_data(f_id, f_id + "_lodur.json", lodur_data)
                    lodur_client.einsatzrapport_scan(
                        f_id,
                        lodur_data,
                        os.path.join(TMP_DIR, file_name),
                        webdav_client,
                    )
                else:
                    f_id = f_type

                logger.info("[%s] Publishing message on Pushover", f_id)

                pushover.send_message(
                    "Scan {} wurde bearbeitet und in Cloud geladen".format(f_id),
                    title="Feuerwehr Scan bearbeitet - {}".format(f_id),
                )

                # Marking message as seen, no need to reprocess again
                imap_client.mark_seen(msg, f_id)

            else:
                logger.error("[%s] Unknown type: %s", f_id, f_type)

        logger.info("Checking WebDav Inbox folder for Einsatzrapporte to process")
        rapporte_to_process = webdav_client.einsatzrapport_inbox_check(TMP_DIR)

        if rapporte_to_process:
            for f_id_rapport in rapporte_to_process:
                filename = f"Einsatzrapport_{f_id_rapport}.pdf"
                local_file = os.path.join(TMP_DIR, filename)
                # Upload to f_id folder
                webdav_client.upload(filename, f_id_rapport)

                # Process it for Lodur
                lodur_id = webdav_client.get_lodur_data(f_id_rapport)["event_id"]
                # Retrieve Lodur data again and store it in Webdav
                lodur_data = lodur_client.retrieve_form_data(lodur_id)
                webdav_client.store_data(
                    f_id_rapport, f_id_rapport + "_lodur.json", lodur_data
                )
                lodur_client.einsatzrapport_scan(
                    f_id_rapport,
                    lodur_data,
                    local_file,
                    webdav_client,
                )
                # Delete processed Einsatzrapport from Inbox and local temp dir
                logger.info("Einsatzrapport processed - deleting file in Inbox")
                webdav_client.delete(f"{WEBDAV_BASEDIR}/Inbox/{filename}")
                os.remove(local_file)

                pushover.send_message(
                    f"Einsatzrapport {f_id_rapport} wurde bearbeitet.",
                    title=f"Feuerwehr Einsatzrapport bearbeitet - {f_id_rapport}",
                )

        # send heartbeat
        requests.get(HEARTBEAT_URL)
        # repeat every
        logger.info("Waiting %s seconds until next check", IMAP_CHECK_INTERVAL)
        time.sleep(int(IMAP_CHECK_INTERVAL))
