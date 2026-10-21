# Ribby – Arten erkennen mit Ton und Bild

Reguläre Ribby-App mit Audio- und Bildanalyse, auf Basis des GitHub-Stands
`ef2b4adf2cfb2467f9b47c81ba7a00b20d1dbc68` vom 13. Juni 2026.
Beide Modi gehören zur gleichen App, Anmeldung, Artenbibliothek und Datenbank.

## Start

Python 3.10 oder neuer, keine zusätzlichen Python-Pakete:

```powershell
python ribby_server.py
```

Die App ist unter `http://localhost:7432` erreichbar. Für die Live-Kamera auf
anderen Geräten ist HTTPS erforderlich. Auf Smartphones steht zusätzlich die
Systemkamera über die Dateiauswahl bereit. Die HTML-Datei kann weiterhin separat
geöffnet werden; Online-Referenzbilder benötigen den aktualisierten Ribby-Server.

Für vorhandene Installationen `ribby_app.html`, `ribby_server.py` und
`ribby_images.py`, alle `ribby_image_seed.zip.part*` und
`ribby_image_seed.zip.manifest.json` gemeinsam aktualisieren. Die bestehenden
Audio-Seed-Dateien aus dem Repository beibehalten. Docker enthält den Bildmodus
und die mitgelieferten Referenzbilder im normalen App-Image.
`RIBBY_DATA_DIR` muss auf Render auf ein persistentes Volume zeigen.

## Bildmodus

1. Auf „Übersicht → Bildanalyse“ wechseln und eine Artengruppe auswählen.
2. Foto mit der Kamera aufnehmen, per Dateiauswahl laden oder hineinziehen.
3. „Analysieren“ starten. Der Fortschritt zeigt die vorbereitete Art;
   eine laufende Analyse kann abgebrochen werden.
4. Vorschläge anhand von Merkmalen prüfen und die Art bestätigen oder korrigieren.
   Der gemeinsame Ribby-Bestätigungsdialog bietet manuelle Artwahl, Fundort und
   GPS sowie optional das Speichern als privates Referenzfoto.

Upload, Aufnahme, Vorschlagskarten und Bestätigung verwenden das bestehende
Ribby-Design. Audio- und Bildanalysen erscheinen im gemeinsamen Verlauf und
auf der Karte. Unter „Verwaltung → Referenzbilder“ lassen sich private Fotos
löschen und die Online-Quellen der Artenliste einsehen. Alle Nutzer können ihre
eigenen Fotos über „Profil → Meine Referenzfotos“ verwalten. Modell und Referenzumfang
sind unter „Analyse-Einstellungen“ aufklappbar. Ein Wechsel des Modus oder der
Seite verwirft veraltete Ergebnisansichten und stoppt eine aktive Kamera.

JPEG, PNG und WebP bis 15 MB werden unterstützt. Ribby richtet das Foto aus,
verkleinert es auf maximal 1600 Pixel und entfernt durch erneutes JPEG-Encoding
EXIF-Metadaten. HEIC bitte vorher in JPEG umwandeln.

Die Bildmerkmale werden standardmäßig mit **BioCLIP v1** in einem Web Worker
auf dem Gerät berechnet. Der geprüfte fp16-Export wird beim ersten Einsatz von
Hugging Face geladen (173 MB), ONNX Runtime Web 1.22.0 von jsDelivr. Modellrevision:
`22a18d2fd141d2301968d93881b9e4431470c149`; SHA-256:
`d982b6800a5b751272485ad4dd266f3d3eb39457b882daa5a0557cbbb62b3e9d`.
Der kompaktere **DINOv2 Small** bleibt als Alternative verfügbar, über
Transformers.js 3.8.1, Revision `c2bb04a51fab207c420665f1946016107bffc701`.
Es ist kein API-Schlüssel und kein
kostenpflichtiger Erkennungsdienst nötig. Ein aktueller Browser mit WebAssembly,
Web Workers, OffscreenCanvas und `createImageBitmap` wird benötigt.

