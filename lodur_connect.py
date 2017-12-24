#!/usr/bin/env python3

import re
from datetime import datetime
import requests

def create_einsatzrapport(username, password, base_url, f_id):

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

    data = {
        'e_r_num': (None, '1'), # 01. Einsatzrapportnummer
        'eins_stat_kantone': (None, '1'), # 02. Einsatzart FKS
        'emergency_concept_id': (None, '2'), # 03. Verrechnungsart
        'ver_sart': (None, 'ab'), # 03. Verrechnungsart internal: ab, th, uh, ak, tt
        'dtv_d': (None, str(datetime.now().day)), # 04. Datum von
        'dtv_m': (None, str(datetime.now().month)), # 04. Datum von
        'dtv_y': (None, str(datetime.now().year)), # 04. Datum von
        'dtb_d': (None, str(datetime.now().day)), # 04. Datum bis
        'dtb_m': (None, str(datetime.now().month)), # 04. Datum bis
        'dtb_y': (None, str(datetime.now().year)), # 04. Datum bis
        'ztv_h': (None, '11'), # 05. Zeit von
        'ztv_m': (None, '11'), # 05. Zeit von
        'ztb_h': (None, '12'), # 05. Zeit bis
        'ztb_m': (None, '12'), # 05. Zeit bis
        'e_ort_1': (None, '306'), # 06. Einsatzort: Urdorf 306, Birmensdorf 298
        'eins_ereig': (None, f_id), # 07. Ereignis
        'adr': (None, 'TBD'), # 08. Adresse
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
        'kopie_gvz': (None, '1'), # 31. Kopie innert 10 Tagen an
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
