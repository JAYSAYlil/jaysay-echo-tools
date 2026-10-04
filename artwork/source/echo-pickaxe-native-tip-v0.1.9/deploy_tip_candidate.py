"""Preflight by default; apply only after independent audit and explicit authorization."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'artwork/validation/v0.1.9'
CANDIDATE = VAL / 'candidate'
MANIFEST = VAL / 'candidate-manifest-v0.1.9.json'
DEPLOYMENT_RECORD = VAL / 'deployment-hashes-v0.1.9.json'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.8.jar'
BASELINE_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
RESOURCE_ROOT = 'assets/echopickaxe/'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def allowed_paths():
    return {f'{RESOURCE_ROOT}{folder}/item/echo_pickaxe_v{i:03d}{suffix}'
            for i in range(1, 32)
            for folder, suffix in (('models', '.json'), ('textures', '.png'), ('textures', '_glow.png'))}


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
    parser.add_argument('--apply', action='store_true', help='write changed candidate files; unchanged glow files are never rewritten')
    args = parser.parse_args()
    if sha(BASELINE.read_bytes()) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.8 JAR SHA mismatch')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    records = manifest.get('resources', [])
    unchanged = manifest.get('unchanged', [])
    if manifest.get('baselineJarSha256') != BASELINE_SHA:
        raise RuntimeError('Candidate manifest baseline mismatch')
    if {r['path'] for r in records} | {r['path'] for r in unchanged} != allowed_paths():
        raise RuntimeError('Manifest is not the exact 93-resource res0 path set')
    if len(records) != 62 or len(unchanged) != 31:
        raise RuntimeError('Expected 62 changed model/base resources and 31 baseline-identical glow resources')

    staged, baseline_hashes = {}, {}
    with zipfile.ZipFile(BASELINE) as archive:
        for record in records:
            rel = record['path']
            data = (CANDIDATE / Path(*PurePosixPath(rel).parts)).read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise RuntimeError(f'Candidate hash mismatch: {rel}')
            baseline_data = archive.read(rel)
            if record.get('baselineSha256') != sha(baseline_data):
                raise RuntimeError(f'Recorded baseline hash mismatch: {rel}')
            target = destination_for(rel)
            if not target.is_file() or target.read_bytes() != baseline_data:
                raise RuntimeError(f'Production target is not exact pinned 0.1.8: {rel}')
            staged[rel] = data
            baseline_hashes[rel] = sha(baseline_data)
        for record in unchanged:
            rel = record['path']
            baseline_data = archive.read(rel)
            if record.get('status') != 'byte-identical-to-baseline' or record.get('sha256') != sha(baseline_data):
                raise RuntimeError(f'Unchanged-resource record mismatch: {rel}')
            target = destination_for(rel)
            if not target.is_file() or target.read_bytes() != baseline_data:
                raise RuntimeError(f'Production unchanged glow is not exact pinned 0.1.8: {rel}')
            baseline_hashes[rel] = sha(baseline_data)
    print('PASS preflight: 62 candidate hashes + 31 unchanged glow hashes match pinned 0.1.8; all 93 production targets are unchanged.')
    if not args.apply:
        print('Dry run only; source files were not written.')
        return

    temporary = {}
    try:
        for rel, data in staged.items():
            target = destination_for(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.v019-stage-', delete=False) as handle:
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
        for record in unchanged:
            rel = record['path']
            actual = destination_for(rel).read_bytes()
            if sha(actual) != record['sha256']:
                raise RuntimeError(f'Unchanged glow bytes unexpectedly differ: {rel}')
    finally:
        for path in temporary.values():
            if path.exists():
                path.unlink()

    deploy_record = {
        'schema': 1,
        'version': '0.1.9-native64-tip-sharpening',
        'status': 'deployed-candidate-hashes-verified',
        'baselineJar': BASELINE.name, 'baselineJarSha256': BASELINE_SHA,
        'manifestSha256': sha(MANIFEST.read_bytes()),
        'allowedResourceCount': len(allowed_paths()), 'writtenResourceCount': len(deployed),
        'unchangedGlowCount': len(unchanged), 'baselineSha256ByPath': baseline_hashes,
        'deployed': sorted(deployed, key=lambda r: r['path']),
        'unchanged': unchanged,
    }
    DEPLOYMENT_RECORD.write_text(json.dumps(deploy_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Applied and verified {len(deployed)} changed resources; deployment record: {DEPLOYMENT_RECORD}')


if __name__ == '__main__':
    main()