BioCLIP und DINOv2 vergleichen Klassenprototypen in einem angepassten Merkmalsraum.
Eine regularisierte lineare Projektion wird offline aus 896 öffentlichen
Referenzfotos gelernt und ist in der HTML-Datei enthalten (`image_metric.json`
dokumentiert den eingefrorenen Stand). Die vortrainierten Bildmodelle selbst
werden nicht verändert. Projektion und Parameter wurden ausschließlich mit nach
Fotografen getrennter, fünffacher Kreuzvalidierung gewählt. Die zusätzlichen
Prüffotos bleiben davon getrennt. Bei Arten außerhalb der erlernten Artengruppe
verwendet Ribby den bisherigen Vergleich als Rückfallverfahren.
Die Kosinuswerte im angepassten Raum werden von −1…1 auf 0…1 abgebildet.
Diese Bildähnlichkeit bleibt gespeichert. Für den geprüften Referenzbestand
berechnet eine offline gelernte Temperaturskalierung daraus zusätzlich eine
geschätzte Trefferchance über alle 14 Arten (`image_calibration.json`, in der
HTML-Datei enthalten). Die Kalibrierung verändert keine Rangfolge. Sie verwendet
ausschließlich nach Fotografen getrennte Vorhersagen der öffentlichen Referenzen;
eigene Fotos und unabhängige Prüffotos fließen nicht in ihre Anpassung ein.
Je Art sind 8, 16 (Standard) oder bis zu 32 Onlinefotos wählbar, ergänzt durch
eigene Referenzen. Mit „Motiv markieren“ lässt sich ein Ausschnitt um das Tier
wählen; „Ganzes Foto“ stellt das ursprüngliche normalisierte Foto wieder her.
Bereits berechnete Referenzmerkmale bleiben in IndexedDB,
das Modell im Browsercache. Nach einer vollständigen Vorbereitung sind eigene
Referenzanalysen auch ohne externe Quellen möglich; die initiale Vorbereitung
benötigt Internet. Bei Serverbetrieb wird für private Referenzen und Verlauf
weiterhin eine Verbindung zum Server benötigt.

**„Trefferchance“ ist eine kalibrierte Schätzung unter der Voraussetzung, dass
das Foto eine der 14 verglichenen Arten zeigt.** Diese Anzeige gilt nur für die
geprüften öffentlichen Referenz-IDs bei 8, 16 oder 32 Bildern je Art und das
zugehörige Modell. Private, geänderte oder fehlende Referenzen sowie andere
Artengruppen erhalten ausdrücklich die Anzeige „Bildähnlichkeit“. Ein späterer
Quellen-Refresh kann diesen Rückfall auslösen. Neue Konfigurationen benötigen
eine eigene Kalibrierung. Werte über 99 % werden als „>99 %“ angezeigt, Werte
unter 1 % als „<1 %“; sie werden nicht zu einer 100-%-Garantie aufgerundet.
Fehlende Referenzen und Quellenfehler
werden angezeigt. Ähnliche Arten, schlechte Fotos und Arten außerhalb der
Bibliothek können falsche Vorschläge erzeugen. Eine fachliche Bestätigung ist
erforderlich. Es wurde keine Feldstudie zur Bestimmungsgenauigkeit durchgeführt.

Zusätzlich zu den Referenz-IDs werden die SHA-256-Prüfsummen der tatsächlich
verwendeten Fotos mit dem eingefrorenen Bestand in `image_reference_integrity.json`
verglichen. Geänderte Bilddateien unter gleicher ID erhalten keine kalibrierte
Trefferchance. Die Kalibrierungsparameter und die Bildmodelle bleiben unverändert.

Gespeicherte Browsermerkmale sind an Modellkennung und Foto-Prüfsumme gebunden.
Ändert sich ein öffentliches oder privates Foto bei gleicher ID, werden seine
Merkmale neu berechnet. Alte Cache-Einträge ohne diese Bindung werden beim ersten
Einsatz erneuert. Passende Einträge und geprüfte mitgelieferte Vektoren bleiben
ohne erneute Modellberechnung nutzbar. Fehlt eine Prüfsumme, wird sie aus dem
Foto ermittelt; passt ein Download nicht mehr zur angekündigten Prüfsumme, wird
dieses Referenzfoto für den laufenden Vergleich verworfen. Nutzerfotos werden
für diese Prüfungen weiterhin nur lokal verarbeitet.

