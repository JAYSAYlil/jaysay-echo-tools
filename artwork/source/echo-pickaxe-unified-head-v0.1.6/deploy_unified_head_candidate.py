"""Deploy the pinned, independently audited v0.1.6 res0 assets.

Default operation is read-only validation. Production files are written only
when the caller explicitly supplies --apply after root authorization.
"""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'artwork/validation/v0.1.6'
CANDIDATE = VAL / 'candidate'
MANIFEST = VAL / 'candidate-manifest-v0.1.6.json'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.5.jar'
BASELINE_SHA = 'CDDEE165380BA810B4C874F0E34C85645B85D8BEBE4D2EF72E1C00EF58DA8706'
RESOURCE_ROOT = 'assets/echopickaxe/'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def allowed_paths():
    paths = set()
    for index in range(1, 32):
        name = f'echo_pickaxe_v{index:03d}'
        paths.update({
            f'{RESOURCE_ROOT}models/item/{name}.json',
            f'{RESOURCE_ROOT}textures/item/{name}.png',
            f'{RESOURCE_ROOT}textures/item/{name}_glow.png',
        })
    return paths


def safe_destination(relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative or not relative.startswith(RESOURCE_ROOT):
        raise RuntimeError(f'Unsafe candidate path: {relative}')
    destination = (ROOT / 'src/main/resources' / Path(*rel.parts)).resolve()
    resource_root = (ROOT / 'src/main/resources').resolve()
    if resource_root not in destination.parents:
        raise RuntimeError(f'Destination escaped resources directory: {destination}')
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='write the prevalidated 93 resources into src')
    args = parser.parse_args()

    if sha(BASELINE.read_bytes()) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.5 baseline JAR SHA mismatch')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('baselineJarSha256') != BASELINE_SHA or manifest.get('candidateResourceCount') != 93:
        raise RuntimeError('Candidate manifest baseline or resource count mismatch')
    records = manifest.get('resources', [])
    if len(records) != 93 or {item['path'] for item in records} != allowed_paths():
        raise RuntimeError('Candidate manifest does not contain the exact 93 allowed res0 paths')

    staged, baseline_entries = {}, {}
    with zipfile.ZipFile(BASELINE) as archive:
        for record in records:
            rel = record['path']
            source = CANDIDATE / Path(*PurePosixPath(rel).parts)
            data = source.read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise RuntimeError(f'Candidate hash/length mismatch: {rel}')
            baseline_data = archive.read(rel)
            if not baseline_data:
                raise RuntimeError(f'Pinned baseline missing resource: {rel}')
            destination = safe_destination(rel)
            if not destination.is_file() or destination.read_bytes() != baseline_data:
                raise RuntimeError(f'Production source is not the exact 0.1.5 baseline: {rel}')
            staged[rel] = data
            baseline_entries[rel] = sha(baseline_data)

    print(f'PASS deployment preflight: exactly {len(staged)} candidate assets; every candidate hash matches manifest; every src target matches pinned 0.1.5.')
    if not args.apply:
        print('Dry run only. No src files changed; rerun with --apply only after root authorization.')
        return

    temporary = {}
    try:
        for rel, data in staged.items():
            destination = safe_destination(rel)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.v016-stage-', delete=False) as handle:
                handle.write(data)
                temporary[rel] = Path(handle.name)
        for rel, temp_path in temporary.items():
            os.replace(temp_path, safe_destination(rel))
        result = []
        for record in records:
            destination = safe_destination(record['path'])
            data = destination.read_bytes()
            if sha(data) != record['sha256']:
                raise RuntimeError(f'Deployed hash mismatch: {record["path"]}')
            result.append({'path': record['path'], 'sha256': sha(data), 'bytes': len(data)})
    finally:
        for path in temporary.values():
            if path.exists():
                path.unlink()

    deployment = {
        'schema': 1,
        'version': '0.1.6-unified-head',
        'status': 'deployed-candidate-hashes-verified',
        'baselineJarSha256': BASELINE_SHA,
        'candidateManifestSha256': sha(MANIFEST.read_bytes()),
        'count': len(result),
        'baselineSha256ByPath': baseline_entries,
        'deployed': result,
    }
    (VAL / 'deployment-hashes-v0.1.6.json').write_text(json.dumps(deployment, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS deployed and verified {len(result)} resource SHA-256 values; hashes saved to {VAL / "deployment-hashes-v0.1.6.json"}')


if __name__ == '__main__':
    main()
