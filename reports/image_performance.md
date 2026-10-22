# Ribby – Prüfung und Beschleunigung der Bildanalyse

Stand: 21.10.2026. Ausgangscommit: `7f4d7239e23433b64f4483621002abc6c46a6dee`, Branch `codex/image-recognition-calibrated`.

## Gemessene Laufzeiten

Echter Browserlauf mit Microsoft Edge unter Windows, lokalem Ribby-Server über den Toolbox-Adminzugang, BioCLIP FP16 (173 MB), allen 20 vorhandenen Arten und bis zu 16 Referenzfotos je Art. Gemessen vom Klick auf „Analysieren“ bis zur vollständig angezeigten Ergebnisliste. Reale Modellberechnung und Referenz-APIs; keine simulierte Erkennung. Nur das Speichern des Testlaufs in der produktiven Historie wurde im Testbrowser unterdrückt.

| Lauf | Vorher | Nachher |
| --- | ---: | ---: |
| Neuer Browser ohne lokalen Modell- und Referenzcache | 131,473 s | 4,750 s |
| Zweite Analyse desselben Fotos | 1,106 s | 0,972 s |
| Dritte Analyse desselben Fotos | 1,087 s | 0,970 s |

Vorher waren beim ersten Lauf 96 Merkmalsberechnungen nötig: das Eingabefoto und 95 fehlende öffentliche Referenzen. Nach der einmaligen zentralen Vorbereitung war auch im komplett neuen Browser nur eine Merkmalsberechnung nötig. Alle 20 Arten und derselbe Referenzumfang blieben eingeschlossen. Ergebnisreihenfolge, Ähnlichkeitswerte und angezeigte Konfidenzwerte waren für dieses Vergleichsfoto in allen drei optimierten Läufen exakt gleich wie zuvor.

Drei verschiedene öffentliche Fotos wurden anschließend in derselben Browsersitzung analysiert: Rana temporaria in 1,636 s, Bufo bufo in 0,903 s und Hyla arborea in 1,587 s. Damit wurde keine Erkennungsquote gemessen.

## Änderungen

- Öffentliche Referenzmerkmale werden nach einer Admin-Berechnung zentral wiederverwendet. Das Modell, die Vektorlänge und die SHA-256-Prüfsumme der tatsächlich gespeicherten Bilddatei müssen passen. Unzulässige Quellen, private Referenzfotos und ungültige Merkmale werden abgewiesen. Bereits gültige Merkmalspakete werden nicht überschrieben.
- Das Modell wird beim Öffnen der Bildfunktion vorbereitet. Gleichzeitige Vorbereitung und Analyse teilen sich denselben Ladevorgang; ein Ladefehler erlaubt einen erneuten Versuch.
- Modellberechnung und Referenzabfragen laufen parallel. Höchstens vier Referenzabfragen beziehungsweise optionale Cache-Rückgaben laufen gleichzeitig; die ursprüngliche Artenreihenfolge bleibt erhalten.
- Die Toolbox leitet die Länge gestreamter Anfragen korrekt weiter. Ohne diese Korrektur wies der Ribby-Server Cache-Rückgaben ab.
- Modellgewichte, Bildvorverarbeitung, Vergleichsrechnung, Ergebnisdarstellung, Layout und Adminzugang wurden nicht geändert. Das Eingabefoto bleibt im Browser. Die optionale Cache-Rückgabe enthält ausschließlich Merkmale öffentlicher Referenzen.

## Grenzen der Messung

Die Zahlen gelten für den getesteten Rechner mit 24 gemeldeten logischen Prozessoren und den aktuellen öffentlichen Referenzen. Der einmalige Download des Modells hängt von der Internetverbindung ab. Neue Arten, ein anderer Modelltyp, ein größerer Referenzumfang oder geänderte beziehungsweise eigene Referenzbilder können eine erneute Vorbereitung benötigen. Während dieser erstmaligen Vorbereitung sind wenige Sekunden nicht garantiert. Anschließende Analysen verwenden vorbereitete, an die konkreten Bilddateien gebundene Merkmale.

Dies ist ein Geschwindigkeitstest mit bereits vorhandenen öffentlichen Referenzfotos, kein unabhängiger Testdatensatz zur Erkennungsgenauigkeit. Es wurde weder eine Trainings-/Testtrennung behauptet noch eine neue Trefferquote berechnet. Die frühere Angabe „31 von 100“ wird durch diesen Test nicht belegt.

## Prüfbilder und Nachvollziehbarkeit

Das erste Foto stammt aus dem vorhandenen öffentlichen Referenzbestand: [Common Frog (1).jpg auf Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Common_Frog_(1).jpg), CC BY 3.0. Es wurde bewusst für einen reproduzierbaren Geschwindigkeitsvergleich verwendet; seine Aufnahme in die Referenzen erlaubt keine unabhängige Genauigkeitsbewertung.

- Weiteres Prüffoto Bufo bufo: [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Bufo_bufo_(41731895194).jpg), CC BY 2.0, Urheberangabe: Donald Hobern  from Copenhagen, Denmark. SHA-256 `776eae4799d9db39f0e3699d4447b4353ea28712760e40cd195baccdd7d8b741`.
- Weiteres Prüffoto Hyla arborea: [iNaturalist](https://www.inaturalist.org/photos/728952892), CC BY 4.0, Urheberangabe: (c) Paul Dufour, some rights reserved (CC BY). SHA-256 `78d9a9f44fc5c9233072fdd5e9d8c539d252fe1ce9fbff293c3c822218eed88c`.

SHA-256 des ersten Prüffotos: `2ed82ad695fbe02c544b19451b120f24d5a1b916d70a8f4a71114557dcad2f27`.

Die lokalen Messprotokolle `baseline.json`, `optimized-clean.json`, `three-photos.json` und der echte Browserablauf `benchmark.cjs` liegen im Arbeitsordner `update_2026-10-21/performance`. Testprofile, Zugangstickets, Nutzerdaten und Bildarchive werden nicht veröffentlicht. Die lokale Bereitstellung verwendet `ribby-toolbox:performance-20261021` und `naturgutachter-ribby-admin-gateway:20261021-perf` mit den bestehenden Datenvolumes.

## Funktions- und Zugriffstests

- 58 erfolgreiche lokale Python-Prüfungen; der zusätzlich lokal übersprungene `requests`-Integrationstest sowie der Streaming-Test bestanden im tatsächlichen Gateway.
- Python-Prüfungen für Referenzen, Prüfsummen, Lizenzen, Cache, API-Berechtigungen und Toolbox-Anmeldung.
- JavaScript-Prüfungen für Syntax, Ranking, Kalibrierungsrechnung, Referenzcache, parallele Abfragen, Abbruch, Abmeldung und erneuten Versuch nach Cache-Fehlern.
- Streaming-Test mit der tatsächlichen `requests`-Bibliothek im Toolbox-Gateway: identische Daten, begrenzte Teilstücke, korrekte Content-Length, keine unbeabsichtigte Chunked-Übertragung.

Die normalen Python-Prüfungen benötigen nur die Standardbibliothek. Der zusätzliche `requests`-Integrationstest läuft im optionalen Toolbox-Laufzeitsystem; ohne diese Bibliothek wird ausschließlich dieser Test übersprungen.