Bei manueller Artkorrektur gehört die Zahl zur gewählten Art. Fehlt für sie ein
gespeicherter Modellwert, wird keine Prozentzahl ergänzt. Verlauf und CSV erhalten
den Score-Typ und die Kalibrierungskennung; alte Bildähnlichkeiten werden nicht
nachträglich als Wahrscheinlichkeiten ausgegeben. Fundort/GPS und bestätigte Art
werden wie bisher gemeinsam gespeichert.

## Onlinebilder und Rechte

- **Wikimedia Commons:** Suche nach dem wissenschaftlichen Namen; zusätzlich muss
  eine passende Artkategorie vorhanden sein. Reine Namensnennungen in Beschreibungen
  und Karten/Zeichnungen werden verworfen. Lizenzprüfung anhand der kanonischen
  `LicenseUrl` jedes einzelnen Bilds.
- **iNaturalist:** wissenschaftlicher Name muss exakt passen, Beobachtung mit
  Research-Grade; zusätzlich wird die Lizenz **jedes Fotos** geprüft. Explizite
  Hybridmarker (`×`, `kl.`) werden bei der Namenssuche normalisiert, damit auch
  der Teichfrosch gefunden wird. Andere Art-Epitheta werden nicht gleichgesetzt.
- Je Beobachtung wird nur ein Foto verwendet. Die Auswahl wechselt zwischen
  Urhebern. iNaturalist-Fotos, die auf Commons gespiegelt wurden, werden über
  ihre ursprüngliche Foto-ID dedupliziert. Gleiche eigene Fotos werden nicht
  mehrfach gespeichert und dürfen nicht zugleich verschiedenen Arten zugeordnet sein.
- Zulässig sind ausschließlich **CC0 1.0** und **CC BY 1.0–4.0**. Unbekannte
  Lizenzen, NC, ND, SA und gebietsspezifische Lizenzvarianten werden verworfen.
- Urheber, Bildtitel, Originalquelle, Lizenzlink und Abrufzeit bleiben gespeichert.
  Die Trefferkarten zeigen Namensnennung, Lizenz und Originalquelle. Bilder werden
  ohne Beschnitt verkleinert angezeigt. Bildzuordnung aus Suchergebnissen bitte
  überprüfen; insbesondere die Commons-Suche ist keine taxonomische Prüfung.
- Metadaten und Referenzbilder liegen unter `ribby_data/image_refs/`. Suchergebnisse
  werden sieben Tage zwischengespeichert, Quellenfehler nur zehn Minuten. Externe
  Bildabrufe sind auf bekannte HTTPS-Hosts beschränkt, einschließlich Weiterleitungen.
  Leere Treffer werden nur zehn Minuten gespeichert. Die neue Cacheversion
  aktualisiert die alten, auf wenige Bilder beschränkten Suchergebnisse automatisch.
  iNaturalist-Abfragen werden auf weniger als 60 pro Minute begrenzt.
  Falls eine Quelle ausfällt, werden gültig lizenzierte gespeicherte Referenzen
  weiterverwendet; der Ausfall wird angezeigt.
- Eigene bestätigte Fotos sind **private Referenzen** des angemeldeten Nutzers.
  Durch das Speichern wird keine öffentliche Nachnutzungslizenz erteilt. Sie können
  unter „Verwaltung → Referenzbilder“ gelöscht werden und sind im vollständigen
  Backup enthalten.

CC BY erlaubt kommerzielle Nutzung unter ihren Bedingungen, insbesondere
Namensnennung und Lizenzlink. CC0 verzichtet weitgehend auf urheberrechtliche
Beschränkungen. Die App bezeichnet daher nicht pauschal alle Bilder einer
Plattform als lizenzfrei. Die Lizenzangaben stammen von den Quellen.

Eigene Fotos verlassen für die Analyse den Browser nicht. Nur wenn eine private
Referenz gespeichert wird, geht das normalisierte Foto an den verbundenen
Ribby-Server. Analyseverlauf und Bestätigung werden ebenfalls dort gespeichert.
Externe Dienste erhalten beim Modell- und Quellenabruf technische Verbindungsdaten,
aber keine Nutzerfotos. Der Onlinequellen-Schalter kann deaktiviert werden.

