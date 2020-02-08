# From Mail to Lodur - all automated

"Loki - Nordischer Gott des Feuers"

*General application description is in German*

**pylokid** ist eine Hilfsapplikation um z.B. Einsatzaufträge, welche die
**Einsatzleitzentrale (ELZ)** per E-Mail versendet, automatisch im
**[Lodur](https://www.lodur.ch/lodur.html)** einzutragen.
Die Applikation versucht so viele Informationen über den Einsatz in
Erfahrung zu bringen, wie nur möglich. Dies geschieht unter anderem
durch Auslesen von Daten aus dem der E-Mail angehängten PDF.

Im Moment ist die Applikation vermutlich nur im **Kanton Zürich** einsetzbar
und vermutlich auch nur für die **[Feuerwehr Urdorf](https://www.feuerwehrurdorf.ch/)**.
Bei Interesse an dieser Applikation von anderen Feuerwehren bin ich
gerne bereit, diese entsprechend zu generalisieren und
[weiter zu entwickeln](https://github.com/tobru/pylokid/issues/new).

## Funktionsweise

Bei einem Feuerwehralarm sendet die ELZ automatisch eine E-Mail
mit einem PDF im Anhang, welches alle notwendigen Informationen
zum Einsatz enthält. Nach Abschluss des Einsatzes sendet die ELZ
ein weiteres E-Mail mit dem Einsatzprotokoll.

pylokid funktioniert so:
* Alle x Sekunden wird das angegebene Postfach nach ELZ E-Mails
  überprüft. Diese identifizieren sich mit dem Betreff
  "Einsatzausdruck_FW" oder "Einsatzprotokoll".
* Wird ein passendes E-Mail gefunden, wird der Anhang (das PDF)
  heruntergeladen, in die Cloud gespeichert (WebDAV) und im Lodur
  ein entsprechender Einsatzrapport eröffnet und vorausgefüllt.
  Das PDF wird sinnvoll umbenannt und als Alarmdepesche ins Lodur
  geladen.
* Kommen weitere E-Mails mit dem Betreff "Einsatzausdruck_FW" werden
  diese im Lodur am entsprechenden Einsatzrapport angehängt.
* Ist der Einsatz abgeschlossen und das Einsatzprotokoll eingetroffen
  werden die Informationen im Lodur nachgetragen.
* Wird der von Hand ausgefüllte Einsatzrapport via Scanner per E-Mail
  an das E-Mail Postfach gesendet (Betreff "Attached Image FXXXXXXXX")
  wird das PDF in der Cloud und im Lodur gespeichert.

Desweiteren wird über Pushover eine Nachricht mit möglichst vielen
Informationen publiziert.

## Stolpersteine / Herausforderungen

Im abgebildeten Prozess gibt es viele Stolpersteine. Zwei davon:

* Die ELZ sendet PDFs welche by design keine Datenstruktur haben.
  Somit ist das herausholen von Informationen mehr Glückssache
  als Verstand. Würde die ELZ die Informationen vom PDF als
  strukturierte Daten liefern, würde das System um einiges stabiler.
* Lodur hat keine API. Alle Datenmanipulationen funktioniert über
  Reverse Engineering der HTML Formulare. Dabei kamen einige
  spezielle Techniken von Lodur zum Vorschein:
  * Nach dem Anlegen eines Einsatzrapportes wird in der Antwort des
    Servers dieselbe Seite mit einem JavaScript Script gesendet,
    welches die Browserseite noch einmal neu lädt und zum angelegten
    Datensatz weiterleitet. Nur in diesem JavaScript Tag findet man
    die zugewiesene Datensatz ID.
  * Zur Bearbeitung eines Datensatzes werden die bekannten Daten nicht
    etwa im HTML Formular als "value" eingetragen, sondern via
    JavaScript ausgefüllt. Und es müssen immer alle Daten nochmals
    gesendet werden, inkl. einiger hidden Fields.

Um die Probleme mit Lodur zu umgehen, werden alle Daten, welche
an Lodur gesendet werden, in einem JSON File im WebDAV neben den
PDFs abgelegt. So lässt sich im Nachhinein ein Datensatz bearbeiten
und eine Zuordnung des Einsatzes im WebDAV und in Lodur herstellen.

## Installation and Configuration

The application is written in Python and runs perfectly on Kubernetes.

Configuration is done via environment variables:

* *IMAP_SERVER*: Adress of IMAP server
* *IMAP_USERNAME*: Username for IMAP login
* *IMAP_PASSWORD*: Password of IMAP user
* *IMAP_MAILBOX*: IMAP Mailbox to check for matching messages. Default: INBOX
* *IMAP_CHECK_INTERVAL*: Interval in seconds to check mailbox. Default: 30
* *WEBDAV_URL*: Complete WebDAV URL
* *WEBDAV_USERNAME*: Username for WebDAV
* *WEBDAV_PASSWORD*: Password of WebDAV user
* *WEBDAV_BASEDIR*: Basedir on WebDAV
* *TMP_DIR*: Temporary directory. Default: /tmp
* *LODUR_USER*: Username for Lodur login
* *LODUR_PASSWORD*: Password of Lodur user
* *LODUR_BASE_URL*: Lodur base URL
* *HEARTBEAT_URL*: URL to send Hearbeat to (https://hchk.io/)
* *PUSHOVER_API_TOKEN*: Pushover API token
* *PUSHOVER_USER_KEY*: Pushover User key

Environment variables can also be stored in a `.env` file.

## WCPGW

What could possibly go wrong? A lot!

* Storing files with "current year" doesn't work well during end of year
* PDF layout may change without information
* PDF parsing may fail due to PDF creation instabilities
* Lodur forms can change without notice
* Error handling doesn't catch all cases

## Lodur Information Gathering

### eins_stat_kantone

_02. Einsatzart FKS_

```
<option value="1">Brandbekämpfung</option>
<option value="2">Elementarereignisse</option>
<option value="3">Strassenrettung</option>
<option value="4">Technische Hilfeleistungen</option>
<option value="5">Ölwehr</option>
<option value="6">Chemierwehr inkl. B-Einsätze</option>
<option value="7">Strahlenwehr</option>
<option value="8">Einsätze auf Bahnanlagen</option>
<option value="9">BMA Unechte Alarme</option>
<option value="10">Verschiedene Einsätze</option>
<option value="11">Keine alarmmässigen Einsätze</option>
```

### emergency_concept_id / ver_sart

_03. Verrechnungsart_

* `emergency_concept_id` = value
* `ver_sart`= rc-id

```
<option value="2" rc-id="ab">ABC-Einsatz inkl. Oel (Ortsfeuerwehr)</option>
<option value="3" rc-id="ab">ABC-Einsätze inkl. Oel (Stützpunkte)</option>
<option value="4" rc-id="ab">ABC-Messwagen (Stützpunkte)</option>
<option value="5" rc-id="ab">Gaseinsätze (Ortsfeuerwehr)</option>
<option value="6" rc-id="ab">Verkehrsunfälle (ohne Strassenrettung)</option>
<option value="7" rc-id="ab">Strassenrettung (Ortsfeuerwehr)</option>
<option value="8" rc-id="ab">Strassenrettung (Stützpunkt)</option>
<option value="9" rc-id="ab">Fahrzeugbrände (ohne Brandstiftung)</option>

<option value="10" rc-id="th">BMA-Alarm</option>
<option value="18" rc-id="th">Hilfeleistungs-Einsätze, verrechenbar durch OFW</option>
<option value="19" rc-id="th">Unterstützung Rettungsdienst (ADL/Hilfskräfte)</option>

<option value="11" rc-id="uh">Dienstleistungen, Verrechenbar durch OFW</option>
<option value="12" rc-id="uh">Stützpunkteinsatz (Grossereignisse)</option>
<option value="14" rc-id="uh">Nachbarschaftshilfe Ortsfeuerwehr</option>
<option value="20" rc-id="uh">Kernaufgaben (Brand, Explosion, Elementar, Erdbeben)</option>
<option value="21" rc-id="uh">ADL-/HRF-Einsatz BRAND (ADL = Stüpt-Fahrzeug)</option>

<option value="13" rc-id="ak">ADL-/HRF-Einsatz BRAND (ADL = OFW-Fahrzeug)</option>
<option value="15" rc-id="tt">Grosstierrettung Stützpunkt (PIF mit Kran)</option>
```

## Notes

### Local dev stuff

`docker run --rm -ti -v $(pwd):/usr/src/pylokid:ro local/pylokid`

`find ./ -name "Einsatzausdruck_FW*.pdf" -exec pdftotext -f 1 -l 1 -x 70 -y 47 -W 50 -H 10 {} - \;`