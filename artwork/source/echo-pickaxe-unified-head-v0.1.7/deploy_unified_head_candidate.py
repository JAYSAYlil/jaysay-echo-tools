"""Preflight/deploy the audited v0.1.7 res0 candidate; never writes without --apply."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'artwork/validation/v0.1.7'
CANDIDATE = VAL / 'candidate'
MANIFEST = VAL / 'candidate-manifest-v0.1.7.json'
DEPLOYMENT_RECORD = VAL / 'deployment-hashes-v0.1.7.json'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.6.jar'
BASELINE_SHA = 'AE44F1DD5D70562301AFE5DAB55B56F4E07ED1291F4FC8A00E0A400C0697A8C4'
RESOURCE_ROOT = 'assets/echopickaxe/'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def allowed_paths():
    result = set()
    for index in range(1, 32):
        item = f'echo_pickaxe_v{index:03d}'
        result.update({
            f'{RESOURCE_ROOT}models/item/{item}.json',
            f'{RESOURCE_ROOT}textures/item/{item}.png',
            f'{RESOURCE_ROOT}textures/item/{item}_glow.png',
        })
    return result


def destination_for(relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative or not relative.startswith(RESOURCE_ROOT):
        raise RuntimeError(f'Unsafe candidate path: {relative}')
    resources = (ROOT / 'src/main/resources').resolve()
    destination = (resources / Path(*rel.parts)).resolve()
    if resources not in destination.parents:
        raise RuntimeError(f'Destination escaped resources directory: {destination}')
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='write candidate bytes after independent audit and explicit authorization')
    args = parser.parse_args()
    if sha(BASELINE.read_bytes()) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.6 baseline JAR SHA mismatch')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    records = manifest.get('resources', [])
    if manifest.get('baselineJarSha256') != BASELINE_SHA or len(records) != 93:
        raise RuntimeError('Candidate manifest baseline or resource count mismatch')
    if {r['path'] for r in records} != allowed_paths():
        raise RuntimeError('Candidate manifest is not the exact 93-resource res0 set')

    staged = {}
    baseline_hashes = {}
    with zipfile.ZipFile(BASELINE) as archive:
        for record in records:
            rel = record['path']
            data = (CANDIDATE / Path(*PurePosixPath(rel).parts)).read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise RuntimeError(f'Candidate manifest hash mismatch: {rel}')
            baseline_data = archive.read(rel)
            target = destination_for(rel)
            if not target.is_file() or target.read_bytes() != baseline_data:
                raise RuntimeError(f'Production target is not exact pinned 0.1.6: {rel}')
            staged[rel] = data
            baseline_hashes[rel] = sha(baseline_data)
    print(f'PASS deployment preflight: 93 candidate hashes and all source targets match pinned 0.1.6; no files changed.')
    if not args.apply:
        print('Dry run only. Deployment requires independent audit and explicit authorization.')
        return

    temporary = {}
    try:
        for rel, data in staged.items():
            target = destination_for(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.v017-stage-', delete=False) as handle:
                handle.write(data)
                temporary[rel] = Path(handle.name)
        for rel, path in temporary.items():
            os.replace(path, destination_for(rel))
        deployed = []
        for rel, data in staged.items():
            actual = destination_for(rel).read_bytes()
            if actual != data:
                raise RuntimeError(f'Deployed bytes differ from candidate: {rel}')
            deployed.append({'path': rel, 'sha256': sha(actual), 'bytes': len(actual)})
    finally:
        for path in temporary.values():
            if path.exists():
                path.unlink()
    record = {
        'schema': 1,
        'version': '0.1.7-shaft-matched-native64-res0',
        'status': 'deployed-candidate-hashes-verified',
        'baselineJar': BASELINE.name,
        'baselineJarSha256': BASELINE_SHA,
        'candidateManifestSha256': sha(MANIFEST.read_bytes()),
        'count': len(deployed),
        'baselineSha256ByPath': baseline_hashes,
        'deployed': sorted(deployed, key=lambda r: r['path']),
    }
    DEPLOYMENT_RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Deployment completed and verified {len(deployed)} resource hashes; record: {DEPLOYMENT_RECORD}')


if __name__ == '__main__':
    main()
