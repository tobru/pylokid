#!/usr/bin/env python3

""" Small Lodur Library for the Module 36 - Einsatzrapport """

import re
import logging
import json
import mechanicalsoup
import pprint
from datetime import datetime, timedelta


class Lodur:
    """ Lodur """

    def __init__(self, url, username, password):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Connecting to Lodur")

        self.url = url
        self.username = username
        self.password = password

        # MechanicalSoup initialization and login to Lodur
        self.browser = mechanicalsoup.StatefulBrowser()

        self.login()
        if self.logged_in():
            self.logger.info("Login to Lodur succeeded")
        else:
            self.logger.fatal("Login to Lodur failed - exiting")
            raise SystemExit(1)

    def login(self):
        """ Login to lodur """

        # The login form is located in module number 9
        self.browser.open(self.url + "?modul=9")
        # only log in when not yed logged in
        if not self.logged_in():
            # open login page again as the logged_in function has navigated to another page
            self.browser.open(self.url + "?modul=9")
            self.browser.select_form()

            self.browser["login_member_name"] = self.username
            self.browser["login_member_pwd"] = self.password
            self.browser.submit_selected()

    def logged_in(self):
        """ check if logged in to lodur - session is valid """
        # Check if login succeeded by finding the img with
        # alt text LOGOUT on dashboard
        self.browser.open(self.url + "?modul=16")
        page = self.browser.get_current_page()
        if page.find(alt="LOGOUT"):
            self.logger.debug("Logged in")
            return True
        else:
            self.logger.debug("Not logged in")
            return False

    def get_einsatzrapport_id(self, f_id, state="open"):
        """ Find ID of automatically created Einsatzrapport """

        # Login to lodur
        self.login()

        # Browse to Einsatzrapport page
        if state == "open":
            self.browser.open("{}?modul=36".format(self.url))

        try:
            einsatzrapport_url = self.browser.find_link(link_regex=re.compile(f_id))
        except mechanicalsoup.LinkNotFoundError:
            self.logger.error("[%s] No Einsatzrapport found in Lodur", f_id)
            return None

        if einsatzrapport_url:
            lodur_id = re.search(
                ".*event=([0-9]{1,})&.*", einsatzrapport_url["href"]
            ).group(1)
            return lodur_id
        else:
            return None

    def retrieve_form_data(self, lodur_id):
        """ Retrieve all fields from an Einsatzrapport in Lodur """

        # Login to lodur
        self.login()

        # Browse to Einsatzrapport page
        self.browser.open(
            "{}?modul=36&what=144&event={}&edit=1".format(self.url, lodur_id)
        )

        # Lodur doesn't simply store form field values in the form value field
        # LOLNOPE - it is stored in javascript in the variable fdata
        # And the data format used is just crap - including mixing of different data types
        # WHAT DO THEY ACTUALLY THINK ABOUT THIS!!

        # Retrieve all <script></script> tags from page
        json_string = None
        all_scripts = self.browser.page.find_all("script", type="text/javascript")
        # Iterate over all tags to find the one containing fdata
        for script in all_scripts:
            # Some scripts don't have content - we're not interested in them
            if script.contents:
                # Search for "var fdata" in all scripts - if found, that's what we're looking for
                content = script.contents[0]
                if "var fdata" in content:
                    # Cut out unnecessary "var fdata"
                    json_string = content.replace("var fdata = ", "")

        # Now let's parse that data into a data structure which helps
        # in filling out the form and make it usable in Python
        if json_string:
            # Remove the last character which is a ;
            usable = {}
            for key, value in json.loads(json_string[:-1]).items():
                # WHY DO THEY MIX DIFFERENT TYPES!
                if isinstance(value, list):
                    usable[key] = value[2]
                elif isinstance(value, dict):
                    usable[key] = value["2"]
            return usable
        else:
            return None

    def einsatzprotokoll(self, f_id, lodur_data, webdav_client):
        """ Prepare Einsatzprotokoll to be sent to Lodur """

        self.logger.info("[%s] Updating Lodur entry", f_id)

        # Complement existing form data
        self.logger.info("[%s] Preparing form data for Einsatzprotokoll", f_id)

        lodur_data["ztb_m"] = lodur_data[
            "ztv_m"
        ]  # 05. Zeit (copy minute from start to round up to 1h)
        lodur_data["eins_ereig"] = "{} - {} - {}".format(
            f_id, lodur_data["ala_stich"], lodur_data["adr"]
        )  # 07. Ereignis
        lodur_data["en_kr_feuwehr"] = "1"  # 21. Einsatzkräfte
        lodur_data["ali_io"] = "1"  # 24. Alarmierung
        lodur_data["keyword_els_zutreffend"] = "1"  # 25. Stichwort
        lodur_data["address_zutreffend"] = "1"  # 26. Adresse zutreffend
        lodur_data["kopie_gvz"] = "1"  # 31. Kopie innert 10 Tagen an GVZ
        lodur_data["mannschaftd_einsa"] = "88"  # 32. Einsatzleiter|in

        # Submit the form
        self.submit_form_einsatzrapport(lodur_data)

        # save lodur data to webdav
        webdav_client.store_data(f_id, f_id + "_lodur.json", lodur_data)

    def upload_alarmdepesche(self, f_id, file_path, webdav_client):
        """ Upload a file to Alarmdepesche """

        self.logger.info(
            '[%s] Submitting file %s to Lodur "Alarmdepesche"', f_id, file_path
        )

        # Login to lodur
        self.login()

        # check if data is already sent to lodur - data contains lodur_id
        lodur_id = webdav_client.get_lodur_data(f_id)["event_id"]

        # Prepare the form
        self.browser.open("{}?modul=36&event={}&what=828".format(self.url, lodur_id))
        frm_alarmdepesche = self.browser.select_form("#frm_alarmdepesche")

        # Fill in form data
        frm_alarmdepesche.set("alarmdepesche", file_path)

        # Submit the form
        self.browser.submit_selected()
        self.logger.info("[%s] File uploaded to Lodur", f_id)

    def einsatzrapport_scan(self, f_id, lodur_data, file_path, webdav_client):
        """ Prepare Einsatzrapport Scan to be sent to Lodur """

        # Complement existing form data
        self.logger.info("[%s] Updating Lodur entry", f_id)
        lodur_data[
            "ang_sit"
        ] = "Siehe Alarmdepesche - Einsatzrapport"  # 17. Angetroffene Situation
        lodur_data["mn"] = "Siehe Alarmdepesche - Einsatzrapport"  # 19. Massnahmen

        # Submit the form
        self.submit_form_einsatzrapport(lodur_data)

        # Upload scan to Alarmdepesche
        self.einsatzrapport_alarmdepesche(
            f_id,
            file_path,
            webdav_client,
        )

    def submit_form_einsatzrapport(self, lodur_data):
        """ Form in module 36 - Einsatzrapport """

        # Login to lodur
        self.login()

        f_id = lodur_data["e_r_num"]

        self.logger.info(
            "[%s] Updating existing entry with ID %s",
            f_id,
            lodur_data["event_id"],
        )

        self.browser.open(
            self.url + "?modul=36&what=144&edit=1&event=" + lodur_data["event_id"]
        )

        form = self.browser.select_form("#einsatzrapport_main_form")

        # Prepare the form data to be submitted
        for key, value in lodur_data.items():
            # Not all keys in the parsed Lodur data are actually part of the form
            # Encode some of the fields so they are sent in correct format
            # Encoding bk causes some troubles - therefore we skip that - but it
            # would be good if it would be encoded as it can / will contain f.e.abs
            # Umlauts
            # AttributeError: 'bytes' object has no attribute 'parent'
            try:
                if key in ("eins_ereig", "adr", "wer_ala"):
                    form.set(key, value.encode("iso-8859-1"))
                else:
                    form.set(key, value)
                self.logger.debug("[%s] Set field %s to %s", f_id, key, value)
            except mechanicalsoup.LinkNotFoundError as e:
                self.logger.debug(
                    "[%s] Could not set field %s to %s. Reason: %s",
                    f_id,
                    key,
                    value,
                    str(e),
                )

        # Submit the form
        self.logger.info("[%s] Submitting form Einsatzrapport", lodur_data["e_r_num"])
        response = self.browser.submit_selected()
        self.logger.info("[%s] Form Einsatzrapport submitted", lodur_data["e_r_num"])

        return True
