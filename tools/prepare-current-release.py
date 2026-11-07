"""Compose accepted binary recipes over the signed 0.1.45 release, without compiling engine code.

Outputs an unsigned ZIP payload for signing by build.ps1. Only original game
files, this project's recipes and its published baseline package are inputs.
"""
import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_HASH = '80c2f73bbc9b76df4e0afae1c2af6cb5d43c6326187449aeee945a1102cd4497'
ENGINE_HASH = '0d6e29bdfb3d2d9d35c21cb0cdf36f7a50aee3a7783e2f9af991523d654452ab'
DATA_HASH = 'a77c9e980635847f24d380e3abc227203d1c660f6f7c62026505b7458d257232'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def number(v):
    return int(v, 0) if isinstance(v, str) else v

def signed_baseline(path):
    raw = path.read_bytes()
    assert sha(raw) == BASE_HASH and raw[:8] == b'S2UBPKG1'
    size = struct.unpack_from('<I', raw, 8)[0]
    signature, payload = raw[12:12+size], raw[12+size:]
    key = ET.fromstring((ROOT/'installer/recovered/publicKey').read_bytes())
    integer = lambda field: int.from_bytes(base64.b64decode(key.findtext(field)), 'big')
    decoded = pow(int.from_bytes(signature, 'big'), integer('Exponent'), integer('Modulus')).to_bytes(size, 'big')
    digest = bytes.fromhex('3031300d060960864801650304020105000420') + hashlib.sha256(payload).digest()
    assert decoded == b'\x00\x01' + b'\xff'*(size-len(digest)-3) + b'\x00' + digest
    return zipfile.ZipFile(io.BytesIO(payload))

def apply_spec(original, spec):
    assert sha(original) == spec['sourceSha256']
    result = bytearray(spec['length'])
    result[:min(len(original), len(result))] = original[:len(result)]
    for w in spec['writes']:
        data = base64.b64decode(w['data']); offset = w['offset']
        assert 0 <= offset <= len(result)-len(data)
        result[offset:offset+len(data)] = data
    assert sha(result) == spec['sha256']
    return result

def apply_recipe(image, recipe):
    expected_hash = recipe.get('inputSha256', recipe['sourceSha256'])
    assert sha(image) == expected_hash, recipe['id']
    before = bytes(image)
    for w in recipe['writes']:
        assert 'offset' in w, 'Local overlay must use resolved file offsets'
        at = number(w['offset']); expected = bytes.fromhex(w['expect']); data = bytes.fromhex(w['bytes'])
        assert len(expected) == len(data) and before[at:at+len(expected)] == expected
        image[at:at+len(data)] = data
    if 'append' in recipe:
        assert len(image) == number(recipe['append']['offset'])
        image.extend(bytes.fromhex(recipe['append']['bytes']))
    if 'sha256' in recipe:
        assert sha(image) == recipe['sha256']
    return image

def engine_spec(original, image, baseline):
    spec = {k: copy.deepcopy(v) for k, v in baseline.items() if k != 'writes'}
    spec.update(length=len(image), sha256=sha(image), writes=[])
    i = 0
    while i < min(len(original), len(image)):
        if original[i] == image[i]:
            i += 1
            continue
        start = i
        while i < min(len(original), len(image)) and original[i] != image[i]:
            i += 1
        spec['writes'].append(dict(offset=start, data=base64.b64encode(image[start:i]).decode()))
    if len(image) > len(original):
        spec['writes'].append(dict(offset=len(original), data=base64.b64encode(image[len(original):]).decode()))
    assert apply_spec(original, spec) == image
    return spec

def patch_segments(spec, writes, source):
    segments = copy.deepcopy(spec['segments'])
    for w in sorted(writes, key=lambda x:x['offset']):
        position = 0; patched = False
        old, new = struct.pack('<f', w['before']), struct.pack('<f', w['after'])
        for i, segment in enumerate(segments):
            data = base64.b64decode(segment['data']) if 'data' in segment else None
            size = len(data) if data is not None else segment['length']
            at = w['offset']-position
            if 0 <= at and at+4 <= size:
                if data is not None:
                    assert data[at:at+4] == old
                    segment['data'] = base64.b64encode(data[:at]+new+data[at+4:]).decode()
                else:
                    with source.open('rb') as stream:
                        stream.seek(segment['offset']+at); assert stream.read(4) == old
                    split = []
                    if at: split.append(dict(offset=segment['offset'], length=at))
                    split.append(dict(data=base64.b64encode(new).decode()))
                    if at+4 < size: split.append(dict(offset=segment['offset']+at+4, length=size-at-4))
                    segments[i:i+1] = split
                patched = True
                break
            position += size
        assert patched, w
    spec['segments'] = segments
    spec['sha256'] = DATA_HASH

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--version', default='0.1.46-gameplay-fixes')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--managed-launcher', type=Path, required=True)
    p.add_argument('--compare-installed', action='store_true')
    args = p.parse_args()
    args.out.resolve().relative_to(ROOT.resolve())
    config = json.loads((ROOT/'patches/release/current.json').read_text())
    archive = signed_baseline(args.baseline)
    manifest = json.loads(archive.read('manifest.json'))
    original = (args.game/'empire.retail.dll').read_bytes()
    native = next(f for f in manifest['files'] if f['destination']=='empire.retail.dll')
    image = apply_spec(original, native)
    for path in config['engineRecipes']:
        recipe = json.loads((ROOT/path).read_text())
        image = apply_recipe(image, recipe)
        manifest['patches'].append(dict(id=recipe['id'], title=recipe['title']))
    assert sha(image) == ENGINE_HASH
    if args.compare_installed:
        assert image == (args.game/'UltimatePatch/empire.retail.dll').read_bytes(), 'Installed engine differs'
    manifest['files'][manifest['files'].index(native)] = engine_spec(original, image, native)
    data = next(f for f in manifest['files'] if f['destination']=='data/data.pack')
    patch_segments(data, config['dataWrites'], args.game/'data/data.pack')
    manifest['patches'].extend(config['dataPatches'])
    manifest['version'] = args.version
    manifest['minimumInstallerVersion'] = args.version
    manifest['createdUtc'] = '2026-11-07T00:00:00Z'
    manifest['signingKeyRotation'] = 'New installer required; old public key retained only for baseline provenance.'
    manager = args.managed_launcher.read_bytes()
    manifest['modManagerSha256'] = sha(manager)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'manifest.json').write_text(json.dumps(manifest, separators=(',',':'))+'\n')
    with zipfile.ZipFile(args.out/'package-payload.zip','w',zipfile.ZIP_DEFLATED) as target:
        for name, data in [('manifest.json',json.dumps(manifest,separators=(',',':')).encode()),
                           ('launcher.exe',archive.read('launcher.exe')),
                           ('mod-manager.exe',manager)]:
            info = zipfile.ZipInfo(name, (2026,11,7,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            target.writestr(info,data)
    (args.out/'empire.retail.dll').write_bytes(image)
    print(json.dumps(dict(baselineSignatureVerified=True, engineRecipes=len(config['engineRecipes']),
                         dataFloatWrites=len(config['dataWrites']), engineSha256=sha(image),
                         engineMatchesInstalled=True if args.compare_installed else None,
                         payload=str(args.out/'package-payload.zip'))))

if __name__ == '__main__':
    main()
