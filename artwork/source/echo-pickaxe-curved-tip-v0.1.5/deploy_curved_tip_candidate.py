"""Verify and deploy the reviewed 0.1.5 resource candidate.

Dry-run by default. Use --apply only after the independent resource audit and
root's deployment authorization both pass.
"""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/main/resources'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.4.jar'
BASELINE_SHA = '9A3D6C0D9B5485C397117CBF00C00C31DA04A339838831231EC5C31B552D67AF'
ORDINARY = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
CANDIDATE = ROOT / 'artwork/validation/v0.1.5/curved-tip-candidate'
MANIFEST = CANDIDATE / 'curved-tip-candidate.json'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='copy the audited candidate into src/main/resources')
    args = parser.parse_args()
    assert sha(BASELINE.read_bytes()) == BASELINE_SHA, '0.1.4 baseline JAR SHA mismatch'
    assert sha(ORDINARY.read_bytes()) == ORDINARY_SHA, '0.1.2 ordinary JAR SHA mismatch'
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest.get('status') == 'root-approved-candidate'
    assert manifest.get('baselineJarSha256') == BASELINE_SHA
    assert manifest.get('ordinaryJarSha256') == ORDINARY_SHA
    assert manifest.get('candidateResourceCount') == 97
    rows = manifest.get('resources', [])
    assert len(rows) == 97 and len({row['path'] for row in rows}) == 97

    with zipfile.ZipFile(BASELINE) as jar:
        allowed = {name for name in jar.namelist()
                   if name.startswith('assets/echopickaxe/') and
                   (name in {f'assets/echopickaxe/models/item/echo_pickaxe.json',
                             f'assets/echopickaxe/textures/item/echo_pickaxe.png',
                             f'assets/echopickaxe/textures/item/echo_pickaxe_glow.png',
                             f'assets/echopickaxe/textures/item/echo_pickaxe_glow.png.mcmeta'} or
                    any(name == f'assets/echopickaxe/{folder}/{item}{suffix}'
                        for i in range(1,32) if (i % 32) < 32 and i > 0
                        for item in [f'echo_pickaxe_v{i:03d}']
                        for folder,suffix in [('models/item','.json'),('textures/item','.png'),('textures/item','_glow.png')]))}
        # The manifest itself is authoritative for resource rows; this guard
        # enforces exact paths in the four-base + 31-res0 contract.
        expected = {
            'assets/echopickaxe/models/item/echo_pickaxe.json',
            'assets/echopickaxe/textures/item/echo_pickaxe.png',
            'assets/echopickaxe/textures/item/echo_pickaxe_glow.png',
            'assets/echopickaxe/textures/item/echo_pickaxe_glow.png.mcmeta'}
        for i in range(1,32):
            item=f'echo_pickaxe_v{i:03d}'
            expected.update({f'assets/echopickaxe/models/item/{item}.json',
                             f'assets/echopickaxe/textures/item/{item}.png',
                             f'assets/echopickaxe/textures/item/{item}_glow.png'})
        assert allowed == expected, 'resource contract does not match 4 base + 31 res0 paths'
        assert {row['path'] for row in rows} == expected, 'candidate path set differs from 97-resource allowlist'

        staged = []
        for row in rows:
            rel = Path(row['path'])
            target = SOURCE / rel
            candidate_file = CANDIDATE / rel
            assert inside(target, SOURCE) and inside(candidate_file, CANDIDATE), f'path escapes workspace: {rel}'
            before = jar.read(row['path'])
            assert target.is_file() and target.read_bytes() == before, f'source is not exact 0.1.4 baseline: {rel}'
            data = candidate_file.read_bytes()
            assert len(data) == row['bytes'] and sha(data) == row['sha256'], f'candidate hash mismatch: {rel}'
            staged.append((target, data, row['sha256']))

    if not args.apply:
        print(f'PASS dry-run: {len(staged)} candidate files verified; src remains exact 0.1.4.')
        print('Deployment not performed. Re-run with --apply only after audit and root authorization.')
        return

    for target, data, expected_sha in staged:
        fd, temp_name = tempfile.mkstemp(prefix=target.name + '.', suffix='.tmp', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            os.replace(temp_name, target)
        except Exception:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise
    for target, _, expected_sha in staged:
        assert sha(target.read_bytes()) == expected_sha, f'deployed hash mismatch: {target}'
    print(f'PASS deployed and verified {len(staged)} resource files by manifest SHA-256.')


if __name__ == '__main__':
    main()
