"""Verify by default; --apply writes the frozen candidate after external audit."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'artwork/validation/v0.1.9'
CANDIDATE = VAL / 'refined-ends-candidate'
MANIFEST = CANDIDATE / 'candidate-manifest-v0.1.9.json'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.8.jar'
BASELINE_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
SOURCE_PREFIX = 'assets/echopickaxe/'
EXPECTED_INDICES = tuple(sorted(set(range(1, 32)) | set(range(4, 32, 4)) | set(range(32, 96, 4))))
RESOURCE_ROOT = (ROOT / 'src/main/resources').resolve()


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def safe_source_path(relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative or not relative.startswith(SOURCE_PREFIX):
        raise RuntimeError(f'Unsafe candidate path: {relative}')
    destination = (RESOURCE_ROOT / Path(*rel.parts)).resolve()
    if RESOURCE_ROOT not in destination.parents:
        raise RuntimeError(f'Destination escaped src/main/resources: {destination}')
    return destination


def expected_paths():
    return {f'{SOURCE_PREFIX}{folder}/item/echo_pickaxe_v{i:03d}{suffix}'
            for i in EXPECTED_INDICES
            for folder, suffix in (('models', '.json'), ('textures', '.png'), ('textures', '_glow.png'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write validated changed files to src/main/resources')
    args = parser.parse_args()
    baseline_bytes = BASELINE.read_bytes()
    if sha(baseline_bytes) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.8 JAR SHA mismatch')
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    if manifest.get('baselineJarSha256') != BASELINE_SHA:
        raise RuntimeError('Candidate manifest baseline mismatch')
    records, unchanged = manifest.get('resources', []), manifest.get('unchanged', [])
    all_records = records + unchanged
    if manifest.get('editedIndices') != list(EXPECTED_INDICES):
        raise RuntimeError('Candidate index scope is not the declared hook + ext0 set')
    if {r['path'] for r in all_records} != expected_paths() or len(all_records) != len(expected_paths()):
        raise RuntimeError('Manifest path set is not exactly the 141 declared resources')

    staged = {}
    with zipfile.ZipFile(BASELINE) as archive:
        for record in records:
            relative = record['path']
            candidate_file = CANDIDATE / Path(*PurePosixPath(relative).parts)
            data = candidate_file.read_bytes()
            if len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise RuntimeError(f'Candidate hash mismatch: {relative}')
            old = archive.read(relative)
            if record.get('baselineSha256') != sha(old):
                raise RuntimeError(f'Baseline hash mismatch in manifest: {relative}')
            target = safe_source_path(relative)
            if not target.is_file() or target.read_bytes() != old:
                raise RuntimeError(f'Production source is not still exact pinned 0.1.8: {relative}')
            staged[relative] = data
        for record in unchanged:
            relative = record['path']
            old = archive.read(relative)
            target = safe_source_path(relative)
            if record.get('sha256') != sha(old) or record.get('status') != 'byte-identical-to-pinned-0.1.8':
                raise RuntimeError(f'Unchanged-resource record mismatch: {relative}')
            if not target.is_file() or target.read_bytes() != old:
                raise RuntimeError(f'Production source differs from 0.1.8: {relative}')

    print(f'PASS preflight: {len(records)} candidate hashes + {len(unchanged)} baseline-identical paths match pinned 0.1.8.')
    print(f'All {len(expected_paths())} production paths are still byte-identical to the 0.1.8 source baseline.')
    if not args.apply:
        print('Read-only mode; src/main/resources was not changed.')
        return

    temp_paths = {}
    try:
        for relative, data in staged.items():
            target = safe_source_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.refined-ends-stage-', delete=False) as handle:
                handle.write(data)
                temp_paths[relative] = Path(handle.name)
        for relative, temporary in temp_paths.items():
            os.replace(temporary, safe_source_path(relative))
        for relative, data in staged.items():
            if safe_source_path(relative).read_bytes() != data:
                raise RuntimeError(f'Post-write candidate mismatch: {relative}')
    finally:
        for temporary in temp_paths.values():
            if temporary.exists():
                temporary.unlink()
    print(f'Applied and verified {len(staged)} changed resources. No deployment record is written by this draft helper.')


if __name__ == '__main__':
    main()
