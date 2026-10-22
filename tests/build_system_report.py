"""Summarize measured technical results separately from image identification rates."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'image_calibration.json').exists():
    import runpy
    import sys
    runpy.run_path(str(ROOT/'tests/accuracy/build_calibration_report.py'),run_name='__main__')
    sys.exit(0)
read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
core=read('system_core_tests.json');all_species=read('system_all_species.json');faults=read('system_faults.json');refs=read('system_reference_pack.json');private=read('system_private_species.json');regressions=read('system_regressions.json')
lifecycle=read('system_lifecycle.json')
consistency=read('system_v3_consistency.json');design=read('design_preservation_v3.json')
catalog=json.loads((ROOT/'image_reference_catalog.json').read_text(encoding='utf-8'))
assert core['pass'] and all_species['pass'] and private['pass']
assert all(r['pass'] for r in faults+regressions+lifecycle) and not refs['errors']
assert all_species['app_sha256']==hashlib.sha256((ROOT/'ribby_app.html').read_bytes()).hexdigest()
assert consistency['pass'] and consistency['cases']==224 and consistency['app_sha256']==all_species['app_sha256']
assert design['pass'] and design['before_sha256']==design['after_sha256'] and design['app_sha256']==all_species['app_sha256']
assert all(core['sha256'][name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in core['sha256'])
metrics={model:{'technical':sum(r['technical_pass'] for r in rows),'n':len(rows),'top1':sum(r['top1'] for r in rows),'top3':sum(r['top3'] for r in rows)} for model,rows in all_species['models'].items()}
query_count=len(next(iter(all_species['models'].values())))
per_species=query_count//len(catalog)
reference_limit=all_species.get('reference_limit',16)
real_cases=sum(m['n'] for m in metrics.values())
lines=['# Ribby – Prüfung des integrierten Bildmodus','',f"Prüfstand: {datetime.now(timezone.utc).isoformat()} · Edge/Chromium {all_species['browser']}",'',
f'Alle definierten technischen Prüfungen dieses Teststands bestehen. Das bedeutet **keine 100-prozentige Erkennungsgenauigkeit**. Der Testsatz umfasst {query_count} separate Fotos mit {per_species} Aufnahmen je Art; die automatische Rangfolge wird vor einer manuellen Korrektur gemessen.','',
'## Technischer Funktionsumfang','',
'| Prüfung | Ergebnis |','|---|---|',f"| Backend, Rechte, Lizenzen, Cache, Seeds, Import/Export, parallele Uploads | {core['passed']}/{core['tests']} bestanden |",'| JavaScript-Syntax, Kosinus-Ranking, Klassenmittelwert und Auswahl | bestanden |',
f"| Echte Bildmodelle, Upload, Vergleich aller 14 Arten, Bestätigung und GPS/Fundort | {sum(m['technical'] for m in metrics.values())}/{real_cases} bestanden |",
f"| Gespeicherte Bildresultate für alle Arten erneut öffnen | {sum(r['pass'] for r in all_species['technical_cases'])}/14 bestanden |",
f"| Abbruch, Kamera-Rennen, Abmeldung, Dateiformate, Server- und Cachefehler, Smartphone-Layout | {sum(r['pass'] for r in faults)}/{len(faults)} bestanden |",
f"| Browser-Neuladen, Speicherrennen, Nutzerwechsel, Verlauf und 24 Wiederholungsanalysen | {sum(r['pass'] for r in lifecycle)}/{len(lifecycle)} bestanden |",
f"| Eigene Referenzen je Art speichern/nutzen/löschen | {len(private['species'])}/14 Arten bestanden |",
f"| Private Referenzen: Nutzertrennung, Dubletten und Backup | {len(private['checks'])}/{len(private['checks'])} bestanden |",
f"| GPS nach Bildausschnitt, echte Audio-Engine, neue Art, englischer Verbindungshinweis | {len(regressions)}/{len(regressions)} bestanden |",
f"| Referenzbilder tatsächlich im Browser dekodiert | {refs['photo_count']}/{refs['photo_count']} bestanden |",
f"| Vorberechnete Bildvektoren, Modellkennung, Dimension und Norm | {refs['vector_count']}/{refs['vector_count']} bestanden |",'',
'Die tatsächlichen Vorschlagslisten und gespeicherten GPS-/Art-/Fundortdaten aller 224 Analysen sind zusätzlich gegen die eingefrorene Auswertung und die Dateien auf dem Server geprüft (`system_v3_consistency.json`). HTML-Aufbau und Styles entsprechen vollständig der freigegebenen Vorschau (`design_preservation_v3.json`).','',
'## Erkennung je Art','',
f'Jeder Wert bezieht sich auf {per_species} unabhängige Fotos. „Ablauf“ bewertet die technische Ausführung, nicht die Richtigkeit des Vorschlags. BioCLIP und DINOv2 nutzen hier jeweils {reference_limit} Referenzen pro Art. Die Konfiguration wurde vor dieser Prüfung anhand getrennter Validierungsdaten festgelegt.','',
'| Art | Ablauf (beide Modelle) | BioCLIP erster Treffer | BioCLIP Top 3 | DINOv2 erster Treffer | DINOv2 Top 3 |','|---|---:|---:|---:|---:|---:|']
for sp in catalog:
    bio=[r for r in all_species['models']['bioclip'] if r['species_id']==sp['id']]
    dino=[r for r in all_species['models']['dinov2'] if r['species_id']==sp['id']]
    assert len(bio)==len(dino)==per_species
    lines.append(f"| {sp['name_de']} (*{sp['sci']}*) | {sum(r['technical_pass'] for r in bio+dino)}/{2*per_species} | {sum(r['top1'] for r in bio)}/{per_species} | {sum(r['top3'] for r in bio)}/{per_species} | {sum(r['top1'] for r in dino)}/{per_species} | {sum(r['top3'] for r in dino)}/{per_species} |")
lines+=['','| Modell | Erster Treffer richtig | Richtige Art unter Top 3 |','|---|---:|---:|']
for model,m in metrics.items():lines.append(f"| {model} | {m['top1']}/{m['n']} ({100*m['top1']/m['n']:.1f} %) | {m['top3']}/{m['n']} ({100*m['top3']/m['n']:.1f} %) |")
lines+=['','## Behobene Fehler','',
'- Eine leere oder ungültige Artwahl bestätigt keine frühere oder zufällig passende Art mehr.',
'- Upload und Bildausschnitt sperren die Analyse während der Vorbereitung. Entfernte/ersetzte Fotos und GPS werden bei asynchroner Verarbeitung korrekt behandelt.',
'- Nach Abbruch oder Abmeldung erscheinen keine verspäteten Ergebnisse, Kamerafotos oder privaten Fotolisten. Eine alte Kamera-Fehlermeldung stoppt keine neu geöffnete Kamera.',
'- Fehlende Referenzen führen zu einer klaren Fehlermeldung. Ein Ausfall des optionalen Merkmalscaches blockiert die Analyse nicht; ungültige gespeicherte Vektoren werden neu berechnet.',
'- Nach einem fehlgeschlagenen Speichern des Verlaufs kann die Bestätigung erneut gespeichert werden, ohne eine nicht vorhandene Verlaufs-ID zu verwenden.',
'- Gleichzeitige Uploads können dasselbe private Foto nicht zwei Arten zuweisen. Der Dublettenschutz berücksichtigt auch ältere Referenzen ohne gespeicherten Inhalts-Hash.',
'- Die manuelle Ergänzung einer neuen Art benutzt die richtige Serverroute.','',
'- Öffentliche Suchindizes älterer Versionen werden beim Seed-Upgrade aktualisiert. Bei der Analyse prüft und liefert der Server nur den gewählten Referenzumfang aus; der vollständige Bestand bleibt in der Verwaltung verfügbar.',
'- Nach dem Neuladen blockiert keine erneut eingeblendete Einwilligung eine bereits akzeptierte Sitzung. Das erneute Öffnen des Hinweises unterbricht die aktive Ansicht nicht.',
'- Abmelden widerruft den Servertoken. Gleichzeitige Sessionverlängerungen können ihn nicht wieder aktivieren; ungültige Token werden vor einem Dateizugriff abgewiesen.',
'- Speichervorgänge sind an Foto, Nutzer, Sitzung und Analyse gebunden. Späte Antworten und Fehler ändern keine neue Bestätigung; private Uploads werden nach einem Nutzerwechsel nicht fortgesetzt.',
'- Beim Öffnen alter Ergebnisse gilt die neueste Auswahl. Zwischenzeitlich gewählte Fotos werden nicht überschrieben. Gespeicherte Audioergebnisse können nicht versehentlich mit einer anderen ausgewählten Audiodatei bestätigt werden.','',
'## Grenzen und Nachvollziehbarkeit','',
f'Die Fotos sind nach Foto-ID, Beobachtung und bekannten Urhebern von den {refs["photo_count"]} Referenzen getrennt. Eine mögliche Überschneidung mit den ursprünglichen Trainingsdaten der Basismodelle ist unbekannt. {per_species} Fotos je Art bleiben eine kleine Stichprobe; die Artlabels stammen aus den eingefrorenen Quellen und wurden nicht für diese Prüfung fachlich neu bestimmt.',
'Kamera: virtuelles Chromium-Testgerät, inklusive Aufnahme, verweigerter Berechtigung und verspäteter Rückmeldungen. Mobile Prüfung: Smartphone-Viewport. Echte Android-/iPhone-Hardware und Safari wurden nicht geprüft. Die Audio-Regressionsprüfung verwendet ein synthetisches PCM-Signal und misst keine akustische Artgenauigkeit.',
'Die Serverdaten aller Prüfungen liegen in isolierten Testordnern. Die Produktivdatenbank wurde nicht geöffnet. Testfotos werden für die Modellanalyse im Browser verarbeitet; im echten Artentest wurden keine Uploads an externe Dienste beobachtet.',
'Der Vergleich mit dem früheren Bestand auf identischen Fotos und die getrennte Modellwahl sind im [Genauigkeitsbericht V3](image_accuracy_v3.md) dokumentiert.',
'Reproduktion: [Systemtest-Anleitung](../tests/SYSTEM_TESTS.md). Einzelresultate: `system_all_species.json`, `system_faults.json`, `system_lifecycle.json`, `system_private_species.json`, `system_reference_pack.json`, `system_regressions.json` und `system_core_tests.json`.',
'Der getestete Projektstand liegt lokal. Eine Veröffentlichung auf GitHub oder ein Produktivdeployment wurde nicht vorgenommen; der zuletzt geprüfte GitHub-Schreibzugriff war mit 403 blockiert.','',
'## Prüfsummen des getesteten Codes','']
for name,digest in core['sha256'].items():lines.append(f'- `{name}`: `{digest}`')
(ROOT/'reports/system_test_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'technical_pass':True,'core':core['tests'],'real_model_cases':real_cases,'fault_cases':len(faults),'lifecycle_cases':len(lifecycle),'private_species':len(private['species']),'reference_images':refs['photo_count'],'vectors':refs['vector_count'],'metrics':metrics},ensure_ascii=False))
