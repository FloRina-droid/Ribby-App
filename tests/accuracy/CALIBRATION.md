# Prozentanzeige reproduzierbar prüfen

Die normale App benötigt nur die Python-Standardbibliothek. Für die Browserprüfung
werden zusätzlich Node.js, Playwright und Edge/Chromium benötigt. Ein anderer
Browserpfad kann mit `RIBBY_BROWSER_PATH` gesetzt werden. Alle Befehle im
Projektordner ausführen. Modellabrufe und der Fotoabruf benötigen Internet.

## Eingefrorene Daten und echte Merkmalsvektoren

```powershell
python tests/accuracy/prepare_test.py
python tests/accuracy/prepare_v3.py
python tests/accuracy/prepare_calibration.py
python tests/accuracy/audit_calibration_probe.py
```

Dies bereitet die 896 Referenzen, die früheren 28/112 Prüffotos und die neuen
68 Prüffotos vor. Fotos, Beobachtungen, bekannte Fotografennamen/-IDs und
identische Dateien werden zwischen den Gruppen ausgeschlossen. Die neuen Fotos
haben jeweils verschiedene bekannte Fotografen. Der Kleine Wasserfrosch hat drei
statt fünf Fotos, weil keine fünf zusätzlichen unabhängigen Fotografen verfügbar
waren. Die Dateien und Quellen sind über die eingefrorenen Manifeste festgelegt;
`collect_calibration_probe.py` ist nur für eine neue Datenerhebung gedacht und
gehört nicht zur Wiederholung dieses Tests.

In einem separaten Terminal den lokalen Benchmarkserver starten:

```powershell
$env:RIBBY_ACCURACY_WORKSPACE = 'accuracy_work/v3'
$env:RIBBY_ACCURACY_DATA_DIR = 'accuracy_work/v3/references'
python tests/accuracy/serve.py
```

Im Arbeitsterminal die früheren 112 und neuen 68 Fotos durch beide echten Modelle
auswerten. Die Referenzvektoren liegen bereits im Seed. Für Prüffotos wird dieselbe
JPEG-Normalisierung wie in der App verwendet. Vorhandene Vektoren werden wieder
verwendet. Ein eigener Browsercache vermeidet Konflikte mit anderen Tests.

```powershell
$env:RIBBY_EMBEDDING_WORKSPACE = 'accuracy_work/v3'
$env:RIBBY_V3_INPUT = 'holdout'
$env:RIBBY_BROWSER_CACHE = 'accuracy_work/calibration/browser_cache'
node tests/accuracy/collect_v3.cjs
$env:RIBBY_EMBEDDING_WORKSPACE = 'accuracy_work/calibration'
$env:RIBBY_V3_INPUT = 'probe'
node tests/accuracy/collect_v3.cjs
node tests/accuracy/evaluate_calibration.cjs
```

Die Auswertung verwendet die tatsächliche Ranking-/Kalibrierungsfunktion aus der
aktuellen HTML-Datei. Sie prüft beide Modelle mit 8/16/32 Referenzen, Normierung
über alle 14 Arten vor dem Kürzen auf fünf Karten, unveränderte Rangfolgen,
Brier-Fehler, gruppierte Kalibrierungsabweichung und gepaarte Bootstrap-Intervalle.
Die neuen 68 Fotos sind die primäre unabhängige Prüfung; die früheren 112 Fotos
bleiben ein separater Regressionstest. Die Ergebnisse werden nicht vermischt.

## Vollständige App-Abläufe und gespeicherte Daten

Die [Systemtests](../SYSTEM_TESTS.md) vollständig ausführen. Der Prüfserver auf
Port 7436 verwendet eine eigene Datenbank. `browser_all_species.cjs` führt die
68 Fotos mit beiden echten Modellen durch Upload, Ergebnisanzeige, Artkorrektur,
Fundort/GPS und Speicherung. `browser_percentages.cjs` prüft sieben spezielle
Anzeigefälle mit einem eingefrorenen Vektor, ohne Erkennungsgenauigkeit zu messen.
Nach allen Browserprüfungen ausführen:

```powershell
python tests/accuracy/verify_calibration_results.py
python tests/build_system_report.py
```

Der Abgleich prüft alle 136 tatsächlichen Vorschlagslisten und gespeicherten
Datensätze gegen die separate Auswertung, einschließlich Score-Typ,
Kalibrierungskennung, bestätigter Art und GPS. Er prüft außerdem den eingefrorenen
Fingerabdruck des akzeptierten statischen HTML-/CSS-Designs. Historische Berichte
liegen unter `reports/v3/`; aktuelle unter `reports/*v4*` und
`reports/system_calibration_*.json`. Die Prüfserver anschließend mit Strg+C beenden.

## Optional: Kalibrierung neu berechnen

Die ausgelieferte `image_calibration.json` ist eingefroren. Eine Wiederholung der
Prüfung braucht kein erneutes Training. Nur für die Offline-Entwicklung benötigt
`fit_calibration.py` zusätzlich NumPy (geprüft mit 2.3.5):

```powershell
$env:OPENBLAS_NUM_THREADS = '2'
python tests/accuracy/fit_calibration.py --embed
```

Das Skript liest ausschließlich die 896 öffentlichen Referenzvektoren. Fotografen
werden über Namen und bekannte iNaturalist-IDs gruppiert. Fünf äußere und drei
innere Falten prüfen die Kalibrierung mit festgehaltenem V3-Vergleich (Ridge α=1).
Die schon früher getroffene V3-Modellwahl wird hier nicht erneut verschachtelt
ausgewählt. Eine positive Temperatur je Modell/Referenzlimit wird aus den
Out-of-fold-Vorhersagen gelernt. `--embed` ersetzt die Parameter auch in der
HTML-Datei. Nach einem solchen Schreibvorgang müssen Auswertung und App-Prüfungen
erneut laufen. Die unabhängigen Prüffotos dürfen nicht zum Nachjustieren dienen.

Die Trefferchance gilt nur innerhalb der 14 bekannten Arten und für exakt die
geprüften öffentlichen Referenzsets. Geänderte oder private Bestände erhalten
Bildähnlichkeit. Die Stichprobe ist klein; unbekannte Fotografen-Aliasnamen und
Vortrainingsdaten bleiben Grenzen. Technisch bestandene Tests garantieren keine
100-prozentige Artbestimmung. Kamera und Smartphone-Layout wurden im virtuellen
Chromium-Testgerät geprüft, nicht auf echter iPhone-/Android-Hardware.
