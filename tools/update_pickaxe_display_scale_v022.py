from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'jaysay-echo-tools-0.2.1.jar'
BASELINE_SHA256 = 'DB6D39B23F2DE75565A6732415050F22D0C5CD5F08D21A2423A88526F1DEB9A1'
MODEL_DIR = ROOT / 'src/main/resources/assets/echopickaxe/models/item'
AUDIT = ROOT / 'artwork/validation/v0.2.2/model-scale-audit.json'
VIEWS = {
    'firstperson_righthand': ('0.816', '0.918'),
    'firstperson_lefthand': ('0.816', '0.918'),
    'thirdperson_righthand': ('1.02', '1.275'),
    'thirdperson_lefthand': ('1.02', '1.275'),
}
NUMBER = r'-?(?:\d+(?:\.\d*)?|\.\d+)'
SCALE_RE = re.compile(r'("scale"\s*:\s*\[)(\s*' + NUMBER + r'(\s*,\s*)' + NUMBER + r'(\s*,\s*)' + NUMBER + r'\s*)(\])')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def files() -> list[Path]:
    return [MODEL_DIR / 'echo_pickaxe.json'] + [MODEL_DIR / f'echo_pickaxe_v{i:03d}.json' for i in range(1, 96)]


def object_bounds(text: str, key: str) -> tuple[int, int]:
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*\{', text)
    if not match:
        raise ValueError(f'missing display transform: {key}')
    start = text.find('{', match.start())
    depth = 0
    quoted = escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise ValueError(f'unclosed display transform: {key}')


def modify_text(text: str, allow_old: bool) -> tuple[str, dict[str, bool]]:
    changes: dict[str, bool] = {}
    for key, (old, new) in VIEWS.items():
        start, end = object_bounds(text, key)
        segment = text[start:end]
        matches = list(SCALE_RE.finditer(segment))
        if len(matches) != 1:
            raise ValueError(f'{key}: expected one scale array, got {len(matches)}')
        m = matches[0]
        values = re.findall(NUMBER, m.group(2))
        if values == [new, new, new]:
            changes[key] = False
            continue
        if values != [old, old, old] or not allow_old:
            raise ValueError(f'{key}: unexpected scale {values}')
        vector = re.sub(NUMBER, lambda match: new, m.group(2))
        updated = segment[:m.start(2)] + vector + segment[m.end(2):]
        text = text[:start] + updated + text[end:]
        changes[key] = True
    return text, changes


def expected_model(model: dict) -> dict:
    result = copy.deepcopy(model)
    for key, (_, new) in VIEWS.items():
        result['display'][key]['scale'] = [float(new)] * 3
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Set the four hand-held Echo Pickaxe display scales to the pinned v0.2.2 values.')
    parser.add_argument('--apply', action='store_true', help='apply exact scale substitutions before auditing')
    parser.add_argument('--audit', type=Path, default=AUDIT)
    args = parser.parse_args()
    if not BASELINE.is_file() or sha(BASELINE.read_bytes()) != BASELINE_SHA256:
        raise SystemExit('pinned 0.2.1 baseline JAR is missing or has the wrong SHA-256')
    model_files = files()
    missing = [str(p) for p in model_files if not p.is_file()]
    if missing:
        raise SystemExit(f'missing model file(s): {missing}')
    results = []
    with zipfile.ZipFile(BASELINE) as jar:
        for path in model_files:
            name = f'assets/echopickaxe/models/item/{path.name}'
            before = jar.read(name)
            original_model = json.loads(before)
            current = path.read_bytes()
            if args.apply:
                text, _ = modify_text(current.decode('utf-8'), allow_old=True)
                current = text.encode('utf-8')
                path.write_bytes(current)
            text = current.decode('utf-8')
            audited_text, changes = modify_text(text, allow_old=False)
            after_model = json.loads(audited_text)
            if after_model != expected_model(original_model):
                raise SystemExit(f'{path.name}: non-target JSON data differs from pinned 0.2.0')
            if audited_text.encode('utf-8') != current:
                raise SystemExit(f'{path.name}: model text is not in the expected final state')
            results.append({'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                            'baselineSha256': sha(before), 'releaseSha256': sha(current),
                            'fourHandTransformsUpdated': True,
                            'onlyExpectedDisplayScalesDiffer': True,
                            'guiPresent': 'gui' in after_model.get('display', {})})
    report = {'baselineJar': BASELINE.name, 'baselineJarSha256': BASELINE_SHA256,
              'modelCount': len(results), 'updatedModelCount': len(results),
              'changedScalarCount': len(results) * 12,
              'firstPersonScale': [0.918, 0.918, 0.918],
              'thirdPersonScale': [1.275, 1.275, 1.275],
              'rotationTranslationAndOtherDisplayDataPreserved': True,
              'geometryUvTextureAndElementDataPreserved': True,
              'eachModelOnlyDiffersAtTheFourHandScaleArrays': True,
              'models': results}
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('modelCount','updatedModelCount','changedScalarCount',
              'rotationTranslationAndOtherDisplayDataPreserved','geometryUvTextureAndElementDataPreserved',
              'eachModelOnlyDiffersAtTheFourHandScaleArrays')}, indent=2))

if __name__ == '__main__':
    main()
