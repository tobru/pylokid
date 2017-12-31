#!/usr/bin/env python3

""" Small Lodur Library for the Module 36 - Einsatzrapport """

import re
import logging
from datetime import datetime
import mechanicalsoup

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

    def einsatzrapport(self, f_id, pdf_data):
        """ Form in module 36 - Einsatzrapport """

        # when PDF parsing fails, pdf_data is false. fill with tbd when this happens
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

        # Prepare the form
        self.browser.open(self.url + '?modul=36')
        self.browser.select_form('#einsatzrapport_main_form')

        # Fill in form data
        self.browser['e_r_num'] = f_id # 01. Einsatzrapportnummer
        self.browser['eins_stat_kantone'] = '1' # 02. Einsatzart FKS
        self.browser['emergency_concept_id'] = '2' # 03. Verrechnungsart
        self.browser['ver_sart'] = 'ab' # 03. Verrechnungsart internal: ab, th, uh, ak, tt
        self.browser['dtv_d'] = str(date.day) # 04. Datum von
        self.browser['dtv_m'] = str(date.month) # 04. Datum von
        self.browser['dtv_y'] = str(date.year) # 04. Datum von
        self.browser['dtb_d'] = str(date.day) # 04. Datum bis - we dont know yet the end date
        self.browser['dtb_m'] = str(date.month) # 04. Datum bis - assume the same day
        self.browser['dtb_y'] = str(date.year) # 04. Datum bis
        self.browser['ztv_h'] = str(time.hour) # 05. Zeit von
        self.browser['ztv_m'] = str(time.minute) # 05. Zeit von
        self.browser['ztb_h'] = str(time.hour + 1) # 05. Zeit bis - we dont know yet the end time
        self.browser['ztb_m'] = str(time.minute) # 05. Zeit bis - just add 1 hour and correct later
        self.browser['e_ort_1'] = '306' # 06. Einsatzort: Urdorf 306, Birmensdorf 298
        self.browser['eins_ereig'] = eins_ereig.encode('iso-8859-1') # 07. Ereignis
        self.browser['adr'] = adr.encode('iso-8859-1') # 08. Adresse
        self.browser['ang_sit'] = 'TBD1' # 17. Angetroffene Situation
        self.browser['mn'] = 'TBD2' # 19. Massnahmen
        self.browser['bk'] = 'TBD3' # 20. Bemerkungen
        self.browser['en_kr_feuwehr'] = '1' # 21. Einsatzkräfte
        self.browser['ali_io'] = '1' # 24. Alarmierung
        self.browser['kopie_gvz'] = '1' # 31. Kopie innert 10 Tagen an GVZ
        self.browser['mannschaftd_einsa'] = '70' # 32. Einsatzleiter|in

        # Submit the form
        self.logger.info('Submitting form Einsatzrapport')
        response = self.browser.submit_selected()

        # very ugly way to find the assigned event id by lodur
        # lodur adds a script element at the bottom of the returned html
        # with the location to reload the page - containing the assigned event id
        lodur_id = re.search('modul=36&event=([0-9].*)&edit=1&what=144', response.text).group(1)
        self.logger.info('Lodur assigned the id ' + lodur_id + ' to ' + f_id)
        return lodur_id

    def einsatzrapport_alarmdepesche(self, lodur_id, file_path):
        """ Upload a file to Alarmdepesche """

        # Prepare the form
        self.browser.open(self.url + '?modul=36&what=828&event=' + lodur_id)
        self.browser.select_form('#frm_alarmdepesche')

        # Fill in form data
        self.logger.info('Submitting Alarmdepesche to Lodur id ' + lodur_id)
        self.browser['alarmdepesche'] = open(file_path, 'rb')

        # Submit the form
        self.browser.submit_selected()
        self.logger.info('Alarmdepesche submitted')
