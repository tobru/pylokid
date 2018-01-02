#!/usr/bin/env python3

""" Small Lodur Library for the Module 36 - Einsatzrapport """

import re
import logging
from datetime import datetime
import mechanicalsoup
from webdav import WebDav

class Lodur:
    """ Lodur """

    def __init__(self, url, username, password):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Connecting to Lodur')

        self.url = url

        # MechanicalSoup initialization and login to Lodur
        self.browser = mechanicalsoup.StatefulBrowser()
        # The login form is located in module number 9
        self.browser.open(self.url + '?modul=9')
        self.browser.select_form()

        self.browser['login_member_name'] = username
        self.browser['login_member_pwd'] = password
        self.browser.submit_selected()

        # Check if login succeeded by finding the img with
        # alt text LOGOUT
        page = self.browser.get_current_page()
        if page.find(alt='LOGOUT'):
            self.logger.info('Login to Lodur succeeded')
        else:
            self.logger.fatal('Login to Lodur failed - exiting')
            raise SystemExit(1)

    def einsatzprotokoll(self, f_id, pdf_data, webdav_client):
        """ Prepare Einsatzprotokoll to be sent to Lodur """

        # check if data is already sent to lodur - data contains lodur_id
        lodur_data = webdav_client.get_lodur_data(f_id)

        if lodur_data:
            # einsatz available in Lodur - updating existing entry
            self.logger.info('[%s] Lodur data found - updating entry', f_id)

            # when PDF parsing fails, pdf_data is false. fill with tbd when this happens
            if pdf_data:
                zh_fw_ausg = datetime.strptime(
                    pdf_data['ausgerueckt'],
                    '%H:%M',
                )
                zh_am_schad = datetime.strptime(
                    pdf_data['anort'],
                    '%H:%M',
                )
            else:
                # Do nothing when no PDF data - we don't have anything to do then
                self.logger.error('[%s] No PDF data found - filling in dummy data', f_id)
                zh_fw_ausg = datetime.now()
                zh_am_schad = datetime.now()

            # Complement existing form data
            self.logger.info('[%s] Preparing form data for Einsatzprotokoll', f_id)
            lodur_data['zh_fw_ausg_h'] = zh_fw_ausg.hour # 13. FW ausgerückt
            lodur_data['zh_fw_ausg_m'] = zh_fw_ausg.minute # 13. FW ausgerückt
            lodur_data['zh_am_schad_h'] = zh_am_schad.hour # 14. Am Schadenplatz
            lodur_data['zh_am_schad_m'] = zh_am_schad.minute # 14. Am Schadenplatz
            # The following fields are currently unknown as PDF parsing is hard for these
            #lodur_data['zh_fw_einge_h'] = UNKNOWN, # 15. FW eingerückt
            #lodur_data['zh_fw_einge_m'] = 'UNKNOWN' # 15. FW eingerückt
            #lodur_data['eins_erst_h'] = 'UNKNOWN' # 16. Einsatzbereitschaft erstellt
            #lodur_data['eins_erst_m'] = 'UNKNOWN' # 16. Einsatzbereitschaft erstellt

            # Submit the form
            self.submit_form_einsatzrapport(lodur_data)
        else:
            # einsatz not available in Lodur
            self.logger.error('[%s] No lodur_id found')
            return False

    def einsatzrapport(self, f_id, pdf_data, webdav_client):
        """ Prepare form in module 36 - Einsatzrapport """

        # when PDF parsing fails, pdf_data is false. fill with placeholder when this happens
        if pdf_data:
            date = datetime.strptime(
                pdf_data['datum'],
                '%d.%m.%Y',
            )
            time = datetime.strptime(
                pdf_data['zeit'],
                '%H:%M',
            )
            eins_ereig = pdf_data['einsatz']
            adr = pdf_data['strasse'] + ', ' + pdf_data['plzort']
        else:
            date = datetime.now()
            time = datetime.now()
            eins_ereig = 'UNKNOWN'
            adr = 'UNKNOWN'

        # Fill in form data
        self.logger.info('[%s] Preparing form data for Einsatzrapport', f_id)
        lodur_data = {
            'e_r_num': f_id, # 01. Einsatzrapportnummer
            'eins_stat_kantone': '1', # 02. Einsatzart FKS
            'emergency_concept_id': '2', # 03. Verrechnungsart
            'ver_sart': 'ab', # 03. Verrechnungsart internal: ab, th, uh, ak, tt
            'dtv_d': str(date.day), # 04. Datum von
            'dtv_m': str(date.month), # 04. Datum von
            'dtv_y': str(date.year), # 04. Datum von
            'dtb_d': str(date.day), # 04. Datum bis - we dont know yet the end date
            'dtb_m': str(date.month), # 04. Datum bis - assume the same day
            'dtb_y': str(date.year), # 04. Datum bis
            'ztv_h': str(time.hour), # 05. Zeit von
            'ztv_m': str(time.minute), # 05. Zeit von
            'ztb_h': str(time.hour + 1), # 05. Zeit bis - we dont know yet the end time
            'ztb_m': str(time.minute), # 05. Zeit bis - just add 1 hour and correct later
            'e_ort_1': '306', # 06. Einsatzort: Urdorf 306, Birmensdorf 298
            'eins_ereig': eins_ereig, # 07. Ereignis
            'adr': adr, # 08. Adresse
            'zh_alarmierung_h': str(time.hour), # 12. Alarmierung
            'zh_alarmierung_m': str(time.minute), # 12. Alarmierung
            'ang_sit': 'TBD1', # 17. Angetroffene Situation
            'mn': 'TBD2', # 19. Massnahmen
            'bk': 'TBD3', # 20. Bemerkungen
            'en_kr_feuwehr': '1', # 21. Einsatzkräfte
            'ali_io': '1', # 24. Alarmierung
            'kopie_gvz': '1', # 31. Kopie innert 10 Tagen an GVZ
            'mannschaftd_einsa': '70', # 32. Einsatzleiter|in
        }

        # Submit the form
        lodur_id, auto_num = self.submit_form_einsatzrapport(lodur_data)

        # save lodur id and data to webdav
        lodur_data['event_id'] = lodur_id
        lodur_data['auto_num'] = auto_num
        webdav_client.store_lodur_data(f_id, lodur_data)

        return lodur_id

    def einsatzrapport_alarmdepesche(self, f_id, file_path, webdav_client):
        """ Upload a file to Alarmdepesche """

        self.logger.info('[%s] Submitting Alarmdepesche to Lodur', f_id)

        # check if data is already sent to lodur - data contains lodur_id
        lodur_id = webdav_client.get_lodur_data(f_id)['event_id']

        # Prepare the form
        self.browser.open(self.url + '?modul=36&what=828&event=' + lodur_id)
        self.browser.select_form('#frm_alarmdepesche')

        # Fill in form data
        self.browser['alarmdepesche'] = open(file_path, 'rb')

        # Submit the form
        self.browser.submit_selected()
        self.logger.info('[%s] Alarmdepesche submitted', f_id)

    def submit_form_einsatzrapport(self, lodur_data):
        """ Form in module 36 - Einsatzrapport """

        # Prepare the form
        if 'event_id' in lodur_data:
            # existing entry to update
            self.logger.info(
                '[%s] Updating existing entry with ID %s',
                lodur_data['e_r_num'],
                lodur_data['event_id'],
            )
            self.browser.open(
                self.url +
                '?modul=36&what=144&edit=1&event=' +
                lodur_data['event_id']
            )
        else:
            self.logger.info('[%s] Creating new entry in Lodur', lodur_data['e_r_num'])
            self.browser.open(
                self.url +
                '?modul=36'
            )

        self.browser.select_form('#einsatzrapport_main_form')

        # Prepare the form data to be submitted
        for key, value in lodur_data.items():
            # Encode fields so they are sent in correct format
            self.logger.debug('Form data: %s = %s', key, value)
            if key in ('eins_ereig', 'adr'):
                self.browser[key] = value.encode('iso-8859-1')
            else:
                self.browser[key] = value

        # Submit the form
        self.logger.info('[%s] Submitting form Einsatzrapport', lodur_data['e_r_num'])
        response = self.browser.submit_selected()
        self.logger.info('[%s] Form Einsatzrapport submitted', lodur_data['e_r_num'])

        if 'event_id' in lodur_data:
            return True
        else:
            # very ugly way to find the assigned event id by lodur
            # lodur adds a script element at the bottom of the returned html
            # with the location to reload the page - containing the assigned event id
            lodur_id = re.search('modul=36&event=([0-9].*)&edit=1&what=144', response.text).group(1)
            self.logger.info('[%s] Lodur assigned the event_id %s', lodur_data['e_r_num'], lodur_id)

            # The hidden field auto_num is also needed for updating the form
            # and it's written somewhere in javascript code - but not on the page
            # delivered after the submission which contains the redirect URL
            # It's only delivered in the next page. So we browse to this page now
            content = self.browser.open(
                self.url +
                '?modul=36&edit=1&what=144&event=' + lodur_id
            ).text
            auto_num = re.search(r"fdata\['auto_num'\]\[2\]='(.*)';", content).group(1)
            self.logger.info('[%s] Lodur assigned the auto_num %s', lodur_data['e_r_num'], auto_num)

            return lodur_id, auto_num