## Mitgelieferte Referenzbilder

Die reguläre App enthält in drei `ribby_image_seed.zip.part*`-Dateien **896 unterschiedliche Fotos für die 14
ursprünglichen Amphibienarten**, alle mit CC0 oder CC BY, Quellenangabe und Urheber.
Außerdem enthalten sie **1792 vorberechnete Merkmalsvektoren** für beide Modelle.
Die Teile sind jeweils kleiner als 50 MiB und ergeben unverändert dasselbe
ZIP-Archiv. Die Manifestdatei enthält Dateilängen und SHA-256-Prüfsummen für jeden
Teil und das Gesamtarchiv. Vor dem Import werden Vollständigkeit und alle
Prüfsummen geprüft. Fehlende, zusätzliche, beschädigte oder gekürzte Teile werden
mit einer Fehlermeldung abgewiesen, bevor Referenzen installiert werden.
Der Server liest die Teile direkt; es wird kein Gesamtarchiv im Arbeitsspeicher
oder auf der Festplatte zusammengesetzt. Ein vorhandenes vollständiges
`ribby_image_seed.zip` aus früheren Downloadpaketen wird weiterhin unterstützt.
Beim normalen Serverstart werden fehlende Referenzdateien automatisch nach
`RIBBY_DATA_DIR` (standardmäßig `ribby_data/`) übernommen. Vorhandene Dateien,
eigene Fotos und die bestehende Audio-Datenbank bleiben erhalten. Öffentliche
Suchindizes einer älteren Cacheversion werden auf den größeren Bestand aktualisiert. Es ist kein
separater Import in der App nötig. Jede Datei wird atomar übernommen, damit ein
abgebrochener Erststart keine unvollständigen Referenzdateien hinterlässt.
`RIBBY_DISABLE_SEED=1` schaltet beide Seeds ab.
Die Merkmale werden gegen Modellkennung,
Dimension und SHA-256 des zugehörigen Fotos geprüft. So muss der Browser die
öffentlichen Referenzbilder nicht erneut durch das Modell rechnen; das eigene
Foto wird weiterhin lokal ausgewertet. Die Modelle selbst sind nicht im Paket.

Den Bestand ohne zusätzliche Python-Pakete neu vorbereiten:

```powershell
python prepare_image_references.py --data-dir ribby_data
# Alternativ den mitgelieferten ursprünglichen Artenkatalog verwenden:
python prepare_image_references.py --data-dir ribby_data --species-file image_reference_catalog.json
```

`--refresh` erneuert die Suchmetadaten, `--metadata-only` lädt keine Bilddateien.
Veraltete Vektoren werden bei geändertem Bild verworfen und lokal neu berechnet.
Der Artenkatalog ergänzt keine Arten automatisch in einer bestehenden Datenbank.

## Gemessene Genauigkeit und Grenzen

Aktuelle Prüfung der Prozentwerte: [Kalibrierungsbericht V4](reports/image_calibration_v4.md).
Auf 68 neuen, von Referenzen und bisherigen Tests getrennten Fotos liegt bei
16 Referenzen die mittlere geschätzte Trefferchance von BioCLIP bei **66,9 %**,
bei **45/68 (66,2 %)** richtigen Ersttreffern. DINOv2 zeigt im Mittel **58,1 %**,
bei **39/68 (57,4 %)** richtigen Ersttreffern. Die Fehlermaße der Prozentwerte
verbessern sich auf denselben Bildern; die Artvorhersagen bleiben unverändert.
Die kleine Stichprobe erlaubt keine Garantie für einzelne Fotos oder Arten.

