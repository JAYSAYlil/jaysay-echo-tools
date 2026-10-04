"""Hash-whitelisted v0.1.11 resource deployer. Default mode is read-only."""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'artwork/source/echo-pickaxe-sculk-bone-v0.1.11'
VAL = ROOT / 'artwork/validation/v0.1.11'
CANDIDATE = (VAL / 'candidate').resolve()
RESOURCE_ROOT = (ROOT / 'src/main/resources').resolve()
JAR = ROOT / 'jaysay-echo-tools-0.1.10.jar'
JAR_SHA = '24E7807050FDB26C2A1C21F6854E9F391F9DAF42E86DBA8AB05A59D0546D20C0'
MANIFEST = SRC / 'v0.1.11-candidate-manifest.json'
MANIFEST_SHA = '944B6837CC5085692E9D1DF05DBDAC8C0CE121AD7E109C07B8948952D30D74A6'
MAP = SRC / 'v0.1.11-resource-map.json'
MAP_SHA = 'BDE0DA7921BF3F070B2A6AD0DDD7F22440BA9B285A5C569CA3A9252ED48BF39E'


def sha(data): return hashlib.sha256(data).hexdigest().upper()


def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def assert_within(path, parent):
    resolved = path.resolve()
    try: resolved.relative_to(parent.resolve())
    except ValueError as error: raise RuntimeError(f'Path escaped approved root: {resolved}') from error
    return resolved


def snapshot_tree(root):
    return {p.relative_to(root).as_posix(): hash_file(p)
            for p in root.rglob('*') if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Write the 285 candidate assets into src/main/resources.')
    args = parser.parse_args()

    if CANDIDATE != (VAL / 'candidate').resolve(): raise RuntimeError('Candidate root path mismatch')
    if sha(MANIFEST.read_bytes()) != MANIFEST_SHA: raise RuntimeError('Frozen manifest SHA mismatch')
    if sha(MAP.read_bytes()) != MAP_SHA: raise RuntimeError('Frozen resource-map SHA mismatch')
    if sha(JAR.read_bytes()) != JAR_SHA: raise RuntimeError('Pinned 0.1.10 baseline JAR SHA mismatch')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('candidateRoot') != 'artwork/validation/v0.1.11/candidate':
        raise RuntimeError('Manifest candidateRoot does not match fixed path')
    if manifest.get('baselineJarSha256') != JAR_SHA or manifest.get('mapSha256') != MAP_SHA:
        raise RuntimeError('Manifest baseline/map identity mismatch')
    if manifest.get('upgradedIndices') != list(range(1,96)):
        raise RuntimeError('Only upgraded indices 001..095 may be in this deployment')

    resources = manifest.get('resources', [])
    expected = {(i,kind) for i in range(1,96) for kind in ('base','glow','model')}
    seen = set()
    with zipfile.ZipFile(JAR) as baseline:
        for item in resources:
            rel = item['path']
            pure = PurePosixPath(rel)
            if pure.is_absolute() or '..' in pure.parts: raise RuntimeError(f'Unsafe manifest path: {rel}')
            prefix = 'assets/echopickaxe/'
            if not rel.startswith(prefix): raise RuntimeError(f'Unexpected asset root: {rel}')
            name = pure.name
            kind = ('model' if pure.parts[2] == 'models' else
                    'glow' if name.endswith('_glow.png') else 'base')
            stem = pure.stem.removesuffix('_glow')
            if not stem.startswith('echo_pickaxe_v') or not stem[-3:].isdigit():
                raise RuntimeError(f'Unexpected candidate filename: {rel}')
            index = int(stem[-3:])
            key = (index,kind)
            if key not in expected or key in seen: raise RuntimeError(f'Unexpected or duplicate whitelist entry: {rel}')
            expected_rel = (f'assets/echopickaxe/models/item/echo_pickaxe_v{index:03d}.json' if kind == 'model'
                            else f'assets/echopickaxe/textures/item/echo_pickaxe_v{index:03d}' + ('_glow.png' if kind == 'glow' else '.png'))
            if rel != expected_rel: raise RuntimeError(f'Unexpected resource path: {rel}')
            seen.add(key)
            candidate_file = assert_within(CANDIDATE / Path(*pure.parts), CANDIDATE)
            destination = assert_within(RESOURCE_ROOT / Path(*pure.parts), RESOURCE_ROOT)
            candidate_hash = hash_file(candidate_file)
            if candidate_hash != item['sha256']: raise RuntimeError(f'Candidate SHA mismatch: {rel}')
            baseline_hash = sha(baseline.read(rel))
            if baseline_hash != item['baselineSha256']: raise RuntimeError(f'Manifest baseline hash mismatch: {rel}')
            if hash_file(destination) != baseline_hash: raise RuntimeError(f'Production baseline differs at {rel}')
    if seen != expected: raise RuntimeError(f'Whitelist incomplete: {len(seen)} of {len(expected)} resources')

    source_snapshot = snapshot_tree(RESOURCE_ROOT)
    mode = 'APPLY' if args.apply else 'READ-ONLY DRY RUN'
    print(f'PASS {mode}: 95 variants, 285 exact paths; production currently matches pinned 0.1.10 baseline.')
    print(f'candidate root: {CANDIDATE}')
    print(f'manifest: {MANIFEST_SHA}; map: {MAP_SHA}; baseline: {JAR_SHA}')
    if not args.apply:
        print('No files changed. Re-run with --apply only after release audit and explicit deployment authorization.')
        return

    allowed = {item['path']:item['sha256'] for item in resources}
    for rel, expected_hash in allowed.items():
        source = assert_within(CANDIDATE / Path(*PurePosixPath(rel).parts), CANDIDATE)
        target = assert_within(RESOURCE_ROOT / Path(*PurePosixPath(rel).parts), RESOURCE_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name+'.', suffix='.codex-tmp', delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(source.read_bytes())
        try:
            os.replace(temp_path, target)
        finally:
            if temp_path.exists(): temp_path.unlink()
        if hash_file(target) != expected_hash: raise RuntimeError(f'Post-copy SHA mismatch: {rel}')

    after = snapshot_tree(RESOURCE_ROOT)
    for rel, digest in source_snapshot.items():
        if rel not in allowed and after.get(rel) != digest:
            raise RuntimeError(f'Non-candidate resource changed: {rel}')
    if set(after) - set(source_snapshot): raise RuntimeError('Unexpected new resource appeared during apply')
    print(f'PASS applied {len(allowed)} candidate resources; all non-candidate resources retained prior hashes.')


if __name__ == '__main__': main()
