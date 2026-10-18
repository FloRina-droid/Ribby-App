# Vollständige Funktionsprüfung des Bildmodus

Die Anwendung bleibt eine Python-App ohne zusätzliche Laufzeitpakete. Für die
optionalen Browsertests werden Node.js, Playwright und ein installierter
Chromium/Edge-Browser benötigt. `RIBBY_BROWSER_PATH` kann einen anderen Browserpfad
angeben. Alle Befehle im Ribby-Projektordner ausführen.

1. `python tests/accuracy/prepare_test.py` lädt die 28 eingefrorenen Testfotos.
   `python tests/accuracy/prepare_v3.py` ergänzt den früheren Prüfsatz mit 112 Fotos
   und bereitet den eingefrorenen Bestand mit 896 Referenzen vor.
   `python tests/accuracy/prepare_calibration.py` lädt die 68 zusätzlichen
   eingefrorenen V4-Prüffotos. Für Prozenttests und die getrennte Auswertung die
   echten Merkmalsvektoren nach [CALIBRATION.md](accuracy/CALIBRATION.md) vorbereiten.
   Vorhandene Fotos unter `accuracy_test_data/` werden ebenfalls erkannt.
   Ein anderer Fotoordner ist über `RIBBY_TEST_PHOTOS` wählbar (mit `image_refs/`).
2. `python tests/system_server.py` startet einen isolierten Prüfserver auf
   `http://127.0.0.1:7436`. Er verwendet `dev/system_data/`, Testkonten und den
   mitgelieferten Referenz-Seed. Die echte Ribby-Datenbank wird nicht geöffnet.
   Die Quellenmetadaten werden für diesen Test eingefroren; die Produktion
   aktualisiert weiterhin ihren Cache nach dem normalen Zeitplan.
3. In einem zweiten Terminal ausführen:

```powershell
python tests/run_core_tests.py
python tests/accuracy/verify_seed_release.py
node tests/test_image_logic.cjs
node tests/test_image_calibration.cjs
node tests/browser_reference_pack.cjs
node tests/browser_all_species.cjs
node tests/browser_percentages.cjs
node tests/browser_faults.cjs
node tests/browser_lifecycle.cjs
node tests/browser_private_species.cjs
node tests/browser_regressions.cjs
python tests/build_system_report.py
```

`browser_all_species.cjs` verwendet die echten Modelle BioCLIP und DINOv2
mit je 68 neuen unabhängigen Fotos (136 vollständige Abläufe). Fünf Fotos je Art,
beim Kleinen Wasserfrosch drei: Für diese Art waren keine fünf zusätzlichen,
von allen früheren Daten getrennten Fotografen verfügbar. Dabei werden alle 14 Arten mit 16
Referenzen verglichen. Das Skript trennt technische Abläufe von den gemessenen
ersten Treffern und Top-3-Vorschlägen. Die manuelle Bestätigung wird auf die
bekannte Testart korrigiert; das zählt ausdrücklich nicht als Erkennungstreffer.

`browser_percentages.cjs` prüft sieben Fälle für die Anzeige und Speicherung von
Wahrscheinlichkeiten, manuelle Artwahl, alte Verlaufseinträge und geänderte
Referenzen. Es verwendet einen eingefrorenen echten Merkmalsvektor anstelle neuer
Inferenz; es misst keine Erkennungsgenauigkeit. `test_image_calibration.cjs`
prüft zusätzlich Normierung vor dem Kürzen auf fünf Vorschläge, unveränderte
Rangfolgen, Geltungsbereich, Zahlenformat, Artkorrektur und CSV-Spalten.

Die zusammengefassten V4-Berichte benötigen zusätzlich die unabhängige
Kalibrierungsauswertung und deren Abgleich mit den App-Ergebnissen. Die vollständige
Reihenfolge steht in [CALIBRATION.md](accuracy/CALIBRATION.md).

Die privaten Referenztests benutzen einen separaten normalen Nutzer. Sie prüfen
Speichern/Nutzen/Löschen für jede Art, Dubletten, Nutzertrennung und Backup.
Der Test der Nutzung privater Referenzen ersetzt die Merkmalsextraktion durch
einen deterministischen Vektor und misst damit keine Erkennungsgenauigkeit.

`browser_regressions.cjs` prüft GPS-Erhalt beim Zuschneiden und Wiederherstellen,
die echte Audio-Engine mit einem synthetischen WAV-Signal sowie das manuelle
Ergänzen einer neuen Art durch einen Administrator. Die zusätzliche Testart wird
anschließend wieder gelöscht. Diese Prüfung nach dem Artentest ausführen.

Die Fehlertests isolieren insbesondere Abbruch, Abmeldung, Kamera-Rennen,
Bildformat-/Größenprüfung, falsche Artwahl, Cache- und Serverausfälle. Ihre
Merkmalsextraktion ist ebenfalls deterministisch; die echten Modelle werden
im vollständigen Artentest geprüft.

`browser_lifecycle.cjs` prüft Browser-Neuladen, Einwilligungsdialog, Widerruf der
Serversitzung beim Abmelden, verzögerte Speicher-/Verlaufsantworten und Nutzerwechsel.
Ein zusätzlicher Lauf mit 24 Analysen wechselt zwischen 8, 16 und 32 Referenzen
je Art und prüft das Freigeben temporärer Bild-URLs beim Abmelden. Die Bildvektoren
dieses Wiederholungstests sind deterministisch; er misst keine Erkennungsquote.

Ergebnisse stehen unter `reports/system_*.json`, der zusammengefasste Bericht
unter `reports/system_test_report.md`. Kameraaufnahmen benutzen das virtuelle
Testgerät des Browsers. Ein Smartphone-Viewport prüft das Layout; das ersetzt
keinen Test auf echter iPhone-/Android-Hardware. Ein bestandener technischer
Testsatz ist keine Garantie für fehlerfreie Artbestimmung bei beliebigen Fotos.

Der Prüfserver enthält ausschließlich Testkonten mit einem festgelegten
Testpasswort und bindet an localhost. Er gehört nicht in eine Produktivumgebung.

`verify_seed_release.py` startet zusätzlich den unveränderten regulären Server in
einem temporären Ordner mit ausschließlich den drei Seed-Teilen und ihrer
Prüfliste. Es prüft sämtliche installierten Dateien, alle 1792 nutzbaren Vektoren,
das erneute Starten des Imports sowie die ausgelieferte HTML-Datei. Die 8 neuen
Backendtests decken Teilgrenzen, fehlende/beschädigte/zusätzliche Dateien, falsche
Prüfsummen, ungültige Prüflisten und unterbrochene atomare Schreibvorgänge ab.