Die frühere Verfahrensprüfung ist im [Genauigkeitsbericht V3](reports/image_accuracy_v3.md)
dokumentiert und verwendet andere Prüffotos:
Der Bestand umfasst 896 Referenzen, 64 pro Art, mit 1792 vorberechneten
Vektoren. Auf 112 zusätzlichen, nach Urhebern/Beobachtungen/Fotos getrennten
Prüffotos verbessert sich BioCLIP von **59 auf 62** richtige Ersttreffer,
DINOv2 von **46 auf 64**. Die richtige Art liegt jeweils **99/112** Mal in den
ersten drei Vorschlägen. Der Zuwachs bei BioCLIP ist klein und statistisch nicht
abgesichert. Ein bloßer größerer Vorrat ohne die angepasste Metrik verändert
die Ersttreffer dieses Tests bei 16 ausgewählten Referenzen nicht.
Auch schwierige Motive, Larven und verdeckte Tiere bleiben im Testsatz.
Das ist keine Feldvalidierung und keine Garantie für richtige Artbestimmung.

## Prüfung

Die vollständige Funktionsprüfung des integrierten Bildmodus mit allen 14 Arten
steht im [System-Prüfbericht](reports/system_test_report.md). Sie trennt technische
Fehlerfreiheit der definierten Abläufe von der gemessenen Erkennungsquote je Art.
Die Browser-Lesbarkeit aller 896 unveränderten Referenzfotos wurde in V3 geprüft.
Beide echten Bildmodelle durchlaufen aktuell den Upload- und Bestätigungsablauf
mit allen 68 neuen Testfotos (136 Abläufe). Die früheren 112 Fotos werden zusätzlich
mit der eingefrorenen Auswertung geprüft. Sieben gezielte Browserfälle prüfen die
Prozentanzeige. Fehlerfälle und eigene Referenzen werden zusätzlich geprüft.
Reproduktion: [Systemtest-Anleitung](tests/SYSTEM_TESTS.md).
Der zusätzliche [Veröffentlichungstest](reports/release_v5.md) prüft den normalen
Serverstart ausschließlich mit den drei Teilen und alle installierten Dateien.
Die zusätzlichen Cache- und Prüfsummenprüfungen sind im
[Optimierungsbericht V6](reports/release_v6.md) dokumentiert.

```powershell
python -m unittest discover -s tests -p test_images.py -v
node tests/test_image_logic.cjs
node tests/test_image_calibration.cjs
node tests/test_image_cache.cjs
python -m py_compile ribby_server.py ribby_images.py
```

Die Tests prüfen Lizenzen, Quellenfilter, Cache, Zugriffsschutz, privaten
Referenzspeicher, Bildverlauf, Kamerarichtlinie, JavaScript-Syntax und Ranking.
Der Browserablauf wurde mit Upload, Kamera-Freigabe/Ablehnung, Bildausschnitt,
echter BioCLIP-Inferenz, gemeinsamem Bestätigungsdialog, Fundort/GPS, Verlauf,
Referenzverwaltung und Smartphone-Layout geprüft. Eine zusätzliche Prüfung
deckt den Moduswechsel während einer noch laufenden Audioauswertung ab.

Quellen: [Commons-Nachnutzung](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia),
[iNaturalist-Bildrechte](https://help.inaturalist.org/en/support/solutions/articles/151000169918),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## Toolbox und App-Icon

Das vorhandene Ribby-Logo wird auch als Browser-Icon verwendet. Für die
Toolbox ist das Original zusätzlich als PNG unter `toolbox/ribby-logo.png` enthalten.
Der optionale direkte Einstieg für bereits angemeldete Toolbox-Admins ist in
[toolbox/README.md](toolbox/README.md) beschrieben. Ohne diese gezielte
Serverkonfiguration bleibt die bisherige eigenständige Anmeldung aktiv.

## Image analysis performance

Public reference features prepared by an administrator are cached centrally for the exact image SHA-256 and model revision. Existing valid packs remain unchanged; private photos are excluded. The image model warms up when photo mode opens, and reference metadata loads with at most four parallel requests. New models, reference photos or species may still need one-time preparation.

See [measured timings and validation](reports/image_performance.md).

## Map background

The GPS map uses BKG TopPlusOpen with visible source and licence links. Failed tiles fall back once to OpenStreetMap; markers remain available if both providers fail. Tile images and explicit place searches send only the app origin as their cross-origin referrer. See [map service verification](reports/map_service.md).
