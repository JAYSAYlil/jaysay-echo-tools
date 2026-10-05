"""Verify every upload asset before hand-over."""
import hashlib
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
pub = root / 'publish'
EXPECTED_JAR_SHA = 'FEF68695D80A2C46390CB4D3AE2F6B01C18A1FDEE0A4822E71B4C2219F951193'
problems = []

jar = root / 'jaysay-echo-tools-0.3.2.jar'
sha = hashlib.sha256(jar.read_bytes()).hexdigest().upper()
print('jar  %-34s %9d B  sha256 %s  %s' % (jar.name, jar.stat().st_size, sha, 'OK' if sha == EXPECTED_JAR_SHA else 'MISMATCH'))
if sha != EXPECTED_JAR_SHA:
    problems.append('jar hash')

def image(rel, expect=None, max_kb=None):
    p = pub / rel
    if not p.is_file():
        problems.append('missing ' + rel); print('  MISSING', rel); return
    with Image.open(p) as im:
        size = im.size
    kb = p.stat().st_size / 1024
    ok = (expect is None or size == expect) and (max_kb is None or kb <= max_kb)
    if not ok:
        problems.append(rel)
    print('img  %-44s %-10s %7.0f KB  %s' % (rel, '%dx%d' % size, kb, 'OK' if ok else 'BAD'))

print()
image('curseforge-icon-400.png', (400, 400))
image('modrinth-icon-256.png', (256, 256), 256)
image('logo-128.png', (128, 128))
for rel in sorted(p.name for p in (pub / 'modrinth/gallery').iterdir() if p.is_file()):
    image('modrinth/gallery/' + rel)
for rel in sorted(p.name for p in (pub / 'curseforge/gallery').iterdir() if p.is_file()):
    image('curseforge/gallery/' + rel)

print()
for rel in ['modrinth/body.md', 'modrinth/summary.txt', 'modrinth/meta.json',
            'curseforge/summary.txt', 'curseforge/description-en.md', 'curseforge/description-zh.md',
            'curseforge/changelog-0.3.2-en.md', 'curseforge/changelog-0.3.2-zh.md',
            'UPLOAD-GUIDE.md', 'PUBLISH-CHECKLIST.md']:
    p = pub / rel
    if p.is_file() and p.stat().st_size > 0:
        print('txt  %-44s %6d B  chars %d' % (rel, p.stat().st_size, len(p.read_text(encoding='utf-8'))))
    else:
        problems.append('missing ' + rel); print('txt  %-44s MISSING' % rel)

print()
print('PROBLEMS:', problems if problems else 'none')
