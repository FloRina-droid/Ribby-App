# Ribby – geprüfte Prozentanzeige und weitere Tests V4

Die Ergebniswerte werden für den geprüften Referenzbestand als geschätzte Trefferchance ausgewiesen. Bildähnlichkeiten bleiben zusätzlich gespeichert. Die Artvorschläge und ihre Rangfolge werden durch diese Kalibrierung nicht verändert.

## Unabhängiger Test der Zahlen

68 neue iNaturalist-Fotos aus 14 Arten; fünf je Art, beim Kleinen Wasserfrosch drei. Es waren nach Ausschluss der bisherigen Fotografen keine fünf unabhängigen neuen Fotografen für diese Art verfügbar. Kein Foto wurde wegen seines Erkennungsergebnisses aussortiert.
Foto-IDs, Beobachtungen, bekannte Fotografennamen und iNaturalist-IDs sowie identische Bilddateien sind von den 896 Referenzen und den 140 früheren Prüffotos getrennt. Alle 68 neuen Fotos haben verschiedene bekannte Fotografen. Die Fotolizenz wird einzeln auf CC0 oder CC BY geprüft. Die Labels stammen aus Research-Grade-Beobachtungen mit exaktem Taxon; eine fachliche Neubestimmung fand nicht statt.
Die folgenden Mittelwerte beziehen sich auf dieselben neuen Fotos bei der bisherigen Standardeinstellung mit 16 Referenzen. Die erste Zahl war eine Bildähnlichkeit und wurde bisher auch so bezeichnet. Die Gegenüberstellung prüft, wie gut eine Prozentanzeige zur tatsächlichen Ersttrefferhäufigkeit passt. Sie ist kein Nachweis, dass die alte Ähnlichkeitsrechnung mathematisch falsch war.

| Modell | Bisheriger Anzeigewert, Mittel | Neue geschätzte Trefferchance, Mittel | Tatsächliche Ersttreffer |
|---|---:|---:|---:|
| bioclip | 86.4 % | 66.9 % | 45/68 (66.2 %) |
| dinov2 | 84.9 % | 58.1 % | 39/68 (57.4 %) |

Die Nähe der Mittelwerte ist keine Garantie für die Richtigkeit eines einzelnen Prozentwerts. Auch gleichbleibende Werte könnten im Mittel passen. Deshalb werden zusätzlich der Brier-Fehler und die Abweichung innerhalb von Wahrscheinlichkeitsgruppen gemessen.

| Modell | Brier vorher, wenn Ähnlichkeit als Chance gelesen wird | Brier kalibriert | 95-%-Intervall der gepaarten Differenz | ECE mit 10 Gruppen vorher → jetzt |
|---|---:|---:|---:|---:|
| bioclip | 0.235 | 0.145 | -0.153 bis -0.031 | 20.3 % → 13.2 % |
| dinov2 | 0.301 | 0.197 | -0.175 bis -0.035 | 27.6 % → 9.6 % |

Beim Brier-Fehler ist kleiner besser, null entspricht perfekten Angaben. Das Intervall beruht auf 2000 gepaarten Bootstrap-Stichproben. ECE mit nur 68 Bildern ist von der Gruppeneinteilung abhängig und bleibt unsicher. Die Verbesserung ist keine Aussage über beliebige Fotos oder jede einzelne Art.

## Kalibrierung ohne Verwendung der neuen Prüfergebnisse

