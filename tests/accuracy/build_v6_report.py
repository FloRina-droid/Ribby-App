"""Audit the V6 cache fix against the published V5 predictions and current tests."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE='95100e182ae805fef23ea270fddd3ea2a01306a9'
read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
baseline=read('prediction_baseline_v5.json')
assert baseline['source_commit']==BASE
current=read('calibration_evaluation_v4.json')
records=[]
for group in ('primary','regression'):
    for model in ('bioclip','dinov2'):
        for limit in ('8','16','32'):
            for row in current[group][model][limit]['rows']:
                records.append([group,model,limit,row['id'],row['predicted'],row['correct'],row['top3'],row['matches']])
comparisons=len(records)
assert comparisons==baseline['prediction_count']==1080
assert hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()==baseline['predictions_sha256']
for name in ('image_metric.json','image_calibration.json'):
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==baseline['parameters_sha256'][name]
core=read('system_core_tests.json');ui=read('system_calibration_species.json')
cache=read('image_cache_unit_v6.json');browser=read('image_cache_browser_v6.json')
consistency=read('system_calibration_consistency.json');seed=read('release_seed_v5.json')
percent=read('system_percentages_v4.json');design=read('design_preservation_v4.json')
faults=read('system_faults.json');lifecycle=read('system_lifecycle.json')
private=read('system_private_species.json');regressions=read('system_regressions.json');pack=read('system_reference_pack.json')
assert not pack['errors'] and pack['photo_count']==896 and pack['vector_count']==1792
assert len(pack['species'])==14 and all(row['pass'] for row in pack['species'])
for report in (core,ui,cache,browser,consistency,seed,percent,design,private):assert report['pass']
assert all(row['pass'] for row in faults+lifecycle+regressions)
app_hash=hashlib.sha256((ROOT/'ribby_app.html').read_bytes()).hexdigest()
assert all(r['app_sha256']==app_hash for r in (ui,cache,browser,consistency,design,current))
assert seed['backend_sha256']==hashlib.sha256((ROOT/'ribby_images.py').read_bytes()).hexdigest()
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in core['sha256'].items())
integrity=json.loads((ROOT/'image_reference_integrity.json').read_text(encoding='utf-8'))
assert integrity['calibration_id']==current['calibration_id'] and len(integrity['images'])==896
cases=sum(len(rows) for rows in ui['models'].values())
report={'pass':True,'baseline_commit':BASE,'backend_tests':core['passed'],
        'cache_unit_cases':len(cache['cases']),'cache_browser_cases':len(browser['cases']),
        'real_model_flows':cases,'stored_results_and_gps':consistency['cases'],
        'percentage_browser_cases':len(percent['cases']),'fault_cases':len(faults),
        'lifecycle_cases':len(lifecycle),'private_species':len(private['species']),
        'regression_cases':len(regressions),'frozen_prediction_comparisons':comparisons,
        'rankings_scores_and_parameters_unchanged':True,'static_design_unchanged':True,
        'integrity_id':integrity['id'],'app_sha256':app_hash,'source_sha256':core['sha256']}
(ROOT/'reports/release_v6.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
lines=['# Ribby – Cache- und Datenintegrität V6','',
'Stand: 21. Oktober 2026. Der bestehende Bildmodus und das akzeptierte Design bleiben erhalten. Diese Änderung verhindert veraltete Referenzmerkmale und unberechtigte kalibrierte Prozentanzeigen nach einem Fotoaustausch. Sie trainiert keine neuen Modelle und behauptet keinen Zuwachs der unveränderten Erkennungsquote.','',
'## Behobene Fälle','',
'Bisher verwendete IndexedDB nur Modellkennung und Bild-ID als Cache-Schlüssel. Ein anderes Foto unter derselben ID konnte deshalb mit alten Merkmalen verglichen werden. Cache-Einträge enthalten jetzt zusätzlich die SHA-256-Prüfsumme des verwendeten Fotos. Ohne passende Modell- und Foto-Bindung werden die Merkmale neu berechnet. Alte Einträge werden beim ersten Einsatz erneuert; passende Einträge benötigen weiterhin keine erneute Referenzinferenz.','',
'Der Server liefert die aktuelle Foto-Prüfsumme auch dann, wenn kein gültiger vorberechneter Vektor vorhanden ist. Er entfernt eventuell mitgespeicherte Features aus Suchmetadaten vor der Validierung. Nur Vektoren mit passendem Modell, Foto-Hash, Dimension, numerischen Werten und Norm werden ergänzt. Boolean-Werte werden nicht als Modellzahlen akzeptiert.','',
'Beim Laden eines Referenzfotos prüft der Browser die tatsächlichen Bytes gegen die angekündigte Prüfsumme. Ein während der Analyse ausgetauschtes Foto wird nicht mit einem alten Wert gemischt. Ungültige Modellantworten werden abgewiesen. Speicherfehler bleiben optional; Abbruch und Nutzerwechsel verhindern verspätete Cache-Schreibvorgänge.','',
'Die kalibrierte Trefferchance erfordert neben den unveränderten Art-/Referenz-IDs auch genau die geprüften Foto-Prüfsummen aus `image_reference_integrity.json`. Andere Fotos unter gleichen IDs erhalten Bildähnlichkeit. Die Registry wurde aus allen 896 Seed-Fotos und beiden zugehörigen Vektorbeständen erzeugt; keine Temperatur wurde nachjustiert. Eine fehlerhafte Referenzprojektion erhält ebenfalls keine kalibrierte Anzeige.','',
'## Prüfung','',
'| Prüfung | Ergebnis |','|---|---:|',
f'| Backend | {core["passed"]}/{core["tests"]} |',
f'| Cache, echte App-Funktion mit kontrollierten Eingaben | {len(cache["cases"])}/{len(cache["cases"])} |',
f'| Cache-/Prüfsummenfälle in der Oberfläche | {len(browser["cases"])}/{len(browser["cases"])} |',
f'| Echte Modelle, 68 Fotos und alle 14 Arten | {cases}/{cases} |',
f'| Gespeicherte Ergebnisse, Art, GPS und Referenz-Prüfsumme | {consistency["cases"]}/{cases} |',
f'| Prozentanzeige | {len(percent["cases"])}/{len(percent["cases"])} |',
f'| Fehlerfälle / Ablaufprüfungen | {len(faults)}/{len(faults)} / {len(lifecycle)}/{len(lifecycle)} |',
f'| Private Referenzen speichern/nutzen/löschen | {len(private["species"])}/14 Arten |',
f'| Audio, GPS/Bildausschnitt, Artanlage und Sprache | {len(regressions)}/{len(regressions)} |',
f'| Vorhersagen gegen veröffentlichten Commit `{BASE[:7]}` | {comparisons}/{comparisons} unverändert |',
'| Seed | 3600 Dateien, 896 Fotos, 1792 nutzbare Vektoren |',
'| Statisches HTML und CSS | unverändert |','',
'Die 1080 Paarvergleiche umfassen beide Modelle, 8/16/32 Referenzen und getrennt die bisherigen 68 bzw. 112 Prüffotos. Alle fünf gespeicherten Scores und ihre Rangfolge bleiben exakt gleich. Bei 16 Referenzen auf den 68 Fotos bleibt BioCLIP bei 45/68 Ersttreffern, DINOv2 bei 39/68. Diese Fotos wurden nicht erneut zum Lernen oder zur Parameterwahl verwendet.','',
'Die 13 Cache-Funktionstests und acht gezielten UI-Fälle benutzen kontrollierte Vektoren und messen keine Erkennungsgenauigkeit. Die 136 Modellabläufe verwenden echte Inferenz. Kamera-/Mobilprüfungen bleiben virtuelle Chromium-Prüfungen. Die geschätzte Trefferchance gilt nur innerhalb der 14 bekannten Arten und des geprüften Bestands; es gibt keine 100-%-Garantie.','',
'Reproduktion: `python tests/run_core_tests.py`, `node tests/test_image_cache.cjs`, `node tests/browser_image_cache.cjs` sowie die vollständigen [Systemtests](../tests/SYSTEM_TESTS.md). Danach `python tests/accuracy/verify_calibration_results.py` und `python tests/accuracy/build_v6_report.py`.','',
f'App-SHA-256: `{app_hash}`',f'Integritätskennung: `{integrity["id"]}`','']
(ROOT/'reports/release_v6.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(report))
