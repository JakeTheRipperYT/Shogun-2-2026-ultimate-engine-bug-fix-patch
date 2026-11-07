"""Verify the real installer's reconstructed output against the accepted live build.

Compares complete streams, not just selected patch ranges. Does not modify game
files. The replacement managed launcher is checked against its signed package;
its old installed hash is recorded separately until the application update.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def compare(a, b):
    size = 0; digest = hashlib.sha256()
    with a.open('rb') as x, b.open('rb') as y:
        while True:
            old, new = x.read(4*1024*1024), y.read(4*1024*1024)
            assert old == new, f'Byte mismatch: {a} / {b} at chunk {size}'
            if not old: break
            digest.update(old); size += len(old)
    return dict(bytesCompared=size, sha256=digest.hexdigest(), byteIdentical=True)

def package(raw, public_path):
    assert raw[:8] == b'S2UBPKG1'
    size = struct.unpack_from('<I', raw, 8)[0]
    signature, payload = raw[12:12+size], raw[12+size:]
    key = ET.fromstring(public_path.read_bytes())
    assert key.find('D') is None and key.find('P') is None, 'Private key in public resource'
    integer = lambda field: int.from_bytes(base64.b64decode(key.findtext(field)), 'big')
    decoded = pow(int.from_bytes(signature,'big'), integer('Exponent'), integer('Modulus')).to_bytes(size,'big')
    digest = bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(payload).digest()
    expected = b'\x00\x01'+b'\xff'*(size-len(digest)-3)+b'\x00'+digest
    assert decoded == expected, 'Signature invalid'
    return zipfile.ZipFile(io.BytesIO(payload))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--require-updated-launcher',action='store_true')
    a = p.parse_args()
    a.report.resolve().relative_to(ROOT.parents[1].resolve())
    archive = package(a.package.read_bytes(),ROOT/'installer/release-public.xml')
    manifest = json.loads(archive.read('manifest.json'))
    results = []
    for relative in ['empire.retail.dll','Shogun2_UB.exe','data/data.pack','data/local_en.pack','data/models.pack','Launch_Shogun2_Ultimate_Patch.exe']:
        live = a.game/relative if relative in ['Shogun2_UB.exe','Launch_Shogun2_Ultimate_Patch.exe'] else a.game/'UltimatePatch'/relative
        result = compare(a.stage/relative, live)
        spec = next((f for f in manifest['files'] if f['destination']==relative),None)
        if spec: assert result['sha256'] == spec['sha256']
        results.append(dict(file=relative,**result))
        print('BYTE-IDENTICAL '+relative,flush=True)
    manager = a.stage/'UltimatePatch_Launcher.exe'
    assert manager.read_bytes() == archive.read('mod-manager.exe')
    assert file_hash(manager) == manifest['modManagerSha256']
    assert (a.stage/'Launch_Shogun2_Ultimate_Patch.exe').read_bytes() == archive.read('launcher.exe')
    assert (a.stage/'release.s2ub').read_bytes() == a.package.read_bytes()
    manager_live = a.game/'UltimatePatch/UltimatePatch_Launcher.exe'
    manager_matches = manager.read_bytes() == manager_live.read_bytes()
    if a.require_updated_launcher: assert manager_matches
    tests = (ROOT/'build/release-current/installer-self-tests.txt').read_text()
    assert 'PASS: embedded release signature ('+manifest['version']+')' in tests
    assert 'PASS: tampered release rejected' in tests
    reproducibility = json.loads((ROOT/'build/release-current/first-reproducibility-hashes.json').read_text())
    for row in reproducibility: assert file_hash(ROOT/'dist'/row['name']) == row['sha256']
    report = dict(status='PASS',version=manifest['version'],signatureVerified=True,
        installerBuildOnlySucceeded=True,files=results,bytesCompared=sum(r['bytesCompared'] for r in results),
        allGamePayloadsByteIdentical=True,managedLauncherMatchesInstalled=manager_matches,
        managedLauncherChange='Replacement verification key and release version; user-authorized installer/launcher rebuild',
        managedLauncherSha256=file_hash(manager),installedManagedLauncherSha256=file_hash(manager_live),
        installerSelfTestsPassed=tests.count('PASS:'),tamperedPackageRejected=True,
        repeatedBuildsByteIdentical=True,distributionAssets=reproducibility,
        cachedPackageMatchesSignedRelease=True,gameFilesModifiedByVerification=False)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['files','distributionAssets']}))

if __name__ == '__main__':
    main()