Das Verfahren ist eine positive Temperaturskalierung über die Ähnlichkeitsscores aller 14 Arten. Alle Klassenwahrscheinlichkeiten werden vor dem Kürzen auf fünf Karten gemeinsam auf Summe eins normalisiert. Eine positive Temperatur ändert keine Rangfolge. Grundlage: [Guo et al., On Calibration of Modern Neural Networks, ICML 2017](https://proceedings.mlr.press/v70/guo17a.html).
Die Temperatur wird ausschließlich aus nach Fotografen getrennten Vorhersagen der 896 Referenzfotos gelernt. Für die interne Prüfung werden fünf äußere und drei innere Falten verwendet: Die inneren Falten lernen die Temperatur, die äußere Falte bewertet sie. Der vorhandene V3-Bildvergleich mit Ridge-Parameter α=1 wird dabei festgehalten. Die schon früher getroffene V3-Modellwahl ist kein Bestandteil dieser verschachtelten Kalibrierungsprüfung.
Die neuen 68 Prüffotos und die früheren 112/28 Prüffotos werden nicht zum Anpassen der Temperatur verwendet. Nach dem Öffnen ihrer Ergebnisse wurden Temperaturen und Referenzlimits nicht nachjustiert.

| Modell / Referenzen | Interner Brier: Ähnlichkeit als Chance → kalibriert | Brier auf den neuen Fotos vorher → jetzt |
|---|---:|---:|
| bioclip / 8 | 0.234 → 0.165 | 0.260 → 0.138 |
| bioclip / 16 | 0.230 → 0.162 | 0.235 → 0.145 |
| bioclip / 32 | 0.233 → 0.161 | 0.206 → 0.153 |
| dinov2 / 8 | 0.278 → 0.186 | 0.292 → 0.209 |
| dinov2 / 16 | 0.267 → 0.185 | 0.301 → 0.197 |
| dinov2 / 32 | 0.270 → 0.183 | 0.280 → 0.202 |

Die 32-Referenz-Konfiguration von BioCLIP hat im neuen Satz einen kleineren Brier-Punktwert; ihr Bootstrap-Intervall umfasst jedoch auch null. Es wird daher kein gesicherter Vorteil jeder Konfiguration behauptet.
Die separate Wiederholung auf den früheren 112 Prüffotos verändert bei 16 Referenzen keine Artvorhersage: BioCLIP bleibt bei 62/112 Ersttreffern, DINOv2 bei 64/112. Die vollständigen Zahlen für alle Referenzlimits stehen in `calibration_evaluation_v4.json`.

## Geltungsbereich und Darstellung

Die Trefferchance gilt unter der Voraussetzung, dass das Foto eine der 14 verglichenen Arten zeigt. Sie ist keine geprüfte Erkennung unbekannter Arten und keine Garantie im Feldeinsatz. Andere Arten, Regionen, Bildqualitäten, Fotografen-Aliasnamen und unbekannte Vortrainingsdaten können abweichende Ergebnisse erzeugen.
Die App verwendet diese Anzeige nur bei passendem Bildmodell, vollständiger Artengruppe und exakt den geprüften öffentlichen Referenz-IDs für 8, 16 oder 32 Bilder je Art. Bei privaten, fehlenden, veränderten oder unbekannten Referenzen/Arten zeigt sie ausdrücklich Bildähnlichkeit. Ein späterer Quellen-Refresh kann diesen Rückfall auslösen. Neue Referenzkonfigurationen müssen neu kalibriert werden.
Die bisherige Oberfläche, Farben, Bedienelemente und Styles bleiben erhalten. Prozentwert, Balken und Beschriftung zeigen die jeweilige Datenbedeutung. Geschätzte Werte über 99 % erscheinen als „>99 %“, unter 1 % als „<1 %“; daraus wird keine gerundete 100-%-Garantie.
Bei manueller Artwahl wird der Prozentwert der gewählten Art verwendet. Wenn dafür kein gespeicherter Modellwert vorhanden ist, bleibt die Zahl leer. Ein fremder Vorschlagswert wird nicht übernommen. Alte Verlaufseinträge werden nicht nachträglich als kalibrierte Werte ausgegeben. CSV enthält Score-Typ und Kalibrierungs-ID; der Audio-Batch-Export hat wieder passend ausgerichtete Spalten.
Referenzfoto, Quelle, Lizenz und Urheber bleiben unverändert. Private Nutzerfotos wurden nicht für die Kalibrierung genutzt.

## Technische Nachweise

- 136/136 neue vollständige App-Abläufe mit beiden echten Modellen; alle 68 Fotos, Bestätigung, Fundort/GPS und Verlauf.
- 136/136 Vorschlagslisten, Wahrscheinlichkeiten und tatsächlich gespeicherte GPS-/Art-/Kalibrierungsdaten gegen die getrennte Auswertung geprüft; maximale Wahrscheinlichkeitsabweichung 6.7e-08.
- 7/7 gezielte Browserprüfungen für Prozentanzeige, manuelle Korrektur, Bestandswechsel und alte Ergebnisse.
- 40/40 Backendtests; JavaScript-Syntax, Ranking, Wahrscheinlichkeitsnormierung, Rückfälle, Zahlenformat und CSV geprüft.
- 18/18 Fehlerszenarien, 13/13 Ablaufprüfungen einschließlich 24 Wiederholungsanalysen; private Referenzen für 14 Arten sowie 4/4 Audio-/GPS-/Artanlage-/Sprachregressionen bestanden.
- Statisches HTML und CSS sind vollständig gleich geblieben (`design_preservation_v4.json`). Kamera/Smartphone-Prüfungen verwenden Chromium-Testgeräte, keine echte Android-/iPhone-Hardware.
Reproduktion: [Systemtests](../tests/SYSTEM_TESTS.md) und [Kalibrierungsprüfung](../tests/accuracy/CALIBRATION.md). Die Prüfungen beziehen sich auf die unten genannten Dateiprüfsummen.

- App-SHA-256: `cfc98f65bed1396e27d55c097d6182278224bec2734f777075a213e8fbe82f68`
- Kalibrierungs-SHA-256: `4c1a7a21c2b8729963b3e744fda6fce9d2bc2bedc4f372e449206fdd64ccc49d`
- Kalibrierungs-ID: `temperature-v1:2959f9ace4fd539902704d04bb7e07f8de675ed62be4201ff5516bf827d91f3a`
