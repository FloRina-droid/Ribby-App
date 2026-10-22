# Echte Modelle und Genauigkeitsprüfung V3

Die App benötigt keine zusätzlichen Python-Pakete. Die optionalen Prüfwerkzeuge
benötigen Node.js, Playwright und Chromium/Edge. Nur für die erneute Auswahl und
Anpassung der Referenzmetrik wird zusätzlich NumPy benötigt. Alle Befehle im
Ribby-Projektordner ausführen. `RIBBY_BROWSER_PATH` kann den Browserpfad ändern.

## Eingefrorenen Vergleich wiederholen

1. `python tests/accuracy/prepare_v3.py` stellt die 896 Referenzen aus dem
   mitgelieferten Seed sowie die 112 unabhängigen Prüffotos her. Es werden die
   eingefrorenen Originalquellen samt Einzellizenzen verwendet.
2. In einem Terminal den lokalen Prüfserver starten:

```powershell
$env:RIBBY_ACCURACY_WORKSPACE='accuracy_work/v3'
$env:RIBBY_ACCURACY_DATA_DIR='accuracy_work/v3/references'
python tests/accuracy/serve.py
```

3. In einem zweiten Terminal die 112 Fotos mit beiden echten Modellen auswerten:

```powershell
$env:RIBBY_V3_INPUT='holdout'
node tests/accuracy/collect_v3.cjs
node tests/accuracy/evaluate_v3.cjs
python tests/accuracy/build_v3_report.py
```

Die Bilddateien werden wie in der App ausgerichtet, auf maximal 1600 Pixel
begrenzt und in JPEG mit Qualität 0,9 normalisiert. Die Ergebnisse liegen unter
`reports/image_accuracy_v3.json` und `reports/image_accuracy_v3.md`. Verglichen
werden immer dieselben Eingaben vor und nach der Änderung. Der frühere
28-Bilder-Satz ist separat als Regression dokumentiert; seine Vektoren liegen
für den Paarvergleich in `reports/accuracy_regression_vectors_v2.json`.

Die zusätzliche vollständige Browserprüfung der regulären Oberfläche ist in
[../SYSTEM_TESTS.md](../SYSTEM_TESTS.md) beschrieben. Sie prüft beide Modelle
mit allen 112 neuen Fotos, Bestätigung, GPS/Fundort und gespeicherten Resultaten.

## Referenzmetrik reproduzieren oder neue Daten sammeln

`select_v3.py` liest ausschließlich Referenzvektoren. Die fünf Validierungsfalten
trennen zusammengehörige Fotografennamen und numerische iNaturalist-IDs. Die
Prüffotos dürfen nicht zur Parameterwahl verwendet werden. Mit NumPy:

```powershell
python tests/accuracy/select_v3.py
python tests/accuracy/fit_v3.py --embed
```

`--embed` aktualisiert die eingefrorene Metrik in der vorhandenen HTML-Datei,
bei unverändertem Seitenaufbau. Danach Codeprüfungen und Browserprüfungen erneut
laufen lassen; bisherige Berichte gehören noch zum alten Code-Hash.

Für eine neue, explorative Beschaffung existiert `expand_dataset.py`.
Es fordert ausschließlich Research-Grade-Beobachtungen mit exaktem Taxon und
CC0-/CC-BY-Fotolizenz an, hält die alten und neuen Prüffotografen aus den
Referenzen heraus und verwendet höchstens drei neue Bilder eines Fotografen
je Art. `collect_v3.cjs` berechnet fehlende Referenzmerkmale, wenn
`RIBBY_V3_INPUT='references'` gesetzt ist. Bereits vorhandene geprüfte Vektoren
werden wiederverwendet. `package_corpus_v3.py` prüft die Quellen, Trennung,
Bild-Hashes und Merkmale vor dem Erstellen des Seeds.

Ein erneuter Live-Abruf liefert eventuell andere Bilder und ist keine exakte
Reproduktion des dokumentierten Snapshots. Für einen weiteren Tuningdurchlauf
ist ein neuer, zuvor nicht ausgewerteter Prüfsatz nötig. Die anfänglichen
Werkzeuge `select_model.cjs` und `evaluate_test.cjs` gehören zur historischen V2.

Dies ist keine Feldvalidierung. Die Labels stammen aus den Quellen, nicht aus
einer erneuten Bestimmung durch Amphibienexperten. Aliasnamen von Fotografen und
Überschneidungen mit dem ursprünglichen Vortraining sind nicht vollständig
bekannt. Foto-Lizenzen und Urheber bleiben in den Manifesten erhalten.
