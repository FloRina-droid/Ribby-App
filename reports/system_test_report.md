# Ribby – Systemprüfung des aktuellen Bildmodus V4

Alle definierten technischen Prüfungen dieses Stands bestehen. Das ist keine 100-prozentige Erkennungsgenauigkeit. Details zur Bedeutung und Qualität der Zahlen: [Prozentbericht V4](image_calibration_v4.md).

| Prüfung | Ergebnis |
|---|---:|
| Backend | 43/43 |
| Echte Bildmodelle mit 68 neuen Fotos, allen 14 Arten, Bestätigung und GPS | 136/136 |
| Persistierte Prognosen, Kalibrierung und Georeferenz | 136/136 |
| Gespeicherte Ergebnisse je Art wieder geöffnet | 14/14 |
| Prozentanzeige und Artkorrektur | 7/7 |
| Fehlerfälle | 18/18 |
| Sitzungen, Speicherrennen und Verlauf | 13/13 |
| Private Referenzen speichern/nutzen/löschen | 14/14 Arten |
| Audio-/GPS-/Artanlage-/Sprachregressionen | 4/4 |
| JavaScript-Ranking, Kalibrierung, Format und CSV | bestanden |
| HTML-Aufbau und Styles | unverändert |

Der öffentliche Referenzbestand mit 896 Fotos und 1792 Vektoren wurde gegenüber V3 nicht verändert. Seine Browser-/Vektorprüfung ist im historischen [V3-Systembericht](v3/system_test_report.md) und `system_reference_pack.json` dokumentiert. Der neue Prüfsatz ist nach Fotografen, Beobachtung, Foto-ID und identischen Bilddateien von allen bisherigen Daten getrennt.

## Erkennung auf den neuen Fotos

| Modell | Erster Treffer | Richtige Art unter Top 3 |
|---|---:|---:|
| bioclip | 45/68 | 60/68 |
| dinov2 | 39/68 | 56/68 |

Die Kalibrierung ändert nur die Interpretation der Prozentwerte, keine Artvorhersage. Die neuen Fotos sind ein anderer Testsatz als die 112 Fotos aus V3; die Erfolgsquoten dürfen nicht als Vorher/Nachher-Verbesserung der Erkennung verglichen werden. Kamera und Smartphone-Layout wurden nur im Chromium-Testgerät geprüft. Der Audio-Test nutzt ein synthetisches Signal und misst keine akustische Artgenauigkeit.

## Prüfsummen

- `ribby_app.html`: `4073c8f916e0f068800942ae0c470dc72e2862e14c997be6c9b3588ce82f2339`
- `ribby_server.py`: `2373dcdb1f0f599daa8500aa46a5c96a6e1678218cc03ca8b1ffb4e4df78cae4`
- `ribby_images.py`: `c660e04058a0403890a408d5f59e7eca64828897eebe8d1719dbec8606032d1a`
