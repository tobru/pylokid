# Lodur Einsatzapp

"Loki - Nordischer Gott des Feuers"

## Idea

* Get mails sent by ELZ with subjects
  "Einsatzausdruck_FW" and "Einsatzprotokoll"
* Store attached PDF in Feuerwehr Cloud (WebDAV)
* Publish new message over MQTT
* Parse PDFs and try to get information about Einsatz
* Connect to Lodur and create a new Einsatzrapport with
  as much information as possible

## Todo

* Move processed mail to subfolder
* Lodur Connect (Create Einsatzrapport)
* IMAP idle
* Error Handling
