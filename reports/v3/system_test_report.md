# Ribby – Prüfung des integrierten Bildmodus

Prüfstand: 2026-10-18T11:38:57.197604+00:00 · Edge/Chromium 155.0.4283.62

Alle definierten technischen Prüfungen dieses Teststands bestehen. Das bedeutet **keine 100-prozentige Erkennungsgenauigkeit**. Der Testsatz umfasst 112 separate Fotos mit 8 Aufnahmen je Art; die automatische Rangfolge wird vor einer manuellen Korrektur gemessen.

## Technischer Funktionsumfang

| Prüfung | Ergebnis |
|---|---|
| Backend, Rechte, Lizenzen, Cache, Seeds, Import/Export, parallele Uploads | 32/32 bestanden |
| JavaScript-Syntax, Kosinus-Ranking, Klassenmittelwert und Auswahl | bestanden |
| Echte Bildmodelle, Upload, Vergleich aller 14 Arten, Bestätigung und GPS/Fundort | 224/224 bestanden |
| Gespeicherte Bildresultate für alle Arten erneut öffnen | 14/14 bestanden |
| Abbruch, Kamera-Rennen, Abmeldung, Dateiformate, Server- und Cachefehler, Smartphone-Layout | 18/18 bestanden |
| Browser-Neuladen, Speicherrennen, Nutzerwechsel, Verlauf und 24 Wiederholungsanalysen | 13/13 bestanden |
| Eigene Referenzen je Art speichern/nutzen/löschen | 14/14 Arten bestanden |
| Private Referenzen: Nutzertrennung, Dubletten und Backup | 4/4 bestanden |
| GPS nach Bildausschnitt, echte Audio-Engine, neue Art, englischer Verbindungshinweis | 4/4 bestanden |
| Referenzbilder tatsächlich im Browser dekodiert | 896/896 bestanden |
| Vorberechnete Bildvektoren, Modellkennung, Dimension und Norm | 1792/1792 bestanden |

Die tatsächlichen Vorschlagslisten und gespeicherten GPS-/Art-/Fundortdaten aller 224 Analysen sind zusätzlich gegen die eingefrorene Auswertung und die Dateien auf dem Server geprüft (`system_v3_consistency.json`). HTML-Aufbau und Styles entsprechen vollständig der freigegebenen Vorschau (`design_preservation_v3.json`).

## Erkennung je Art

Jeder Wert bezieht sich auf 8 unabhängige Fotos. „Ablauf“ bewertet die technische Ausführung, nicht die Richtigkeit des Vorschlags. BioCLIP und DINOv2 nutzen hier jeweils 16 Referenzen pro Art. Die Konfiguration wurde vor dieser Prüfung anhand getrennter Validierungsdaten festgelegt.

| Art | Ablauf (beide Modelle) | BioCLIP erster Treffer | BioCLIP Top 3 | DINOv2 erster Treffer | DINOv2 Top 3 |
|---|---:|---:|---:|---:|---:|
| Grasfrosch (*Rana temporaria*) | 16/16 | 1/8 | 7/8 | 1/8 | 5/8 |
| Moorfrosch (*Rana arvalis*) | 16/16 | 4/8 | 8/8 | 6/8 | 8/8 |
| Springfrosch (*Rana dalmatina*) | 16/16 | 6/8 | 7/8 | 5/8 | 7/8 |
| Erdkröte (*Bufo bufo*) | 16/16 | 8/8 | 8/8 | 4/8 | 7/8 |
| Wechselkröte (*Bufotes viridis*) | 16/16 | 7/8 | 8/8 | 6/8 | 8/8 |
| Kreuzkröte (*Epidalea calamita*) | 16/16 | 6/8 | 7/8 | 4/8 | 7/8 |
| Knoblauchkröte (*Pelobates fuscus*) | 16/16 | 4/8 | 7/8 | 7/8 | 7/8 |
| Seefrosch (*Pelophylax ridibundus*) | 16/16 | 3/8 | 6/8 | 1/8 | 5/8 |
| Kleiner Wasserfrosch (*Pelophylax lessonae*) | 16/16 | 1/8 | 5/8 | 3/8 | 6/8 |
| Teichfrosch (*Pelophylax esculentus*) | 16/16 | 4/8 | 8/8 | 3/8 | 8/8 |
| Laubfrosch (*Hyla arborea*) | 16/16 | 8/8 | 8/8 | 8/8 | 8/8 |
| Rotbauchunke (*Bombina bombina*) | 16/16 | 5/8 | 7/8 | 5/8 | 8/8 |
| Gelbbauchunke (*Bombina variegata*) | 16/16 | 2/8 | 5/8 | 6/8 | 7/8 |
| Geburtshelferkröte (*Alytes obstetricans*) | 16/16 | 3/8 | 8/8 | 5/8 | 8/8 |

| Modell | Erster Treffer richtig | Richtige Art unter Top 3 |
|---|---:|---:|
| bioclip | 62/112 (55.4 %) | 99/112 (88.4 %) |
| dinov2 | 64/112 (57.1 %) | 99/112 (88.4 %) |

