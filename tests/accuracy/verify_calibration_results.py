"""Compare real app forecasts and stored confirmations with frozen evaluation."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
read = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8'))
ui = read('reports/system_calibration_species.json')
evaluation = read('reports/calibration_evaluation_v4.json')
calibration = read('image_calibration.json')
integrity = read('image_reference_integrity.json')
app_hash = hashlib.sha256((ROOT / 'ribby_app.html').read_bytes()).hexdigest()
assert ui['pass'] and ui['app_sha256'] == evaluation['app_sha256'] == app_hash
assert evaluation['calibration_id'] == calibration['id']
cases = 0
maximum = 0.0
for model, rows in ui['models'].items():
    expected = {row['id']: row for row in evaluation['primary'][model]['16']['rows']}
    assert len(rows) == len(expected) and {row['id'] for row in rows} == set(expected)
    for row in rows:
        reference = expected[row['id']]
        assert row['technical_pass']
        assert [m['species'] for m in row['matches']] == [m['species'] for m in reference['matches']]
        assert row['top1'] == reference['correct'] and row['top3'] == reference['top3']
        history = read('dev/system_data/history/' + row['history_id'] + '.json')
        assert history['media_type'] == 'image'
        assert history['confirmed_species_id'] == row['species_id']
        assert history['area'] == 'Systemtest ' + row['expected']
        assert history['gps'] == {'lat': 52.5, 'lon': 13.4, 'acc': 0}
        assert len(history['matches']) == len(row['matches']) == 5
        for actual, frozen, saved in zip(row['matches'], reference['matches'], history['matches']):
            difference = abs(actual['probability'] - frozen['probability'])
            assert difference < 1e-6
            maximum = max(maximum, difference)
            assert abs(actual['score'] - frozen['similarity']) < 1e-6
            assert saved['scientific_name'] == actual['species']
            assert saved['probability'] == saved['confidence'] == actual['probability']
            assert saved['similarity'] == actual['score']
            assert saved['score_type'] == actual['score_type'] == 'calibrated_probability'
            assert saved['calibration_id'] == actual['calibration_id'] == calibration['id']
            assert saved['compared_species'] == 14 and saved['nRefs'] == actual['refs'] == 16
            assert saved['reference']['image_sha256'] == integrity['images'][saved['reference']['id']]
        cases += 1
report = {'pass': True, 'cases': cases, 'app_sha256': app_hash,
          'calibration_id': calibration['id'], 'rankings_equal': True,
          'max_probability_difference': maximum,
          'gps_confirmation_and_original_forecasts_persisted': True}
(ROOT / 'reports/system_calibration_consistency.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

# Frozen fingerprint of the accepted V3 markup/styles, with script blocks removed.
accepted = '1bbb105ad7e2ace2c15c2dd2f7e68513a61100c0b6e334edc90b937ba392e6ae'
markup = re.sub(r'<script\b[^>]*>.*?</script>', '', (ROOT / 'ribby_app.html').read_text(encoding='utf-8'), flags=re.S | re.I)
current = hashlib.sha256(markup.encode('utf-8')).hexdigest()
assert current == accepted, 'Static markup/styles changed from the accepted design'
design = {'pass': True, 'scope': 'Complete static HTML and CSS after removing scripts; dynamic score text/data updated',
          'before_sha256': accepted, 'after_sha256': current, 'app_sha256': app_hash}
(ROOT / 'reports/design_preservation_v4.json').write_text(json.dumps(design, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'cases': cases, 'max_probability_difference': maximum, 'static_design_unchanged': True}))
