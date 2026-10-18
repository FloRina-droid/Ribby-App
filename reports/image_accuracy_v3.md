# Ribby – mehr Bilddaten und Genauigkeitsprüfung V3

Historischer Bericht zur Verfahrenswahl und zum damaligen App-Stand. Der aktuelle
Stand ergänzt eine Kalibrierung der Prozentanzeige, ohne die hier geprüfte
Rangfolge zu verändern: [Prozentbericht V4](image_calibration_v4.md).

## Bestand und Trennung

896 unterschiedliche CC0-/CC-BY-Referenzfotos, 64 für jede der 14 ursprünglichen Arten; zuvor 447. Quellen: 816 iNaturalist-Fotos und 80 Wikimedia-Commons-Fotos. 1792 geprüfte Merkmalsvektoren für die beiden Bildmodelle werden mitgeliefert.
112 zusätzliche Prüffotos, acht je Art, wurden vor der Verfahrenswahl eingefroren. Foto-IDs, Beobachtungen, normalisierte Fotografennamen und bekannte iNaturalist-Urheber-IDs sind von den Referenzen getrennt. Auch identische Bilddateien wurden über SHA-256 ausgeschlossen. Die 28 früheren Prüffotos und deren bekannte Urheber bleiben ebenfalls außerhalb des Referenzbestands.
Der neue Testsatz enthält auch schwierige Motive, kleine/verdeckte Tiere, Larven und tote Tiere. Diese Fälle werden nicht nach dem Erkennungsergebnis aussortiert. Die Sichtprüfung prüft Bildinhalt und Lesbarkeit, ersetzt aber keine fachliche Neubestimmung der Artenlabels.

## Auswahl vor dem Prüfsatz

Fünffache Kreuzvalidierung über die 896 Referenzfotos. Verbundene Fotografennamen und numerische iNaturalist-IDs liegen jeweils vollständig in derselben Falte. Verglichen werden feste Referenzlimits und Verfahren; zusätzliche explorative Verfahren sind im JSON mit aufgeführt. Die Wahl für den App-Betrieb bleibt bei den bestehenden 8/16/32-Bedienelementen und einem Vergleich der ausgewählten Referenzfotos.
Gewählt wurde BioCLIP mit 16 Referenzen und einer regularisierten linearen Projektion (Ridge, α=1) vor dem Kosinusvergleich der Klassenprototypen. In der gruppierten Validierung: 615/896 (68.6 %) Ersttreffer und 819/896 (91.4 %) Top-3-Treffer. Das ist ein Wert zur Verfahrenswahl, keine unabhängige Erfolgsquote.
Die Projektion nutzt ausschließlich die Referenzdaten. Die BioCLIP-/DINOv2-Bildencoder bleiben unverändert. Die eingefrorenen Gewichte stehen in `image_metric.json` und in der HTML-Datei. Nach Öffnen der Prüfergebnisse wurden Verfahren, Referenzlimits und Gewichte nicht anhand dieser Labels nachjustiert. BioCLIP bleibt aufgrund der Validierung der Standard; der kleinere DINOv2 ist über die vorhandene Auswahl verfügbar.

## Neue, unabhängige Fotos: gepaarter Vergleich

Alle Zahlen vor und nach der Änderung beziehen sich auf dieselben 112 Bilder mit derselben JPEG-Normalisierung der App. Die Rangfolge wird vor der manuellen Artkorrektur gemessen.

| Modell | Ersttreffer vorher | Ersttreffer jetzt | Top 3 vorher | Top 3 jetzt |
|---|---:|---:|---:|---:|
| bioclip | 59/112 (52.7 %) | 62/112 (55.4 %) | 98/112 (87.5 %) | 99/112 (88.4 %) |
| dinov2 | 46/112 (41.1 %) | 64/112 (57.1 %) | 73/112 (65.2 %) | 99/112 (88.4 %) |

Allein das Vergrößern des Vorrats bei weiterhin 16 ausgewählten Vergleichsbildern ändert hier die Rangfolge nicht: Die ausgewählten ersten Referenzen bleiben erhalten. Der Zugewinn entsteht durch die aus dem größeren Bestand gelernte Projektion. Weitere Referenzen sind bei 32 Bildern in der vorhandenen Einstellung nutzbar.
Die Verbesserung des Standards BioCLIP ist klein: acht bisher falsche Bilder werden richtig, fünf bisher richtige werden falsch. Sie belegt keinen statistisch gesicherten Zuwachs im Feldeinsatz.

| Modell | 95-%-Wilson-Intervall des neuen Ersttrefferanteils | Verbessert / verschlechtert | Gepaarter exakter p-Wert |
|---|---:|---:|---:|
| bioclip | 46.1–64.2 % | 8 / 5 | 0.5811 |
| dinov2 | 47.9–65.9 % | 27 / 9 | 0.0039 |

Die p-Werte sind explorativ und nicht für mehrere Vergleiche korrigiert. Acht Fotos je Art bleiben eine kleine Stichprobe. Ein unbekannter Anteil der Fotos kann in den ursprünglichen Vortrainingsdaten der Basismodelle enthalten sein.

## Ergebnis je Art auf den neuen Fotos

