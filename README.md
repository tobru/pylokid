# From Mail to Lodur - all automated

"Loki - Nordischer Gott des Feuers"

This app helps a Feuerwehr Fourier from the Canton of Zurich
in Switzerland to ease the pain of the huge work for getting
Einsätze correctly into [Lodur](https://www.lodur.ch/lodur.html).

## Idea

* Get mails sent by ELZ with subjects
  "Einsatzausdruck_FW" and "Einsatzprotokoll"
* Store attached PDF in Feuerwehr Cloud (WebDAV)
* Publish new message over MQTT
* Parse PDFs and try to get information about Einsatz
* Connect to Lodur and create a new Einsatzrapport with
  as much information as possible

## TODO

### Version 1

* Much more error handling
* Parse PDF
  * Store parsed data in Lodur text fields for copy/paste
* Cleanup code into proper functions and classes
  * Lodur "API" class
* Proper exit
* Healthchecks for Kubernetes probes

Before version 1 can be tagged, it must have processed at least 5 real
Einsätze!

### Known instabilities

* Storing files with "current year" doesn't work well during end of year

### Future versions

* Generalize
* Documentation
* IMAP idle
* Display PDF on Dashboard
* Send statistics to InfluxDB
* Webapp to see what's going on
* Get as many data out of the PDFs as possible
* Simple webform to fill-in missing data (skipping Lodur completely)
  * Webapp for chosing who was there during the Einsatz (tablet ready)

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
