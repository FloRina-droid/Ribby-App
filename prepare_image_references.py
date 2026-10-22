"""Prepare a licensed, diverse reference collection without an AI service key.

Run separately from the server. The normal app also fetches references on demand.
"""
import argparse
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import ribby_images as images


def prepare(data_dir, catalog, download=True, refresh=False):
    summary = []
    for index, species in enumerate(catalog):
        result = images.reference_photos(data_dir, species, force=refresh)
        refs, failures = result['references'], []
        if download:
            with ThreadPoolExecutor(max_workers=3) as pool:
                tasks = {pool.submit(images.reference_file, data_dir, ref['id']): ref for ref in refs}
                for task in as_completed(tasks):
                    try:
                        task.result()
                    except Exception as error:
                        failures.append({'id': tasks[task]['id'], 'error': str(error)})
        row = {'species_id': species['id'], 'scientific_name': species['sci'], 'name_de': species.get('name_de'),
               'references': len(refs), 'downloaded': len(refs)-len(failures) if download else 0,
               'creators': result.get('creators', 0), 'sources': {source: sum(r['provider']==source for r in refs)
                for source in sorted({r['provider'] for r in refs})}, 'failures': failures, 'warnings': result['warnings']}
        summary.append(row)
        print(json.dumps({'index': index+1, 'total': len(catalog), **row}, ensure_ascii=False), flush=True)
    report = {'prepared_at': time.time(), 'cache_version': images.CACHE_VERSION, 'species': summary,
              'total_references': sum(s['references'] for s in summary),
              'total_downloaded': sum(s['downloaded'] for s in summary)}
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    (Path(data_dir)/'image_reference_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent/'ribby_data')
    parser.add_argument('--species-file', type=Path, help='JSON list of species; defaults to DATA_DIR/species/*.json')
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--refresh', action='store_true', help='Refresh search metadata before the cache expires')
    args = parser.parse_args()
    catalog = (json.loads(args.species_file.read_text(encoding='utf-8')) if args.species_file else
               [json.loads(p.read_text(encoding='utf-8')) for p in (args.data_dir/'species').glob('*.json')])
    if not catalog:
        parser.error('Kein Artenkatalog gefunden. --species-file oder --data-dir angeben.')
    prepare(args.data_dir, catalog, download=not args.metadata_only, refresh=args.refresh)
