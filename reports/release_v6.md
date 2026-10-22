# Ribby – Cache- und Datenintegrität V6

Stand: 21. Oktober 2026. Der bestehende Bildmodus und das akzeptierte Design bleiben erhalten. Diese Änderung verhindert veraltete Referenzmerkmale und unberechtigte kalibrierte Prozentanzeigen nach einem Fotoaustausch. Sie trainiert keine neuen Modelle und behauptet keinen Zuwachs der unveränderten Erkennungsquote.

## Behobene Fälle

Bisher verwendete IndexedDB nur Modellkennung und Bild-ID als Cache-Schlüssel. Ein anderes Foto unter derselben ID konnte deshalb mit alten Merkmalen verglichen werden. Cache-Einträge enthalten jetzt zusätzlich die SHA-256-Prüfsumme des verwendeten Fotos. Ohne passende Modell- und Foto-Bindung werden die Merkmale neu berechnet. Alte Einträge werden beim ersten Einsatz erneuert; passende Einträge benötigen weiterhin keine erneute Referenzinferenz.

Der Server liefert die aktuelle Foto-Prüfsumme auch dann, wenn kein gültiger vorberechneter Vektor vorhanden ist. Er entfernt eventuell mitgespeicherte Features aus Suchmetadaten vor der Validierung. Nur Vektoren mit passendem Modell, Foto-Hash, Dimension, numerischen Werten und Norm werden ergänzt. Boolean-Werte werden nicht als Modellzahlen akzeptiert.

Beim Laden eines Referenzfotos prüft der Browser die tatsächlichen Bytes gegen die angekündigte Prüfsumme. Ein während der Analyse ausgetauschtes Foto wird nicht mit einem alten Wert gemischt. Ungültige Modellantworten werden abgewiesen. Speicherfehler bleiben optional; Abbruch und Nutzerwechsel verhindern verspätete Cache-Schreibvorgänge.

Die kalibrierte Trefferchance erfordert neben den unveränderten Art-/Referenz-IDs auch genau die geprüften Foto-Prüfsummen aus `image_reference_integrity.json`. Andere Fotos unter gleichen IDs erhalten Bildähnlichkeit. Die Registry wurde aus allen 896 Seed-Fotos und beiden zugehörigen Vektorbeständen erzeugt; keine Temperatur wurde nachjustiert. Eine fehlerhafte Referenzprojektion erhält ebenfalls keine kalibrierte Anzeige.

## Prüfung

| Prüfung | Ergebnis |
|---|---:|
| Backend | 43/43 |
| Cache, echte App-Funktion mit kontrollierten Eingaben | 13/13 |
| Cache-/Prüfsummenfälle in der Oberfläche | 8/8 |
| Echte Modelle, 68 Fotos und alle 14 Arten | 136/136 |
| Gespeicherte Ergebnisse, Art, GPS und Referenz-Prüfsumme | 136/136 |
| Prozentanzeige | 7/7 |
| Fehlerfälle / Ablaufprüfungen | 18/18 / 13/13 |
| Private Referenzen speichern/nutzen/löschen | 14/14 Arten |
| Audio, GPS/Bildausschnitt, Artanlage und Sprache | 4/4 |
| Vorhersagen gegen veröffentlichten Commit `95100e1` | 1080/1080 unverändert |
| Seed | 3600 Dateien, 896 Fotos, 1792 nutzbare Vektoren |
| Statisches HTML und CSS | unverändert |

Die 1080 Paarvergleiche umfassen beide Modelle, 8/16/32 Referenzen und getrennt die bisherigen 68 bzw. 112 Prüffotos. Alle fünf gespeicherten Scores und ihre Rangfolge bleiben exakt gleich. Bei 16 Referenzen auf den 68 Fotos bleibt BioCLIP bei 45/68 Ersttreffern, DINOv2 bei 39/68. Diese Fotos wurden nicht erneut zum Lernen oder zur Parameterwahl verwendet.

Die 13 Cache-Funktionstests und acht gezielten UI-Fälle benutzen kontrollierte Vektoren und messen keine Erkennungsgenauigkeit. Die 136 Modellabläufe verwenden echte Inferenz. Kamera-/Mobilprüfungen bleiben virtuelle Chromium-Prüfungen. Die geschätzte Trefferchance gilt nur innerhalb der 14 bekannten Arten und des geprüften Bestands; es gibt keine 100-%-Garantie.

Reproduktion: `python tests/run_core_tests.py`, `node tests/test_image_cache.cjs`, `node tests/browser_image_cache.cjs` sowie die vollständigen [Systemtests](../tests/SYSTEM_TESTS.md). Danach `python tests/accuracy/verify_calibration_results.py` und `python tests/accuracy/build_v6_report.py`.

App-SHA-256: `4073c8f916e0f068800942ae0c470dc72e2862e14c997be6c9b3588ce82f2339`
Integritätskennung: `reference-integrity-v1:f9038851b13e4f2ed1c61b624745c68d7e0dbf92193ca38a566849f2702c2953`
