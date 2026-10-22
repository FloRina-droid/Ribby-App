"""Report paired held-out results without conflating them with validation scores."""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
report=read('image_accuracy_v3.json');selection=read('model_selection_v3.json');corpus=read('reference_corpus_v3.json')
ui=read('system_all_species.json');consistency=read('system_v3_consistency.json')
assert ui['pass'] and consistency['pass'] and consistency['cases']==224
assert ui['app_sha256']==report['app_sha256']==consistency['app_sha256']
assert report['app_sha256']==hashlib.sha256((ROOT/'ribby_app.html').read_bytes()).hexdigest()
assert report['metric_sha256']==hashlib.sha256((ROOT/'image_metric.json').read_bytes()).hexdigest()
def pct(k,n):return f'{k}/{n} ({100*k/n:.1f} %)'
def interval(k,n):
    z=1.96;p=k/n;denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return f'{100*(center-half):.1f}–{100*(center+half):.1f} %'
def paired_p(row):
    a,b=row['improved'],row['regressed'];n=a+b
    return min(1,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1
lines=['# Ribby – mehr Bilddaten und Genauigkeitsprüfung V3','',
'## Bestand und Trennung','',
'896 unterschiedliche CC0-/CC-BY-Referenzfotos, 64 für jede der 14 ursprünglichen Arten; zuvor 447. Quellen: 816 iNaturalist-Fotos und 80 Wikimedia-Commons-Fotos. 1792 geprüfte Merkmalsvektoren für die beiden Bildmodelle werden mitgeliefert.',
'112 zusätzliche Prüffotos, acht je Art, wurden vor der Verfahrenswahl eingefroren. Foto-IDs, Beobachtungen, normalisierte Fotografennamen und bekannte iNaturalist-Urheber-IDs sind von den Referenzen getrennt. Auch identische Bilddateien wurden über SHA-256 ausgeschlossen. Die 28 früheren Prüffotos und deren bekannte Urheber bleiben ebenfalls außerhalb des Referenzbestands.',
'Der neue Testsatz enthält auch schwierige Motive, kleine/verdeckte Tiere, Larven und tote Tiere. Diese Fälle werden nicht nach dem Erkennungsergebnis aussortiert. Die Sichtprüfung prüft Bildinhalt und Lesbarkeit, ersetzt aber keine fachliche Neubestimmung der Artenlabels.','',
'## Auswahl vor dem Prüfsatz','',
'Fünffache Kreuzvalidierung über die 896 Referenzfotos. Verbundene Fotografennamen und numerische iNaturalist-IDs liegen jeweils vollständig in derselben Falte. Verglichen werden feste Referenzlimits und Verfahren; zusätzliche explorative Verfahren sind im JSON mit aufgeführt. Die Wahl für den App-Betrieb bleibt bei den bestehenden 8/16/32-Bedienelementen und einem Vergleich der ausgewählten Referenzfotos.',
'Gewählt wurde BioCLIP mit 16 Referenzen und einer regularisierten linearen Projektion (Ridge, α=1) vor dem Kosinusvergleich der Klassenprototypen. In der gruppierten Validierung: '+pct(selection['selected']['correct'],896)+' Ersttreffer und '+pct(selection['selected']['top3_correct'],896)+' Top-3-Treffer. Das ist ein Wert zur Verfahrenswahl, keine unabhängige Erfolgsquote.',
'Die Projektion nutzt ausschließlich die Referenzdaten. Die BioCLIP-/DINOv2-Bildencoder bleiben unverändert. Die eingefrorenen Gewichte stehen in `image_metric.json` und in der HTML-Datei. Nach Öffnen der Prüfergebnisse wurden Verfahren, Referenzlimits und Gewichte nicht anhand dieser Labels nachjustiert. BioCLIP bleibt aufgrund der Validierung der Standard; der kleinere DINOv2 ist über die vorhandene Auswahl verfügbar.','',
'## Neue, unabhängige Fotos: gepaarter Vergleich','',
'Alle Zahlen vor und nach der Änderung beziehen sich auf dieselben 112 Bilder mit derselben JPEG-Normalisierung der App. Die Rangfolge wird vor der manuellen Artkorrektur gemessen.','',
'| Modell | Ersttreffer vorher | Ersttreffer jetzt | Top 3 vorher | Top 3 jetzt |','|---|---:|---:|---:|---:|']
for model,row in report['primary'].items():
    n=row['n'];lines.append(f"| {model} | {pct(row['before_top1'],n)} | {pct(row['after_top1'],n)} | {pct(row['before_top3'],n)} | {pct(row['after_top3'],n)} |")
lines+=['',
'Allein das Vergrößern des Vorrats bei weiterhin 16 ausgewählten Vergleichsbildern ändert hier die Rangfolge nicht: Die ausgewählten ersten Referenzen bleiben erhalten. Der Zugewinn entsteht durch die aus dem größeren Bestand gelernte Projektion. Weitere Referenzen sind bei 32 Bildern in der vorhandenen Einstellung nutzbar.',
'Die Verbesserung des Standards BioCLIP ist klein: acht bisher falsche Bilder werden richtig, fünf bisher richtige werden falsch. Sie belegt keinen statistisch gesicherten Zuwachs im Feldeinsatz.','',
'| Modell | 95-%-Wilson-Intervall des neuen Ersttrefferanteils | Verbessert / verschlechtert | Gepaarter exakter p-Wert |','|---|---:|---:|---:|']
for model,row in report['primary'].items():
    lines.append(f"| {model} | {interval(row['after_top1'],row['n'])} | {row['improved']} / {row['regressed']} | {paired_p(row):.4f} |")
lines+=['','Die p-Werte sind explorativ und nicht für mehrere Vergleiche korrigiert. Acht Fotos je Art bleiben eine kleine Stichprobe. Ein unbekannter Anteil der Fotos kann in den ursprünglichen Vortrainingsdaten der Basismodelle enthalten sein.','',
'## Ergebnis je Art auf den neuen Fotos','',
'| Art | BioCLIP vorher → jetzt | BioCLIP Top 3 jetzt | DINOv2 vorher → jetzt | DINOv2 Top 3 jetzt |','|---|---:|---:|---:|---:|']
for species in corpus['species']:
    a=[r for r in report['primary']['bioclip']['rows'] if r['species_id']==species['id']]
    b=[r for r in report['primary']['dinov2']['rows'] if r['species_id']==species['id']]
    assert len(a)==len(b)==8
    lines.append(f"| {species['name_de']} (*{species['sci']}*) | {sum(r['before_top1'] for r in a)} → {sum(r['after_top1'] for r in a)} / 8 | {sum(r['after_top3'] for r in a)}/8 | {sum(r['before_top1'] for r in b)} → {sum(r['after_top1'] for r in b)} / 8 | {sum(r['after_top3'] for r in b)}/8 |")
lines+=['','## Frühere 28 Fotos als Regressionstest','',
'Diese bereits früher ausgewerteten Bilder werden separat gezeigt und nicht als neuer unabhängiger Nachweis gezählt.','',
'| Modell | Ersttreffer vorher → jetzt | Top 3 vorher → jetzt |','|---|---:|---:|']
for model,row in report['regression'].items():
    lines.append(f"| {model} | {row['before_top1']} → {row['after_top1']} / 28 | {row['before_top3']} → {row['after_top3']} / 28 |")
lines+=['','Bei BioCLIP verbessert sich der Ersttreffer, die Top-3-Quote dieses alten Satzes sinkt jedoch um ein Foto. Es gibt somit keine Verbesserung für jedes Bild oder jede Kennzahl.','',
'## Technische Prüfung und Nachweise','',
'In der regulären App-Oberfläche bestehen 224/224 Abläufe mit beiden echten Modellen, allen 112 Fotos, Artbestätigung und Fundort/GPS. Gespeicherte Resultate für alle 14 Arten wurden erneut geöffnet. Vorschlagslisten und tatsächliche GPS-/Art-/Fundortdateien stimmen in allen 224 Fällen mit der separaten Prüfung überein. Der [Systembericht](system_test_report.md) dokumentiert die Abläufe getrennt von deren Erkennungsquote.',
'Zusätzlich: 32 Backendtests einschließlich Seed-Upgrade und begrenzter Vektorauslieferung; JavaScript-Prüfung einschließlich negativer Kosinuswerte und Rückfall für neue Arten; 18 Fehlerfälle; 13 Ablaufprüfungen mit 24 Wiederholungsanalysen; private Referenzen für 14 Arten. Kamera und Smartphone-Layout werden im Chromium-Testgerät geprüft, nicht auf echter iPhone-/Android-Hardware.',
'Aufbau, HTML-Elemente und Styles der freigegebenen Oberfläche bleiben unverändert. Der Vergleich entfernt nur die Scriptblöcke und prüft danach die vollständige Übereinstimmung. Beleg: `design_preservation_v3.json`.',
'Die Quellenlizenzen sind pro Foto eingefroren; Urheber, Lizenzlink und Originalquelle bleiben sichtbar. [iNaturalist-Bildrechte](https://help.inaturalist.org/en/support/solutions/articles/151000169918), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [CC0](https://creativecommons.org/publicdomain/zero/1.0/). Die Lizenz einer Beobachtung ersetzt keine Fotolizenz.',
'Die angepassten Kosinuswerte werden von −1…1 auf 0…1 abgebildet. Prozentwerte sind Bildähnlichkeiten, keine kalibrierten Bestimmungswahrscheinlichkeiten und nicht direkt mit älteren Versionswerten vergleichbar.',
'Reproduktion: [Genauigkeitsprüfung](../tests/accuracy/README.md) und [Systemtests](../tests/SYSTEM_TESTS.md). Rohdaten: `image_accuracy_v3.json`, `model_selection_v3.json`, `reference_manifest_v3.json`, `accuracy_holdout_v3.json`.','',
f"- App-SHA-256: `{report['app_sha256']}`",f"- Metrik-SHA-256: `{report['metric_sha256']}`",'']
(ROOT/'reports/image_accuracy_v3.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:{'top1':v['after_top1'],'n':v['n'],'p':paired_p(v)} for k,v in report['primary'].items()}))