## Behobene Fehler

- Eine leere oder ungültige Artwahl bestätigt keine frühere oder zufällig passende Art mehr.
- Upload und Bildausschnitt sperren die Analyse während der Vorbereitung. Entfernte/ersetzte Fotos und GPS werden bei asynchroner Verarbeitung korrekt behandelt.
- Nach Abbruch oder Abmeldung erscheinen keine verspäteten Ergebnisse, Kamerafotos oder privaten Fotolisten. Eine alte Kamera-Fehlermeldung stoppt keine neu geöffnete Kamera.
- Fehlende Referenzen führen zu einer klaren Fehlermeldung. Ein Ausfall des optionalen Merkmalscaches blockiert die Analyse nicht; ungültige gespeicherte Vektoren werden neu berechnet.
- Nach einem fehlgeschlagenen Speichern des Verlaufs kann die Bestätigung erneut gespeichert werden, ohne eine nicht vorhandene Verlaufs-ID zu verwenden.
- Gleichzeitige Uploads können dasselbe private Foto nicht zwei Arten zuweisen. Der Dublettenschutz berücksichtigt auch ältere Referenzen ohne gespeicherten Inhalts-Hash.
- Die manuelle Ergänzung einer neuen Art benutzt die richtige Serverroute.

- Öffentliche Suchindizes älterer Versionen werden beim Seed-Upgrade aktualisiert. Bei der Analyse prüft und liefert der Server nur den gewählten Referenzumfang aus; der vollständige Bestand bleibt in der Verwaltung verfügbar.
- Nach dem Neuladen blockiert keine erneut eingeblendete Einwilligung eine bereits akzeptierte Sitzung. Das erneute Öffnen des Hinweises unterbricht die aktive Ansicht nicht.
- Abmelden widerruft den Servertoken. Gleichzeitige Sessionverlängerungen können ihn nicht wieder aktivieren; ungültige Token werden vor einem Dateizugriff abgewiesen.
- Speichervorgänge sind an Foto, Nutzer, Sitzung und Analyse gebunden. Späte Antworten und Fehler ändern keine neue Bestätigung; private Uploads werden nach einem Nutzerwechsel nicht fortgesetzt.
- Beim Öffnen alter Ergebnisse gilt die neueste Auswahl. Zwischenzeitlich gewählte Fotos werden nicht überschrieben. Gespeicherte Audioergebnisse können nicht versehentlich mit einer anderen ausgewählten Audiodatei bestätigt werden.

## Grenzen und Nachvollziehbarkeit

Die Fotos sind nach Foto-ID, Beobachtung und bekannten Urhebern von den 896 Referenzen getrennt. Eine mögliche Überschneidung mit den ursprünglichen Trainingsdaten der Basismodelle ist unbekannt. 8 Fotos je Art bleiben eine kleine Stichprobe; die Artlabels stammen aus den eingefrorenen Quellen und wurden nicht für diese Prüfung fachlich neu bestimmt.
Kamera: virtuelles Chromium-Testgerät, inklusive Aufnahme, verweigerter Berechtigung und verspäteter Rückmeldungen. Mobile Prüfung: Smartphone-Viewport. Echte Android-/iPhone-Hardware und Safari wurden nicht geprüft. Die Audio-Regressionsprüfung verwendet ein synthetisches PCM-Signal und misst keine akustische Artgenauigkeit.
Die Serverdaten aller Prüfungen liegen in isolierten Testordnern. Die Produktivdatenbank wurde nicht geöffnet. Testfotos werden für die Modellanalyse im Browser verarbeitet; im echten Artentest wurden keine Uploads an externe Dienste beobachtet.
Der Vergleich mit dem früheren Bestand auf identischen Fotos und die getrennte Modellwahl sind im [Genauigkeitsbericht V3](image_accuracy_v3.md) dokumentiert.
Reproduktion: [Systemtest-Anleitung](../tests/SYSTEM_TESTS.md). Einzelresultate: `system_all_species.json`, `system_faults.json`, `system_lifecycle.json`, `system_private_species.json`, `system_reference_pack.json`, `system_regressions.json` und `system_core_tests.json`.
Der getestete Projektstand liegt lokal. Eine Veröffentlichung auf GitHub oder ein Produktivdeployment wurde nicht vorgenommen; der zuletzt geprüfte GitHub-Schreibzugriff war mit 403 blockiert.

## Prüfsummen des getesteten Codes

- `ribby_app.html`: `04d32c4191828ad19aae55c0a8174d48b3156739498eb129666b67bace135bfd`
- `ribby_server.py`: `2373dcdb1f0f599daa8500aa46a5c96a6e1678218cc03ca8b1ffb4e4df78cae4`
- `ribby_images.py`: `0ae1e3826ce75cdf37c5680c644699af9ccdd6745d36180c8f150f540d898ead`
