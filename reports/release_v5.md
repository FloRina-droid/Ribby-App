# Ribby – Veröffentlichung des integrierten Bildmodus V5

Die reguläre Ribby-App enthält Audio und Bildanalyse mit Kamera/Upload, denselben
Trefferkarten, Artbestätigung, Fundort/GPS, Verlauf und Karte. Das akzeptierte
statische HTML und CSS sind unverändert. Die Kalibrierung der Prozentanzeige und
ihre gemessenen Grenzen stehen im [Prozentbericht V4](image_calibration_v4.md).
V5 ändert weder die Bildmodelle noch die Rangfolge oder deren Trefferquote.

## Zuverlässiger Import und GitHub-Verteilung

Der öffentliche Bestand ist bytegleich erhalten: 896 CC0-/CC-BY-Fotos aus 14 Arten
und 1792 vorberechnete Vektoren für BioCLIP und DINOv2. Das bisherige ZIP mit
143.266.637 Bytes wird als drei Dateien von jeweils höchstens 48 MiB verteilt.
GitHub blockiert reguläre Git-Dateien über 100 MiB; die Teile liegen auch unter
der 50-MiB-Warnschwelle ([GitHub-Dokumentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)).

Das Manifest enthält Größe und SHA-256 jedes Teils sowie des Gesamtarchivs. Vor
dem Import werden alle Teile vollständig geprüft. Fehlende, zusätzliche,
beschädigte, gekürzte oder falsch angeordnete Teile erzeugen eine Fehlermeldung,
bevor Dateien übernommen werden. Der Server liest das ZIP direkt über die Teile;
ein zusätzlicher Gesamtarchiv-Export auf Festplatte oder in den Arbeitsspeicher
entfällt. Ein vollständiges altes ZIP bleibt kompatibel.

Einzelne Referenzdateien werden erst nach vollständigem Schreiben atomar an ihren
Zielort verschoben. Bei Schreibfehlern wird die temporäre Datei aufgeräumt. Das
verhindert, dass ein späterer Start eine unvollständige Datei als vorhanden
überspringt. Bereits vorhandene Referenzen und private Daten werden wie bisher
beibehalten.

## Nachweise

- 40/40 Backendtests, darunter acht neue Prüfungen für Teilgrenzen,
  Vollständigkeit, Beschädigung, Prüflisten, Prüfsummen und atomare Schreibfehler.
- Regulärer `ribby_server.py` startet in einem neuen Datenordner ausschließlich
  mit den Teilen und ihrer Prüfliste. HTML und `/api/ping` sind erreichbar.
- Sämtliche installierten Seed-Dateien stimmen byteweise mit dem vollständigen
  Archiv überein; alle 896 Fotos und 1792 Vektoren sind vorhanden. Alle Vektoren
  bestehen weiterhin die Modell-, Dimensions-, Norm- und Foto-Hash-Prüfungen.
- Erneuter Import kopiert keine vorhandenen Dateien.
- Die unveränderten Frontend-Prüfungen und der Abgleich der 136 echten
  Modellabläufe mit gespeicherten Ergebnissen/GPS bleiben Bestandteil des
  [Systemberichts](system_test_report.md).

Maschinenlesbare Nachweise: `release_seed_v5.json`, `system_core_tests.json` und
`system_calibration_consistency.json`. Reproduktion:

```powershell
python tests/run_core_tests.py
python tests/accuracy/verify_seed_release.py
node tests/test_image_logic.cjs
node tests/test_image_calibration.cjs
python tests/accuracy/verify_calibration_results.py
python tests/build_system_report.py
```

Der Seed-Gesamthash bleibt
`dcb3af82d9660e9aad43bf4bcc7061969464d1a086ad03b6c127d9230df67182`.
Das Docker-Image übernimmt ebenfalls alle drei Teile und die Prüfliste. Die
bisherigen Audio-Seed-Teile aus GitHub gehören weiterhin zur Installation.
Kalibrierungswerte bleiben Schätzungen für den geprüften 14-Arten-Bestand, keine
Garantie für beliebige Fotos. Kamera-/Smartphoneprüfungen verwenden virtuelle
Chromium-Testgeräte; eine Prüfung auf echter Mobilhardware steht weiterhin aus.
