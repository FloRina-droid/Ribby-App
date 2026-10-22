# Ribby Bildmodus – Prüfbericht Version 2

Historischer Stand. Aktuelle Daten und Messungen: [Genauigkeitsbericht V3](image_accuracy_v3.md).

Stand: 18. Oktober 2026. Basis: GitHub `ef2b4ad` plus lokaler Bildmodus.

## Referenzbestand

447 unterschiedliche Fotos für 14 Amphibienarten, 31–32 Fotos je Art.
Quellen: Wikimedia Commons und iNaturalist. Jedes Foto hat einen eigenen
CC0-/CC-BY-Nachweis, Urheber und Originalquellen-Link. Bei iNaturalist gilt
Research-Grade und exakte Taxonzuordnung einschließlich expliziter Hybridmarker.
Commons erfordert eine passende Artkategorie. Eine fachliche Sichtprüfung aller
Bilder wurde nicht durchgeführt.

Es werden keine Modelle nachtrainiert. Die Daten dienen dem Vergleich von
Bildmerkmalen bei der Anwendung. Die Bildmodelle sind vortrainiert und bleiben
unverändert. Mögliches Überschneiden mit deren Vortrainingsdaten ist unbekannt.

## Auswahl des Verfahrens

Acht feste Kombinationen aus DINOv2/BioCLIP und nächster Referenz, gewichtetem
Top-2-Vergleich, Top-3-Mittelwert oder Klassenprototyp wurden auf den 447 Bildern
mit fünffacher Kreuzvalidierung verglichen. Der Faltenwechsel erfolgt anhand
normalisierter Fotografennamen; Bilder desselben bekannten Urhebers sind jeweils
gemeinsam auf der Referenz- oder Prüfseite. Je Klasse werden bis zu 16 nach
Urhebern verteilte Referenzen verwendet.

| Verfahren | Erster Treffer | Korrekte Art in Top 3 |
|---|---:|---:|
| DINOv2, gewichtete Top 2 | 214/447 (47,9 %) | 363/447 (81,2 %) |
| BioCLIP, Klassenprototyp | 288/447 (64,4 %) | 408/447 (91,3 %) |

Gewählt: BioCLIP, 16 Referenzen, normalisierter Klassenprototyp. Eine kleinere
Voruntersuchung mit 14 Validierungs- und 28 Prüfbildern war explorativ und wird
nicht als abschließender Nachweis verwendet.

## Zusätzliche Prüfung nach Verfahrenswahl

28 weitere iNaturalist-Fotos, je zwei pro Art, wurden getrennt beschafft.
Foto-IDs, Beobachtungs-IDs und normalisierte Urhebernamen kommen im gesamten
Referenzbestand nicht vor. Die Eingaben durchlaufen dieselbe Ausrichtung,
Verkleinerung und JPEG-Normalisierung wie in der App. Dieses Set wurde nicht für
die Wahl von Modell oder Vergleichsverfahren verwendet.

| Verfahren | Erster Treffer | Korrekte Art in Top 3 |
|---|---:|---:|
| DINOv2, vier Referenzen, gewichtete Top 2 | 15/28 (53,6 %) | 20/28 (71,4 %) |
| BioCLIP, 16 Referenzen, Klassenprototyp | 15/28 (53,6 %) | 24/28 (85,7 %) |

Die Vorschlagsliste wurde in dieser Stichprobe besser. Die Ersttrefferquote
blieb unverändert. Aus 28 Bildern lässt sich keine verlässliche Genauigkeit im
Feldeinsatz ableiten. Grundlage der Labels ist die Quellenzuordnung, keine
erneute Bestimmung durch einen unabhängigen Amphibienexperten. Besonders ähnliche
Arten können weiter verwechselt werden. Die App verlangt deshalb eine fachliche
Bestätigung und zeigt Bildähnlichkeiten statt Wahrscheinlichkeiten.

Maschinenlesbare Einzelergebnisse, die verglichenen Validierungsverfahren und
Testquellen stehen in [image_accuracy_v2.json](image_accuracy_v2.json).

## Funktionsprüfung

- 22 Python-Tests für Lizenzen, Taxonfilter, Hybridnamen, Bild-Deduplizierung,
  Cache-Migration, Quellen-Ausfall, Vektorprüfung, Zugriffsschutz, private Referenzen und Backup.
- JavaScript-Prüfung für Syntax, Rangfolge, Klassenprototypen, unterschiedliche
  Modell-Caches und Ausschnittkoordinaten einschließlich Bildrändern.
- Desktop-/Smartphone-Browser: Fotoauswahl, Kameraaufnahme, abgelehnte Freigabe,
  Motivausschnitt und Wiederherstellung, Abbruch, Bestätigung, Verlauf.
- Beide echten Modelle wurden auf allen 447 Referenzbildern ausgeführt.

Die Modellwahl, Eingaben und Resultate sollen bei späteren Änderungen erneut
geprüft werden. Ein größerer, von Experten bestimmter Feldtest ist für belastbare
Genauigkeitsangaben erforderlich.
