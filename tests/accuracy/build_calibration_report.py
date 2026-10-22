"""Build the current system report and the independent percentage audit."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
evaluation=read('calibration_evaluation_v4.json');training=read('calibration_training_v4.json');ui=read('system_calibration_species.json')
core=read('system_core_tests.json');percent=read('system_percentages_v4.json');consistency=read('system_calibration_consistency.json')
audit=read('calibration_probe_audit_v4.json');design=read('design_preservation_v4.json')
faults=read('system_faults.json');lifecycle=read('system_lifecycle.json');private=read('system_private_species.json');regressions=read('system_regressions.json')
calibration=json.loads((ROOT/'image_calibration.json').read_text(encoding='utf-8'))
app_hash=hashlib.sha256((ROOT/'ribby_app.html').read_bytes()).hexdigest()
assert ui['pass'] and core['pass'] and percent['pass'] and consistency['pass'] and audit['pass'] and design['pass'] and private['pass']
assert all(r['pass'] for r in faults+lifecycle+regressions)
assert all(core['sha256'][name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in core['sha256'])
assert all(item['app_sha256']==app_hash for item in (evaluation,ui,consistency,design))
assert hashlib.sha256((ROOT/'image_calibration.json').read_bytes()).hexdigest()==evaluation['calibration_sha256']
assert evaluation['ranking_changes']==0 and evaluation['normalization_errors']==0
pct=lambda value:f'{100*value:.1f} %'
n=audit['new_photos'];cases=sum(len(rows) for rows in ui['models'].values())
lines=['# Ribby – geprüfte Prozentanzeige und weitere Tests V4','',
'Die Ergebniswerte werden für den geprüften Referenzbestand als geschätzte Trefferchance ausgewiesen. Bildähnlichkeiten bleiben zusätzlich gespeichert. Die Artvorschläge und ihre Rangfolge werden durch diese Kalibrierung nicht verändert.','',
'## Unabhängiger Test der Zahlen','',
f'{n} neue iNaturalist-Fotos aus {len(audit["species_counts"])} Arten; fünf je Art, beim Kleinen Wasserfrosch drei. Es waren nach Ausschluss der bisherigen Fotografen keine fünf unabhängigen neuen Fotografen für diese Art verfügbar. Kein Foto wurde wegen seines Erkennungsergebnisses aussortiert.',
'Foto-IDs, Beobachtungen, bekannte Fotografennamen und iNaturalist-IDs sowie identische Bilddateien sind von den 896 Referenzen und den 140 früheren Prüffotos getrennt. Alle 68 neuen Fotos haben verschiedene bekannte Fotografen. Die Fotolizenz wird einzeln auf CC0 oder CC BY geprüft. Die Labels stammen aus Research-Grade-Beobachtungen mit exaktem Taxon; eine fachliche Neubestimmung fand nicht statt.',
'Die folgenden Mittelwerte beziehen sich auf dieselben neuen Fotos bei der bisherigen Standardeinstellung mit 16 Referenzen. Die erste Zahl war eine Bildähnlichkeit und wurde bisher auch so bezeichnet. Die Gegenüberstellung prüft, wie gut eine Prozentanzeige zur tatsächlichen Ersttrefferhäufigkeit passt. Sie ist kein Nachweis, dass die alte Ähnlichkeitsrechnung mathematisch falsch war.','',
'| Modell | Bisheriger Anzeigewert, Mittel | Neue geschätzte Trefferchance, Mittel | Tatsächliche Ersttreffer |','|---|---:|---:|---:|']
for model in ('bioclip','dinov2'):
    r=evaluation['primary'][model]['16']
    lines.append(f"| {model} | {pct(r['mean_similarity'])} | {pct(r['mean_probability'])} | {r['correct']}/{r['n']} ({pct(r['accuracy'])}) |")
lines+=['','Die Nähe der Mittelwerte ist keine Garantie für die Richtigkeit eines einzelnen Prozentwerts. Auch gleichbleibende Werte könnten im Mittel passen. Deshalb werden zusätzlich der Brier-Fehler und die Abweichung innerhalb von Wahrscheinlichkeitsgruppen gemessen.','',
'| Modell | Brier vorher, wenn Ähnlichkeit als Chance gelesen wird | Brier kalibriert | 95-%-Intervall der gepaarten Differenz | ECE mit 10 Gruppen vorher → jetzt |','|---|---:|---:|---:|---:|']
for model in ('bioclip','dinov2'):
    r=evaluation['primary'][model]['16'];low,high=r['paired_brier_delta_95']
    lines.append(f"| {model} | {r['raw_as_chance_brier']:.3f} | {r['calibrated_brier']:.3f} | {low:.3f} bis {high:.3f} | {pct(r['raw_ece10'])} → {pct(r['calibrated_ece10'])} |")
lines+=['','Beim Brier-Fehler ist kleiner besser, null entspricht perfekten Angaben. Das Intervall beruht auf 2000 gepaarten Bootstrap-Stichproben. ECE mit nur 68 Bildern ist von der Gruppeneinteilung abhängig und bleibt unsicher. Die Verbesserung ist keine Aussage über beliebige Fotos oder jede einzelne Art.','',
'## Kalibrierung ohne Verwendung der neuen Prüfergebnisse','',
'Das Verfahren ist eine positive Temperaturskalierung über die Ähnlichkeitsscores aller 14 Arten. Alle Klassenwahrscheinlichkeiten werden vor dem Kürzen auf fünf Karten gemeinsam auf Summe eins normalisiert. Eine positive Temperatur ändert keine Rangfolge. Grundlage: [Guo et al., On Calibration of Modern Neural Networks, ICML 2017](https://proceedings.mlr.press/v70/guo17a.html).',
'Die Temperatur wird ausschließlich aus nach Fotografen getrennten Vorhersagen der 896 Referenzfotos gelernt. Für die interne Prüfung werden fünf äußere und drei innere Falten verwendet: Die inneren Falten lernen die Temperatur, die äußere Falte bewertet sie. Der vorhandene V3-Bildvergleich mit Ridge-Parameter α=1 wird dabei festgehalten. Die schon früher getroffene V3-Modellwahl ist kein Bestandteil dieser verschachtelten Kalibrierungsprüfung.',
'Die neuen 68 Prüffotos und die früheren 112/28 Prüffotos werden nicht zum Anpassen der Temperatur verwendet. Nach dem Öffnen ihrer Ergebnisse wurden Temperaturen und Referenzlimits nicht nachjustiert.','',
'| Modell / Referenzen | Interner Brier: Ähnlichkeit als Chance → kalibriert | Brier auf den neuen Fotos vorher → jetzt |','|---|---:|---:|']
for model in ('bioclip','dinov2'):
    for limit in ('8','16','32'):
        a=training['models'][model][limit];b=evaluation['primary'][model][limit]
        lines.append(f"| {model} / {limit} | {a['raw_as_chance']['brier']:.3f} → {a['calibrated']['brier']:.3f} | {b['raw_as_chance_brier']:.3f} → {b['calibrated_brier']:.3f} |")
lines+=['','Die 32-Referenz-Konfiguration von BioCLIP hat im neuen Satz einen kleineren Brier-Punktwert; ihr Bootstrap-Intervall umfasst jedoch auch null. Es wird daher kein gesicherter Vorteil jeder Konfiguration behauptet.',
'Die separate Wiederholung auf den früheren 112 Prüffotos verändert bei 16 Referenzen keine Artvorhersage: BioCLIP bleibt bei 62/112 Ersttreffern, DINOv2 bei 64/112. Die vollständigen Zahlen für alle Referenzlimits stehen in `calibration_evaluation_v4.json`.','',
'## Geltungsbereich und Darstellung','',
'Die Trefferchance gilt unter der Voraussetzung, dass das Foto eine der 14 verglichenen Arten zeigt. Sie ist keine geprüfte Erkennung unbekannter Arten und keine Garantie im Feldeinsatz. Andere Arten, Regionen, Bildqualitäten, Fotografen-Aliasnamen und unbekannte Vortrainingsdaten können abweichende Ergebnisse erzeugen.',
'Die App verwendet diese Anzeige nur bei passendem Bildmodell, vollständiger Artengruppe und exakt den geprüften öffentlichen Referenz-IDs für 8, 16 oder 32 Bilder je Art. Bei privaten, fehlenden, veränderten oder unbekannten Referenzen/Arten zeigt sie ausdrücklich Bildähnlichkeit. Ein späterer Quellen-Refresh kann diesen Rückfall auslösen. Neue Referenzkonfigurationen müssen neu kalibriert werden.',
'Die bisherige Oberfläche, Farben, Bedienelemente und Styles bleiben erhalten. Prozentwert, Balken und Beschriftung zeigen die jeweilige Datenbedeutung. Geschätzte Werte über 99 % erscheinen als „>99 %“, unter 1 % als „<1 %“; daraus wird keine gerundete 100-%-Garantie.',
'Bei manueller Artwahl wird der Prozentwert der gewählten Art verwendet. Wenn dafür kein gespeicherter Modellwert vorhanden ist, bleibt die Zahl leer. Ein fremder Vorschlagswert wird nicht übernommen. Alte Verlaufseinträge werden nicht nachträglich als kalibrierte Werte ausgegeben. CSV enthält Score-Typ und Kalibrierungs-ID; der Audio-Batch-Export hat wieder passend ausgerichtete Spalten.',
'Referenzfoto, Quelle, Lizenz und Urheber bleiben unverändert. Private Nutzerfotos wurden nicht für die Kalibrierung genutzt.','',
'## Technische Nachweise','',
f'- {cases}/{cases} neue vollständige App-Abläufe mit beiden echten Modellen; alle {n} Fotos, Bestätigung, Fundort/GPS und Verlauf.',
f'- {consistency["cases"]}/{cases} Vorschlagslisten, Wahrscheinlichkeiten und tatsächlich gespeicherte GPS-/Art-/Kalibrierungsdaten gegen die getrennte Auswertung geprüft; maximale Wahrscheinlichkeitsabweichung {consistency["max_probability_difference"]:.2g}.',
f'- {len(percent["cases"])}/{len(percent["cases"])} gezielte Browserprüfungen für Prozentanzeige, manuelle Korrektur, Bestandswechsel und alte Ergebnisse.',
f'- {core["passed"]}/{core["tests"]} Backendtests; JavaScript-Syntax, Ranking, Wahrscheinlichkeitsnormierung, Rückfälle, Zahlenformat und CSV geprüft.',
f'- {len(faults)}/{len(faults)} Fehlerszenarien, {len(lifecycle)}/{len(lifecycle)} Ablaufprüfungen einschließlich 24 Wiederholungsanalysen; private Referenzen für 14 Arten sowie {len(regressions)}/{len(regressions)} Audio-/GPS-/Artanlage-/Sprachregressionen bestanden.',
'- Statisches HTML und CSS sind vollständig gleich geblieben (`design_preservation_v4.json`). Kamera/Smartphone-Prüfungen verwenden Chromium-Testgeräte, keine echte Android-/iPhone-Hardware.',
'Reproduktion: [Systemtests](../tests/SYSTEM_TESTS.md) und [Kalibrierungsprüfung](../tests/accuracy/CALIBRATION.md). Die Prüfungen beziehen sich auf die unten genannten Dateiprüfsummen.','',
f'- App-SHA-256: `{app_hash}`',f'- Kalibrierungs-SHA-256: `{evaluation["calibration_sha256"]}`',f'- Kalibrierungs-ID: `{calibration["id"]}`','']
(ROOT/'reports/image_calibration_v4.md').write_text('\n'.join(lines),encoding='utf-8')
system=['# Ribby – Systemprüfung des aktuellen Bildmodus V4','',
f'Alle definierten technischen Prüfungen dieses Stands bestehen. Das ist keine 100-prozentige Erkennungsgenauigkeit. Details zur Bedeutung und Qualität der Zahlen: [Prozentbericht V4](image_calibration_v4.md).','',
'| Prüfung | Ergebnis |','|---|---:|',f'| Backend | {core["passed"]}/{core["tests"]} |',f'| Echte Bildmodelle mit {n} neuen Fotos, allen 14 Arten, Bestätigung und GPS | {cases}/{cases} |',
f'| Persistierte Prognosen, Kalibrierung und Georeferenz | {consistency["cases"]}/{cases} |',f'| Gespeicherte Ergebnisse je Art wieder geöffnet | {len(ui["technical_cases"])}/14 |',f'| Prozentanzeige und Artkorrektur | {len(percent["cases"])}/{len(percent["cases"])} |',f'| Fehlerfälle | {len(faults)}/{len(faults)} |',f'| Sitzungen, Speicherrennen und Verlauf | {len(lifecycle)}/{len(lifecycle)} |','| Private Referenzen speichern/nutzen/löschen | 14/14 Arten |',f'| Audio-/GPS-/Artanlage-/Sprachregressionen | {len(regressions)}/{len(regressions)} |','| JavaScript-Ranking, Kalibrierung, Format und CSV | bestanden |','| HTML-Aufbau und Styles | unverändert |','',
'Der öffentliche Referenzbestand mit 896 Fotos und 1792 Vektoren wurde gegenüber V3 nicht verändert. Seine Browser-/Vektorprüfung ist im historischen [V3-Systembericht](v3/system_test_report.md) und `system_reference_pack.json` dokumentiert. Der neue Prüfsatz ist nach Fotografen, Beobachtung, Foto-ID und identischen Bilddateien von allen bisherigen Daten getrennt.',
'', '## Erkennung auf den neuen Fotos','', '| Modell | Erster Treffer | Richtige Art unter Top 3 |','|---|---:|---:|']
for model,rows in ui['models'].items():system.append(f"| {model} | {sum(r['top1'] for r in rows)}/{len(rows)} | {sum(r['top3'] for r in rows)}/{len(rows)} |")
system+=['','Die Kalibrierung ändert nur die Interpretation der Prozentwerte, keine Artvorhersage. Die neuen Fotos sind ein anderer Testsatz als die 112 Fotos aus V3; die Erfolgsquoten dürfen nicht als Vorher/Nachher-Verbesserung der Erkennung verglichen werden. Kamera und Smartphone-Layout wurden nur im Chromium-Testgerät geprüft. Der Audio-Test nutzt ein synthetisches Signal und misst keine akustische Artgenauigkeit.',
'','## Prüfsummen','']
for name,value in core['sha256'].items():system.append(f'- `{name}`: `{value}`')
(ROOT/'reports/system_test_report.md').write_text('\n'.join(system)+'\n',encoding='utf-8')
print(json.dumps({'pass':True,'new_photo_cases':n,'real_model_flows':cases,'percentage_ui_cases':len(percent['cases']),'mean_probabilities':{m:evaluation['primary'][m]['16']['mean_probability'] for m in ('bioclip','dinov2')}},ensure_ascii=False))