| Art | BioCLIP vorher → jetzt | BioCLIP Top 3 jetzt | DINOv2 vorher → jetzt | DINOv2 Top 3 jetzt |
|---|---:|---:|---:|---:|
| Grasfrosch (*Rana temporaria*) | 0 → 1 / 8 | 7/8 | 3 → 1 / 8 | 5/8 |
| Moorfrosch (*Rana arvalis*) | 5 → 4 / 8 | 8/8 | 3 → 6 / 8 | 8/8 |
| Springfrosch (*Rana dalmatina*) | 4 → 6 / 8 | 7/8 | 5 → 5 / 8 | 7/8 |
| Erdkröte (*Bufo bufo*) | 6 → 8 / 8 | 8/8 | 3 → 4 / 8 | 7/8 |
| Wechselkröte (*Bufotes viridis*) | 7 → 7 / 8 | 8/8 | 7 → 6 / 8 | 8/8 |
| Kreuzkröte (*Epidalea calamita*) | 6 → 6 / 8 | 7/8 | 4 → 4 / 8 | 7/8 |
| Knoblauchkröte (*Pelobates fuscus*) | 4 → 4 / 8 | 7/8 | 5 → 7 / 8 | 7/8 |
| Seefrosch (*Pelophylax ridibundus*) | 4 → 3 / 8 | 6/8 | 0 → 1 / 8 | 5/8 |
| Kleiner Wasserfrosch (*Pelophylax lessonae*) | 2 → 1 / 8 | 5/8 | 1 → 3 / 8 | 6/8 |
| Teichfrosch (*Pelophylax esculentus*) | 1 → 4 / 8 | 8/8 | 2 → 3 / 8 | 8/8 |
| Laubfrosch (*Hyla arborea*) | 8 → 8 / 8 | 8/8 | 7 → 8 / 8 | 8/8 |
| Rotbauchunke (*Bombina bombina*) | 5 → 5 / 8 | 7/8 | 1 → 5 / 8 | 8/8 |
| Gelbbauchunke (*Bombina variegata*) | 4 → 2 / 8 | 5/8 | 2 → 6 / 8 | 7/8 |
| Geburtshelferkröte (*Alytes obstetricans*) | 3 → 3 / 8 | 8/8 | 3 → 5 / 8 | 8/8 |

## Frühere 28 Fotos als Regressionstest

Diese bereits früher ausgewerteten Bilder werden separat gezeigt und nicht als neuer unabhängiger Nachweis gezählt.

| Modell | Ersttreffer vorher → jetzt | Top 3 vorher → jetzt |
|---|---:|---:|
| bioclip | 15 → 20 / 28 | 24 → 23 / 28 |
| dinov2 | 14 → 20 / 28 | 24 → 25 / 28 |

Bei BioCLIP verbessert sich der Ersttreffer, die Top-3-Quote dieses alten Satzes sinkt jedoch um ein Foto. Es gibt somit keine Verbesserung für jedes Bild oder jede Kennzahl.

## Technische Prüfung und Nachweise

In der damaligen regulären App-Oberfläche bestehen 224/224 Abläufe mit beiden echten Modellen, allen 112 Fotos, Artbestätigung und Fundort/GPS. Gespeicherte Resultate für alle 14 Arten wurden erneut geöffnet. Vorschlagslisten und tatsächliche GPS-/Art-/Fundortdateien stimmen in allen 224 Fällen mit der separaten Prüfung überein. Der [V3-Systembericht](v3/system_test_report.md) dokumentiert die Abläufe getrennt von deren Erkennungsquote.
Zusätzlich: 32 Backendtests einschließlich Seed-Upgrade und begrenzter Vektorauslieferung; JavaScript-Prüfung einschließlich negativer Kosinuswerte und Rückfall für neue Arten; 18 Fehlerfälle; 13 Ablaufprüfungen mit 24 Wiederholungsanalysen; private Referenzen für 14 Arten. Kamera und Smartphone-Layout werden im Chromium-Testgerät geprüft, nicht auf echter iPhone-/Android-Hardware.
Aufbau, HTML-Elemente und Styles der freigegebenen Oberfläche bleiben unverändert. Der Vergleich entfernt nur die Scriptblöcke und prüft danach die vollständige Übereinstimmung. Beleg: `design_preservation_v3.json`.
Die Quellenlizenzen sind pro Foto eingefroren; Urheber, Lizenzlink und Originalquelle bleiben sichtbar. [iNaturalist-Bildrechte](https://help.inaturalist.org/en/support/solutions/articles/151000169918), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [CC0](https://creativecommons.org/publicdomain/zero/1.0/). Die Lizenz einer Beobachtung ersetzt keine Fotolizenz.
Die angepassten Kosinuswerte werden von −1…1 auf 0…1 abgebildet. Prozentwerte sind Bildähnlichkeiten, keine kalibrierten Bestimmungswahrscheinlichkeiten und nicht direkt mit älteren Versionswerten vergleichbar.
Reproduktion: [Genauigkeitsprüfung](../tests/accuracy/README.md) und [Systemtests](../tests/SYSTEM_TESTS.md). Rohdaten: `image_accuracy_v3.json`, `model_selection_v3.json`, `reference_manifest_v3.json`, `accuracy_holdout_v3.json`.

- App-SHA-256: `04d32c4191828ad19aae55c0a8174d48b3156739498eb129666b67bace135bfd`
- Metrik-SHA-256: `205d9f12587344242428ea393a4a0560a9993d99c44308ece82779a54724d784`
