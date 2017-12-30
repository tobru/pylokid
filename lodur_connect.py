#!/usr/bin/env python3

import re
from datetime import datetime
import requests

def create_einsatzrapport(username, password, base_url, f_id, pdf_data):

    session = requests.session()
    login_data = {
        'login_member_name': username,
        'login_member_pwd': password,
    }

    # Authenticate
    session.post(base_url, data=login_data)

    params = (
        ('modul', '36'),
        ('what', '144'),
        ('sp', '1'),
        ('event', ''),
        ('edit', ''),
        ('is_herznotfall', ''),
    )

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
        eins_ereig = 'TBD'
        adr = 'TBD'

    data = {
        'e_r_num': (None, f_id), # 01. Einsatzrapportnummer
        'eins_stat_kantone': (None, '1'), # 02. Einsatzart FKS
        'emergency_concept_id': (None, '2'), # 03. Verrechnungsart
        'ver_sart': (None, 'ab'), # 03. Verrechnungsart internal: ab, th, uh, ak, tt
        'dtv_d': (None, str(date.day)), # 04. Datum von
        'dtv_m': (None, str(date.month)), # 04. Datum von
        'dtv_y': (None, str(date.year)), # 04. Datum von
        'dtb_d': (None, str(date.day)), # 04. Datum bis - we dont know yet the end date
        'dtb_m': (None, str(date.month)), # 04. Datum bis - assume the same day
        'dtb_y': (None, str(date.year)), # 04. Datum bis
        'ztv_h': (None, str(time.hour)), # 05. Zeit von
        'ztv_m': (None, str(time.minute)), # 05. Zeit von
        'ztb_h': (None, str(time.hour + 1)), # 05. Zeit bis - we dont know yet the end time
        'ztb_m': (None, str(time.minute)), # 05. Zeit bis - just add one hour and correct later
        'e_ort_1': (None, '306'), # 06. Einsatzort: Urdorf 306, Birmensdorf 298
        'eins_ereig': (None, eins_ereig.encode('iso-8859-1')), # 07. Ereignis
        'adr': (None, adr.encode('iso-8859-1')), # 08. Adresse
        #'zh_alarmierung_h': (None, 'UNKNOWN'), # 12. Alarmierung
        #'zh_alarmierung_m': (None, 'UNKNOWN'), # 12. Alarmierung
        #'zh_fw_ausg_h': (None, 'UNKNOWN'), # 13. FW ausgerückt
        #'zh_fw_ausg_m': (None, 'UNKNOWN'), # 13. FW ausgerückt
        #'zh_am_schad_h': (None, 'UNKNOWN'), # 14. Am Schadenplatz
        #'zh_am_schad_m': (None, 'UNKNOWN'), # 14. Am Schadenplatz
        #'zh_fw_einge_h': (None, 'UNKNOWN'), # 15. FW eingerückt
        #'zh_fw_einge_m': (None, 'UNKNOWN'), # 15. FW eingerückt
        #'eins_erst_h': (None, 'UNKNOWN'), # 16. Einsatzbereitschaft erstellt
        #'eins_erst_m': (None, 'UNKNOWN'), # 16. Einsatzbereitschaft erstellt
        'ang_sit': (None, 'TBD1'), # 17. Angetroffene Situation
        'mn': (None, 'TBD2'), # 19. Massnahmen
        'bk': (None, 'TBD3'), # 20. Bemerkungen
        'en_kr_feuwehr': (None, '1'), # 21. Einsatzkräfte
        'ali_io': (None, '1'), # 24. Alarmierung
        'kopie_gvz': (None, '1'), # 31. Kopie innert 10 Tagen an GVZ
        'mannschaftd_einsa': (None, '70'), # 32. Einsatzleiter|in
    }

    # post data to create new einsatzrapport
    answer = session.post(
        'https://lodur-zh.ch/urdorf/index.php',
        params=params,
        files=data,
    )
    # very ugly way to find the assigned event id by lodur
    # lodur really adds a script element at the bottom of the returned html
    # with the location to reload the page - containing the assigned event id
    lodur_id = re.search('modul=36&event=([0-9].*)&edit=1&what=144', answer.text).group(1)
    return lodur_id

def upload_alarmdepesche(username, password, base_url, lodur_id, file_name, file_path):
    session = requests.session()
    login_data = {
        'login_member_name': username,
        'login_member_pwd': password,
    }

    # Authenticate
    session.post(base_url, data=login_data)

    params = (
        ('modul', '36'),
        ('what', '828'),
        ('event', lodur_id),
    )

    data = {'alarmdepesche': open(file_path, 'rb')}

    session.post(
        'https://lodur-zh.ch/urdorf/index.php',
        params=params,
        files=data,
    )

# TODO this doesnt work. We first have to fetch the current form with its
# data, update the fields we want to change and resubmit the form
def update_einsatzrapport(username, password, base_url, lodur_id, data):
    """ Update the Einsatzrapport """

    session = requests.session()
    login_data = {
        'login_member_name': username,
        'login_member_pwd': password,
    }

    # Authenticate
    session.post(base_url, data=login_data)

    params = (
        ('modul', '36'),
        ('what', '144'),
        ('sp', '1'),
        ('event', lodur_id),
        ('edit', '1'),
        ('is_herznotfall', ''),
    )

    answer = session.post(
        'https://lodur-zh.ch/urdorf/index.php',
        params=params,
        files=data,
    )
    print(answer.headers)
