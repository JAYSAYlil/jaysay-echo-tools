"""Version-independent release audit: metadata, structure, packaged resources vs source."""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
props = {}
for line in (root / 'gradle.properties').read_text(encoding='utf-8').splitlines():
    if '=' in line and line.strip().startswith('mod_'):
        key, value = line.split('=', 1)
        props[key.strip()] = value.strip()
version = props['mod_version']
archive = props['mod_archive_name']
modid = props['mod_id']
name = '%s-%s.jar' % (archive, version)

root_jar = root / name
build_jar = root / 'build' / 'libs' / name
src = root / 'src/main/resources'
failures = []


def check(ok, message):
    print(('PASS: ' if ok else 'FAIL: ') + message)
    if not ok:
        failures.append(message)


check(root_jar.is_file(), 'root jar exists: ' + name)
check(build_jar.is_file(), 'build/libs jar exists: ' + name)
if root_jar.is_file() and build_jar.is_file():
    check(root_jar.read_bytes() == build_jar.read_bytes(), 'root and build/libs jars are byte-identical')

if root_jar.is_file():
    with zipfile.ZipFile(root_jar) as z:
        names = [n for n in z.namelist() if not n.endswith('/')]
        mods = z.read('META-INF/mods.toml').decode('utf-8')
        check('version="%s"' % version in mods, 'mods.toml declares version ' + version)
        check('modId="%s"' % modid in mods, 'mods.toml declares modId ' + modid)
        manifest = z.read('META-INF/MANIFEST.MF').decode('utf-8')
        check('Implementation-Version: ' + version in manifest, 'MANIFEST keeps Implementation-Version')
        check('Automatic-Module-Name: ' + modid in manifest, 'MANIFEST keeps Automatic-Module-Name')

        # META-INF/mods.toml and pack.mcmeta are expanded by processResources, so they
        # are validated by their parsed metadata rather than by byte identity.
        packaged = [n for n in names if n.startswith(('assets/', 'data/'))]
        missing = [n for n in packaged if not (src / n).is_file()]
        check(not missing, 'every packaged asset/data entry exists in src/main/resources')
        mismatched = [n for n in packaged if (src / n).is_file() and z.read(n) != (src / n).read_bytes()]
        check(not mismatched, '%d packaged assets/data match src/main/resources byte-for-byte' % len(packaged))

        logo = re.search(r'logoFile\s*=\s*"([^"]+)"', mods)
        check(bool(logo), 'mods.toml declares a logoFile')
        if logo:
            check(logo.group(1) in names, 'declared logo is packaged: ' + logo.group(1))
        check('displayURL="' in mods and 'issueTrackerURL="' in mods, 'mods.toml declares project URLs')

        structured = [n for n in names if n.endswith(('.json', '.mcmeta'))]
        bad = []
        for n in structured:
            try:
                json.loads(z.read(n))
            except Exception as exc:
                bad.append('%s: %s' % (n, exc))
        check(not bad, '%d json/mcmeta entries parse' % len(structured))

        classes = [n for n in names if n.endswith('.class')]
        print('INFO: entries=%d classes=%d bytes=%d sha256=%s'
              % (len(names), len(classes), root_jar.stat().st_size,
                 hashlib.sha256(root_jar.read_bytes()).hexdigest().upper()))

print()
if failures:
    print('AUDIT FAILED (%d problem(s))' % len(failures))
    sys.exit(1)
print('AUDIT PASSED')
