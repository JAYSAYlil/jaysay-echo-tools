"""Read-only preflight by default; --apply copies only manifest-listed changed upgrade resources."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'artwork/validation/v0.1.10'
CANDIDATE = VAL / 'refined-ends-candidate'
MANIFEST = CANDIDATE / 'candidate-manifest-v0.1.10.json'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.9.jar'
BASELINE_SHA = 'BB7136E6B343E7371A161E3A6D27A9A81311F9850C54FA0C6DA41FB17FA430B6'
SOURCE_PREFIX = 'assets/echopickaxe/'
EXPECTED_INDICES = tuple(range(1, 96))
RESOURCE_ROOT = (ROOT / 'src/main/resources').resolve()


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def expected_paths():
    return {f'{SOURCE_PREFIX}{folder}/item/echo_pickaxe_v{i:03d}{suffix}'
            for i in EXPECTED_INDICES
            for folder, suffix in (('models', '.json'), ('textures', '.png'), ('textures', '_glow.png'))}


def safe_source_path(relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative or not relative.startswith(SOURCE_PREFIX):
        raise RuntimeError(f'Unsafe candidate path: {relative}')
    target = (RESOURCE_ROOT / Path(*rel.parts)).resolve()
    if RESOURCE_ROOT not in target.parents:
        raise RuntimeError(f'Destination escaped src/main/resources: {target}')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write changed manifest-listed resources into src/main/resources')
    args = parser.parse_args()
    baseline_data = BASELINE.read_bytes()
    if sha(baseline_data) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.9 JAR SHA mismatch')
    manifest_data = MANIFEST.read_bytes()
    manifest = json.loads(manifest_data.decode('utf-8'))
    if manifest.get('baselineJarSha256') != BASELINE_SHA:
        raise RuntimeError('Candidate baseline SHA mismatch')
    resources = manifest.get('resources', [])
    unchanged = manifest.get('unchanged', [])
    all_records = resources + unchanged
    if manifest.get('editedIndices') != list(EXPECTED_INDICES):
        raise RuntimeError('Candidate does not cover exactly upgraded indices 001..095')
    if manifest.get('allowedResourceCount') != len(expected_paths()):
        raise RuntimeError('Manifest allowed path count mismatch')
    if {r['path'] for r in all_records} != expected_paths() or len(all_records) != len(expected_paths()):
        raise RuntimeError('Manifest paths are not exactly the declared upgraded model/base/glow resources')
    if any(Path(r['path']).name in {'echo_pickaxe.png', 'echo_pickaxe_glow.png', 'echo_pickaxe.json'} for r in all_records):
        raise RuntimeError('Ordinary item resources must not be included')

    staged = {}
    with zipfile.ZipFile(BASELINE) as archive:
        for record in resources:
            rel = record['path']
            data = (CANDIDATE / Path(*PurePosixPath(rel).parts)).read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise RuntimeError(f'Candidate SHA mismatch: {rel}')
            old = archive.read(rel)
            if record.get('baselineSha256') != sha(old):
                raise RuntimeError(f'Baseline SHA mismatch in manifest: {rel}')
            target = safe_source_path(rel)
            if not target.is_file() or target.read_bytes() != old:
                raise RuntimeError(f'Production source is not exact pinned 0.1.9: {rel}')
            staged[rel] = data
        for record in unchanged:
            rel = record['path']
            old = archive.read(rel)
            target = safe_source_path(rel)
            if record.get('sha256') != sha(old) or record.get('status') != 'byte-identical-to-pinned-0.1.9':
                raise RuntimeError(f'Unchanged-resource record mismatch: {rel}')
            if not target.is_file() or target.read_bytes() != old:
                raise RuntimeError(f'Production source is not exact pinned 0.1.9: {rel}')

    print(f'PASS read-only preflight: {len(resources)} candidate resources and {len(unchanged)} baseline-identical paths match pinned 0.1.9.')
    print(f'All {len(expected_paths())} production paths remain byte-identical to 0.1.9; ordinary resources are excluded.')
    if not args.apply:
        print('Read-only mode; src/main/resources was not changed.')
        return

    temp_paths = {}
    try:
        for rel, data in staged.items():
            target = safe_source_path(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.ends-v010-stage-', delete=False) as handle:
                handle.write(data)
                temp_paths[rel] = Path(handle.name)
        for rel, temp in temp_paths.items():
            os.replace(temp, safe_source_path(rel))
        for rel, data in staged.items():
            if safe_source_path(rel).read_bytes() != data:
                raise RuntimeError(f'Post-write candidate mismatch: {rel}')
    finally:
        for temp in temp_paths.values():
            if temp.exists():
                temp.unlink()
    print(f'Applied and SHA-verified {len(staged)} candidate resources.')


if __name__ == '__main__':
    main()
